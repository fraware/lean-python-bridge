import Lean
import MathDefs
import MatrixProps
import PythonIntegration

namespace Tests
open Lean
open MathDefs
open MatrixProps
open PythonIntegration
open IO

/--
  A test that verifies the formal proof of nonnegative matrix sum.
--/
def testNonNegMatrixProof : IO Unit := do
  let M : Matrix := { rows := [[1,2],[0,5],[3,4]] }
  /-
    We prove that M is nonNegative by construction.
    We'll do a simple "by rewrite" approach:
  -/
  let checkAllNonNeg : nonNegative M := by
    intro r c hSome
    match hSome with
    | some x =>
      -- We see that in the matrix, all entries are ≥ 0
      apply Nat.zero_le
    | none =>
      -- no value => no contradiction
      trivial

  -- Now confirm that `nonNegMatrixSum M checkAllNonNeg` is indeed ≥ 0
  let pf := nonNegMatrixSum M checkAllNonNeg
  IO.println s!"[TEST] The matrix sum is proven to be >= 0. => {pf}."

/--
  A test that calls the Python server to compute a matrix sum.
--/
def testPythonMatrixSum : IO Unit := do
  let M : Matrix := { rows := [[1,2],[3,4]] }
  IO.println "[TEST] Attempting to compute sum in Python..."
  callPythonMatrixSum M "TestModel" "0.1"

#eval testNonNegMatrixProof
#eval testPythonMatrixSum

end Tests
