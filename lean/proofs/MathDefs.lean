import Lean

namespace MathDefs

structure Matrix where
  rows : List (List Int)
  deriving Repr

/--
  Sum all integers in a list.
  We'll define a standard function for summation on a list of Ints.
--/
def listSum (xs : List Int) : Int :=
  xs.foldl (fun acc x => acc + x) 0

/--
  Sum all elements in a matrix (list of lists).
--/
def matrixSum (M : Matrix) : Int :=
  M.rows.foldl (fun acc row => acc + listSum row) 0

/--
  A property stating that a matrix is "nonNegative"
  if every entry in the matrix is ≥ 0.
--/
def nonNegative (M : Matrix) : Prop :=
  ∀ (r c : Nat), (M.rows.get? r).bind (List.get? c) = some (x : Int) → x ≥ 0

end MathDefs
