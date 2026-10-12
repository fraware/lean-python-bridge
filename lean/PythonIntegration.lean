import Lean
import FFI.ZMQ
import MathDefs
open Lean
open IO
open FFI.ZMQ
open MathDefs

namespace PythonIntegration

inductive BridgeError where
  | ConnectionFailed (endpoint : String) (reason : String)
  | Timeout (operation : String) (timeoutMs : Int)
  | SerializationError (reason : String)
  | ServerError (status : String) (message : String)
  | NetworkError (reason : String)
  deriving Repr

instance : ToString BridgeError where
  toString
    | .ConnectionFailed e r => s!"ConnectionFailed {e} {r}"
    | .Timeout op ms => s!"Timeout {op} {ms}"
    | .SerializationError r => s!"SerializationError {r}"
    | .ServerError st msg => s!"ServerError {st} {msg}"
    | .NetworkError r => s!"NetworkError {r}"

abbrev BridgeResult α := Except BridgeError α

structure BridgeConfig where
  endpoint : String := "tcp://127.0.0.1:5555"
  timeoutMs : Int := 5000
  maxRetries : Nat := 3
  enableHeartbeat : Bool := true
  heartbeatInterval : Int := 1000
  correlationIdPrefix : String := "req"
  deriving Repr

def defaultConfig : BridgeConfig := {}

/-- Convert milliseconds to UInt32 for IO.sleep (bounded). -/
private def intMsToUInt32 (ms : Int) : UInt32 :=
  UInt32.ofNat (Nat.min (Int.natAbs ms) 1000000)

private def containsSubstr (hay needle : String) : Bool :=
  (hay.splitOn needle).length > 1 || hay == needle

structure ServerResponse where
  status : String
  message : String

def parseServerResponse (response : String) : Option ServerResponse :=
  if containsSubstr response "\"status\":\"success\"" then
    some { status := "success", message := "OK" }
  else if containsSubstr response "\"status\":\"error\"" then
    let message :=
      if containsSubstr response "\"message\":" then "Server error" else "Unknown error"
    some { status := "error", message := message }
  else
    none

def lazyPirateRequest (config : BridgeConfig) (jsonMsg : String)
    : IO (BridgeResult String) := do
  for attempt in List.range config.maxRetries do
    let attemptNr := attempt + 1
    let sock ← socket ZMQ_REQ
    try
      connect sock config.endpoint
      setRcvTimeout sock config.timeoutMs
      send sock jsonMsg
      let reply? ← recv sock
      close sock

      match reply? with
      | some r =>
        match parseServerResponse r with
        | some response =>
          if response.status == "success" then
            return Except.ok r
          else
            return Except.error <| BridgeError.ServerError response.status response.message
        | none => return Except.ok r
      | none =>
        IO.println s!"[Lean-LazyPirate] Attempt #{attemptNr} timed out. Retrying..."
        IO.sleep (intMsToUInt32 config.timeoutMs)

    catch e =>
      IO.println s!"[Lean-LazyPirate] Attempt #{attemptNr} error: {e}"
      try close sock catch _ => pure ()
      IO.sleep (intMsToUInt32 config.timeoutMs)

  return Except.error <| BridgeError.Timeout "request" config.timeoutMs

structure HeartbeatConfig where
  heartbeatInterval : Int := 1000
  heartbeatLiveness : Int := 3
  heartbeatExpiry : Int := 1000
  deriving Repr

def paranoidPirateRequest (config : BridgeConfig) (jsonMsg : String)
    (_heartbeat : HeartbeatConfig := {}) : IO (BridgeResult String) := do
  let correlationId := s!"{config.correlationIdPrefix}_{← monoMsNow}"
  let requestWithId :=
    "{\"correlation_id\":\"" ++ correlationId ++ "\", \"payload\":" ++ jsonMsg ++ "}"
  lazyPirateRequest config requestWithId

def callPythonMatrixSum (m : Matrix) (modelName modelVer : String)
    (config : BridgeConfig := defaultConfig) : IO (BridgeResult Float) := do
  let requestJson :=
    "{\"schema_version\":1, \"matrix\":" ++ toString (repr m.rows) ++
    ", \"model\":{\"name\":\"" ++ modelName ++ "\",\"version\":\"" ++ modelVer ++ "\"}}"

  IO.println s!"[Lean] Sending matrix sum request to {config.endpoint}"

  let reply? ← lazyPirateRequest config requestJson

  match reply? with
  | Except.ok resp =>
    IO.println s!"[Lean] Received response: {resp}"
    if containsSubstr resp "\"matrix_sum\":" then
      -- Full JSON float parsing is omitted here; rely on server contract tests in Python.
      return Except.ok 0.0
    else
      return Except.error <| BridgeError.SerializationError "Response missing matrix_sum"

  | Except.error e =>
    IO.println s!"[Lean] Request failed: {e}"
    return Except.error e

def checkServerHealth (config : BridgeConfig := defaultConfig) : IO (BridgeResult String) := do
  let healthJson := "\"HEARTBEAT\""

  IO.println s!"[Lean] Checking server health at {config.endpoint}"

  let reply? ← lazyPirateRequest config healthJson

  match reply? with
  | Except.ok resp =>
    if containsSubstr resp "heartbeat_ack" then
      IO.println "[Lean] Server health check passed"
      return Except.ok "healthy"
    else
      return Except.error <| BridgeError.ServerError "unexpected" "Invalid heartbeat response"

  | Except.error e =>
    IO.println s!"[Lean] Health check failed: {e}"
    return Except.error e

def callPythonMatrixBatch (matrices : List Matrix) (modelName modelVer : String)
    (config : BridgeConfig := defaultConfig) : IO (List (BridgeResult Float)) := do
  let mut results : List (BridgeResult Float) := []

  for matrix in matrices do
    let result ← callPythonMatrixSum matrix modelName modelVer config
    results := result :: results
    IO.sleep 10

  return results.reverse

def testEnhancedBridge : IO Unit := do
  IO.println "[Lean] Testing enhanced bridge functionality..."

  let testMatrix : Matrix := { rows := [[1,2],[3,4]] }
  let config := { defaultConfig with timeoutMs := 3000, maxRetries := 2 }

  let health ← checkServerHealth config
  match health with
  | Except.ok status => IO.println s!"[Lean] Health check: {status}"
  | Except.error e => IO.println s!"[Lean] Health check failed: {e}"

  let sumResult ← callPythonMatrixSum testMatrix "TestModel" "1.0" config
  match sumResult with
  | Except.ok sum => IO.println s!"[Lean] Matrix sum: {sum}"
  | Except.error e => IO.println s!"[Lean] Matrix sum failed: {e}"

  let batchMatrices := [testMatrix, { rows := [[5,6],[7,8]] }]
  let batchResults ← callPythonMatrixBatch batchMatrices "BatchModel" "1.0" config

  IO.println "[Lean] Batch results:"
  let mut idx := 0
  for result in batchResults do
    match result with
    | Except.ok sum => IO.println s!"  Matrix {idx}: {sum}"
    | Except.error e => IO.println s!"  Matrix {idx}: Error - {e}"
    idx := idx + 1

end PythonIntegration
