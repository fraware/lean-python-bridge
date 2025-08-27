import zmq
import json
import logging
import numpy as np
import time
import threading
import multiprocessing
import queue
import os
import signal
from typing import Dict, Any, Optional
from dataclasses import dataclass
from concurrent.futures import ProcessPoolExecutor
from validation import validate_matrix_model
from codec import SerializationCodec

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
    worker_processes: int = max(1, multiprocessing.cpu_count() - 1)
    worker_threads: int = 4
    max_queue_size: int = 1000
    heartbeat_interval: float = 1.0
    request_timeout: int = 5000
    enable_metrics: bool = os.getenv("ENABLE_METRICS", "false").lower() == "true"
    enable_curve: bool = os.getenv("ENABLE_CURVE", "false").lower() == "true"


class WorkerPool:
    """Worker pool for handling requests"""

    def __init__(self, config: ServerConfig):
        self.config = config
        self.request_queue = queue.Queue(maxsize=config.max_queue_size)
        self.response_queue = queue.Queue()
        self.workers = []
        self.running = False

    def start(self):
        """Start worker processes and threads"""
        self.running = True

        # Start worker processes
        self.process_pool = ProcessPoolExecutor(
            max_workers=self.config.worker_processes,
            mp_context=multiprocessing.get_context("spawn"),
        )

        # Start worker threads
        for i in range(self.config.worker_processes):
            worker = threading.Thread(
                target=self._worker_thread, args=(i,), daemon=True
            )
            worker.start()
            self.workers.append(worker)

        logger.info(
            f"Started {self.config.worker_processes} processes and "
            f"{self.config.worker_threads} threads"
        )

    def stop(self):
        """Stop all workers"""
        self.running = False
        if hasattr(self, "process_pool"):
            self.process_pool.shutdown(wait=True)
        logger.info("Worker pool stopped")

    def _worker_thread(self, worker_id: int):
        """Worker thread function"""
        logger.info(f"Worker thread {worker_id} started")

        while self.running:
            try:
                # Get request from queue with timeout
                request_data = self.request_queue.get(timeout=1.0)
                if request_data is None:  # Shutdown signal
                    break

                client_id, correlation_id, payload = request_data

                # Process request
                start_time = time.time()
                try:
                    response = self._process_request(payload)
                    response["correlation_id"] = correlation_id
                    response["processing_time"] = time.time() - start_time
                except Exception as e:
                    logger.error(f"Error processing request {correlation_id}: {e}")
                    response = {
                        "status": "error",
                        "message": str(e),
                        "correlation_id": correlation_id,
                        "processing_time": time.time() - start_time,
                    }

                # Put response in response queue
                self.response_queue.put((client_id, response))

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Worker thread {worker_id} error: {e}")
                continue

        logger.info(f"Worker thread {worker_id} stopped")

    def _process_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single request"""
        # Validate payload
        if "payload" in payload:
            # New format with correlation ID
            data = payload["payload"]
        else:
            # Legacy format
            data = payload

        validate_matrix_model(data)

        # Extract data
        matrix = data["matrix"]
        model_info = data["model"]
        schema_version = data.get("schema_version", 1)

        # Process matrix using numpy
        np_mat = np.array(matrix, dtype=np.float64)
        sum_val = float(np_mat.sum())

        # Use codec for response
        codec = SerializationCodec()

        return {
            "status": "success",
            "matrix_sum": sum_val,
            "model_checked": model_info["name"],
            "schema_version_used": schema_version,
            "timestamp": time.time(),
            "matrix_shape": list(np_mat.shape),
            "data_type": str(np_mat.dtype),
        }

    def submit_request(
        self, client_id: str, correlation_id: str, payload: Dict[str, Any]
    ) -> bool:
        """Submit a request to the worker pool"""
        try:
            self.request_queue.put_nowait((client_id, correlation_id, payload))
            return True
        except queue.Full:
            logger.warning(f"Request queue full, rejecting request {correlation_id}")
            return False

    def get_response(self, timeout: float = 1.0) -> Optional[tuple]:
        """Get a response from the worker pool"""
        try:
            return self.response_queue.get(timeout=timeout)
        except queue.Empty:
            return None


class AdvancedServer:
    """Advanced server with ROUTER/DEALER pattern and worker pool"""

    def __init__(self, config: ServerConfig):
        self.config = config
        self.context = zmq.Context()
        self.frontend = None
        self.backend = None
        self.worker_pool = WorkerPool(config)
        self.running = False
        self.request_count = 0
        self.start_time = time.time()

        # Metrics
        self.metrics = {
            "requests_total": 0,
            "requests_success": 0,
            "requests_error": 0,
            "requests_rejected": 0,
            "avg_processing_time": 0.0,
            "queue_size": 0,
        }

    def setup_sockets(self):
        """Setup ROUTER/DEALER sockets"""
        # Frontend socket (ROUTER) - handles client connections
        self.frontend = self.context.socket(zmq.ROUTER)
        self.frontend.bind(self.config.endpoint)

        # Backend socket (DEALER) - distributes work to workers
        self.backend = self.context.socket(zmq.DEALER)
        self.backend.bind("inproc://backend")

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
            self.worker_pool.start()
            self.running = True

            # Start metrics collection
            if self.config.enable_metrics:
                self._start_metrics_collection()

            logger.info("Advanced server started successfully")

            # Main event loop
            self._main_loop()

        except Exception as e:
            logger.error(f"Server error: {e}")
            raise
        finally:
            self.cleanup()

    def _main_loop(self):
        """Main server event loop"""
        poller = zmq.Poller()
        poller.register(self.frontend, zmq.POLLIN)
        poller.register(self.backend, zmq.POLLIN)

        while self.running:
            try:
                events = dict(poller.poll(timeout=1000))

                # Handle frontend (client requests)
                if self.frontend in events:
                    self._handle_frontend()

                # Handle backend (worker responses)
                if self.backend in events:
                    self._handle_backend()

                # Handle worker pool responses
                self._handle_worker_responses()

                # Update metrics
                self._update_metrics()

            except KeyboardInterrupt:
                logger.info("Shutdown requested")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                continue

    def _handle_frontend(self):
        """Handle incoming client requests"""
        try:
            # Receive multipart message: [client_id, empty, correlation_id, payload]
            message = self.frontend.recv_multipart()
            if len(message) < 4:
                return

            client_id, empty, correlation_id, payload = message[:4]

            # Parse payload
            try:
                data = json.loads(payload.decode("utf-8"))
            except json.JSONDecodeError:
                self._send_error_response(client_id, correlation_id, "Invalid JSON")
                return

            # Check if it's a heartbeat
            if data == "HEARTBEAT":
                self._send_heartbeat_response(client_id)
                return

            # Submit to worker pool
            if self.worker_pool.submit_request(
                client_id.decode(), correlation_id.decode(), data
            ):
                self.metrics["requests_total"] += 1
            else:
                self.metrics["requests_rejected"] += 1
                self._send_error_response(
                    client_id, correlation_id, "Server overloaded"
                )

        except Exception as e:
            logger.error(f"Error handling frontend: {e}")

    def _handle_backend(self):
        """Handle worker responses"""
        try:
            message = self.backend.recv_multipart()
            if len(message) >= 2:
                worker_id, response = message[:2]
                # Forward response to frontend
                self.frontend.send_multipart([worker_id, b"", response])
        except Exception as e:
            logger.error(f"Error handling backend: {e}")

    def _handle_worker_responses(self):
        """Handle responses from worker pool"""
        while True:
            response = self.worker_pool.get_response(timeout=0.001)
            if response is None:
                break

            client_id, response_data = response

            # Send response to client
            try:
                response_bytes = json.dumps(response_data).encode("utf-8")
                self.frontend.send_multipart([client_id.encode(), b"", response_bytes])

                if response_data.get("status") == "success":
                    self.metrics["requests_success"] += 1
                else:
                    self.metrics["requests_error"] += 1

            except Exception as e:
                logger.error(f"Error sending response: {e}")

    def _send_error_response(
        self, client_id: bytes, correlation_id: bytes, message: str
    ):
        """Send error response to client"""
        error_response = {
            "status": "error",
            "message": message,
            "correlation_id": correlation_id.decode(),
            "timestamp": time.time(),
        }

        try:
            response_bytes = json.dumps(error_response).encode("utf-8")
            self.frontend.send_multipart([client_id, b"", response_bytes])
        except Exception as e:
            logger.error(f"Error sending error response: {e}")

    def _send_heartbeat_response(self, client_id: bytes):
        """Send heartbeat response"""
        heartbeat_response = {
            "status": "heartbeat_ack",
            "timestamp": time.time(),
            "server_id": f"server_{id(self)}",
        }

        try:
            response_bytes = json.dumps(heartbeat_response).encode("utf-8")
            self.frontend.send_multipart([client_id, b"", response_bytes])
        except Exception as e:
            logger.error(f"Error sending heartbeat: {e}")

    def _start_metrics_collection(self):
        """Start metrics collection thread"""

        def metrics_loop():
            while self.running:
                time.sleep(10)  # Update every 10 seconds
                self._update_metrics()

        metrics_thread = threading.Thread(target=metrics_loop, daemon=True)
        metrics_thread.start()

    def _update_metrics(self):
        """Update server metrics"""
        self.metrics["queue_size"] = self.worker_pool.request_queue.qsize()

        # Calculate average processing time
        if self.metrics["requests_success"] > 0:
            # This would need to be implemented with actual timing data
            pass

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

        if self.worker_pool:
            self.worker_pool.stop()

        if self.frontend:
            self.frontend.close()

        if self.backend:
            self.backend.close()

        if self.context:
            self.context.term()

        logger.info("Server cleanup completed")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Advanced Lean-Python Bridge Server")
    parser.add_argument("--dev", action="store_true", help="Development mode")
    parser.add_argument("--endpoint", default="tcp://*:5555", help="ZMQ endpoint")
    parser.add_argument(
        "--workers", type=int, default=None, help="Number of worker processes"
    )
    parser.add_argument(
        "--threads", type=int, default=None, help="Number of worker threads"
    )

    args = parser.parse_args()

    # Configuration
    config = ServerConfig(
        endpoint=args.endpoint,
        worker_processes=args.workers
        or (1 if args.dev else max(1, multiprocessing.cpu_count() - 1)),
        worker_threads=args.threads or (2 if args.dev else 4),
        enable_metrics=True,
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
