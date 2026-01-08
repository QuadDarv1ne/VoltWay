import time
from functools import wraps
from typing import Callable, Any

import logging

logger = logging.getLogger(__name__)


class QueryProfiler:
    """Simple query profiler to measure database query performance"""
    
    def __init__(self):
        self.queries = []
    
    def profile(self, func: Callable) -> Callable:
        """Decorator to profile function execution time"""
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                self._log_query(func.__name__, execution_time, args, kwargs)
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                self._log_query(func.__name__, execution_time, args, kwargs, error=str(e))
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                self._log_query(func.__name__, execution_time, args, kwargs)
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                self._log_query(func.__name__, execution_time, args, kwargs, error=str(e))
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    def _log_query(self, func_name: str, execution_time: float, args: tuple, kwargs: dict, error: str = None):
        """Log query performance data"""
        log_entry = {
            'function': func_name,
            'execution_time': execution_time,
            'args_count': len(args),
            'kwargs_keys': list(kwargs.keys()),
            'timestamp': time.time()
        }
        
        if error:
            log_entry['error'] = error
            logger.warning(f"Slow query in {func_name}: {execution_time:.4f}s - Error: {error}")
        elif execution_time > 1.0:  # Log queries taking more than 1 second
            logger.warning(f"Slow query in {func_name}: {execution_time:.4f}s")
        else:
            logger.debug(f"Query {func_name} executed in {execution_time:.4f}s")
        
        self.queries.append(log_entry)
    
    def get_stats(self) -> dict:
        """Get performance statistics"""
        if not self.queries:
            return {}
        
        execution_times = [q['execution_time'] for q in self.queries if 'error' not in q]
        if not execution_times:
            return {'total_queries': len(self.queries), 'errors': len([q for q in self.queries if 'error' in q])}
        
        return {
            'total_queries': len(self.queries),
            'successful_queries': len(execution_times),
            'average_time': sum(execution_times) / len(execution_times),
            'max_time': max(execution_times),
            'min_time': min(execution_times),
            'slow_queries': len([t for t in execution_times if t > 1.0]),
            'errors': len([q for q in self.queries if 'error' in q])
        }
    
    def clear(self):
        """Clear collected query data"""
        self.queries.clear()


# Global profiler instance
query_profiler = QueryProfiler()