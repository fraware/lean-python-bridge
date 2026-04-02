# Lean-Python Bridge Quickstart

## 1) Clone

```bash
git clone https://github.com/fraware/lean-python-bridge.git
cd lean-python-bridge
```

## 2) Prerequisites

- **Python 3.11** (matches CI and lockfiles).
- **Lean:** [elan](https://github.com/leanprover/elan) or another install matching `lean-toolchain`.
- **Native `lake build`:** a C compiler (`cc`/`gcc`), **libzmq** development package, and **libgmp** dev files. If this is painful on your OS, use **Docker** (see below) for a full Lean build.

## 3) Install Python dependencies (hash-locked)

```bash
python -m pip install --upgrade pip
pip install --require-hashes -r python/requirements-runtime.lock.txt
pip install --require-hashes -r python/requirements-dev.lock.txt
pip install -r bench/requirements.txt
```

If you edit `python/requirements-runtime.in` or `python/requirements-dev.in`, regenerate locks:

```bash
python scripts/compile_python_locks.py
```

## 4) Build Lean

From the **repository root**:

```bash
lake build
```

This compiles the `LeanPythonBridge` library (including `lean/FFI/LeanZMQ.c` linked against libzmq).

## 5) Start the Python bridge server

From the repository root:

```bash
cd python
python src/server.py --dev
```

Default REP socket: `tcp://*:5555` unless you set `ZMQ_ENDPOINT`. With metrics enabled (`ENABLE_METRICS=true`), scrape `http://127.0.0.1:8000/metrics` (port from `METRICS_PORT`).

## 6) Send a smoke-test request

In a second terminal (repository root or any cwd):

```bash
python - <<'PY'
import json
import zmq

ctx = zmq.Context()
sock = ctx.socket(zmq.REQ)
sock.connect("tcp://127.0.0.1:5555")
payload = {
    "schema_version": 1,
    "matrix": [[1, 2], [3, 4]],
    "model": {"name": "TestModel", "version": "1.0"},
}
sock.send_string(json.dumps(payload))
print(sock.recv_string())
sock.close()
ctx.term()
PY
```

**Heartbeat** (JSON string payload, as the server expects):

```bash
python - <<'PY'
import json, zmq
ctx = zmq.Context()
s = ctx.socket(zmq.REQ)
s.connect("tcp://127.0.0.1:5555")
s.send_string(json.dumps("HEARTBEAT"))
print(s.recv_string())
s.close()
ctx.term()
PY
```

## 7) Run tests

**Python:**

```bash
cd python && pytest -q tests
```

**Lean (representative checks):**

```bash
lake env lean lean/ExampleProof.lean
lake env lean lean/MatrixProps.lean
lake env lean lean/MLProofs.lean
lake env lean lean/Tests.lean
```

Full bridge integration (needs server running on `tcp://127.0.0.1:5555`):

```bash
lake env lean lean/PythonIntegration.lean
```

## 8) Run benchmarks

From repository root (with server listening on the default endpoint if you measure live traffic):

```bash
python bench/runner.py --duration 30 --payload-size 1000 --save-results
```

Larger run:

```bash
python bench/runner.py --full-suite --save-results
```

Output directories such as `bench/results/` and `bench/profiles/` are created when you save results.

## Docker quick path

Build includes `lake build` in an Ubuntu stage; runtime image runs the Python server with `.lake` copied in for tooling that expects artifacts.

```bash
docker build -t lean-python-bridge .
docker run --rm -p 5555:5555 -p 8000:8000 \
  -e ENABLE_METRICS=true \
  lean-python-bridge
```

Compose (dev profile mounts local `python/` and `lean/`):

```bash
docker compose --profile dev up lean-python-bridge-dev
```

## Troubleshooting pointers

- Transport, retries, and Lean API details: [transport-troubleshooting.md](transport-troubleshooting.md)
- CI and dependency policy: `.github/workflows/ci.yml`
- Repository overview: [README.md](../README.md)
