# Lean-Python Bridge Quickstart Guide

## Overview

This guide will get you up and running with the Lean-Python bridge in under 30 minutes. The bridge enables formal verification in Lean 4 with high-performance numerical computation in Python via ZeroMQ.

## Prerequisites

- **Docker & Docker Compose** (recommended)
- **Python 3.11+** (if running locally)
- **Lean 4.7.0+** (if running locally)
- **ZeroMQ libraries** (if running locally)

## Quick Start with Docker (Recommended)

### 1. Clone and Setup (2 minutes)

```bash
git clone https://github.com/yourusername/lean-python-bridge.git
cd lean-python-bridge
```

### 2. Start Development Environment (3 minutes)

```bash
# Start development environment
docker-compose --profile dev up -d

# Check services
docker-compose ps
```

This starts:
- **Lean-Python Bridge Server** (port 5555)
- **Jupyter Notebook** (port 8888) - for testing and development

### 3. Test the Bridge (5 minutes)

```bash
# Test from command line
python -c "
import zmq
import json
context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.connect('tcp://localhost:5555')

# Send test matrix
data = {
    'schema_version': 1,
    'matrix': [[1, 2], [3, 4]],
    'model': {'name': 'TestModel', 'version': '1.0'}
}
socket.send_string(json.dumps(data))
response = socket.recv_string()
print('Response:', response)
"
```

Expected output:
```json
{"status": "success", "matrix_sum": 10.0, "model_checked": "TestModel", ...}
```

### 4. Run Benchmarks (10 minutes)

```bash
# Install benchmark dependencies
pip install -r bench/requirements.txt

# Run quick benchmark
python bench/runner.py --duration 30 --payload-size 1000 --save-results

# Run full suite
python bench/runner.py --full-suite
```

### 5. Monitor Performance (5 minutes)

```bash
# Start production monitoring stack
docker-compose --profile prod up -d

# Access monitoring
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3000 (admin/admin)
```

## Local Development Setup

### 1. Install Dependencies

```bash
# Python dependencies
pip install -r python/requirements.txt
pip install -r bench/requirements.txt

# Lean 4 (using elan)
curl -sSL https://get.elan.sh | sh
elan install 4.7.0
elan default 4.7.0
```

### 2. Build Lean Project

```bash
cd lean
lake build
```

### 3. Start Server

```bash
# Terminal 1: Start Python server
cd python
python src/server.py --dev

# Terminal 2: Test Lean integration
cd lean
lean proofs/PythonIntegration.lean
```

## Production Deployment

### 1. Environment Configuration

```bash
# Set production environment variables
export ZMQ_ENDPOINT="tcp://0.0.0.0:5555"
export LOG_LEVEL="WARNING"
export ENABLE_METRICS="true"
export ENABLE_CURVE="true"
export ZMQ_CURVE_PUBLICKEY="your_public_key"
export ZMQ_CURVE_SECRETKEY="your_secret_key"
```

### 2. Start Production Stack

```bash
# Start with production profile
docker-compose --profile prod up -d

# Scale workers
docker-compose --profile prod up -d --scale lean-python-bridge-prod=3
```

### 3. Health Checks

```bash
# Check server health
curl http://localhost:5555/health

# Check metrics
curl http://localhost:5555/metrics

# Monitor logs
docker-compose logs -f lean-python-bridge-prod
```

## Performance Tuning

### 1. Server Configuration

```bash
# Start with custom worker configuration
python src/server.py --workers 4 --threads 8 --endpoint tcp://0.0.0.0:5555
```

### 2. Load Testing

```bash
# Test with different payload sizes
python bench/runner.py --duration 60 --payload-size 10000 --concurrency 4

# Test with different concurrency levels
python bench/runner.py --duration 60 --payload-size 1000 --concurrency 1
python bench/runner.py --duration 60 --payload-size 1000 --concurrency 2
python bench/runner.py --duration 60 --payload-size 1000 --concurrency 4
```

### 3. Monitor SLOs

Key performance targets:
- **P99 Latency**: ≤50ms for 1K-float vectors
- **Throughput**: ≥100 req/s sustained
- **Error Rate**: ≤0.1% under normal load
- **Recovery Time**: ≤5s after server restart

## Troubleshooting

### Common Issues

1. **Connection Refused**
   ```bash
   # Check if server is running
   docker-compose ps
   
   # Check server logs
   docker-compose logs lean-python-bridge
   ```

2. **High Latency**
   ```bash
   # Check server metrics
   curl http://localhost:5555/metrics
   
   # Check queue utilization
   # Look for queue_size vs max_queue_size
   ```

3. **Memory Issues**
   ```bash
   # Check memory usage
   docker stats lean-python-bridge
   
   # Restart with more memory
   docker-compose down
   docker-compose --profile prod up -d
   ```

### Debug Mode

```bash
# Start server in debug mode
python src/server.py --dev --endpoint tcp://0.0.0.0:5555

# Enable verbose logging
export LOG_LEVEL="DEBUG"
```

## Next Steps

After completing this quickstart:

1. **Explore the Codebase**: Review `lean/proofs/` for mathematical definitions
2. **Run Benchmarks**: Use `bench/runner.py` to establish performance baselines
3. **Monitor SLOs**: Set up alerts in Grafana for performance thresholds
4. **Scale Up**: Increase worker processes and threads based on load testing
5. **Security**: Enable CURVE encryption for production deployments

## Support

- **Documentation**: See `docs/` directory for detailed guides
- **Issues**: Report bugs and feature requests on GitHub
- **Discussions**: Join community discussions for questions and ideas

## Performance Expectations

Based on current benchmarks:
- **1K matrix**: P99 ≤ 50ms, ~65 req/s
- **10K matrix**: P99 ≤ 200ms, ~25 req/s  
- **100K matrix**: P99 ≤ 1000ms, ~5 req/s

Your mileage may vary based on hardware and configuration.

