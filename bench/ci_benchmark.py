#!/usr/bin/env python3
"""
CI-friendly benchmark runner for GitHub Actions

This script runs benchmarks and outputs results in a format suitable for CI/CD pipelines.
"""

import json
import subprocess
import sys
import time
from pathlib import Path


def run_lean_benchmark():
    """Run the Lean-side benchmark"""
    print("Running Lean benchmark...")

    try:
        # Build the Lean project first
        subprocess.run(["cd lean && lake build"], shell=True, check=True)

        # Run the benchmark
        result = subprocess.run(
            ["lean", "bench/lean/TestBench.lean"],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )

        if result.returncode == 0:
            print("✓ Lean benchmark completed successfully")
            return True
        else:
            print(f"✗ Lean benchmark failed: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print("✗ Lean benchmark timed out")
        return False
    except Exception as e:
        print(f"✗ Lean benchmark error: {e}")
        return False


def run_python_benchmark():
    """Run the Python-side benchmark"""
    print("Running Python benchmark...")

    try:
        # Quick benchmark run
        result = subprocess.run(
            [
                "python",
                "bench/runner.py",
                "--duration",
                "30",
                "--payload-size",
                "1000",
                "--save-results",
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode == 0:
            print("✓ Python benchmark completed successfully")
            return True
        else:
            print(f"✗ Python benchmark failed: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print("✗ Python benchmark timed out")
        return False
    except Exception as e:
        print(f"✗ Python benchmark error: {e}")
        return False


def check_python_server():
    """Check if Python server is running"""
    print("Checking Python server availability...")

    try:
        import zmq

        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.RCVTIMEO, 2000)  # 2 second timeout
        socket.connect("tcp://127.0.0.1:5555")

        # Send test request
        test_payload = {
            "schema_version": 1,
            "matrix": [[1, 2], [3, 4]],
            "model": {"name": "TestModel", "version": "1.0"},
        }

        socket.send_string(json.dumps(test_payload))
        response = socket.recv_string()
        response_data = json.loads(response)

        if response_data.get("status") == "success":
            print("✓ Python server is responding")
            socket.close()
            context.term()
            return True
        else:
            print("✗ Python server returned error")
            socket.close()
            context.term()
            return False

    except Exception as e:
        print(f"✗ Python server check failed: {e}")
        return False


def generate_ci_summary():
    """Generate summary for CI"""
    summary = {
        "timestamp": time.time(),
        "benchmarks": {"lean": "pending", "python": "pending"},
        "server_status": "unknown",
        "overall_status": "pending",
    }

    # Check server first
    server_ok = check_python_server()
    summary["server_status"] = "running" if server_ok else "not_responding"

    if not server_ok:
        print("Warning: Python server not available, some benchmarks may fail")

    # Run benchmarks
    lean_ok = run_lean_benchmark()
    summary["benchmarks"]["lean"] = "passed" if lean_ok else "failed"

    python_ok = run_python_benchmark()
    summary["benchmarks"]["python"] = "passed" if python_ok else "failed"

    # Overall status
    if lean_ok and python_ok:
        summary["overall_status"] = "passed"
    else:
        summary["overall_status"] = "failed"

    # Save summary
    summary_file = Path("bench/results/ci_summary.json")
    summary_file.parent.mkdir(exist_ok=True)

    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2)

    # Print summary
    print("\n" + "=" * 50)
    print("CI BENCHMARK SUMMARY")
    print("=" * 50)
    print(f"Server Status: {summary['server_status']}")
    print(f"Lean Benchmark: {summary['benchmarks']['lean']}")
    print(f"Python Benchmark: {summary['benchmarks']['python']}")
    print(f"Overall Status: {summary['overall_status'].upper()}")
    print("=" * 50)

    return summary["overall_status"] == "passed"


def main():
    """Main CI benchmark runner"""
    print("Lean-Python Bridge CI Benchmark Runner")
    print("=====================================")

    success = generate_ci_summary()

    if success:
        print("\n✓ All benchmarks passed!")
        sys.exit(0)
    else:
        print("\n✗ Some benchmarks failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
