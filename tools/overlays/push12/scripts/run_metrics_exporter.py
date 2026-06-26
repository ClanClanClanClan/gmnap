#!/usr/bin/env python3
import os
import time

from prometheus_client import start_http_server

if __name__ == "__main__":
    port = int(os.getenv("GMNAP_METRICS_PORT", "9308"))
    start_http_server(port)
    print(f"Prometheus metrics exporter listening on :{port}")
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        pass
