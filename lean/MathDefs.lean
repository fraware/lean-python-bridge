import Lean

namespace MathDefs

structure Matrix where
  rows : List (List Int)
  deriving Repr

def listSum (xs : List Int) : Int :=
  xs.foldl (fun acc x => acc + x) 0

def matrixSum (M : Matrix) : Int :=
  M.rows.foldl (fun acc row => acc + listSum row) 0

def nonNegative (M : Matrix) : Prop :=
  ∀ (r c : Nat) (x : Int),
    (M.rows.get? r).bind (fun row => row.get? c) = some x → x ≥ 0

theorem nonNegative_of_mem (M : Matrix) (h : nonNegative M) :
    ∀ row ∈ M.rows, ∀ x ∈ row, 0 ≤ x := by
  intro row hRow x hX
  rcases (List.mem_iff_get?).1 hRow with ⟨r, hr⟩
  rcases (List.mem_iff_get?).1 hX with ⟨c, hc⟩
  have hbind :
      (M.rows.get? r).bind (fun row' => row'.get? c) = some x := by
    rw [hr]
    simpa [Option.bind] using hc
  exact h r c x hbind

private theorem foldl_int_add (xs : List Int) (a : Int) :
    xs.foldl (fun acc x => acc + x) a =
      a + xs.foldl (fun acc x => acc + x) 0 := by
  induction xs generalizing a with
  | nil => simp [List.foldl]
  | cons x xs ih =>
      simp [List.foldl]
      rw [ih (a + x), ih x]
      simp [Int.add_assoc]

theorem listSum_cons (x : Int) (xs : List Int) : listSum (x :: xs) = x + listSum xs := by
  simp [listSum, List.foldl]
  simpa using foldl_int_add xs x

theorem listSum_nonneg_of_forall_mem_nonneg (xs : List Int)
    (h : ∀ x ∈ xs, 0 ≤ x) : 0 ≤ listSum xs := by
  induction xs with
  | nil =>
      simp [listSum]
  | cons x xs ih =>
      have hx : 0 ≤ x := h x (by simp)
      have hxs : ∀ y ∈ xs, 0 ≤ y := by
        intro y hy
        exact h y (by simp [hy])
      have hs : 0 ≤ listSum xs := ih hxs
      rw [listSum_cons x xs]
      exact Int.add_nonneg hx hs

private theorem foldl_listSum_eq (rows : List (List Int)) (a : Int) :
    rows.foldl (fun acc row => acc + listSum row) a =
      a + rows.foldl (fun acc row => acc + listSum row) 0 := by
  induction rows generalizing a with
  | nil => simp [List.foldl]
  | cons r rows ih =>
      simp [List.foldl]
      rw [ih (a + listSum r), ih (listSum r)]
      ac_rfl

theorem matrixSum_cons (row : List Int) (rows : List (List Int)) :
    matrixSum { rows := row :: rows } = listSum row + matrixSum { rows := rows } := by
  simp [matrixSum, List.foldl]
  rw [foldl_listSum_eq rows (listSum row)]

theorem matrixSum_nonneg_of_nonNegative (M : Matrix) (h : nonNegative M) :
    0 ≤ matrixSum M := by
  suffices ∀ rows, nonNegative (Matrix.mk rows) → 0 ≤ matrixSum (Matrix.mk rows) by
    simpa [Matrix] using this M.rows h
  intro rows₀ h'
  induction rows₀ with
  | nil =>
      simp [matrixSum]
  | cons row rows ih =>
      have hM := h'
      have hRow : 0 ≤ listSum row := by
        apply listSum_nonneg_of_forall_mem_nonneg
        intro x hx
        have hm : row ∈ (Matrix.mk (row :: rows)).rows := by simp [Matrix]
        exact nonNegative_of_mem (Matrix.mk (row :: rows)) hM row hm x hx
      have hTailM : nonNegative (Matrix.mk rows) := by
        intro r c x hbind
        exact hM (Nat.succ r) c x hbind
      have hsum : 0 ≤ matrixSum (Matrix.mk rows) := ih hTailM
      rw [matrixSum_cons row rows]
      exact Int.add_nonneg hRow hsum

end MathDefs
