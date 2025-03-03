namespace ExampleProof

theorem addZero (n : Nat) : n + 0 = n := by
  rfl

#eval IO.println "[ExampleProof] The theorem addZero compiles successfully!"

end ExampleProof
