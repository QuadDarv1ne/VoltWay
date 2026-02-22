"""
Background tasks for periodic data updates and maintenance.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.station import Station
from app.services.external_api import ExternalAPIService
from app.utils.cache.manager import cache

logger = logging.getLogger(__name__)


class BackgroundTaskManager:
    """Manager for background tasks"""
    
    def __init__(self):
        self.tasks: list[asyncio.Task] = []
        self.running = False
        self.external_api = ExternalAPIService()
    
    async def start(self):
        """Start all background tasks"""
        if self.running:
            logger.warning("Background tasks already running")
            return
        
        self.running = True
        logger.info("Starting background tasks")
        
        # Start periodic tasks
        self.tasks.append(
            asyncio.create_task(self._periodic_station_update())
        )
        self.tasks.append(
            asyncio.create_task(self._periodic_cache_cleanup())
        )
        self.tasks.append(
            asyncio.create_task(self._periodic_health_check())
        )
    
    async def stop(self):
        """Stop all background tasks"""
        if not self.running:
            return
        
        logger.info("Stopping background tasks")
        self.running = False
        
        # Cancel all tasks
        for task in self.tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.tasks.clear()
    
    async def _periodic_station_update(self):
        """
        Periodically update station data from external APIs.
        Runs every 6 hours.
        """
        interval = 6 * 60 * 60  # 6 hours
        
        while self.running:
            try:
                logger.info("Starting periodic station update")
                await self._update_stations()
                logger.info("Periodic station update completed")
            except Exception as e:
                logger.error(f"Error in periodic station update: {e}", exc_info=True)
            
            # Wait for next interval
            await asyncio.sleep(interval)
    
    async def _update_stations(self):
        """Update station data from external APIs"""
        async with AsyncSessionLocal() as db:
            try:
                # Get stations that haven't been updated in the last 24 hours
                cutoff_time = datetime.utcnow() - timedelta(hours=24)
                result = await db.execute(
                    select(Station).where(Station.last_updated < cutoff_time)
                )
                stale_stations = result.scalars().all()
                
                logger.info(f"Found {len(stale_stations)} stations to update")
                
                # Update in batches
                batch_size = 10
                for i in range(0, len(stale_stations), batch_size):
                    batch = stale_stations[i:i + batch_size]
                    
                    for station in batch:
                        try:
                            # Fetch updated data from external API
                            # This is a placeholder - implement actual API call
                            station.last_updated = datetime.utcnow()
                            
                            # Clear cache for this station
                            cache.delete(f"station:{station.id}")
                        except Exception as e:
                            logger.error(f"Error updating station {station.id}: {e}")
                    
                    await db.commit()
                    
                    # Small delay between batches to avoid rate limiting
                    await asyncio.sleep(1)
                
                logger.info(f"Updated {len(stale_stations)} stations")
                
            except Exception as e:
                logger.error(f"Error in station update: {e}", exc_info=True)
                await db.rollback()
    
    async def _periodic_cache_cleanup(self):
        """
        Periodically clean up expired cache entries.
        Runs every hour.
        """
        interval = 60 * 60  # 1 hour
        
        while self.running:
            try:
                logger.info("Starting periodic cache cleanup")
                
                # Get cache stats before cleanup
                stats_before = cache.stats()
                
                # Cleanup is handled by the cache manager itself
                # Just log the stats
                logger.info(f"Cache stats: {stats_before}")
                
            except Exception as e:
                logger.error(f"Error in periodic cache cleanup: {e}", exc_info=True)
            
            await asyncio.sleep(interval)
    
    async def _periodic_health_check(self):
        """
        Periodically check system health and log metrics.
        Runs every 5 minutes.
        """
        interval = 5 * 60  # 5 minutes
        
        while self.running:
            try:
                async with AsyncSessionLocal() as db:
                    # Check database connectivity
                    await db.execute(select(1))
                    
                    # Get station count
                    result = await db.execute(select(Station))
                    station_count = len(result.scalars().all())
                    
                    # Log health metrics
                    logger.info(
                        "Health check",
                        extra={
                            "station_count": station_count,
                            "cache_stats": cache.stats(),
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )
                
            except Exception as e:
                logger.error(f"Error in health check: {e}", exc_info=True)
            
            await asyncio.sleep(interval)


# Global instance
background_task_manager = BackgroundTaskManager()
