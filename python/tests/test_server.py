import subprocess
import time
import zmq
import json
import pytest


@pytest.fixture(scope="module")
def zmq_server():
    proc = subprocess.Popen(["python3", "src/server.py"])
    time.sleep(1)
    yield
    proc.terminate()


def test_v1_sum(zmq_server):
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
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


def test_v2_schema(zmq_server):
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
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
