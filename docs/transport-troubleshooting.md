# ZeroMQ Transport Pattern Troubleshooting

## Overview

This document covers troubleshooting for the ZeroMQ transport patterns implemented in the Lean-Python bridge:

- **Lazy Pirate**: Basic retry pattern with socket recreation
- **Paranoid Pirate**: Advanced pattern with heartbeats and correlation IDs

## Transport Patterns

### Lazy Pirate Pattern

The Lazy Pirate pattern is implemented in `lean/proofs/PythonIntegration.lean` and provides:

- Automatic retry on failures
- Socket recreation for each attempt
- Configurable timeout and retry count
- Exponential backoff between retries

**Usage:**
```lean
let result ← lazyPirateRequest endpoint jsonMsg 1000 3
```

**Parameters:**
- `endpoint`: ZMQ endpoint (e.g., "tcp://127.0.0.1:5555")
- `jsonMsg`: JSON string to send
- `timeoutMs`: Receive timeout in milliseconds (default: 1000)
- `maxRetries`: Maximum retry attempts (default: 3)

### Paranoid Pirate Pattern

The Paranoid Pirate pattern extends Lazy Pirate with:

- Heartbeat monitoring
- Request correlation IDs
- Server liveness detection
- Advanced error handling

**Usage:**
```lean
let heartbeatConfig := { heartbeatInterval := 1000, heartbeatLiveness := 3 }
let result ← paranoidPirateRequest endpoint jsonMsg 5000 5 heartbeatConfig
```

**Parameters:**
- `endpoint`: ZMQ endpoint
- `jsonMsg`: JSON string to send
- `timeoutMs`: Receive timeout in milliseconds (default: 5000)
- `maxRetries`: Maximum retry attempts (default: 5)
- `heartbeat`: Heartbeat configuration

## Common Issues and Solutions

### 1. Connection Refused

**Symptoms:**
- `zmq_connect failed` errors
- Connection timeout in Lean
- Python server not responding

**Solutions:**
1. Ensure Python server is running: `python src/server.py`
2. Check endpoint configuration matches server binding
3. Verify firewall settings allow connections on port 5555
4. Check server logs for binding errors

**Debugging:**
```bash
# Check if port is listening
netstat -an | grep 5555

# Test with simple ZMQ client
python -c "
import zmq
context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.connect('tcp://127.0.0.1:5555')
print('Connection successful')
"
```

### 2. Request Timeouts

**Symptoms:**
- Lean requests hang indefinitely
- No response from Python server
- High latency in benchmark results

**Solutions:**
1. Increase timeout values in Lean code
2. Check Python server performance under load
3. Verify matrix size isn't overwhelming server
4. Monitor server CPU and memory usage

**Configuration:**
```lean
-- Increase timeout for large matrices
let result ← lazyPirateRequest endpoint jsonMsg 10000 5
```

### 3. Lost Responses

**Symptoms:**
- Some requests succeed, others fail
- Inconsistent benchmark results
- Correlation ID mismatches

**Solutions:**
1. Use Paranoid Pirate pattern for critical requests
2. Implement proper request correlation
3. Check for server restarts during testing
4. Verify idempotency of operations

**Implementation:**
```lean
-- Use correlation IDs for tracking
let correlationId := s!"req_{System.monoMsNow}"
let requestWithId := s!"{{\"correlation_id\":\"{correlationId}\", \"payload\":{jsonMsg}}}"
```

### 4. Server Crashes

**Symptoms:**
- Python server process terminates
- Connection errors after server restart
- Benchmark failures

**Solutions:**
1. Implement graceful shutdown handling
2. Use Paranoid Pirate pattern for automatic recovery
3. Monitor server health with heartbeats
4. Implement server restart automation

**Server Health Check:**
```python
# Add to server.py
def health_check(self):
    return {
        "status": "healthy",
        "uptime": time.time() - self.start_time,
        "requests_processed": self.request_count
    }
```

### 5. Memory Leaks

**Symptoms:**
- Increasing memory usage over time
- Server becomes unresponsive
- Benchmark performance degrades

**Solutions:**
1. Ensure proper socket cleanup in Lean
2. Monitor Python server memory usage
3. Implement request correlation ID cleanup
4. Use memory profiling tools

**Memory Monitoring:**
```bash
# Monitor Python process memory
ps aux | grep python | grep server

# Use memory profiler
python -m memory_profiler src/server.py
```

## Performance Tuning

### Socket Options

**Lean Side:**
```lean
-- Set receive timeout
setRcvTimeout sock 5000

-- Set send timeout (if implemented)
-- setSndTimeout sock 5000
```

**Python Side:**
```python
# Configure socket options
socket.setsockopt(zmq.RCVTIMEO, 5000)
socket.setsockopt(zmq.SNDTIMEO, 5000)
socket.setsockopt(zmq.LINGER, 0)
```

### Load Testing

**Benchmark Configuration:**
```bash
# Run comprehensive benchmark
python bench/runner.py --full-suite --save-results

# Test specific scenarios
python bench/runner.py --duration 60 --payload-size 10000 --concurrency 4
```

**Expected Performance:**
- **1K matrix**: P99 ≤ 50ms
- **10K matrix**: P99 ≤ 200ms  
- **100K matrix**: P99 ≤ 1000ms
- **Throughput**: ≥100 req/s sustained

## Monitoring and Debugging

### Logging

**Lean Side:**
```lean
IO.println s!"[Lean] Sending request: {requestId}"
IO.println s!"[Lean] Received response: {response}"
```

**Python Side:**
```python
logging.info(f"Processing request {correlation_id}")
logging.warning(f"Client heartbeat missed")
logging.error(f"Request failed: {error}")
```

### Metrics Collection

**Request Metrics:**
- Total requests processed
- Success/failure rates
- Response time percentiles
- Correlation ID tracking

**System Metrics:**
- CPU usage
- Memory consumption
- Network I/O
- Socket state

## Best Practices

1. **Always use timeouts** to prevent hanging requests
2. **Implement proper error handling** for all failure modes
3. **Use correlation IDs** for request tracking
4. **Monitor server health** with heartbeats
5. **Implement exponential backoff** for retries
6. **Clean up resources** properly on both sides
7. **Test failure scenarios** including server crashes
8. **Monitor performance metrics** continuously

## References

- [ZeroMQ Guide - Reliable Request-Reply](https://zguide.zeromq.org/docs/chapter4/)
- [ZeroMQ Patterns](https://zguide.zeromq.org/docs/chapter4/#reliable-request-reply)
- [Lean 4 FFI Documentation](https://lean-lang.org/lean4/doc/dev/ffi.html)
