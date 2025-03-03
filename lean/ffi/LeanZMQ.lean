import Lean

namespace FFI.ZMQ

@[extern "lean_zmq_init"]
constant initZmq : IO Unit

@[extern "lean_zmq_socket"]
constant c_socket (socketType : UInt32) : IO UInt64

@[extern "lean_zmq_close"]
constant c_close (sock : UInt64) : IO Int

@[extern "lean_zmq_bind"]
constant c_bind (sock : UInt64) (endpoint : @& String) : IO Int

@[extern "lean_zmq_connect"]
constant c_connect (sock : UInt64) (endpoint : @& String) : IO Int

@[extern "lean_zmq_set_rcvtimeo"]
constant c_set_rcvtimeo (sock : UInt64) (ms : Int) : IO Int

@[extern "lean_zmq_send"]
constant c_send (sock : UInt64) (msg : @& String) : IO Int

@[extern "lean_zmq_recv"]
constant c_recv (sock : UInt64) : IO (@& UInt64)

@[extern "lean_zmq_free"]
constant c_free (ptr : @& UInt64) : IO Unit

@[extern "strlen"]
constant c_strlen (ptr : @& UInt64) : UInt64

@[extern "memcpy"]
constant c_memcpy (dst : @& UInt64) (src : @& UInt64) (n : @& UInt64) : Unit

def copyCStr (ptr : UInt64) : IO String := do
  if ptr == 0 then
    return ""
  let len := c_strlen ptr
  let mut b : ByteArray := ByteArray.mkEmpty (UInt64.toNat len)
  b := b.pushn 0 (UInt64.toNat len)  -- allocate space
  let dst := b.dataPtr
  c_memcpy (UInt64.ofNat dst.toUInt64) ptr len
  let s := String.fromUTF8Unchecked b
  return s

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
    throw <| userError s!"zmq_close failed with code {rc}"

def bind (sock : Socket) (endpoint : String) : IO Unit := do
  let rc ← c_bind sock endpoint
  if rc ≠ 0 then
    throw <| userError s!"zmq_bind failed with code {rc}"

def connect (sock : Socket) (endpoint : String) : IO Unit := do
  let rc ← c_connect sock endpoint
  if rc ≠ 0 then
    throw <| userError s!"zmq_connect failed with code {rc}"

def setRcvTimeout (sock : Socket) (timeoutMs : Int) : IO Unit := do
  let rc ← c_set_rcvtimeo sock timeoutMs
  if rc ≠ 0 then
    throw <| userError s!"zmq_setsockopt(RCVTIMEO) failed with code {rc}"

def send (sock : Socket) (msg : String) : IO Unit := do
  let rc ← c_send sock msg
  if rc < 0 then
    throw <| userError "zmq_send error"

def recv (sock : Socket) : IO (Option String) := do
  let ptr ← c_recv sock
  if ptr == 0 then
    -- Means we timed out or had an error in c_recv
    return none
  -- Copy the pointer's content into Lean memory
  let s ← copyCStr ptr
  -- We must free the pointer after copying
  c_free ptr
  return some s

end FFI.ZMQ
