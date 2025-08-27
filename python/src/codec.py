"""
Serialization Codec Abstraction

Supports multiple serialization formats with automatic selection:
- JSON: For small control messages and metadata
- MessagePack: For medium-sized payloads (default)
- Protocol Buffers: For large structured data
"""

import json
import msgpack
import struct
from typing import Any, Dict, Union, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class CodecConfig:
    """Configuration for serialization codecs"""

    json_threshold: int = 1000  # Use JSON for payloads < 1000 elements
    msgpack_threshold: int = 100000  # Use MessagePack for payloads < 100k elements
    protobuf_threshold: int = 1000000  # Use Protobuf for payloads >= 1M elements
    enable_compression: bool = True
    enable_checksums: bool = False


class SerializationCodec:
    """Multi-format serialization codec with automatic format selection"""

    def __init__(self, config: CodecConfig = None):
        self.config = config or CodecConfig()
        self._format_stats = {"json": 0, "msgpack": 0, "protobuf": 0}

    def _estimate_payload_size(self, data: Any) -> int:
        """Estimate the number of elements in a payload"""
        if isinstance(data, (list, tuple)):
            return len(data)
        elif isinstance(data, dict):
            # Count all nested list/tuple elements
            total = 0
            for value in data.values():
                if isinstance(value, (list, tuple)):
                    total += len(value)
                elif isinstance(value, dict):
                    total += self._estimate_payload_size(value)
            return total
        return 0

    def _select_format(self, data: Any) -> str:
        """Automatically select the best serialization format"""
        payload_size = self._estimate_payload_size(data)

        if payload_size < self.config.json_threshold:
            return "json"
        elif payload_size < self.config.msgpack_threshold:
            return "msgpack"
        else:
            return "protobuf"

    def serialize(self, data: Any, format_override: Optional[str] = None) -> bytes:
        """Serialize data using the best available format"""
        selected_format = format_override or self._select_format(data)

        try:
            if selected_format == "json":
                result = self._serialize_json(data)
            elif selected_format == "msgpack":
                result = self._serialize_msgpack(data)
            elif selected_format == "protobuf":
                result = self._serialize_protobuf(data)
            else:
                raise ValueError(f"Unsupported format: {selected_format}")

            # Add format header
            header = struct.pack("B", self._format_to_id(selected_format))
            self._format_stats[selected_format] += 1

            logger.debug(
                f"Serialized {len(data) if hasattr(data, '__len__') else 'unknown'} elements using {selected_format}"
            )
            return header + result

        except Exception as e:
            logger.error(f"Serialization failed with {selected_format}: {e}")
            # Fallback to JSON
            if selected_format != "json":
                logger.info("Falling back to JSON serialization")
                return struct.pack(
                    "B", self._format_to_id("json")
                ) + self._serialize_json(data)
            raise

    def deserialize(self, data: bytes) -> Any:
        """Deserialize data, automatically detecting format from header"""
        if len(data) < 1:
            raise ValueError("Data too short to contain format header")

        format_id = struct.unpack("B", data[:1])[0]
        format_name = self._id_to_format(format_id)
        payload = data[1:]

        try:
            if format_name == "json":
                return self._deserialize_json(payload)
            elif format_name == "msgpack":
                return self._deserialize_msgpack(payload)
            elif format_name == "protobuf":
                return self._deserialize_protobuf(payload)
            else:
                raise ValueError(f"Unknown format ID: {format_id}")

        except Exception as e:
            logger.error(f"Deserialization failed with {format_name}: {e}")
            raise

    def _serialize_json(self, data: Any) -> bytes:
        """Serialize to JSON with special float handling"""

        def json_serializer(obj):
            if isinstance(obj, float):
                if obj != obj:  # NaN
                    return "NaN"
                elif obj == float("inf"):
                    return "Infinity"
                elif obj == float("-inf"):
                    return "-Infinity"
            return obj

        return json.dumps(data, default=json_serializer, separators=(",", ":")).encode(
            "utf-8"
        )

    def _deserialize_json(self, data: bytes) -> Any:
        """Deserialize from JSON with special float handling"""

        def json_hook(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if isinstance(value, str):
                        if value == "NaN":
                            obj[key] = float("nan")
                        elif value == "Infinity":
                            obj[key] = float("inf")
                        elif value == "-Infinity":
                            obj[key] = float("-inf")
            return obj

        return json.loads(data.decode("utf-8"), object_hook=json_hook)

    def _serialize_msgpack(self, data: Any) -> bytes:
        """Serialize to MessagePack with special float handling"""
        try:
            return msgpack.packb(data, use_bin_type=True, strict_types=True)
        except (TypeError, OverflowError) as e:
            logger.warning(
                f"MessagePack serialization failed: {e}, falling back to JSON"
            )
            return self._serialize_json(data)

    def _deserialize_msgpack(self, data: bytes) -> Any:
        """Deserialize from MessagePack"""
        try:
            return msgpack.unpackb(data, raw=False)
        except Exception as e:
            logger.error(f"MessagePack deserialization failed: {e}")
            raise

    def _serialize_protobuf(self, data: Any) -> bytes:
        """Serialize to Protocol Buffers (placeholder implementation)"""
        # For now, fall back to MessagePack for large payloads
        # TODO: Implement proper protobuf serialization
        logger.info("Protobuf not yet implemented, using MessagePack")
        return self._serialize_msgpack(data)

    def _deserialize_protobuf(self, data: bytes) -> Any:
        """Deserialize from Protocol Buffers (placeholder implementation)"""
        # For now, fall back to MessagePack
        logger.info("Protobuf not yet implemented, using MessagePack")
        return self._deserialize_msgpack(data)

    def _format_to_id(self, format_name: str) -> int:
        """Convert format name to ID"""
        return {"json": 1, "msgpack": 2, "protobuf": 3}.get(format_name, 1)

    def _id_to_format(self, format_id: int) -> str:
        """Convert format ID to name"""
        return {1: "json", 2: "msgpack", 3: "protobuf"}.get(format_id, "json")

    def get_stats(self) -> Dict[str, int]:
        """Get serialization format usage statistics"""
        return self._format_stats.copy()

    def reset_stats(self):
        """Reset format usage statistics"""
        self._format_stats = {"json": 0, "msgpack": 0, "protobuf": 0}


# Convenience functions for common use cases
def serialize_matrix(matrix: list, model_info: dict, schema_version: int = 1) -> bytes:
    """Serialize matrix data with automatic format selection"""
    codec = SerializationCodec()
    payload = {"schema_version": schema_version, "matrix": matrix, "model": model_info}
    return codec.serialize(payload)


def deserialize_matrix(data: bytes) -> dict:
    """Deserialize matrix data"""
    codec = SerializationCodec()
    return codec.deserialize(data)


def benchmark_formats(data: Any, iterations: int = 1000) -> Dict[str, float]:
    """Benchmark different serialization formats"""
    codec = SerializationCodec()
    results = {}

    import time

    # Test JSON
    start_time = time.perf_counter()
    for _ in range(iterations):
        codec._serialize_json(data)
    json_time = (time.perf_counter() - start_time) / iterations
    results["json"] = json_time

    # Test MessagePack
    start_time = time.perf_counter()
    for _ in range(iterations):
        codec._serialize_msgpack(data)
    msgpack_time = (time.perf_counter() - start_time) / iterations
    results["msgpack"] = msgpack_time

    # Test Protobuf (placeholder)
    start_time = time.perf_counter()
    for _ in range(iterations):
        codec._serialize_protobuf(data)
    protobuf_time = (time.perf_counter() - start_time) / iterations
    results["protobuf"] = protobuf_time

    return results
