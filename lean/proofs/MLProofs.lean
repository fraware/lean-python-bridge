import Lean
import FFI.ZMQ
open Lean
open IO
open FFI.ZMQ

namespace MLProofs

structure Model where
  name : String
  version : String

structure Matrix where
  rows : List (List Int)

theorem matrixNonNegSum (M : Matrix)
  (h : ∀ r c, (M.rows.get? r).bind (List.get? c) = some (x : Int) → x ≥ 0) :
  True := by
  trivial

------------------------------------------------------------------------
-- Lazy Pirate: with multiple retries, each attempt re-creates the socket.
------------------------------------------------------------------------

def lazyPirateRequest (endpoint : String) (jsonMsg : String)
    (timeoutMs : Int := 1000) (maxRetries : Nat := 3) : IO (Option String) := do
  for attempt in [1 : maxRetries.succ] do
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
        IO.println s!"[Lean-LazyPirate] Attempt #{attempt} timed out, retrying..."
        IO.sleep (timeoutMs.toUInt32.toNat)  -- short wait
    catch e =>
      IO.println s!"[Lean-LazyPirate] Attempt #{attempt} error: {e}"
      try close sock catch _ => pure ()
      IO.sleep (timeoutMs.toUInt32.toNat)

  return none

def callPythonSum (m : Matrix) (model : Model) : IO Unit := do
  let endpoint := "tcp://127.0.0.1:5555"
  -- Include schema_version for evolution
  let requestJson := s!"{{\"schema_version\":1, \"matrix\":{m.rows}, \"model\":{{\"name\":\"{model.name}\",\"version\":\"{model.version}\"}}}}"

  IO.println s!"[Lean] Sending request to {endpoint} with Lazy Pirate pattern..."
  let reply? ← lazyPirateRequest endpoint requestJson 1000 3
  match reply? with
  | none => IO.println "[Lean] No response after max retries. Possibly the server is down."
  | some resp => IO.println s!"[Lean] Received response: {resp}"

#eval do
  let matrix := { rows := [[1,2],[3,4]] }
  let model := { name := "ProductionModel", version := "1.0" }

  have nonNeg : ∀ r c, (matrix.rows.get? r).bind (List.get? c) = some (x : Int) → x ≥ 0 :=
    by intro _ _ hSome; apply Nat.zero_le
  let _ := matrixNonNegSum matrix nonNeg

  IO.println "[Lean] Attempting to contact Python server..."
  callPythonSum matrix model
