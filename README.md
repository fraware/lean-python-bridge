# Lean-Python Bridge for Scientific Computing

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Project Structure](#project-structure)
- [Prerequisites & Installation](#prerequisites--installation)
- [Usage](#usage)
  - [Lean Side](#lean-side)
  - [Python Side](#python-side)
- [Docker Usage](#docker-usage)
- [Testing & Verification](#testing--verification)
- [Security Considerations](#security-considerations)
- [Contributing](#contributing)
- [License](#license)

## Overview

This repository provides a production-ready prototype for formal verification of machine learning or scientific pipelines using **Lean 4** (a modern theorem prover and programming language) and **Python** (for numerical computations, data science, and ML libraries). Communication between Lean and Python is facilitated by **ZeroMQ**, offering reliable request-reply patterns with timeouts and retries (“Lazy Pirate”).

**Key Goals:**

- **Mathematically Rigor:** Prove key properties of transformations and models in Lean 4 (e.g., convexity, stability, nonnegativity).
- **Numerical Execution:** Offload heavy computations (e.g., summation, ML inference, dataset transformations) to Python.
- **Robust Communication:** Use ZeroMQ with built-in timeouts, retries, and error handling.
- **Extensibility:** Easily add new theorems in Lean or new Python libraries (NumPy, PyTorch, scikit-learn, etc.).

## Features

### Lean ↔ Python Bridge

- Native ZeroMQ FFI integration in Lean 4 (no separate Python client).
- **Advanced reliability patterns**: Lazy Pirate + Paranoid Pirate with heartbeats and correlation IDs.
- **Multi-format serialization**: Automatic selection between JSON, MessagePack, and Protocol Buffers.
- **Zero-copy data paths** for large numeric payloads (planned).

### Formal Proofs & Definitions

- **MathDefs.lean** for common mathematical abstractions (e.g., matrix sums).
- **MatrixProps.lean** with formal theorems (e.g., nonnegative matrix ⇒ nonnegative sum).

### Modular Codebase

- **PythonIntegration.lean** isolates IO bridging from mathematical logic.
- **Tests.lean** offers a built-in test harness for verifying proofs and integration.

### Structured Data & Serialization

- Python side uses `jsonschema` for data validation.
- `schema_version` field for schema evolution.
- **Intelligent format selection** based on payload size for optimal performance.
- **Special float handling** for NaN/Inf values across all formats.

### Performance & Benchmarking

- **Comprehensive benchmarking suite** measuring latency, throughput, and resource usage.
- **CI integration** with automated performance testing and regression detection.
- **Performance targets** with SLOs for P99 latency and throughput.

### Docker Container

- Includes Lean 4, ZeroMQ, Python environment.
- Ready for easy deployment.

### Automated CI

- GitHub Actions pipeline runs Lean build/tests and Python unit tests on each commit.
- **Performance benchmarking** integrated into CI pipeline.
- **Automated result analysis** with CSV exports and performance plots.

## Project Structure

```plaintext
lean-python-bridge/
├── lean
│   ├── lakefile.lean
│   ├── ffi
│   │   ├── LeanZMQ.c
│   │   ├── LeanZMQ.h
│   │   ├── LeanZMQ.lean         // ZeroMQ FFI binding
│   └── proofs
│       ├── MathDefs.lean        // Basic mathematical definitions
│       ├── MatrixProps.lean     // Formal theorems about matrices
│       ├── PythonIntegration.lean // ZeroMQ client logic (Lazy Pirate), calls to Python
│       ├── Tests.lean           // Lean test harness & examples
│       └── ExampleProof.lean    // Simple demonstration theorem
├── python
│   ├── src
│   │   ├── server.py            // ZeroMQ REP server that handles requests & computations
│   │   └── validation.py        // JSON schema validations
│   ├── tests
│   │   ├── test_server.py       // Integration test for server
├── Dockerfile
├── README.md
└── .github
    └── workflows
        └── ci.yml               // GitHub Actions pipeline
```

**Key Modules:**

- **Lean**

  - `MathDefs.lean`: Reusable definitions (lists, matrix sums, etc.).
  - `MatrixProps.lean`: Fully formal theorems (e.g., nonNegMatrixSum).
  - `PythonIntegration.lean`: All ZeroMQ bridging code.
  - `Tests.lean`: Test harness for verifying proofs and Python calls.

- **Python**

- `server.py`: ZeroMQ server with request-reply pattern.
- `validation.py`: JSON schema checks for structured data.

## Prerequisites & Installation

### Lean 4

Install from [Lean’s official docs](https://leanprover.github.io/).

### ZeroMQ

Install the ZeroMQ library & headers (e.g., `libzmq3-dev` on Ubuntu, `zeromq` on macOS via Homebrew, etc.).

### Python 3

Ensure you have `pyzmq`, `numpy`, and `jsonschema`.

Example:

```bash
pip install pyzmq numpy jsonschema
```

### C Toolchain

For compiling the FFI code (`LeanZMQ.c`) into a library. Usually gcc or clang.

Once dependencies are installed:

```bash
git clone https://github.com/YourUsername/lean-python-bridge.git
cd lean-python-bridge
```

## Usage

### Lean Side

1. **Build** the Lean library and FFI code:

```bash
cd lean
lake build
```

This compiles your Lean modules and builds the `libLeanZMQ.a` library from `LeanZMQ.c`.

2. **Run Proof & Integration Tests:**

```bash
 -- Option 1: Evaluate the test file directly
lean proofs/Tests.lean

 -- Option 2: Use Lake
lake exe Tests
```

3. **Result:**

- Lean verifies theorems like nonNegMatrixSum.
- Lean tries to call the Python server (via ZeroMQ).

### Python Side

1. **Launch** the ZeroMQ server:

```bash
cd python
python src/server.py
```

By default, it binds to `tcp://\*:5555.`

2. **(Optional)** Test the Python code with `pytest`:

```bash
pytest --maxfail=1 --disable-warnings -q
```

This runs integration tests (e.g., `test_server.py`).

## Docker Usage

A **Dockerfile** is provided for convenience. It installs Lean 4, ZeroMQ, Python, and dependencies.

1. **Build the image:**

```bash
docker build -t lean-python-bridge .
```

2. **Run the container:**

```bash
docker run --rm -p 5555:5555 lean-python-bridge
```

This starts the Python server inside the container, listening on port 5555. (You can adjust the `CMD` in the Dockerfile if you prefer running Lean from within the container, etc.)

## Testing & Verification

### Lean Tests

The file `Tests.lean` has `#eval` statements that verify key theorems and optionally call Python.  
You can also define a custom test harness using Lean 4’s unit test framework.

### Python Tests

Located in `python/tests/`.  
Run `pytest` to ensure the server handles data and schema validations correctly.

### Continuous Integration

A GitHub Actions workflow (`.github/workflows/ci.yml`) automatically builds the Lean code and runs tests on each push/pull request.  
Extending this with coverage reports or advanced QA checks is encouraged.

## Security Considerations

- **ZeroMQ Encryption**: Consider enabling CURVE security in both Lean (via FFI `setsockopt`) and Python for production scenarios with untrusted networks.
- **Data Validation**: The Python side uses `jsonschema` to ensure well-structured requests. For large or specialized data (e.g., big ML models), consider a binary format like Protocol Buffers.
- **Dependency Management**: Keep an eye on ZeroMQ, Lean, and Python dependencies. Perform regular security updates.

## Contributing

1. **Fork** this repo and create your feature branch.
2. **Implement** or refine proofs, add new Python features, or improve the bridging.
3. **Open a Pull Request** with a clear description of changes.
4. **Coordinate** with maintainers for reviews and merges.

Feel free to open issues for discussions or bug reports.

## License

MIT License.
