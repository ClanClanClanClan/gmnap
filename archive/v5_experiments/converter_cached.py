from functools import lru_cache
import logging
from .converter_with_backoff import convert_with_backoff
from concurrent.futures import ThreadPoolExecutor
import time

logger = logging.getLogger(__name__)

@lru_cache(maxsize=10000)
def convert_cached(romanized):
    """Cache frequent conversions"""
    return convert_with_backoff(romanized)

def convert_batch(names, batch_size=100):
    """Process names in batches"""
    results = []
    for i in range(0, len(names), batch_size):
        batch = names[i:i+batch_size]
        # Process batch in parallel
        batch_results = parallel_convert(batch)
        results.extend(batch_results)
    return results

def parallel_convert(names, max_workers=4):
    """Convert names in parallel threads"""
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(convert_cached, names))
    return results

class PerformanceMonitor:
    """Monitor conversion performance metrics"""
    
    def __init__(self):
        self.conversion_times = []
        self.cache_hits = 0
        self.cache_misses = 0
    
    def time_conversion(self, func, *args, **kwargs):
        """Time a conversion and record metrics"""
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        
        duration_ms = (end_time - start_time) * 1000
        self.conversion_times.append(duration_ms)
        
        return result, duration_ms
    
    def get_p95_latency(self):
        """Calculate P95 latency"""
        if not self.conversion_times:
            return 0
        sorted_times = sorted(self.conversion_times)
        p95_index = int(0.95 * len(sorted_times))
        return sorted_times[p95_index]
    
    def get_cache_hit_rate(self):
        """Calculate cache hit rate"""
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0
        return self.cache_hits / total
    
    def record_cache_hit(self):
        """Record a cache hit"""
        self.cache_hits += 1
    
    def record_cache_miss(self):
        """Record a cache miss"""
        self.cache_misses += 1

# Global performance monitor
monitor = PerformanceMonitor()

def optimized_convert(romanized):
    """Optimized conversion with monitoring"""
    # Check cache first
    cache_info = convert_cached.cache_info()
    
    result, duration = monitor.time_conversion(convert_cached, romanized)
    
    # Record cache metrics
    if cache_info.hits < convert_cached.cache_info().hits:
        monitor.record_cache_hit()
    else:
        monitor.record_cache_miss()
    
    # Log performance warning if slow
    if duration > 120:  # P95 target <120ms
        logger.warning(f"Slow conversion: {romanized} took {duration:.1f}ms")
    
    return result