import Lean

namespace FFI.ZMQ

@[extern "lean_zmq_init"]
opaque initZmq : IO Unit

@[extern "lean_zmq_socket"]
opaque c_socket (socketType : UInt32) : IO UInt64

@[extern "lean_zmq_close"]
opaque c_close (sock : UInt64) : IO Int

@[extern "lean_zmq_bind"]
opaque c_bind (sock : UInt64) (endpoint : @& String) : IO Int

@[extern "lean_zmq_connect"]
opaque c_connect (sock : UInt64) (endpoint : @& String) : IO Int

@[extern "lean_zmq_set_rcvtimeo"]
opaque c_set_rcvtimeo (sock : UInt64) (ms : Int) : IO Int

@[extern "lean_zmq_send"]
opaque c_send (sock : UInt64) (msg : @& String) : IO Int

@[extern "lean_zmq_recv"]
opaque c_recv (sock : UInt64) : IO (@& UInt64)

@[extern "lean_zmq_free"]
opaque c_free (ptr : @& UInt64) : IO Unit

@[extern "lean_zmq_strlen_ptr"]
opaque c_strlen_ptr (ptr : UInt64) : UInt64

@[extern "lean_zmq_read_byte"]
opaque readByte (ptr : UInt64) (i : USize) : UInt8

def copyCStr (ptr : UInt64) : IO String := do
  if ptr == 0 then
    return ""
  let len := c_strlen_ptr ptr
  let n := UInt64.toNat len
  let mut b : ByteArray := ByteArray.empty
  for i in List.range n do
    b := b.push (readByte ptr (USize.ofNat i))
  match String.fromUTF8? b with
  | some s => return s
  | none => throw (IO.userError "Invalid UTF-8 received from ZeroMQ")

--------------------------------------------------------------------------------

def Socket := UInt64

def ZMQ_REQ : UInt32 := 3
def ZMQ_REP : UInt32 := 4

open IO

def socket (socketType : UInt32) : IO Socket := do
  initZmq
  c_socket socketType

def close (sock : Socket) : IO Unit := do
  let rc ← c_close sock
  if rc ≠ 0 then
    throw (IO.userError s!"zmq_close failed with code {rc}")

def bind (sock : Socket) (endpoint : String) : IO Unit := do
  let rc ← c_bind sock endpoint
  if rc ≠ 0 then
    throw (IO.userError s!"zmq_bind failed with code {rc}")

def connect (sock : Socket) (endpoint : String) : IO Unit := do
  let rc ← c_connect sock endpoint
  if rc ≠ 0 then
    throw (IO.userError s!"zmq_connect failed with code {rc}")

def setRcvTimeout (sock : Socket) (timeoutMs : Int) : IO Unit := do
  let rc ← c_set_rcvtimeo sock timeoutMs
  if rc ≠ 0 then
    throw (IO.userError s!"zmq_setsockopt(RCVTIMEO) failed with code {rc}")

def send (sock : Socket) (msg : String) : IO Unit := do
  let rc ← c_send sock msg
  if rc < 0 then
    throw (IO.userError "zmq_send error")

def recv (sock : Socket) : IO (Option String) := do
  let ptr ← c_recv sock
  if ptr == 0 then
    return none
  let s ← copyCStr ptr
  c_free ptr
  return some s

def withSocket (socketType : UInt32) (action : Socket → IO α) : IO α := do
  let sock ← socket socketType
  try
    action sock
  finally
    try
      close sock
    catch _ =>
      pure ()

end FFI.ZMQ
