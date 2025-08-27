#!/usr/bin/env python3
"""
Serialization Format Benchmark

Compares performance of JSON, MessagePack, and Protocol Buffers
for various payload sizes and types.
"""

import time
import json
import msgpack
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python", "src"))

from codec import SerializationCodec, benchmark_formats, CodecConfig


def generate_test_data(size: int, data_type: str = "matrix") -> dict:
    """Generate test data of specified size and type"""
    if data_type == "matrix":
        # Generate NxN matrix
        n = int(np.sqrt(size))
        matrix = np.random.rand(n, n).tolist()
        return {
            "schema_version": 1,
            "matrix": matrix,
            "model": {"name": f"TestModel_{size}", "version": "1.0"},
        }
    elif data_type == "vector":
        # Generate vector
        vector = np.random.rand(size).tolist()
        return {
            "schema_version": 1,
            "vector": vector,
            "model": {"name": f"TestModel_{size}", "version": "1.0"},
        }
    elif data_type == "mixed":
        # Generate mixed data structure
        return {
            "schema_version": 1,
            "metadata": {
                "timestamp": time.time(),
                "user_id": "test_user",
                "session_id": "session_123",
            },
            "data": {
                "features": np.random.rand(size // 2).tolist(),
                "labels": np.random.randint(0, 10, size // 2).tolist(),
                "weights": np.random.rand(size // 4).tolist(),
            },
            "model": {
                "name": f"TestModel_{size}",
                "version": "1.0",
                "parameters": {"learning_rate": 0.001, "batch_size": 32, "epochs": 100},
            },
        }
    else:
        raise ValueError(f"Unknown data type: {data_type}")


def benchmark_serialization_speed(data: dict, iterations: int = 1000) -> dict:
    """Benchmark serialization speed for different formats"""
    print(f"Benchmarking serialization for {len(str(data))} bytes of data...")

    results = {}

    # Test JSON
    start_time = time.perf_counter()
    for _ in range(iterations):
        json.dumps(data, separators=(",", ":"))
    json_time = (time.perf_counter() - start_time) / iterations
    results["json"] = json_time

    # Test MessagePack
    try:
        start_time = time.perf_counter()
        for _ in range(iterations):
            msgpack.packb(data, use_bin_type=True)
        msgpack_time = (time.perf_counter() - start_time) / iterations
        results["msgpack"] = msgpack_time
    except Exception as e:
        print(f"MessagePack failed: {e}")
        results["msgpack"] = float("inf")

    # Test our codec
    try:
        codec = SerializationCodec()
        start_time = time.perf_counter()
        for _ in range(iterations):
            codec.serialize(data)
        codec_time = (time.perf_counter() - start_time) / iterations
        results["codec"] = codec_time
    except Exception as e:
        print(f"Codec failed: {e}")
        results["codec"] = float("inf")

    return results


def benchmark_deserialization_speed(data: dict, iterations: int = 1000) -> dict:
    """Benchmark deserialization speed for different formats"""
    print(f"Benchmarking deserialization for {len(str(data))} bytes of data...")

    results = {}

    # Prepare serialized data
    json_data = json.dumps(data, separators=(",", ":")).encode("utf-8")

    try:
        msgpack_data = msgpack.packb(data, use_bin_type=True)
    except Exception as e:
        print(f"MessagePack serialization failed: {e}")
        msgpack_data = b""

    try:
        codec = SerializationCodec()
        codec_data = codec.serialize(data)
    except Exception as e:
        print(f"Codec serialization failed: {e}")
        codec_data = b""

    # Test JSON deserialization
    start_time = time.perf_counter()
    for _ in range(iterations):
        json.loads(json_data.decode("utf-8"))
    json_time = (time.perf_counter() - start_time) / iterations
    results["json"] = json_time

    # Test MessagePack deserialization
    if msgpack_data:
        try:
            start_time = time.perf_counter()
            for _ in range(iterations):
                msgpack.unpackb(msgpack_data, raw=False)
            msgpack_time = (time.perf_counter() - start_time) / iterations
            results["msgpack"] = msgpack_time
        except Exception as e:
            print(f"MessagePack deserialization failed: {e}")
            results["msgpack"] = float("inf")
    else:
        results["msgpack"] = float("inf")

    # Test codec deserialization
    if codec_data:
        try:
            start_time = time.perf_counter()
            for _ in range(iterations):
                codec.deserialize(codec_data)
            codec_time = (time.perf_counter() - start_time) / iterations
            results["codec"] = codec_time
        except Exception as e:
            print(f"Codec deserialization failed: {e}")
            results["codec"] = float("inf")
    else:
        results["codec"] = float("inf")

    return results


def benchmark_memory_usage(data: dict, iterations: int = 100) -> dict:
    """Benchmark memory usage for different formats"""
    print(f"Benchmarking memory usage for {len(str(data))} bytes of data...")

    import psutil
    import gc

    results = {}

    # Test JSON
    gc.collect()
    process = psutil.Process()
    mem_before = process.memory_info().rss

    for _ in range(iterations):
        json.dumps(data, separators=(",", ":"))

    gc.collect()
    mem_after = process.memory_info().rss
    results["json"] = (mem_after - mem_before) / iterations

    # Test MessagePack
    gc.collect()
    mem_before = process.memory_info().rss

    try:
        for _ in range(iterations):
            msgpack.packb(data, use_bin_type=True)

        gc.collect()
        mem_after = process.memory_info().rss
        results["msgpack"] = (mem_after - mem_before) / iterations
    except Exception as e:
        print(f"MessagePack memory test failed: {e}")
        results["msgpack"] = float("inf")

    # Test codec
    gc.collect()
    mem_before = process.memory_info().rss

    try:
        codec = SerializationCodec()
        for _ in range(iterations):
            codec.serialize(data)

        gc.collect()
        mem_after = process.memory_info().rss
        results["codec"] = (mem_after - mem_before) / iterations
    except Exception as e:
        print(f"Codec memory test failed: {e}")
        results["codec"] = float("inf")

    return results


def run_comprehensive_benchmark():
    """Run comprehensive benchmark across different data sizes and types"""
    print("Lean-Python Bridge Serialization Benchmark")
    print("=" * 50)

    # Test configurations
    sizes = [100, 1000, 10000, 100000]
    data_types = ["matrix", "vector", "mixed"]

    all_results = {}

    for data_type in data_types:
        print(f"\n--- Testing {data_type} data ---")
        all_results[data_type] = {}

        for size in sizes:
            print(f"\nSize: {size} elements")

            # Generate test data
            data = generate_test_data(size, data_type)

            # Run benchmarks
            serialization_results = benchmark_serialization_speed(data, 100)
            deserialization_results = benchmark_deserialization_speed(data, 100)
            memory_results = benchmark_memory_usage(data, 50)

            # Store results
            all_results[data_type][size] = {
                "serialization": serialization_results,
                "deserialization": deserialization_results,
                "memory": memory_results,
                "data_size_bytes": len(str(data)),
            }

            # Print summary
            print(f"  Data size: {len(str(data))} bytes")
            print(
                f"  Serialization (μs): JSON={serialization_results['json']*1e6:.2f}, "
                f"MsgPack={serialization_results['msgpack']*1e6:.2f}, "
                f"Codec={serialization_results['codec']*1e6:.2f}"
            )
            print(
                f"  Deserialization (μs): JSON={deserialization_results['json']*1e6:.2f}, "
                f"MsgPack={deserialization_results['msgpack']*1e6:.2f}, "
                f"Codec={deserialization_results['codec']*1e6:.2f}"
            )

    return all_results


def generate_plots(results: dict):
    """Generate performance comparison plots"""
    print("\nGenerating performance plots...")

    # Create results directory
    results_dir = Path("bench/results")
    results_dir.mkdir(exist_ok=True)

    # Plot serialization performance
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle("Serialization Performance Comparison", fontsize=16)

    for i, data_type in enumerate(["matrix", "vector", "mixed"]):
        if i >= 3:
            break

        ax = axes[i // 2, i % 2]
        sizes = list(results[data_type].keys())

        json_times = [
            results[data_type][size]["serialization"]["json"] * 1e6 for size in sizes
        ]
        msgpack_times = [
            results[data_type][size]["serialization"]["msgpack"] * 1e6 for size in sizes
        ]
        codec_times = [
            results[data_type][size]["serialization"]["codec"] * 1e6 for size in sizes
        ]

        ax.plot(sizes, json_times, "o-", label="JSON", linewidth=2)
        ax.plot(sizes, msgpack_times, "s-", label="MessagePack", linewidth=2)
        ax.plot(sizes, codec_times, "^-", label="Codec", linewidth=2)

        ax.set_xlabel("Data Size (elements)")
        ax.set_ylabel("Serialization Time (μs)")
        ax.set_title(f"{data_type.capitalize()} Data")
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_xscale("log")
        ax.set_yscale("log")

    # Memory usage plot
    ax = axes[1, 1]
    data_type = "matrix"  # Use matrix for memory plot
    sizes = list(results[data_type].keys())

    json_memory = [results[data_type][size]["memory"]["json"] / 1024 for size in sizes]
    msgpack_memory = [
        results[data_type][size]["memory"]["msgpack"] / 1024 for size in sizes
    ]
    codec_memory = [
        results[data_type][size]["memory"]["codec"] / 1024 for size in sizes
    ]

    ax.plot(sizes, json_memory, "o-", label="JSON", linewidth=2)
    ax.plot(sizes, msgpack_memory, "s-", label="MessagePack", linewidth=2)
    ax.plot(sizes, codec_memory, "^-", label="Codec", linewidth=2)

    ax.set_xlabel("Data Size (elements)")
    ax.set_ylabel("Memory Usage (KB)")
    ax.set_title("Memory Usage")
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_xscale("log")

    plt.tight_layout()
    plot_file = results_dir / "serialization_performance.png"
    plt.savefig(plot_file, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"Plots saved to: {plot_file}")


def save_results(results: dict):
    """Save benchmark results to JSON file"""
    import json as json_lib

    results_dir = Path("bench/results")
    results_dir.mkdir(exist_ok=True)

    # Convert numpy types to native Python types for JSON serialization
    def convert_numpy(obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return obj

    # Clean results for JSON serialization
    clean_results = {}
    for data_type, type_results in results.items():
        clean_results[data_type] = {}
        for size, size_results in type_results.items():
            clean_results[data_type][size] = {}
            for metric, metric_results in size_results.items():
                if isinstance(metric_results, dict):
                    clean_results[data_type][size][metric] = {
                        k: convert_numpy(v) for k, v in metric_results.items()
                    }
                else:
                    clean_results[data_type][size][metric] = convert_numpy(
                        metric_results
                    )

    results_file = results_dir / "serialization_benchmark_results.json"
    with open(results_file, "w") as f:
        json_lib.dump(clean_results, f, indent=2)

    print(f"Results saved to: {results_file}")


def main():
    """Main benchmark execution"""
    print("Starting serialization benchmark...")

    try:
        # Run comprehensive benchmark
        results = run_comprehensive_benchmark()

        # Generate plots
        generate_plots(results)

        # Save results
        save_results(results)

        print("\nBenchmark completed successfully!")

        # Print summary
        print("\nSummary:")
        for data_type in ["matrix", "vector", "mixed"]:
            if data_type in results:
                print(f"\n{data_type.capitalize()} data:")
                for size in [100, 1000, 10000, 100000]:
                    if size in results[data_type]:
                        json_time = (
                            results[data_type][size]["serialization"]["json"] * 1e6
                        )
                        msgpack_time = (
                            results[data_type][size]["serialization"]["msgpack"] * 1e6
                        )
                        if msgpack_time != float("inf"):
                            speedup = json_time / msgpack_time
                            print(
                                f"  {size} elements: {speedup:.1f}x speedup with MessagePack"
                            )

    except Exception as e:
        print(f"Benchmark failed: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
