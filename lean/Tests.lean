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

private theorem nonNegative_two_by_two :
    nonNegative (Matrix.mk [[1, 2], [3, 4]]) := by
  intro r c x hbind
  cases r with
  | zero =>
    cases c with
    | zero =>
      simp [Matrix, List.get?, Option.bind] at hbind
      rcases hbind with ⟨rfl⟩; decide
    | succ c =>
      cases c with
      | zero =>
        simp [Matrix, List.get?, Option.bind] at hbind
        rcases hbind with ⟨rfl⟩; decide
      | succ c =>
        simp [Matrix, List.get?, Option.bind] at hbind
  | succ r =>
    cases r with
    | zero =>
      cases c with
      | zero =>
        simp [Matrix, List.get?, Option.bind] at hbind
        rcases hbind with ⟨rfl⟩; decide
      | succ c =>
        cases c with
        | zero =>
          simp [Matrix, List.get?, Option.bind] at hbind
          rcases hbind with ⟨rfl⟩; decide
        | succ c =>
          simp [Matrix, List.get?, Option.bind] at hbind
    | succ r =>
      simp [Matrix, List.get?, Option.bind] at hbind

def testNonNegMatrixProof : IO Unit := do
  let M : Matrix := { rows := [[1, 2], [3, 4]] }
  have h : nonNegative M := by simpa [M] using nonNegative_two_by_two
  let _pf := nonNegMatrixSum M h
  IO.println "[TEST] nonnegative matrix sum holds (proof checked)"

def testPythonMatrixSum : IO Unit := do
  let M : Matrix := { rows := [[1, 2], [3, 4]] }
  IO.println "[TEST] Attempting to compute sum in Python..."
  let _ ← callPythonMatrixSum M "TestModel" "0.1"
  pure ()

end Tests
