import Lean
import FFI.ZMQ
import MathDefs
import MatrixProps
open Lean
open IO
open FFI.ZMQ
open MathDefs

namespace MLProofs

structure Model where
  name : String
  version : String

theorem matrixNonNegSum (M : Matrix) (h : nonNegative M) : 0 ≤ matrixSum M :=
  MatrixProps.nonNegMatrixSum M h

private def intMsToUInt32 (ms : Int) : UInt32 :=
  UInt32.ofNat (Nat.min (Int.natAbs ms) 1000000)

def lazyPirateRequest (endpoint : String) (jsonMsg : String)
    (timeoutMs : Int := 1000) (maxRetries : Nat := 3) : IO (Option String) := do
  for attempt in List.range maxRetries do
    let attemptNr := attempt + 1
    let sock ← socket ZMQ_REQ
    try
      connect sock endpoint
      setRcvTimeout sock timeoutMs

      send sock jsonMsg
      let reply ← recv sock
      close sock

      match reply with
      | some resp => return some resp
      | none =>
        IO.println s!"[Lean-LazyPirate] Attempt #{attemptNr} timed out, retrying..."
        IO.sleep (intMsToUInt32 timeoutMs)
    catch e =>
      IO.println s!"[Lean-LazyPirate] Attempt #{attemptNr} error: {e}"
      try close sock catch _ => pure ()
      IO.sleep (intMsToUInt32 timeoutMs)

  return none

def callPythonSum (m : Matrix) (model : Model) : IO Unit := do
  let endpoint := "tcp://127.0.0.1:5555"
  let requestJson :=
    "{\"schema_version\":1, \"matrix\":" ++ toString (repr m.rows) ++
    ", \"model\":{\"name\":\"" ++ model.name ++ "\",\"version\":\"" ++ model.version ++ "\"}}"

  IO.println s!"[Lean] Sending request to {endpoint} with Lazy Pirate pattern..."
  let reply? ← lazyPirateRequest endpoint requestJson 1000 3
  match reply? with
  | none => IO.println "[Lean] No response after max retries. Possibly the server is down."
  | some resp => IO.println s!"[Lean] Received response: {resp}"

end MLProofs
