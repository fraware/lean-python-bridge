import pytest

from src.codec import SerializationCodec


def test_protobuf_round_trip():
    codec = SerializationCodec()
    payload = {
        "schema_version": 1,
        "matrix": [[1.0, 2.0], [3.0, 4.0]],
        "model": {"name": "TestModel", "version": "1.0"},
    }
    blob = codec.serialize(payload, format_override="protobuf")
    decoded = codec.deserialize(blob)
    assert decoded["schema_version"] == 1.0
    assert decoded["model"]["name"] == "TestModel"


def test_unknown_header_rejected():
    codec = SerializationCodec()
    with pytest.raises(ValueError):
        codec.deserialize(b"\xffpayload")
