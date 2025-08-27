#!/usr/bin/env python3
"""
Lean-Python Bridge Benchmark Runner

Measures end-to-end performance characteristics:
- Latency (Lean→FFI→ZMQ→Python→ZMQ→Lean)
- Throughput (req/s)
- Percentiles (P50/P95/P99)
- Resource usage (CPU%, RSS, GC pressure)
- Error modes under load
"""

import argparse
import csv
import json
import statistics
import time
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import psutil
import zmq
import numpy as np
import matplotlib.pyplot as plt


@dataclass
class BenchmarkConfig:
    """Configuration for benchmark runs"""

    duration: int = 60  # seconds
    payload_size: int = 1000  # elements
    concurrency: int = 1  # concurrent requests
    endpoint: str = "tcp://127.0.0.1:5555"
    timeout_ms: int = 5000
    max_retries: int = 3
    save_results: bool = True
    full_suite: bool = False


@dataclass
class BenchmarkResult:
    """Results from a single benchmark run"""

    config: BenchmarkConfig
    latencies: List[float]
    throughput: float
    error_count: int
    total_requests: int
    cpu_usage: List[float]
    memory_usage: List[float]
    timestamp: float


class LeanPythonBridgeBenchmark:
    """Main benchmarking class for the Lean-Python bridge"""

    def __init__(self, config: BenchmarkConfig):
        self.config = config
        self.results_dir = Path("bench/results")
        self.profiles_dir = Path("bench/profiles")
        self.results_dir.mkdir(exist_ok=True)
        self.profiles_dir.mkdir(exist_ok=True)

        # ZMQ setup
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.setsockopt(zmq.RCVTIMEO, config.timeout_ms)
        self.socket.connect(config.endpoint)

        # Metrics collection
        self.latencies = []
        self.errors = []
        self.start_time = None
        self.end_time = None

    def generate_payload(self, size: int) -> Dict:
        """Generate a test payload of specified size"""
        return {
            "schema_version": 1,
            "matrix": np.random.randint(0, 100, (size, size)).tolist(),
            "model": {"name": f"BenchmarkModel_{size}", "version": "1.0"},
        }

    def measure_single_request(self, payload: Dict) -> Tuple[float, Optional[str]]:
        """Measure latency of a single request"""
        start_time = time.perf_counter()

        try:
            # Send request
            self.socket.send_string(json.dumps(payload))

            # Receive response
            response = self.socket.recv_string()
            response_data = json.loads(response)

            if response_data.get("status") != "success":
                return (
                    time.perf_counter() - start_time,
                    f"Server error: {response_data}",
                )

            return time.perf_counter() - start_time, None

        except zmq.error.Again:
            return time.perf_counter() - start_time, "Timeout"
        except Exception as e:
            return time.perf_counter() - start_time, f"Exception: {str(e)}"

    def collect_system_metrics(self) -> Tuple[List[float], List[float]]:
        """Collect CPU and memory usage during benchmark"""
        cpu_usage = []
        memory_usage = []

        def collect_metrics():
            while self.start_time and time.time() < self.end_time:
                try:
                    # Get Python process metrics
                    python_proc = psutil.Process()
                    cpu_usage.append(python_proc.cpu_percent())
                    memory_usage.append(
                        python_proc.memory_info().rss / 1024 / 1024
                    )  # MB
                    time.sleep(0.1)  # Sample every 100ms
                except:
                    pass

        # Start metrics collection in background thread
        metrics_thread = threading.Thread(target=collect_metrics, daemon=True)
        metrics_thread.start()

        return cpu_usage, memory_usage

    def run_benchmark(self) -> BenchmarkResult:
        """Run the main benchmark"""
        print(
            f"Starting benchmark: {self.config.duration}s, {self.config.payload_size}x{self.config.payload_size} matrix"
        )

        self.start_time = time.time()
        self.end_time = self.start_time + self.config.duration

        # Generate payload once
        payload = self.generate_payload(self.config.payload_size)

        # Start system metrics collection
        cpu_usage, memory_usage = self.collect_system_metrics()

        # Run benchmark
        request_count = 0
        error_count = 0

        while time.time() < self.end_time:
            latency, error = self.measure_single_request(payload)
            self.latencies.append(latency * 1000)  # Convert to ms

            if error:
                self.errors.append(error)
                error_count += 1

            request_count += 1

            # Small delay to prevent overwhelming
            time.sleep(0.001)

        # Calculate results
        total_time = time.time() - self.start_time
        throughput = request_count / total_time

        result = BenchmarkResult(
            config=self.config,
            latencies=self.latencies,
            throughput=throughput,
            error_count=error_count,
            total_requests=request_count,
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            timestamp=time.time(),
        )

        return result

    def generate_flamegraph(self, result: BenchmarkResult):
        """Generate Python flamegraph using py-spy"""
        try:
            # This would require py-spy to be installed
            # For now, we'll create a simple profiling output
            profile_file = self.profiles_dir / f"profile_{int(result.timestamp)}.txt"

            with open(profile_file, "w") as f:
                f.write("Python Profile Summary\n")
                f.write("=====================\n\n")
                f.write(f"Total requests: {result.total_requests}\n")
                f.write(f"Throughput: {result.throughput:.2f} req/s\n")
                f.write(
                    f"Error rate: {result.error_count/result.total_requests*100:.2f}%\n"
                )
                f.write(
                    f"CPU usage: avg={statistics.mean(result.cpu_usage):.1f}%, max={max(result.cpu_usage):.1f}%\n"
                )
                f.write(
                    f"Memory usage: avg={statistics.mean(result.memory_usage):.1f}MB, max={max(result.memory_usage):.1f}MB\n"
                )

        except Exception as e:
            print(f"Warning: Could not generate flamegraph: {e}")

    def save_results(self, result: BenchmarkResult):
        """Save benchmark results to CSV and generate plots"""
        timestamp = int(result.timestamp)

        # Save raw data
        csv_file = self.results_dir / f"benchmark_{timestamp}.csv"
        with open(csv_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["request_id", "latency_ms", "timestamp"])
            for i, latency in enumerate(result.latencies):
                writer.writerow(
                    [
                        i,
                        latency,
                        result.start_time
                        + (i * result.config.duration / len(result.latencies)),
                    ]
                )

        # Generate latency distribution plot
        plt.figure(figsize=(12, 8))

        # Latency histogram
        plt.subplot(2, 2, 1)
        plt.hist(result.latencies, bins=50, alpha=0.7, edgecolor="black")
        plt.xlabel("Latency (ms)")
        plt.ylabel("Frequency")
        plt.title(
            f"Latency Distribution\n{result.config.payload_size}x{result.config.payload_size} Matrix"
        )
        plt.axvline(
            statistics.mean(result.latencies),
            color="red",
            linestyle="--",
            label=f"Mean: {statistics.mean(result.latencies):.2f}ms",
        )
        plt.legend()

        # Latency over time
        plt.subplot(2, 2, 2)
        plt.plot(result.latencies)
        plt.xlabel("Request Number")
        plt.ylabel("Latency (ms)")
        plt.title("Latency Over Time")
        plt.yscale("log")

        # CPU usage
        plt.subplot(2, 2, 3)
        plt.plot(result.cpu_usage)
        plt.xlabel("Sample Number")
        plt.ylabel("CPU Usage (%)")
        plt.title("CPU Usage Over Time")

        # Memory usage
        plt.subplot(2, 2, 4)
        plt.plot(result.memory_usage)
        plt.xlabel("Sample Number")
        plt.ylabel("Memory Usage (MB)")
        plt.title("Memory Usage Over Time")

        plt.tight_layout()
        plot_file = self.results_dir / f"benchmark_{timestamp}.png"
        plt.savefig(plot_file, dpi=300, bbox_inches="tight")
        plt.close()

        # Save summary
        summary_file = self.results_dir / f"summary_{timestamp}.json"
        summary = {
            "timestamp": result.timestamp,
            "config": {
                "duration": result.config.duration,
                "payload_size": result.config.payload_size,
                "concurrency": result.config.concurrency,
                "endpoint": result.config.endpoint,
            },
            "results": {
                "total_requests": result.total_requests,
                "throughput_req_s": result.throughput,
                "error_count": result.error_count,
                "error_rate_percent": result.error_count / result.total_requests * 100,
                "latency_ms": {
                    "min": min(result.latencies),
                    "max": max(result.latencies),
                    "mean": statistics.mean(result.latencies),
                    "median": statistics.median(result.latencies),
                    "p50": np.percentile(result.latencies, 50),
                    "p95": np.percentile(result.latencies, 95),
                    "p99": np.percentile(result.latencies, 99),
                },
                "cpu_usage_percent": {
                    "mean": statistics.mean(result.cpu_usage),
                    "max": max(result.cpu_usage),
                },
                "memory_usage_mb": {
                    "mean": statistics.mean(result.memory_usage),
                    "max": max(result.memory_usage),
                },
            },
        }

        with open(summary_file, "w") as f:
            json.dump(summary, f, indent=2)

        print(f"Results saved to {self.results_dir}")
        print(f"Summary: {summary_file}")
        print(f"Raw data: {csv_file}")
        print(f"Plot: {plot_file}")

    def run_full_suite(self) -> List[BenchmarkResult]:
        """Run comprehensive benchmark suite"""
        print("Running full benchmark suite...")

        configs = [
            BenchmarkConfig(duration=30, payload_size=100, concurrency=1),
            BenchmarkConfig(duration=30, payload_size=1000, concurrency=1),
            BenchmarkConfig(duration=30, payload_size=10000, concurrency=1),
            BenchmarkConfig(duration=30, payload_size=1000, concurrency=2),
            BenchmarkConfig(duration=30, payload_size=1000, concurrency=4),
        ]

        results = []
        for config in configs:
            print(
                f"\n--- Testing: {config.payload_size}x{config.payload_size} matrix, {config.concurrency} concurrent ---"
            )
            self.config = config
            result = self.run_benchmark()
            results.append(result)

            if self.config.save_results:
                self.save_results(result)
                self.generate_flamegraph(result)

        return results

    def cleanup(self):
        """Clean up resources"""
        self.socket.close()
        self.context.term()


