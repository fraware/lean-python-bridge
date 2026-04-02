import Lake
open System Lake DSL

package leanPythonBridge where
  description := "Lean 4 ↔ Python bridge over ZeroMQ: FFI bindings, formal proofs, and a Python numerical server."
  homepage := "https://github.com/fraware/lean-python-bridge"
  keywords := #["lean4", "python", "zeromq", "ffi", "formal-methods"]
  license := "MIT"
  readmeFile := "README.md"
  srcDir := "lean"

@[default_target]
lean_lib LeanPythonBridge where
  roots := #[
    `FFI.ZMQ,
    `MathDefs,
    `MatrixProps,
    `PythonIntegration,
    `Tests,
    `ExampleProof,
    `MLProofs
  ]
  precompileModules := true
  moreLinkArgs := #["-lzmq"]

target zmqffi_o (pkg : NPackage _package.name) : System.FilePath := do
  let oFile := pkg.buildDir / "ffi" / "LeanZMQ.o"
  let srcJob ← inputTextFile <| pkg.dir / "lean" / "FFI" / "LeanZMQ.c"
  -- Use system `cc` (not `leanc`) so glibc + libzmq headers resolve consistently on Linux.
  let weakArgs := #["-I", (pkg.dir / "lean" / "FFI").toString]
  let traceArgs := #["-fPIC"]
  buildO oFile srcJob weakArgs traceArgs

extern_lib leanZMQSupport (pkg : NPackage _package.name) := do
  let ffiO ← zmqffi_o.fetch
  let name := nameToStaticLib "LeanZMQ"
  -- NPackage does not expose staticLibDir; place the archive under the package build tree.
  buildStaticLib (pkg.buildDir / "lib" / name) #[ffiO]
