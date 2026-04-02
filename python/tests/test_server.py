import subprocess
import time
import zmq
import json
import pytest
import socket
import sys
from pathlib import Path


def is_port_open(port):
    """Check if a port is open"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex(("127.0.0.1", port))
            return result == 0
    except Exception:
        return False


@pytest.fixture(scope="module")
def zmq_server():
    """Start an isolated server subprocess and cleanly tear it down."""
    if is_port_open(5555):
        pytest.skip("Port 5555 already in use; refusing to kill unrelated processes.")

    # Start server
    proc = subprocess.Popen(
        [sys.executable, "src/server.py", "--dev", "--metrics-port", "8001"],
        cwd=str(Path(__file__).resolve().parents[1]),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for server to start with timeout
    max_wait = 10
    while not is_port_open(5555) and max_wait > 0:
        time.sleep(0.5)
        max_wait -= 1

    if not is_port_open(5555):
        proc.terminate()
        pytest.fail("Server failed to start within timeout")

    yield proc

    # Cleanup
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


def test_v1_sum(zmq_server):
    """Test v1 schema matrix sum"""
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
    socket.setsockopt(zmq.SNDTIMEO, 5000)  # 5 second timeout

    try:
        socket.connect("tcp://127.0.0.1:5555")

        data = {
            "schema_version": 1,
            "matrix": [[1, 2], [3, 4]],
            "model": {"name": "TestModel", "version": "0.1"},
        }
        socket.send_string(json.dumps(data))
        reply_str = socket.recv_string()
        reply = json.loads(reply_str)

        assert reply["status"] == "success"
        assert reply["matrix_sum"] == 10.0
        assert reply["model_checked"] == "TestModel"
    finally:
        socket.close()
        context.term()


def test_v2_schema(zmq_server):
    """Test v2 schema with additional fields"""
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
    socket.setsockopt(zmq.SNDTIMEO, 5000)  # 5 second timeout

    try:
        socket.connect("tcp://127.0.0.1:5555")

        data = {
            "schema_version": 2,
            "matrix": [[1, 2], [3, 4]],
            "model": {"name": "AnotherModel", "version": "1.2", "author": "Jane Doe"},
        }
        socket.send_string(json.dumps(data))
        reply_str = socket.recv_string()
        reply = json.loads(reply_str)

        assert reply["status"] == "success"
        assert reply["matrix_sum"] == 10.0
        assert reply["model_checked"] == "AnotherModel"
        assert reply["schema_version_used"] == 2
    finally:
        socket.close()
        context.term()


def test_server_health(zmq_server):
    """Health probe over ZMQ heartbeat contract."""
    context = zmq.Context()
    client = context.socket(zmq.REQ)
    client.setsockopt(zmq.RCVTIMEO, 3000)
    client.connect("tcp://127.0.0.1:5555")
    try:
        client.send_string(json.dumps("HEARTBEAT"))
        reply = json.loads(client.recv_string())
        assert reply["status"] == "heartbeat_ack"
        assert "timestamp" in reply
    finally:
        client.close()
        context.term()


def test_validation_schemas():
    """Test validation schema loading"""
    from src.validation import load_schemas

    schemas = load_schemas()
    assert "v1" in schemas
    assert "v2" in schemas


def test_imports():
    """Test that all required modules can be imported"""
    import zmq
    import jsonschema
    import numpy

    assert zmq is not None
    assert jsonschema is not None
    assert numpy is not None
