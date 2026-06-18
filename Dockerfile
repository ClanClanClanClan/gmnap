# Multi-stage build — round 34 phase 3.
#
# Stage 1 (builder) compiles the fastText CLI from source (the
# fasttext-wheel hits OOM under g++ in Docker; the official binary
# is the canonical path for the surname classifier per
# scripts/install_fasttext.sh).
#
# Stage 2 (runtime) starts fresh from slim, copies in only the
# fasttext binary + the Python deps + the app source. Drops
# build-essential, git, libicu-dev, and the fastText git checkout
# from the final image — saves ~250 MB and shrinks the CVE surface
# (build tools are common targets in container scans).
#
# Layer ordering: requirements → source (so a code-only change
# doesn't invalidate the heavy dep-install layer).

FROM python:3.12-slim AS builder

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        git \
    && rm -rf /var/lib/apt/lists/*

# Compile fastText (346 KB binary; ~30 s build)
RUN git clone --depth 1 https://github.com/facebookresearch/fastText.git /tmp/fasttext-build \
    && cd /tmp/fasttext-build && make -j"$(nproc)" \
    && cp /tmp/fasttext-build/fasttext /usr/local/bin/fasttext


FROM python:3.12-slim AS runtime

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/src:/app

# Runtime-only system deps. libicu-dev was here for `icu` Python
# wheel which we no longer require (round-34 dep prune).
RUN apt-get update && apt-get install -y --no-install-recommends \
        zstd \
        sqlite3 \
        curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Bring the compiled fastText binary across
COPY --from=builder /usr/local/bin/fasttext /usr/local/bin/fasttext

WORKDIR /app

# Install Python deps first (cache layer)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Then the app source
COPY . .

RUN mkdir -p /app/cache/gs /app/cache/bad_json /app/data

# Non-root runtime user (defense in depth — limits blast radius if
# a request handler ever lands a write-anywhere bug).
RUN useradd --create-home --shell /bin/false --uid 1000 gmnap \
    && chown -R gmnap:gmnap /app
USER gmnap

EXPOSE 8080

# Healthcheck calls /healthz (cheap process-alive probe).
# Compose / k8s use /readyz separately for routing decisions.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8080/healthz > /dev/null || exit 1

# uvicorn's --timeout-graceful-shutdown coordinates with the
# docker-compose stop_grace_period (120 s) and the lifespan
# shutdown hook in src/api/server.py — together they drain
# in-flight requests on SIGTERM rather than dropping them.
CMD ["python3", "-m", "uvicorn", "src.api.server:app", \
     "--host", "0.0.0.0", \
     "--port", "8080", \
     "--timeout-graceful-shutdown", "60"]
