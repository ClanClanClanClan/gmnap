from prometheus_client import Counter, Histogram, Gauge
import time
import psutil
import os

# Prometheus metrics
conversion_latency = Histogram('korean_conv_latency_ms', 'Conversion latency in milliseconds')
conversion_errors = Counter('korean_conv_errors_total', 'Total conversion errors')
accuracy_gauge = Gauge('korean_roundtrip_accuracy', 'Current round-trip accuracy')
cache_hit_rate = Gauge('korean_cache_hit_rate', 'Cache hit rate')
memory_usage = Gauge('korean_memory_usage_mb', 'Memory usage in MB')
throughput_gauge = Gauge('korean_throughput_per_sec', 'Conversions per second')

class MetricsCollector:
    """Collect and report performance metrics"""
    
    def __init__(self):
        self.start_time = time.time()
        self.conversion_count = 0
        self.error_count = 0
    
    def record_conversion(self, duration_ms, success=True):
        """Record a conversion attempt"""
        conversion_latency.observe(duration_ms)
        self.conversion_count += 1
        
        if not success:
            conversion_errors.inc()
            self.error_count += 1
    
    def update_accuracy(self, accuracy_score):
        """Update current accuracy gauge"""
        accuracy_gauge.set(accuracy_score)
    
    def update_cache_metrics(self, hit_rate):
        """Update cache hit rate"""
        cache_hit_rate.set(hit_rate)
    
    def update_memory_usage(self):
        """Update memory usage metrics"""
        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / 1024 / 1024
        memory_usage.set(memory_mb)
        
        # Alert if memory exceeds 500MB target
        if memory_mb > 500:
            print(f"WARNING: Memory usage {memory_mb:.1f}MB exceeds 500MB target")
    
    def calculate_throughput(self):
        """Calculate current throughput"""
        elapsed = time.time() - self.start_time
        if elapsed > 0:
            throughput = self.conversion_count / elapsed
            throughput_gauge.set(throughput)
            return throughput
        return 0
    
    def get_performance_report(self):
        """Generate performance report"""
        throughput = self.calculate_throughput()
        memory_mb = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
        
        return {
            "total_conversions": self.conversion_count,
            "total_errors": self.error_count,
            "error_rate": self.error_count / max(self.conversion_count, 1),
            "throughput_per_sec": throughput,
            "memory_usage_mb": memory_mb,
            "uptime_seconds": time.time() - self.start_time
        }

# Global metrics collector
metrics = MetricsCollector()

def monitor_performance(func):
    """Decorator to monitor function performance"""
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        
        try:
            result = func(*args, **kwargs)
            success = True
        except Exception as e:
            result = None
            success = False
            raise
        finally:
            duration_ms = (time.perf_counter() - start_time) * 1000
            metrics.record_conversion(duration_ms, success)
            metrics.update_memory_usage()
        
        return result
    return wrapper