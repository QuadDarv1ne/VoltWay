import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from app.utils.cache import cache

logger = logging.getLogger(__name__)


class CacheCleanupManager:
    """Manages automatic cache cleanup based on various policies"""
    
    def __init__(self):
        self.cleanup_interval = 300  # 5 minutes
        self.max_cache_size = 1000   # Maximum number of cache entries
        self.max_memory_usage = 100 * 1024 * 1024  # 100MB
        self.running = False
        
    async def start_cleanup_scheduler(self):
        """Start the periodic cleanup scheduler"""
        if not cache.redis_client:
            logger.warning("Redis not available, cache cleanup scheduler not started")
            return
            
        self.running = True
        logger.info("Starting cache cleanup scheduler")
        
        while self.running:
            try:
                await self.perform_cleanup_cycle()
                await asyncio.sleep(self.cleanup_interval)
            except Exception as e:
                logger.error(f"Error in cache cleanup cycle: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    def stop_cleanup_scheduler(self):
        """Stop the cleanup scheduler"""
        self.running = False
        logger.info("Cache cleanup scheduler stopped")
    
    async def perform_cleanup_cycle(self):
        """Perform one cleanup cycle with multiple strategies"""
        if not cache.redis_client:
            return
            
        logger.debug("Starting cache cleanup cycle")
        
        # Strategy 1: Remove expired entries
        expired_cleaned = self._cleanup_expired_entries()
        
        # Strategy 2: Check cache size and trim if needed
        size_cleaned = await self._cleanup_by_size()
        
        # Strategy 3: Check memory usage and cleanup if needed
        memory_cleaned = await self._cleanup_by_memory()
        
        # Strategy 4: Cleanup old unused entries
        unused_cleaned = await self._cleanup_unused_entries()
        
        total_cleaned = expired_cleaned + size_cleaned + memory_cleaned + unused_cleaned
        
        if total_cleaned > 0:
            logger.info(f"Cache cleanup cycle completed: {total_cleaned} entries cleaned")
        else:
            logger.debug("Cache cleanup cycle completed: no entries cleaned")
    
    def _cleanup_expired_entries(self) -> int:
        """Remove expired cache entries (Redis handles this automatically, 
        but we can force cleanup of known patterns)"""
        try:
            # For station cache entries, we know they expire after 600 seconds
            # This is mainly for cleanup of any orphaned entries
            station_keys = cache.redis_client.keys("stations:*")
            cleaned_count = 0
            
            # Check TTL and remove entries with negative TTL (expired)
            for key in station_keys[:50]:  # Limit to prevent long operations
                ttl = cache.redis_client.ttl(key)
                if ttl == -2:  # Key doesn't exist
                    cleaned_count += 1
                elif ttl == -1:  # Key exists but no TTL
                    # Set appropriate TTL for station entries
                    cache.redis_client.expire(key, 600)
                    
            return cleaned_count
        except Exception as e:
            logger.error(f"Error cleaning expired entries: {e}")
            return 0
    
    async def _cleanup_by_size(self) -> int:
        """Clean up cache if it exceeds maximum size"""
        try:
            # Get all cache keys
            all_keys = cache.redis_client.keys("*")
            current_size = len(all_keys)
            
            if current_size <= self.max_cache_size:
                return 0
            
            # Need to clean up excess entries
            excess_count = current_size - self.max_cache_size
            logger.info(f"Cache size {current_size} exceeds limit {self.max_cache_size}, cleaning up {excess_count} entries")
            
            # Prioritize cleaning: stations cache first, then others
            cleaned_count = 0
            
            # Clean station cache entries
            station_keys = cache.redis_client.keys("stations:*")
            if len(station_keys) > 50:  # Keep at least 50 station entries
                # Sort by TTL (clean entries that expire sooner first)
                keys_with_ttl = []
                for key in station_keys:
                    ttl = cache.redis_client.ttl(key)
                    keys_with_ttl.append((key, ttl if ttl > 0 else float('inf')))
                
                # Sort by TTL ascending (shortest TTL first)
                keys_with_ttl.sort(key=lambda x: x[1])
                
                # Delete excess entries
                for i in range(min(excess_count, len(keys_with_ttl))):
                    cache.redis_client.delete(keys_with_ttl[i][0])
                    cleaned_count += 1
                    excess_count -= 1
            
            # If still need to clean more, clean other entries
            if excess_count > 0:
                other_keys = [k for k in all_keys if not k.startswith(b"stations:")]
                for i in range(min(excess_count, len(other_keys))):
                    cache.redis_client.delete(other_keys[i])
                    cleaned_count += 1
            
            return cleaned_count
        except Exception as e:
            logger.error(f"Error cleaning by size: {e}")
            return 0
    
    async def _cleanup_by_memory(self) -> int:
        """Clean up cache if memory usage is too high"""
        try:
            # Get memory info
            info = cache.redis_client.info()
            used_memory = info.get('used_memory', 0)
            
            if used_memory <= self.max_memory_usage:
                return 0
            
            logger.info(f"Memory usage {used_memory} exceeds limit {self.max_memory_usage}, performing cleanup")
            
            # Calculate how much memory to free (20% of excess)
            excess_memory = used_memory - self.max_memory_usage
            target_reduction = int(excess_memory * 0.2)
            
            # Get entries sorted by size (approximate)
            all_keys = cache.redis_client.keys("*")
            key_sizes = []
            
            for key in all_keys[:100]:  # Sample first 100 keys to estimate
                try:
                    value = cache.redis_client.get(key)
                    if value:
                        size = len(value)
                        key_sizes.append((key, size))
                except:
                    continue
            
            # Sort by size descending (largest first)
            key_sizes.sort(key=lambda x: x[1], reverse=True)
            
            # Delete largest entries until we meet target
            cleaned_count = 0
            freed_memory = 0
            
            for key, size in key_sizes:
                if freed_memory >= target_reduction:
                    break
                    
                cache.redis_client.delete(key)
                freed_memory += size
                cleaned_count += 1
            
            logger.info(f"Freed approximately {freed_memory} bytes by deleting {cleaned_count} entries")
            return cleaned_count
        except Exception as e:
            logger.error(f"Error cleaning by memory: {e}")
            return 0
    
    async def _cleanup_unused_entries(self) -> int:
        """Clean up entries that haven't been accessed recently"""
        try:
            # This is a simplified approach - in production, you might want
            # to track access times separately
            
            # For now, we'll clean up very old station entries
            # that are older than 1 hour (even if not expired)
            station_keys = cache.redis_client.keys("stations:*")
            cleaned_count = 0
            
            for key in station_keys[:20]:  # Limit to prevent long operations
                ttl = cache.redis_client.ttl(key)
                # If TTL is very long (> 3000 seconds), reduce it
                if ttl > 3000:
                    cache.redis_client.expire(key, 1800)  # Set to 30 minutes
                    cleaned_count += 1
            
            return cleaned_count
        except Exception as e:
            logger.error(f"Error cleaning unused entries: {e}")
            return 0
    
    def get_cleanup_stats(self) -> Dict:
        """Get current cleanup statistics"""
        if not cache.redis_client:
            return {"error": "Redis not available"}
        
        try:
            info = cache.redis_client.info()
            all_keys = cache.redis_client.keys("*")
            station_keys = cache.redis_client.keys("stations:*")
            
            return {
                "total_entries": len(all_keys),
                "station_entries": len(station_keys),
                "other_entries": len(all_keys) - len(station_keys),
                "memory_usage": info.get('used_memory_human', 'N/A'),
                "running": self.running,
                "cleanup_interval": self.cleanup_interval,
                "max_cache_size": self.max_cache_size,
                "max_memory_usage_mb": self.max_memory_usage / (1024 * 1024)
            }
        except Exception as e:
            return {"error": str(e)}


# Global cleanup manager instance
cleanup_manager = CacheCleanupManager()