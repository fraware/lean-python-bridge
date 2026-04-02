# Multi-stage Docker build for lean-python-bridge
FROM ubuntu:22.04 AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    git \
    libgmp-dev \
    libzmq3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY lakefile.lean lake-manifest.json lean-toolchain ./
COPY lean/ lean/

RUN curl -fsSL https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh | sh -s -- -y \
    && export PATH="$HOME/.elan/bin:$PATH" \
    && elan default "$(tr -d '\r\n' < lean-toolchain)" \
    && lake build

# Stage 2: Runtime (Python server)
FROM python:3.11-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    libzmq5 \
    libgmp10 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

RUN useradd --create-home --shell /bin/bash app \
    && mkdir -p /app \
    && chown app:app /app

COPY python/requirements-runtime.lock.txt /tmp/
RUN pip install --no-cache-dir --require-hashes -r /tmp/requirements-runtime.lock.txt

COPY --from=builder /build/.lake /app/.lake
COPY --chown=app:app python/ /app/python/
COPY --chown=app:app monitoring/ /app/monitoring/
COPY --chown=app:app README.md /app/README.md
COPY --chown=app:app LICENSE /app/LICENSE

USER app
WORKDIR /app

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import zmq; ctx = zmq.Context(); sock = ctx.socket(zmq.REQ); sock.connect('tcp://127.0.0.1:5555'); sock.close(); ctx.term()" || exit 1

EXPOSE 5555 8000

CMD ["python", "python/src/server.py"]
