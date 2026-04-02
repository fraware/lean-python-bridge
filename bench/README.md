# Lean-Python Bridge Benchmarking

## Overview

This directory contains **Python** tooling to stress the ZMQ bridge (client-side latencies, throughput, and resource sampling). The data path is:

```text
Client (Python bench) → ZeroMQ REQ → Python server (REP) → response
```

A separate **Lean** script at `bench/lean/TestBench.lean` can be used for experiments; it is **not** part of the default `lake build` roots in `lakefile.lean` (only modules under `lean/` are). After `lake build`, you can try `lake env lean bench/lean/TestBench.lean` if your environment resolves imports; CI does not compile this file.

## Architecture (end-to-end bridge)

When measuring from Lean through FFI, the full chain is:

```text
Lean 4 → FFI (C) → ZeroMQ → Python server → ZeroMQ → FFI → Lean 4
```

The default `runner.py` workload speaks ZMQ directly from Python, which is appropriate for server and network tuning without rebuilding Lean for every run.

## Baseline notes

Numbers in earlier versions of this file (latency percentiles, req/s) are **illustrative**. Record your own baselines with `--save-results` and treat comparisons as relative to your hardware and server flags.

## Files

| File | Purpose |
|------|---------|
| `runner.py` | Main CLI benchmark driver |
| `ci_benchmark.py` | CI-oriented benchmark entry |
| `serialization_benchmark.py` | Serialization-focused experiments |
| `requirements.txt` | Bench-only Python deps (pinned where required by CI policy) |
| `bench/lean/TestBench.lean` | Optional Lean-side harness (not a default Lake root) |

Directories **`bench/results/`** and **`bench/profiles/`** are created when you save results or profiling output.

## Running benchmarks

### Prerequisites

```bash
python -m pip install --upgrade pip
pip install --require-hashes -r ../python/requirements-runtime.lock.txt
pip install -r requirements.txt
```

From the **repository root**, build Lean if you need artifacts for Lean-side tests:

```bash
lake build
```

If `../python/requirements-*.in` changes, regenerate lockfiles:

```bash
python ../scripts/compile_python_locks.py
```

### Quick run

From repository root:

```bash
python bench/runner.py --duration 60 --payload-size 1000
```

### Full suite

```bash
python bench/runner.py --full-suite --save-results
```

Ensure the server is listening on the configured endpoint (default `tcp://127.0.0.1:5555`) when you benchmark live traffic.

## Interpreting results

- **Latency percentiles** (P50 / P95 / P99): tail behavior under your concurrency and payload settings.
- **Throughput:** requests per second for the chosen scenario; scales with cores, GIL, and matrix work.
- **Errors:** timeouts, JSON issues, or ZMQ errors — see runner logs.

## Targets (goals)

Use these as **engineering goals**, not CI assertions:

- Low tail latency for small payloads on a warm local server.
- Sustainable throughput under declared concurrency.
- Error rate near zero under normal load.

## Roadmap (engineering backlog)

1. Transport hardening (correlation IDs are supported server-side; extend Lean as needed).
2. Serialization experiments (see `serialization_benchmark.py`).
3. Optional integration of `bench/lean/TestBench.lean` into Lake as an explicit target if you want CI to compile it.

## Contributing

When adding benchmarks:

1. Document the scenario and default parameters.
2. Prefer deterministic or seeded workloads where possible.
3. Update this README if new scripts or artifacts are added.
