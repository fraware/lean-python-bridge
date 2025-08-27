# Multi-stage Docker build for Lean-Python Bridge
# Stage 1: Builder stage for Lean and FFI compilation
FROM ubuntu:22.04 AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    wget \
    git \
    libgmp-dev \
    libzmq3-dev \
    build-essential \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install Lean 4
RUN wget https://github.com/leanprover/lean4/releases/download/v4.7.0/lean-4.7.0-linux.tar.gz \
    && tar -xzf lean-4.7.0-linux.tar.gz \
    && cp lean-4.7.0-linux/bin/lean /usr/local/bin/lean \
    && cp lean-4.7.0-linux/bin/leanc /usr/local/bin/leanc \
    && rm -rf lean-4.7.0-linux*

# Install Python dependencies for build
RUN pip3 install --no-cache-dir pyzmq numpy

# Copy source and build Lean project
WORKDIR /build
COPY lean/ lean/
RUN cd lean && lake build

# Stage 2: Runtime stage
FROM python:3.11-slim AS runtime

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libzmq5 \
    libgmp10 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && mkdir -p /app \
    && chown app:app /app

# Copy Python dependencies and install
COPY python/requirements.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy built Lean artifacts and Python source
COPY --from=builder /build/lean/.lake/build /app/lean/.lake/build
COPY python/ /app/python/
COPY --chown=app:app . /app/

# Switch to app user
USER app
WORKDIR /app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import zmq; ctx = zmq.Context(); sock = ctx.socket(zmq.REQ); sock.connect('tcp://127.0.0.1:5555'); sock.close(); ctx.term()" || exit 1

# Expose port
EXPOSE 5555

# Default command
CMD ["python", "python/src/server.py"]