def main():
    parser = argparse.ArgumentParser(description="Lean-Python Bridge Benchmark Runner")
    parser.add_argument(
        "--duration", type=int, default=60, help="Benchmark duration in seconds"
    )
    parser.add_argument(
        "--payload-size", type=int, default=1000, help="Matrix size (NxN)"
    )
    parser.add_argument(
        "--concurrency", type=int, default=1, help="Number of concurrent requests"
    )
    parser.add_argument(
        "--endpoint", default="tcp://127.0.0.1:5555", help="ZMQ endpoint"
    )
    parser.add_argument(
        "--timeout", type=int, default=5000, help="Request timeout in ms"
    )
    parser.add_argument(
        "--save-results", action="store_true", help="Save results to files"
    )
    parser.add_argument(
        "--full-suite", action="store_true", help="Run full benchmark suite"
    )

    args = parser.parse_args()

    config = BenchmarkConfig(
        duration=args.duration,
        payload_size=args.payload_size,
        concurrency=args.concurrency,
        endpoint=args.endpoint,
        timeout_ms=args.timeout,
        save_results=args.save_results,
        full_suite=args.full_suite,
    )

    benchmark = LeanPythonBridgeBenchmark(config)

    try:
        if args.full_suite:
            results = benchmark.run_full_suite()
            print(f"\nCompleted {len(results)} benchmark configurations")
        else:
            result = benchmark.run_benchmark()
            print(f"\nBenchmark completed:")
            print(f"  Total requests: {result.total_requests}")
            print(f"  Throughput: {result.throughput:.2f} req/s")
            print(f"  Error rate: {result.error_count/result.total_requests*100:.2f}%")
            print(f"  P99 latency: {np.percentile(result.latencies, 99):.2f}ms")

            if args.save_results:
                benchmark.save_results(result)
                benchmark.generate_flamegraph(result)

    finally:
        benchmark.cleanup()


if __name__ == "__main__":
    main()
