# ZeroMQ Transport Pattern Troubleshooting

## Overview

This document covers troubleshooting for the ZeroMQ REQ/REP path between Lean and the Python server.

Lean client logic lives in **`lean/PythonIntegration.lean`**:

- **`lazyPirateRequest`:** retries with fresh REQ sockets, receive timeout, and sleeps between attempts (via `BridgeConfig`).
- **`paranoidPirateRequest`:** wraps the JSON body in an object with a **`correlation_id`** and delegates to **`lazyPirateRequest`**. The `HeartbeatConfig` parameter is reserved for future use; there is no separate heartbeat socket protocol in Lean today.
- **`checkServerHealth`:** sends the JSON string **`"HEARTBEAT"`** and expects a reply containing **`heartbeat_ack`** (see Python server).

Install dependencies from lockfiles before debugging:

```bash
python -m pip install --upgrade pip
pip install --require-hashes -r python/requirements-runtime.lock.txt
pip install --require-hashes -r python/requirements-dev.lock.txt
```

## Configuration: `BridgeConfig`

Retry and endpoint behavior are controlled by **`BridgeConfig`** (defaults in `PythonIntegration.defaultConfig`):

| Field | Role |
|--------|------|
| `endpoint` | ZMQ connect string (default `tcp://127.0.0.1:5555`) |
| `timeoutMs` | REQ receive timeout per attempt |
| `maxRetries` | Number of attempts in `lazyPirateRequest` |
| `correlationIdPrefix` | Prefix for generated correlation IDs (`paranoidPirateRequest`) |
| `enableHeartbeat` | Reserved / future use |

### Lazy Pirate (Lean)

```lean
open PythonIntegration

def cfg : BridgeConfig :=
  { endpoint := "tcp://127.0.0.1:5555", timeoutMs := 1000, maxRetries := 3 }

-- ...
let result ← lazyPirateRequest cfg jsonMsg
```

`result` is `IO (BridgeResult String)` where `BridgeResult` is `Except BridgeError String`.

### Paranoid Pirate (Lean) — correlation wrapper

```lean
def cfg : BridgeConfig := { defaultConfig with maxRetries := 5 }

let result ← paranoidPirateRequest cfg jsonMsg {}
```

The server unwraps `{"correlation_id": "...", "payload": <original JSON>}` and echoes `correlation_id` on success or error responses when present.

## Common issues and solutions

### 1) Connection refused

**Symptoms:** `zmq_connect` failures in C/Lean, timeouts, no reply in Python.

**Checks:**

1. Start the server from repo root: `cd python && python src/server.py --dev` (or your production command).
2. Client `endpoint` must match server bind (e.g. server `tcp://*:5555` → client `tcp://127.0.0.1:5555`).
3. Firewall / container port mapping (`-p 5555:5555`).

**Quick socket test:**

```bash
python - <<'PY'
import zmq
ctx = zmq.Context()
sock = ctx.socket(zmq.REQ)
sock.connect("tcp://127.0.0.1:5555")
print("connected")
sock.close()
ctx.term()
PY
```

On Windows you can use `netstat` or PowerShell `Get-NetTCPConnection`; on Linux, `ss -tlnp | grep 5555`.

### 2) Request timeouts

**Symptoms:** Lean logs retries, `BridgeError.Timeout`, or REQ stuck until retry.

**Mitigations:**

1. Increase `timeoutMs` / `maxRetries` in `BridgeConfig`.
2. Reduce matrix size or load; watch Python CPU.
3. Align client timeout with server `RCVTIMEO` / processing time.

Example:

```lean
let cfg := { defaultConfig with timeoutMs := 10000, maxRetries := 5 }
let result ← lazyPirateRequest cfg jsonMsg
```

### 3) Lost or mismatched responses

**Symptoms:** Occasional failures under load, wrong pairing in benchmarks.

**Mitigations:**

1. Use **`paranoidPirateRequest`** so responses can carry **`correlation_id`**.
2. Avoid sharing one REQ socket across threads without synchronization.
3. After server restarts, recreate REQ sockets (Lean already does per attempt in `lazyPirateRequest`).

### 4) Heartbeat / health check

The server treats the JSON value **`"HEARTBEAT"`** specially and returns JSON containing **`heartbeat_ack`**.

**Python one-liner:**

```bash
python - <<'PY'
import json, zmq
ctx = zmq.Context()
sock = ctx.socket(zmq.REQ)
sock.connect("tcp://127.0.0.1:5555")
sock.send_string(json.dumps("HEARTBEAT"))
print(sock.recv_string())
sock.close()
ctx.term()
PY
```

In Lean, prefer **`checkServerHealth`** with a `BridgeConfig` pointing at the same endpoint.

### 5) Server crashes or restarts

**Mitigations:**

1. REQ/REP state is fragile; Lean’s per-attempt socket recreation helps after failures.
2. Watch Python logs and metrics (`requests_error`, histograms).
3. Use process supervision or container restart policies in production.

### 6) Memory growth

**Mitigations:**

1. Ensure sockets are closed on error paths (Lean `lazyPirateRequest` closes after recv or on catch).
2. Python: `zmq.LINGER` and clean shutdown (see server code).
3. Profile long-running benchmarks separately.

## Performance tuning

### Socket options

**Lean (FFI):** receive timeout is set from `BridgeConfig.timeoutMs` via `setRcvTimeout`.

**Python (`server.py`):** `zmq.RCVTIMEO` on the REP socket, optional CURVE, metrics on `METRICS_PORT`.

### Load testing

```bash
python bench/runner.py --full-suite --save-results
python bench/runner.py --duration 60 --payload-size 10000 --concurrency 4
```

Treat documented SLO-style numbers in `bench/README.md` as **targets or historical baselines**, not guarantees on every machine.

## Monitoring

- **Prometheus:** HTTP metrics when `ENABLE_METRICS=true` (default port `8000`).
- **Compose:** `monitoring/prometheus.yml` and Grafana provisioning under `monitoring/` (see `docker-compose.yml` **prod** profile).

## Best practices

1. Install from **hashed lockfiles** for reproducible Python envs.
2. Regenerate locks after editing `.in` files: `python scripts/compile_python_locks.py`.
3. Always use **timeouts** on client and server.
4. Use **correlation IDs** for traced requests (`paranoidPirateRequest` + server unwrap).
5. Validate untrusted JSON with **`validation.py`** on the Python side.

## References

- [ZeroMQ Guide — Reliable Request-Reply](https://zguide.zeromq.org/docs/chapter4/)
- [Lean 4 FFI](https://lean-lang.org/lean4/doc/dev/ffi.html)
