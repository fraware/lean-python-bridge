import argparse
import json
import logging
import os
import signal
import time
from dataclasses import dataclass
from typing import Any, Dict

import numpy as np
import zmq
from prometheus_client import Counter, Gauge, Histogram, start_http_server

from validation import validate_matrix_model

# Configure logging
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
)
logger = logging.getLogger(__name__)


@dataclass
class ServerConfig:
    """Server configuration"""

    endpoint: str = "tcp://*:5555"
    request_timeout: int = 5000
    enable_metrics: bool = os.getenv("ENABLE_METRICS", "false").lower() == "true"
    metrics_port: int = int(os.getenv("METRICS_PORT", "8000"))
    enable_curve: bool = os.getenv("ENABLE_CURVE", "false").lower() == "true"


class RequestValidationError(Exception):
    """Raised for invalid client payloads."""


class TransportError(Exception):
    """Raised for ZMQ transport issues."""


class AdvancedServer:
    """Production-grade REQ/REP server with metrics and typed errors."""

    def __init__(self, config: ServerConfig):
        self.config = config
        self.context = zmq.Context()
        self.frontend = None
        self.running = False
        self.start_time = time.time()
        self.processing_time_total = 0.0
        self.processing_count = 0
        self.metrics = {
            "requests_total": 0,
            "requests_success": 0,
            "requests_error": 0,
            "avg_processing_time": 0.0,
        }
        self._requests_total = Counter(
            "requests_total", "Total number of received requests"
        )
        self._requests_success = Counter(
            "requests_success", "Total number of successful requests"
        )
        self._requests_error = Counter("requests_error", "Total number of failed requests")
        self._request_duration = Histogram(
            "request_duration_seconds", "Request processing duration in seconds"
        )
        self._uptime_seconds = Gauge("server_uptime_seconds", "Server uptime in seconds")

    def setup_sockets(self):
        """Setup server socket."""
        self.frontend = self.context.socket(zmq.REP)
        self.frontend.setsockopt(zmq.RCVTIMEO, self.config.request_timeout)
        self.frontend.bind(self.config.endpoint)

        # Setup CURVE if enabled
        if self.config.enable_curve:
            self._setup_curve()

        logger.info(f"Server sockets bound to {self.config.endpoint}")

    def _setup_curve(self):
        """Setup CURVE encryption"""
        try:
            public_key = os.getenv("ZMQ_CURVE_PUBLICKEY")
            secret_key = os.getenv("ZMQ_CURVE_SECRETKEY")

            if public_key and secret_key:
                self.frontend.curve_secretkey = secret_key.encode()
                self.frontend.curve_publickey = public_key.encode()
                self.frontend.curve_server = True
                logger.info("CURVE encryption enabled")
            else:
                logger.warning("CURVE enabled but keys not provided")
        except Exception as e:
            logger.error(f"Failed to setup CURVE: {e}")

    def start(self):
        """Start the server"""
        try:
            self.setup_sockets()
            self.running = True

            if self.config.enable_metrics:
                start_http_server(self.config.metrics_port)
                logger.info("Prometheus metrics endpoint started on :%s", self.config.metrics_port)

            logger.info("Advanced server started successfully")

            # Main event loop
            self._main_loop()

        except Exception as e:
            logger.error(f"Server error: {e}")
            raise
        finally:
            self.cleanup()

    def _main_loop(self):
        """Main REQ/REP loop."""
        while self.running:
            try:
                request = self.frontend.recv()
                started = time.perf_counter()
                response = self._handle_request(request)
                elapsed = time.perf_counter() - started
                self._request_duration.observe(elapsed)
                self.processing_time_total += elapsed
                self.processing_count += 1
                self._update_metrics()
                self.frontend.send(response)

            except KeyboardInterrupt:
                logger.info("Shutdown requested")
                break
            except zmq.Again:
                self._update_metrics()
                continue
            except zmq.ZMQError as exc:
                logger.error("Transport error in main loop: %s", exc)
                raise TransportError(str(exc)) from exc
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                continue

    def _handle_request(self, request: bytes) -> bytes:
        """Handle one request and return encoded response bytes."""
        try:
            data = json.loads(request.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise RequestValidationError("Invalid JSON payload") from exc

        if data == "HEARTBEAT":
            return json.dumps(
                {"status": "heartbeat_ack", "timestamp": time.time(), "server_id": f"server_{id(self)}"}
            ).encode("utf-8")

        if isinstance(data, dict) and "payload" in data:
            correlation_id = data.get("correlation_id")
            payload = data["payload"]
        else:
            correlation_id = None
            payload = data

        try:
            validate_matrix_model(payload)
            matrix = payload["matrix"]
            model_info = payload["model"]
            schema_version = payload.get("schema_version", 1)
            np_mat = np.array(matrix, dtype=np.float64)
            body = {
                "status": "success",
                "matrix_sum": float(np_mat.sum()),
                "model_checked": model_info["name"],
                "schema_version_used": schema_version,
                "timestamp": time.time(),
                "matrix_shape": list(np_mat.shape),
                "data_type": str(np_mat.dtype),
            }
            if correlation_id is not None:
                body["correlation_id"] = correlation_id
            self.metrics["requests_total"] += 1
            self.metrics["requests_success"] += 1
            self._requests_total.inc()
            self._requests_success.inc()
            return json.dumps(body).encode("utf-8")
        except Exception as exc:
            self.metrics["requests_total"] += 1
            self.metrics["requests_error"] += 1
            self._requests_total.inc()
            self._requests_error.inc()
            error_body = {
                "status": "error",
                "message": str(exc),
                "timestamp": time.time(),
            }
            if correlation_id is not None:
                error_body["correlation_id"] = correlation_id
            return json.dumps(error_body).encode("utf-8")

    def _update_metrics(self):
        """Update server metrics"""
        if self.processing_count > 0:
            self.metrics["avg_processing_time"] = (
                self.processing_time_total / self.processing_count
            )
        self._uptime_seconds.set(time.time() - self.start_time)

    def get_metrics(self) -> Dict[str, Any]:
        """Get current server metrics"""
        uptime = time.time() - self.start_time
        return {
            **self.metrics,
            "uptime_seconds": uptime,
            "requests_per_second": (
                self.metrics["requests_total"] / uptime if uptime > 0 else 0
            ),
        }

    def cleanup(self):
        """Clean up server resources"""
        self.running = False

        if self.frontend is not None:
            self.frontend.close()
        if self.context is not None:
            self.context.term()

        logger.info("Server cleanup completed")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Advanced Lean-Python Bridge Server")
    parser.add_argument("--dev", action="store_true", help="Development mode")
    parser.add_argument("--endpoint", default="tcp://*:5555", help="ZMQ endpoint")
    parser.add_argument("--metrics-port", type=int, default=8000, help="Prometheus metrics port")

    args = parser.parse_args()

    # Configuration
    config = ServerConfig(
        endpoint=args.endpoint,
        enable_metrics=True,
        metrics_port=args.metrics_port,
        enable_curve=not args.dev,
    )

    # Create and start server
    server = AdvancedServer(config)

    # Signal handling
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        server.running = False

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        server.start()
    except KeyboardInterrupt:
        logger.info("Shutdown requested")
    finally:
        server.cleanup()


if __name__ == "__main__":
    main()
