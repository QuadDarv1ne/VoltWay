"""
Advanced analytics and insights engine for VoltWay.

Provides:
- Usage analytics and statistics
- Popular stations identification
- Peak hour analysis
- Trend analysis
- User behavior insights
- Revenue analytics
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict
import statistics

logger = logging.getLogger(__name__)


@dataclass
class UsageStats:
    """Usage statistics for a station or time period."""

    total_visits: int = 0
    unique_visitors: int = 0
    peak_hour: Optional[int] = None
    peak_day: Optional[str] = None
    avg_visit_duration_minutes: float = 0
    total_charging_time_minutes: float = 0
    revenue: float = 0
    rating: float = 0
    reviews_count: int = 0


@dataclass
class AnalyticsEvent:
    """Single analytics event."""

    event_type: str  # "visit", "charge", "favorite", etc
    station_id: int
    user_id: int
    timestamp: datetime
    duration_minutes: float = 0
    amount_spent: float = 0
    metadata: Dict[str, Any] = None


class AnalyticsEngine:
    """Centralized analytics processing engine."""

    def __init__(self):
        """Initialize analytics engine."""
        self.events: List[AnalyticsEvent] = []
        self.cache: Dict[str, Any] = {}

    def record_event(self, event: AnalyticsEvent) -> None:
        """Record analytics event."""
        self.events.append(event)
        self._invalidate_cache()

    def record_events(self, events: List[AnalyticsEvent]) -> None:
        """Record multiple events in batch."""
        self.events.extend(events)
        self._invalidate_cache()

    def _invalidate_cache(self) -> None:
        """Invalidate cached analytics."""
        self.cache.clear()

    def get_station_stats(self, station_id: int) -> UsageStats:
        """Get usage statistics for a station."""
        cache_key = f"station_stats:{station_id}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        station_events = [e for e in self.events if e.station_id == station_id]

        stats = UsageStats()
        stats.total_visits = len(station_events)
        stats.unique_visitors = len(set(e.user_id for e in station_events))

        if station_events:
            stats.peak_hour = self._get_peak_hour(station_events)
            stats.peak_day = self._get_peak_day(station_events)
            stats.avg_visit_duration_minutes = statistics.mean(
                e.duration_minutes for e in station_events if e.duration_minutes
            )
            stats.total_charging_time_minutes = sum(
                e.duration_minutes for e in station_events
            )
            stats.revenue = sum(e.amount_spent for e in station_events)

        self.cache[cache_key] = stats
        return stats

    def get_user_stats(self, user_id: int) -> UsageStats:
        """Get usage statistics for a user."""
        cache_key = f"user_stats:{user_id}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        user_events = [e for e in self.events if e.user_id == user_id]

        stats = UsageStats()
        stats.total_visits = len(user_events)
        stats.unique_visitors = 1  # User themselves
        stats.total_charging_time_minutes = sum(
            e.duration_minutes for e in user_events
        )
        stats.revenue = sum(e.amount_spent for e in user_events)

        if user_events:
            stats.avg_visit_duration_minutes = statistics.mean(
                e.duration_minutes for e in user_events if e.duration_minutes
            )

        self.cache[cache_key] = stats
        return stats

    def get_popular_stations(
        self, limit: int = 10, time_days: int = 30
    ) -> List[Tuple[int, int]]:
        """Get most popular stations by visit count."""
        cache_key = f"popular_stations:{limit}:{time_days}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        cutoff_date = datetime.utcnow() - timedelta(days=time_days)
        recent_events = [e for e in self.events if e.timestamp >= cutoff_date]

        visit_counts = defaultdict(int)
        for event in recent_events:
            if event.event_type == "visit":
                visit_counts[event.station_id] += 1

        popular = sorted(visit_counts.items(), key=lambda x: x[1], reverse=True)[
            :limit
        ]
        self.cache[cache_key] = popular
        return popular

    def get_peak_hours(self, time_days: int = 7) -> Dict[int, int]:
        """Get peak hours across all stations."""
        cache_key = f"peak_hours:{time_days}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        cutoff_date = datetime.utcnow() - timedelta(days=time_days)
        recent_events = [e for e in self.events if e.timestamp >= cutoff_date]

        hour_counts = defaultdict(int)
        for event in recent_events:
            hour = event.timestamp.hour
            hour_counts[hour] += 1

        self.cache[cache_key] = dict(hour_counts)
        return dict(hour_counts)

    def get_peak_days(self, time_weeks: int = 4) -> Dict[str, int]:
        """Get peak days of week."""
        cache_key = f"peak_days:{time_weeks}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        cutoff_date = datetime.utcnow() - timedelta(weeks=time_weeks)
        recent_events = [e for e in self.events if e.timestamp >= cutoff_date]

        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        day_counts = defaultdict(int)

        for event in recent_events:
            day_of_week = event.timestamp.weekday()
            day_name = day_names[day_of_week]
            day_counts[day_name] += 1

        self.cache[cache_key] = dict(day_counts)
        return dict(day_counts)

    def get_revenue_analytics(self, time_days: int = 30) -> Dict[str, Any]:
        """Get revenue analytics."""
        cache_key = f"revenue:{time_days}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        cutoff_date = datetime.utcnow() - timedelta(days=time_days)
        recent_events = [e for e in self.events if e.timestamp >= cutoff_date]

        revenue_data = [e.amount_spent for e in recent_events if e.amount_spent]

        analytics = {
            "total_revenue": sum(revenue_data),
            "avg_transaction": (
                statistics.mean(revenue_data) if revenue_data else 0
            ),
            "max_transaction": max(revenue_data) if revenue_data else 0,
            "min_transaction": min(revenue_data) if revenue_data else 0,
            "transaction_count": len(revenue_data),
        }

        if len(revenue_data) > 1:
            analytics["revenue_std_dev"] = statistics.stdev(revenue_data)

        self.cache[cache_key] = analytics
        return analytics

    def get_user_behavior(self, user_id: int) -> Dict[str, Any]:
        """Get detailed user behavior profile."""
        cache_key = f"user_behavior:{user_id}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        user_events = [e for e in self.events if e.user_id == user_id]

        if not user_events:
            return {}

        favorite_stations = defaultdict(int)
        for event in user_events:
            if event.event_type == "visit":
                favorite_stations[event.station_id] += 1

        behavior = {
            "total_visits": len(user_events),
            "favorite_stations": dict(
                sorted(favorite_stations.items(), key=lambda x: x[1], reverse=True)[:5]
            ),
            "avg_session_duration": statistics.mean(
                e.duration_minutes for e in user_events if e.duration_minutes
            ),
            "total_spent": sum(e.amount_spent for e in user_events),
            "first_visit": min(e.timestamp for e in user_events),
            "last_visit": max(e.timestamp for e in user_events),
        }

        self.cache[cache_key] = behavior
        return behavior

    def get_trend_analysis(self, time_days: int = 30) -> Dict[str, List[float]]:
        """Get trend analysis over time."""
        cache_key = f"trends:{time_days}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        cutoff_date = datetime.utcnow() - timedelta(days=time_days)
        recent_events = [e for e in self.events if e.timestamp >= cutoff_date]

        daily_visits = defaultdict(int)
        daily_revenue = defaultdict(float)

        for event in recent_events:
            date = event.timestamp.date()
            daily_visits[date] += 1
            daily_revenue[date] += event.amount_spent

        trends = {
            "daily_visits": [count for _, count in sorted(daily_visits.items())],
            "daily_revenue": [
                revenue for _, revenue in sorted(daily_revenue.items())
            ],
        }

        self.cache[cache_key] = trends
        return trends

    def get_station_comparison(self, station_ids: List[int]) -> Dict[int, Dict]:
        """Compare multiple stations side by side."""
        comparison = {}
        for station_id in station_ids:
            comparison[station_id] = {
                "stats": self.get_station_stats(station_id),
                "popular": station_id in [s[0] for s in self.get_popular_stations(100)],
            }
        return comparison

    def _get_peak_hour(self, events: List[AnalyticsEvent]) -> int:
        """Find peak hour from events."""
        hour_counts = defaultdict(int)
        for event in events:
            hour_counts[event.timestamp.hour] += 1
        return max(hour_counts, key=hour_counts.get) if hour_counts else 0

    def _get_peak_day(self, events: List[AnalyticsEvent]) -> str:
        """Find peak day from events."""
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        day_counts = defaultdict(int)
        for event in events:
            day_of_week = event.timestamp.weekday()
            day_counts[day_names[day_of_week]] += 1
        return max(day_counts, key=day_counts.get) if day_counts else "Unknown"


class RecommendationEngine:
    """Generate personalized recommendations."""

    def __init__(self, analytics_engine: AnalyticsEngine):
        """Initialize recommendation engine."""
        self.analytics = analytics_engine

    def recommend_stations(self, user_id: int, limit: int = 5) -> List[int]:
        """Recommend stations for a user."""
        user_stats = self.analytics.get_user_stats(user_id)
        popular_stations = self.analytics.get_popular_stations(limit=limit * 2)

        # Filter out already visited
        user_events = [
            e
            for e in self.analytics.events
            if e.user_id == user_id and e.event_type == "visit"
        ]
        visited_stations = set(e.station_id for e in user_events)

        recommendations = [
            station_id
            for station_id, _ in popular_stations
            if station_id not in visited_stations
        ]

        return recommendations[:limit]

    def get_personalized_insights(self, user_id: int) -> Dict[str, Any]:
        """Get personalized insights for user."""
        behavior = self.analytics.get_user_behavior(user_id)

        insights = {
            "usage_level": self._categorize_usage(behavior.get("total_visits", 0)),
            "next_recommendations": self.recommend_stations(user_id, limit=3),
            "spending_pattern": self._analyze_spending(behavior.get("total_spent", 0)),
        }

        return insights

    def _categorize_usage(self, visit_count: int) -> str:
        """Categorize user usage level."""
        if visit_count == 0:
            return "new_user"
        elif visit_count < 5:
            return "casual"
        elif visit_count < 20:
            return "regular"
        else:
            return "power_user"

    def _analyze_spending(self, total_spent: float) -> str:
        """Analyze spending pattern."""
        if total_spent < 10:
            return "low_spender"
        elif total_spent < 100:
            return "average_spender"
        else:
            return "high_value_customer"


__all__ = [
    "UsageStats",
    "AnalyticsEvent",
    "AnalyticsEngine",
    "RecommendationEngine",
]
