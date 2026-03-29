import os


def setup_gmnap_streaming():
    """Auto-enable GMNAP streaming patch if GMNAP_STREAMING=1"""
    if os.getenv("GMNAP_STREAMING") == "1":
        try:
            from src.core.patch.pipeline_v7_integration_patch import enable_streaming_patch

            chunk = int(os.getenv("GMNAP_CHUNK", "2000"))
            inflight = int(os.getenv("GMNAP_INFLIGHT", "4"))
            threshold = int(os.getenv("GMNAP_STREAM_THRESHOLD", "10000"))
            retries = int(os.getenv("GMNAP_RETRIES", "1"))

            enable_streaming_patch(
                chunk=chunk, inflight=inflight, threshold=threshold, retries=retries
            )
        except Exception:
            pass  # Silently ignore if components aren't available yet


# Auto-run on import
setup_gmnap_streaming()
