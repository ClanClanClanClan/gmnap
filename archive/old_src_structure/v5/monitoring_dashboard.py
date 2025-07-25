#!/usr/bin/env python3
"""
Monitoring dashboard for Korean V5 converter
Implements success metrics from blueprint Phase 15
"""

from prometheus_client import Counter, Histogram, Gauge, start_http_server
import time
import json
import yaml
import psutil
import os
from datetime import datetime, timedelta
import threading

# Metrics from blueprint lines 913-926
conversion_latency = Histogram('korean_conv_latency_ms', 'Conversion latency in milliseconds')
conversion_errors = Counter('korean_conv_errors_total', 'Total conversion errors')
accuracy_gauge = Gauge('korean_roundtrip_accuracy', 'Current round-trip accuracy')
cache_hit_rate = Gauge('korean_cache_hit_rate', 'Cache hit rate')
memory_usage = Gauge('korean_memory_usage_mb', 'Memory usage in MB')
throughput_gauge = Gauge('korean_throughput_per_sec', 'Conversions per second')

class KoreanMonitoringDashboard:
    """Monitoring dashboard for Korean V5 system"""
    
    def __init__(self, port=8090):
        self.port = port
        self.start_time = time.time()
        self.conversion_count = 0
        self.error_count = 0
        self.last_accuracy_check = 0
        self.running = False
    
    def start(self):
        """Start the monitoring dashboard"""
        print(f"Starting Korean monitoring dashboard on port {self.port}")
        
        # Start Prometheus metrics server
        start_http_server(self.port)
        
        # Start background monitoring thread
        self.running = True
        monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        monitor_thread.start()
        
        print(f"✅ Dashboard running at http://localhost:{self.port}/metrics")
    
    def stop(self):
        """Stop the monitoring dashboard"""
        self.running = False
    
    def _monitor_loop(self):
        """Background monitoring loop"""
        while self.running:
            try:
                # Update memory usage
                self._update_memory_metrics()
                
                # Update throughput
                self._update_throughput_metrics()
                
                # Check accuracy periodically (every hour)
                if time.time() - self.last_accuracy_check > 3600:
                    self._update_accuracy_metrics()
                    self.last_accuracy_check = time.time()
                
                # Sleep for 30 seconds
                time.sleep(30)
                
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
                time.sleep(60)  # Wait longer on error
    
    def _update_memory_metrics(self):
        """Update memory usage metrics"""
        try:
            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / 1024 / 1024
            memory_usage.set(memory_mb)
            
            # Log warning if exceeding target
            if memory_mb > 500:  # 500MB target from blueprint
                print(f"WARNING: Memory usage {memory_mb:.1f}MB exceeds 500MB target")
                
        except Exception as e:
            print(f"Error updating memory metrics: {e}")
    
    def _update_throughput_metrics(self):
        """Update throughput metrics"""
        try:
            elapsed = time.time() - self.start_time
            if elapsed > 0:
                throughput = self.conversion_count / elapsed
                throughput_gauge.set(throughput)
                
        except Exception as e:
            print(f"Error updating throughput metrics: {e}")
    
    def _update_accuracy_metrics(self):
        """Update accuracy metrics by running evaluation"""
        try:
            print("Running accuracy check...")
            
            # Import here to avoid circular imports
            import subprocess
            
            # Run evaluation script
            result = subprocess.run([
                "python", "scripts/evaluate_roundtrip.py",
                "-i", "data/korean.yaml",
                "-t", "0.97"
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                # Parse accuracy from output
                output_lines = result.stdout.strip().split('\n')
                for line in output_lines:
                    if "Overall accuracy:" in line:
                        # Extract percentage (e.g., "Overall accuracy: 97.2% (729/751)")
                        import re
                        match = re.search(r'(\d+\.?\d*)%', line)
                        if match:
                            accuracy = float(match.group(1)) / 100
                            accuracy_gauge.set(accuracy)
                            print(f"Updated accuracy gauge: {accuracy:.3f}")
                            break
            else:
                print(f"Accuracy check failed: {result.stderr}")
                
        except Exception as e:
            print(f"Error updating accuracy metrics: {e}")
    
    def record_conversion(self, duration_ms, success=True):
        """Record a conversion attempt"""
        conversion_latency.observe(duration_ms)
        self.conversion_count += 1
        
        if not success:
            conversion_errors.inc()
            self.error_count += 1
    
    def update_cache_hit_rate(self, hits, misses):
        """Update cache hit rate"""
        total = hits + misses
        if total > 0:
            hit_rate = hits / total
            cache_hit_rate.set(hit_rate)
    
    def get_current_metrics(self):
        """Get current metrics summary"""
        elapsed = time.time() - self.start_time
        throughput = self.conversion_count / elapsed if elapsed > 0 else 0
        
        try:
            memory_mb = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
        except:
            memory_mb = 0
        
        return {
            "uptime_seconds": elapsed,
            "total_conversions": self.conversion_count,
            "total_errors": self.error_count,
            "error_rate": self.error_count / max(self.conversion_count, 1),
            "throughput_per_sec": throughput,
            "memory_usage_mb": memory_mb,
            "timestamp": datetime.now().isoformat()
        }
    
    def daily_accuracy_check(self):
        """Daily accuracy check as specified in blueprint line 922-926"""
        try:
            # Run evaluation
            import subprocess
            result = subprocess.run([
                "python", "scripts/evaluate_roundtrip.py",
                "-i", "data/korean.yaml", 
                "-t", "0.97"
            ], capture_output=True, text=True, timeout=600)
            
            if result.returncode == 0:
                # Log success
                print(f"✅ Daily accuracy check passed")
                return True
            else:
                # Log failure and send alert
                print(f"❌ Daily accuracy check FAILED")
                print(result.stdout)
                print(result.stderr)
                
                # Could integrate with alerting system here
                # send_alert("Korean accuracy check failed")
                
                return False
                
        except Exception as e:
            print(f"Error in daily accuracy check: {e}")
            return False

# Global dashboard instance
dashboard = None

def start_monitoring(port=8090):
    """Start the global monitoring dashboard"""
    global dashboard
    if dashboard is None:
        dashboard = KoreanMonitoringDashboard(port)
        dashboard.start()
    return dashboard

def stop_monitoring():
    """Stop the global monitoring dashboard"""
    global dashboard
    if dashboard:
        dashboard.stop()
        dashboard = None

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Korean V5 Monitoring Dashboard")
    parser.add_argument("--port", type=int, default=8090, help="Metrics server port")
    parser.add_argument("--daily-check", action="store_true", help="Run daily accuracy check")
    
    args = parser.parse_args()
    
    if args.daily_check:
        # Run daily accuracy check
        dashboard_inst = KoreanMonitoringDashboard()
        success = dashboard_inst.daily_accuracy_check()
        exit(0 if success else 1)
    else:
        # Start dashboard server
        dashboard_inst = start_monitoring(args.port)
        
        try:
            print("Dashboard running. Press Ctrl+C to stop.")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping dashboard...")
            stop_monitoring()