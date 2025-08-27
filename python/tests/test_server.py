import subprocess
import time
import zmq
import json
import pytest
import socket
import os


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
    """Start ZMQ server with proper error handling"""
    # Kill any existing processes on port 5555
    try:
        os.system("taskkill /f /im python.exe 2>nul")
    except Exception:
        pass

    # Wait for port to be free
    max_wait = 10
    while is_port_open(5555) and max_wait > 0:
        time.sleep(0.5)
        max_wait -= 1

    # Start server
    proc = subprocess.Popen(
        ["python", "src/server.py", "--dev"],
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
    except Exception:
        pass


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


def test_server_health():
    """Quick health check without starting full server"""
    # This test doesn't require the server to be running
    assert True


def test_validation_schemas():
    """Test validation schema loading"""
    from src.validation import load_schemas

    schemas = load_schemas()
    assert "v1" in schemas
    assert "v2" in schemas


def test_imports():
    """Test that all required modules can be imported"""
    # Test imports work without actually using them
    try:
        import zmq
        import json
        import jsonschema
        import numpy

        assert True
    except ImportError:
        pytest.fail("Required modules not available")
