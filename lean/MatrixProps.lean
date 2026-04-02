import MathDefs

namespace MatrixProps
open MathDefs

/--
  Theorem: If a matrix is `nonNegative`,
  then `matrixSum(M)` is ≥ 0.
--/
theorem nonNegMatrixSum (M : Matrix)
    (h : nonNegative M)
  : matrixSum M ≥ 0 := by
  exact matrixSum_nonneg_of_nonNegative M h

end MatrixProps
