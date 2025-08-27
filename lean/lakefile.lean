import Lake
open Lake DSL

package leanPythonBridge {
  -- configure as needed
}

@[default_target]
lean_lib LeanPythonBridge {
  roots := #[
    `FFI.ZMQ,
    `MathDefs,
    `MatrixProps,
    `PythonIntegration,
    `Tests,
    `ExampleProof
  ]
}

-- Build the C FFI code for ZeroMQ
target zmqffi (pkg : Package) : FilePath := do
  let src := #[ "ffi/LeanZMQ.c" ]
  let oFiles ← src.mapM fun c =>
    buildO (pkg.buildDir / c, pkg.dir / c)
      #[ "-I", (pkg.dir / "ffi").toString,
         "-lzmq"
       ]
  buildStaticLib (pkg.buildDir / "libLeanZMQ.a") oFiles

extern_lib leanZMQSupport (pkg := leanPythonBridge) := do
  let zmqA := pkg.target zmqffi
  pure {
    name := "LeanZMQ"
    staticLibs := #[zmqA.get]
  }
