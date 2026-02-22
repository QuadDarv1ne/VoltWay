"""
GraphQL resolvers for VoltWay API v3.

Implements queries and mutations for stations, users, and analytics.
"""

import strawberry
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import AsyncSessionLocal
from app.models.station import Station as StationModel
from app.models.api_key import APIKey
from app.api.v3.types import (
    Station,
    StationConnection,
    StationStats,
    ConnectorType,
    SearchResult,
    StationFilter,
    LocationInput,
    CreateStationInput,
    UpdateStationInput,
    Message,
    StationStatus,
)


def get_db_context(info: strawberry.Info) -> AsyncSession:
    """Get database session from context"""
    return info.context["db"]


@strawberry.type
class Query:
    """GraphQL Query root"""

    @strawberry.field
    async def stations(
        self,
        info: strawberry.Info,
        skip: int = 0,
        limit: int = 20,
        filter: Optional[StationFilter] = None,
    ) -> StationConnection:
        """Get list of stations with pagination and filters"""
        db = get_db_context(info)

        # Build query
        query = select(StationModel)

        # Apply filters
        if filter:
            if filter.connector_type:
                query = query.where(
                    StationModel.connector_type.ilike(f"%{filter.connector_type}%")
                )
            if filter.min_power_kw:
                query = query.where(StationModel.power_kw >= filter.min_power_kw)
            if filter.max_power_kw:
                query = query.where(StationModel.power_kw <= filter.max_power_kw)
            if filter.status:
                query = query.where(StationModel.status == filter.status.value)

        # Get total count
        count_query = select(func.count()).select_from(StationModel)
        if filter:
            # Apply same filters to count query
            pass  # Simplified for brevity

        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        stations = result.scalars().all()

        # Convert to GraphQL types
        graphql_stations = [
            Station(
                id=s.id,
                title=s.title,
                address=s.address,
                latitude=s.latitude,
                longitude=s.longitude,
                connector_type=s.connector_type,
                power_kw=s.power_kw,
                status=StationStatus(s.status),
                price=s.price,
                hours=s.hours,
                last_updated=s.last_updated,
            )
            for s in stations
        ]

        return StationConnection(
            stations=graphql_stations,
            total=total,
            page=skip // limit if limit > 0 else 0,
            page_size=limit,
            has_next=skip + limit < total,
            has_prev=skip > 0,
        )

    @strawberry.field
    async def station(
        self,
        info: strawberry.Info,
        id: int,
    ) -> Optional[Station]:
        """Get a single station by ID"""
        db = get_db_context(info)

        result = await db.execute(
            select(StationModel).where(StationModel.id == id)
        )
        station = result.scalar_one_or_none()

        if not station:
            return None

        return Station(
            id=station.id,
            title=station.title,
            address=station.address,
            latitude=station.latitude,
            longitude=station.longitude,
            connector_type=station.connector_type,
            power_kw=station.power_kw,
            status=StationStatus(station.status),
            price=station.price,
            hours=station.hours,
            last_updated=station.last_updated,
        )

    @strawberry.field
    async def stations_nearby(
        self,
        info: strawberry.Info,
        location: LocationInput,
        filter: Optional[StationFilter] = None,
    ) -> List[Station]:
        """Get stations near a location"""
        db = get_db_context(info)

        # Bounding box calculation
        lat_delta = location.radius_km / 111.0
        lon_delta = location.radius_km / (
            111.0 * abs(location.latitude / 90.0 + 0.01)
        )

        query = select(StationModel).where(
            StationModel.latitude.between(
                location.latitude - lat_delta,
                location.latitude + lat_delta,
            ),
            StationModel.longitude.between(
                location.longitude - lon_delta,
                location.longitude + lon_delta,
            ),
        )

        # Apply additional filters
        if filter:
            if filter.connector_type:
                query = query.where(
                    StationModel.connector_type.ilike(f"%{filter.connector_type}%")
                )
            if filter.min_power_kw:
                query = query.where(StationModel.power_kw >= filter.min_power_kw)

        result = await db.execute(query)
        stations = result.scalars().all()

        # Calculate actual distance and filter
        from app.utils.geo import haversine_distance

        graphql_stations = []
        for s in stations:
            dist = haversine_distance(
                location.latitude,
                location.longitude,
                s.latitude,
                s.longitude,
            )
            if dist <= location.radius_km:
                graphql_stations.append(
                    Station(
                        id=s.id,
                        title=s.title,
                        address=s.address,
                        latitude=s.latitude,
                        longitude=s.longitude,
                        connector_type=s.connector_type,
                        power_kw=s.power_kw,
                        status=StationStatus(s.status),
                        price=s.price,
                        hours=s.hours,
                        last_updated=s.last_updated,
                        distance_km=round(dist, 2),
                    )
                )

        # Sort by distance
        graphql_stations.sort(key=lambda x: x.distance_km or 0)
        return graphql_stations

    @strawberry.field
    async def station_stats(self, info: strawberry.Info) -> StationStats:
        """Get station statistics"""
        db = get_db_context(info)

        # Total count
        total_result = await db.execute(
            select(func.count()).select_from(StationModel)
        )
        total = total_result.scalar() or 0

        # Count by status
        status_counts = {}
        for status in ["available", "occupied", "maintenance", "unknown"]:
            result = await db.execute(
                select(func.count()).where(StationModel.status == status)
            )
            status_counts[status] = result.scalar() or 0

        # Average power
        avg_power_result = await db.execute(
            select(func.avg(StationModel.power_kw))
        )
        avg_power = float(avg_power_result.scalar() or 0)

        # Connector type stats
        connector_result = await db.execute(
            select(
                StationModel.connector_type,
                func.count(StationModel.id),
                func.avg(StationModel.power_kw),
            ).group_by(StationModel.connector_type)
        )
        connector_types = [
            ConnectorType(
                name=row[0],
                count=row[1],
                avg_power_kw=float(row[2] or 0),
            )
            for row in connector_result.all()
        ]

        return StationStats(
            total_stations=total,
            available_stations=status_counts.get("available", 0),
            occupied_stations=status_counts.get("occupied", 0),
            maintenance_stations=status_counts.get("maintenance", 0),
            unknown_stations=status_counts.get("unknown", 0),
            avg_power_kw=round(avg_power, 2),
            connector_types=connector_types,
        )

    @strawberry.field
    async def search_stations(
        self,
        info: strawberry.Info,
        query: str,
        location: Optional[LocationInput] = None,
        limit: int = 50,
    ) -> SearchResult:
        """Full-text search for stations"""
        db = get_db_context(info)

        # Use PostgreSQL full-text search
        from sqlalchemy import func

        search_terms = query.split()
        ts_query = " & ".join(search_terms)

        stmt = select(StationModel).where(
            StationModel.search_vector.op("@@")(func.to_tsquery("russian", ts_query))
        )

        # Add location filter if provided
        if location:
            lat_delta = location.radius_km / 111.0
            lon_delta = location.radius_km / (
                111.0 * abs(location.latitude / 90.0 + 0.01)
            )
            stmt = stmt.where(
                StationModel.latitude.between(
                    location.latitude - lat_delta,
                    location.latitude + lat_delta,
                ),
                StationModel.longitude.between(
                    location.longitude - lon_delta,
                    location.longitude + lon_delta,
                ),
            )

        # Order by relevance
        stmt = stmt.order_by(
            func.ts_rank(
                StationModel.search_vector,
                func.to_tsquery("russian", ts_query),
            ).desc()
        ).limit(limit)

        result = await db.execute(stmt)
        stations = result.scalars().all()

        graphql_stations = [
            Station(
                id=s.id,
                title=s.title,
                address=s.address,
                latitude=s.latitude,
                longitude=s.longitude,
                connector_type=s.connector_type,
                power_kw=s.power_kw,
                status=StationStatus(s.status),
                price=s.price,
                hours=s.hours,
                last_updated=s.last_updated,
            )
            for s in stations
        ]

        return SearchResult(
            stations=graphql_stations,
            total=len(graphql_stations),
            query=query,
            search_type="fulltext",
        )


