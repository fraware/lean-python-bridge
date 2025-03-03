import Lean
import FFI.ZMQ
import MathDefs
open Lean
open IO
open FFI.ZMQ

namespace PythonIntegration

/--
  Lazy Pirate request with timeouts & retries
--/
def lazyPirateRequest (endpoint : String) (jsonMsg : String)
    (timeoutMs : Int := 1000) (maxRetries : Nat := 3) : IO (Option String) := do

  for attempt in [1 : maxRetries.succ] do
    let sock ← socket ZMQ_REQ
    try
      connect sock endpoint
      setRcvTimeout sock timeoutMs
      send sock jsonMsg
      let reply? ← recv sock
      close sock
      match reply? with
      | some r => return some r
      | none =>
        IO.println s!"[Lean-LazyPirate] Attempt #{attempt} timed out. Retrying..."
        IO.sleep (timeoutMs.toUInt32.toNat)
    catch e =>
      IO.println s!"[Lean-LazyPirate] Attempt #{attempt} error: {e}"
      try close sock catch _ => pure ()
      IO.sleep (timeoutMs.toUInt32.toNat)

  return none

/--
  Build JSON from a `Matrix` and model info,
  call Python to compute sum on the server side.
--/
def callPythonMatrixSum (m : MathDefs.Matrix) (modelName modelVer : String) : IO Unit := do
  let endpoint := "tcp://127.0.0.1:5555"
  let requestJson := s!"{{\"schema_version\":1, \"matrix\":{m.rows}, \"model\":{{\"name\":\"{modelName}\", \"version\":\"{modelVer}\"}}}}"
  IO.println s!"[Lean] Sending to {endpoint}"
  let reply? ← lazyPirateRequest endpoint requestJson
  match reply? with
  | none => IO.println "[Lean] No response after max retries."
  | some resp => IO.println s!"[Lean] Received: {resp}"

end PythonIntegration
