import Lean
import FFI.ZMQ
import MathDefs
import PythonIntegration
open Lean
open IO
open FFI.ZMQ
open MathDefs
open PythonIntegration

namespace TestBench

/--
  Benchmark configuration for Lean-side testing
--/
structure BenchConfig where
  matrixSize : Nat
  iterations : Nat
  endpoint : String
  timeoutMs : Int
  maxRetries : Nat
  deriving Repr

/--
  Results from a benchmark run
--/
structure BenchResult where
  config : BenchConfig
  totalTime : Float
  avgLatency : Float
  minLatency : Float
  maxLatency : Float
  successCount : Nat
  errorCount : Nat
  throughput : Float
  deriving Repr

/--
  Default benchmark configuration
--/
def defaultConfig : BenchConfig := {
  matrixSize := 1000
  iterations := 100
  endpoint := "tcp://127.0.0.1:5555"
  timeoutMs := 5000
  maxRetries := 3
}

/--
  Generate a test matrix of specified size
--/
def generateTestMatrix (size : Nat) : Matrix := {
  rows := List.range size |>.map fun i =>
    List.range size |>.map fun j =>
      if i == j then 1 else 0
}

/--
  Measure execution time of a single operation
--/
def measureTime (op : IO α) : IO (Float × α) := do
  let start ← IO.monoMsNow
  let result ← op
  let end ← IO.monoMsNow
  let duration := (end - start).toFloat / 1000.0  -- Convert to seconds
  return (duration, result)

/--
  Run a single benchmark iteration
--/
def runSingleBenchmark (config : BenchConfig) : IO (Float × Option String) := do
  let matrix := generateTestMatrix config.matrixSize
  let modelName := s!"BenchmarkModel_{config.matrixSize}"
  let modelVer := "1.0"

  let (latency, result) ← measureTime <|
    callPythonMatrixSum matrix modelName modelVer

  return (latency, result)

/--
  Run complete benchmark suite
--/
def runBenchmark (config : BenchConfig) : IO BenchResult := do
  IO.println s!"Starting benchmark: {config.matrixSize}x{config.matrixSize} matrix, {config.iterations} iterations"

  let mut latencies : List Float := []
  let mut successCount : Nat := 0
  let mut errorCount : Nat := 0
  let startTime ← IO.monoMsNow

  -- Run iterations
  for i in List.range config.iterations do
    if i % 10 == 0 then
      IO.println s!"Progress: {i}/{config.iterations}"

    let (latency, result) ← runSingleBenchmark config
    latencies := latency :: latencies

    match result with
    | some _ => successCount := successCount + 1
    | none => errorCount := errorCount + 1

    -- Small delay to prevent overwhelming
    IO.sleep 1

  let endTime ← IO.monoMsNow
  let totalTime := (endTime - startTime).toFloat / 1000.0

  -- Calculate statistics
  let avgLatency := if latencies.isEmpty then 0.0 else
    latencies.foldl (· + ·) 0.0 / latencies.length.toFloat
  let minLatency := if latencies.isEmpty then 0.0 else
    latencies.foldl Float.min Float.inf
  let maxLatency := if latencies.isEmpty then 0.0 else
    latencies.foldl Float.max 0.0
  let throughput := successCount.toFloat / totalTime

  return {
    config := config
    totalTime := totalTime
    avgLatency := avgLatency
    minLatency := minLatency
    maxLatency := maxLatency
    successCount := successCount
    errorCount := errorCount
    throughput := throughput
  }

/--
  Print benchmark results in a formatted way
--/
def printResults (result : BenchResult) : IO Unit := do
  IO.println "\n" ++ "=".repeat 50
  IO.println "BENCHMARK RESULTS"
  IO.println "=".repeat 50
  IO.println s!"Matrix Size: {result.config.matrixSize}x{result.config.matrixSize}"
  IO.println s!"Iterations: {result.config.iterations}"
  IO.println s!"Total Time: {result.totalTime:.2f}s"
  IO.println s!"Success Rate: {result.successCount}/{result.config.iterations} ({result.successCount.toFloat / result.config.iterations.toFloat * 100.0:.1f}%)"
  IO.println s!"Throughput: {result.throughput:.2f} req/s"
  IO.println s!"Latency (avg): {result.avgLatency * 1000:.2f}ms"
  IO.println s!"Latency (min): {result.minLatency * 1000:.2f}ms"
  IO.println s!"Latency (max): {result.maxLatency * 1000:.2f}ms"
  IO.println "=".repeat 50

/--
  Run multiple benchmark configurations
--/
def runBenchmarkSuite : IO (List BenchResult) := do
  let configs := [
    { defaultConfig with matrixSize := 100, iterations := 50 },
    { defaultConfig with matrixSize := 1000, iterations := 30 },
    { defaultConfig with matrixSize := 5000, iterations := 10 }
  ]

  let mut results : List BenchResult := []

  for config in configs do
    IO.println s!"\n--- Testing {config.matrixSize}x{config.matrixSize} matrix ---"
    let result ← runBenchmark config
    results := result :: results
    printResults result

  return results.reverse

/--
  Function timing breakdown for Lean functions
--/
def profileFunctionTiming : IO Unit := do
  IO.println "\nProfiling individual function performance..."

  let matrix := generateTestMatrix 1000

  -- Profile matrix generation
  let (genTime, _) ← measureTime <| pure (generateTestMatrix 1000)
  IO.println s!"Matrix generation (1000x1000): {genTime * 1000:.2f}ms"

  -- Profile JSON serialization (approximate)
  let (serializeTime, _) ← measureTime <| pure <|
    s!"{{\"matrix\":{matrix.rows}, \"model\":{{\"name\":\"test\", \"version\":\"1.0\"}}}}"
  IO.println s!"JSON serialization: {serializeTime * 1000:.2f}ms"

  -- Profile ZMQ socket operations
  let (socketTime, sock) ← measureTime <| socket ZMQ_REQ
  IO.println s!"ZMQ socket creation: {socketTime * 1000:.2f}ms"

  let (connectTime, _) ← measureTime <| connect sock "tcp://127.0.0.1:5555"
  IO.println s!"ZMQ connect: {connectTime * 1000:.2f}ms"

  let (closeTime, _) ← measureTime <| close sock
  IO.println s!"ZMQ socket close: {closeTime * 1000:.2f}ms"

/--
  Main benchmark execution
--/
def main : IO Unit := do
  IO.println "Lean-Python Bridge Benchmark Suite"
  IO.println "================================="

  -- Check if Python server is reachable
  IO.println "Checking Python server availability..."
  let testMatrix := generateTestMatrix 10
  let testResult ← callPythonMatrixSum testMatrix "TestModel" "1.0"

  match testResult with
  | some _ => IO.println "✓ Python server is reachable"
  | none =>
    IO.println "✗ Python server is not reachable"
    IO.println "Please start the Python server first: python src/server.py"
    return

  -- Run function timing profile
  profileFunctionTiming

  -- Run benchmark suite
  let results ← runBenchmarkSuite

  -- Summary
  IO.println "\n" ++ "=".repeat 50
  IO.println "SUMMARY"
  IO.println "=".repeat 50
  for result in results do
    IO.println s!"{result.config.matrixSize}x{result.config.matrixSize}: {result.throughput:.1f} req/s, {result.avgLatency * 1000:.1f}ms avg latency"

  IO.println "=".repeat 50
  IO.println "Benchmark completed!"

#eval main

end TestBench
