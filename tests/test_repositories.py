"""
Tests for repository layer.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.station import Station
from app.repositories.station import StationRepository


@pytest.mark.asyncio
async def test_station_repository_get(db_session: AsyncSession):
    """Test getting a station by ID"""
    repo = StationRepository()
    
    # Create test station
    station = Station(
        title="Test Station",
        address="123 Test St",
        latitude=55.7558,
        longitude=37.6173,
        connector_type="CCS",
        power_kw=50.0,
        status="available",
    )
    db_session.add(station)
    await db_session.commit()
    await db_session.refresh(station)
    
    # Test get
    result = await repo.get(db_session, station.id)
    assert result is not None
    assert result.title == "Test Station"


@pytest.mark.asyncio
async def test_station_repository_get_by_location(db_session: AsyncSession):
    """Test getting stations by location"""
    repo = StationRepository()
    
    # Create test stations
    station1 = Station(
        title="Nearby Station",
        address="123 Test St",
        latitude=55.7558,
        longitude=37.6173,
        connector_type="CCS",
        power_kw=50.0,
        status="available",
    )
    station2 = Station(
        title="Far Station",
        address="456 Far St",
        latitude=56.0,
        longitude=38.0,
        connector_type="Type 2",
        power_kw=22.0,
        status="available",
    )
    db_session.add_all([station1, station2])
    await db_session.commit()
    
    # Test location query (5km radius should only get station1)
    results = await repo.get_by_location(
        db_session,
        latitude=55.7558,
        longitude=37.6173,
        radius_km=5.0,
    )
    
    assert len(results) == 1
    assert results[0].title == "Nearby Station"


@pytest.mark.asyncio
async def test_station_repository_get_by_filters(db_session: AsyncSession):
    """Test getting stations with filters"""
    repo = StationRepository()
    
    # Create test stations
    station1 = Station(
        title="CCS Station",
        address="123 Test St",
        latitude=55.7558,
        longitude=37.6173,
        connector_type="CCS",
        power_kw=50.0,
        status="available",
    )
    station2 = Station(
        title="Type 2 Station",
        address="456 Test St",
        latitude=55.7560,
        longitude=37.6175,
        connector_type="Type 2",
        power_kw=22.0,
        status="occupied",
    )
    db_session.add_all([station1, station2])
    await db_session.commit()
    
    # Test connector type filter
    results = await repo.get_by_filters(
        db_session,
        connector_type="CCS",
    )
    assert len(results) == 1
    assert results[0].connector_type == "CCS"
    
    # Test power filter
    results = await repo.get_by_filters(
        db_session,
        min_power_kw=40.0,
    )
    assert len(results) == 1
    assert results[0].power_kw >= 40.0
    
    # Test status filter
    results = await repo.get_by_filters(
        db_session,
        status="available",
    )
    assert len(results) == 1
    assert results[0].status == "available"
