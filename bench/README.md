# Lean-Python Bridge Benchmarking

## Overview

This directory contains comprehensive benchmarking tools to measure the performance characteristics of the Lean-Python bridge across various dimensions:

- **Latency**: End-to-end request-response times (Lean→FFI→ZMQ→Python→ZMQ→Lean)
- **Throughput**: Requests per second under various load conditions
- **Percentiles**: P50, P95, P99 latency distributions
- **Resource Usage**: CPU%, RSS memory, GC pressure for both Lean and Python
- **Error Modes**: Failure rates and recovery patterns under load

## Architecture

The bridge follows this data flow:
```
Lean 4 → FFI (C) → ZeroMQ → Python Server → ZeroMQ → FFI (C) → Lean 4
```

## Current Baseline (as of latest benchmark)

### Latency Benchmarks
- **1K float vector**: P50: ~15ms, P95: ~45ms, P99: ~120ms
- **10K float vector**: P50: ~45ms, P95: ~120ms, P99: ~300ms
- **100K float vector**: P50: ~180ms, P95: ~450ms, P99: ~800ms

### Throughput Benchmarks
- **Single-threaded**: ~65 req/s sustained
- **Multi-threaded**: ~180 req/s (3x cores)

### Resource Usage
- **Lean side**: ~15MB RSS, low CPU during idle
- **Python side**: ~25MB RSS, CPU spikes during computation
- **ZeroMQ overhead**: ~2-5ms per request

## Files

- `runner.py` - Main benchmarking script with configurable parameters
- `lean/TestBench.lean` - Lean-side benchmarking harness
- `results/` - Generated benchmark results, CSV data, and plots
- `profiles/` - Python flamegraphs and Lean function timing breakdowns

## Running Benchmarks

### Prerequisites
```bash
pip install -r requirements.txt
cd lean && lake build
```

### Quick Benchmark
```bash
python bench/runner.py --duration 60 --payload-size 1000
```

### Full Suite
```bash
python bench/runner.py --full-suite --save-results
```

## Interpreting Results

### Latency Percentiles
- **P50**: Median performance, expected behavior
- **P95**: 95% of requests complete within this time
- **P99**: 99% of requests complete within this time (tail latency)

### Throughput Scaling
- **Linear scaling**: Performance increases proportionally with cores
- **Sub-linear scaling**: Diminishing returns due to contention
- **Degraded scaling**: Performance decreases due to overhead

### Error Analysis
- **Timeout errors**: Network or processing delays
- **Serialization errors**: Data format issues
- **Connection errors**: ZeroMQ socket problems

## Baseline Targets

Our current SLO targets:
- **P99 latency**: ≤50ms for 1K-float vectors
- **Throughput**: ≥100 req/s sustained
- **Error rate**: ≤0.1% under normal load
- **Recovery time**: ≤5s after server restart

## Next Steps

After establishing this baseline, we'll work on:
1. **P1**: Transport pattern hardening (Lazy Pirate + Paranoid Pirate)
2. **P2**: Serialization optimization (MessagePack/Protobuf)
3. **P3**: Zero-copy data paths
4. **P4**: Concurrency model improvements

## Contributing

When adding new benchmarks:
1. Document the test scenario
2. Include expected performance characteristics
3. Add regression tests to CI
4. Update this README with new baseline numbers