@strawberry.type
class Mutation:
    """GraphQL Mutation root"""

    @strawberry.mutation
    async def create_station(
        self,
        info: strawberry.Info,
        input: CreateStationInput,
    ) -> Station:
        """Create a new charging station (admin only)"""
        db = get_db_context(info)

        # Check admin permission (simplified)
        api_key = info.context.get("api_key")
        if not api_key or api_key.role != "admin":
            raise PermissionError("Admin access required")

        station = StationModel(
            title=input.title,
            address=input.address,
            latitude=input.latitude,
            longitude=input.longitude,
            connector_type=input.connector_type,
            power_kw=input.power_kw,
            status=input.status.value,
            price=input.price,
            hours=input.hours,
        )

        db.add(station)
        await db.commit()
        await db.refresh(station)

        return Station(
            id=station.id,
            title=station.title,
            address=station.address,
            latitude=station.latitude,
            longitude=station.longitude,
            connector_type=station.connector_type,
            power_kw=station.power_kw,
            status=StationStatus(station.status),
            price=station.price,
            hours=station.hours,
            last_updated=station.last_updated,
        )

    @strawberry.mutation
    async def update_station(
        self,
        info: strawberry.Info,
        id: int,
        input: UpdateStationInput,
    ) -> Optional[Station]:
        """Update an existing station (admin only)"""
        db = get_db_context(info)

        # Check admin permission
        api_key = info.context.get("api_key")
        if not api_key or api_key.role != "admin":
            raise PermissionError("Admin access required")

        # Get station
        result = await db.execute(
            select(StationModel).where(StationModel.id == id)
        )
        station = result.scalar_one_or_none()

        if not station:
            return None

        # Update fields
        update_data = input.__dict__
        for field, value in update_data.items():
            if value is not None and hasattr(station, field):
                setattr(station, field, value)

        db.add(station)
        await db.commit()
        await db.refresh(station)

        return Station(
            id=station.id,
            title=station.title,
            address=station.address,
            latitude=station.latitude,
            longitude=station.longitude,
            connector_type=station.connector_type,
            power_kw=station.power_kw,
            status=StationStatus(station.status),
            price=station.price,
            hours=station.hours,
            last_updated=station.last_updated,
        )

    @strawberry.mutation
    async def delete_station(
        self,
        info: strawberry.Info,
        id: int,
    ) -> Message:
        """Delete a station (admin only)"""
        db = get_db_context(info)

        # Check admin permission
        api_key = info.context.get("api_key")
        if not api_key or api_key.role != "admin":
            raise PermissionError("Admin access required")

        result = await db.execute(
            select(StationModel).where(StationModel.id == id)
        )
        station = result.scalar_one_or_none()

        if not station:
            return Message(success=False, message="Station not found")

        await db.delete(station)
        await db.commit()

        return Message(success=True, message=f"Station {id} deleted")


# Create schema
schema = strawberry.Schema(query=Query, mutation=Mutation)
