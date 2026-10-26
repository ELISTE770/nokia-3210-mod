import ctypes
import time

kernel32 = ctypes.windll.kernel32
kernel32.VirtualAlloc.restype = ctypes.c_void_p
kernel32.VirtualAlloc.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint32, ctypes.c_uint32]

MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
PAGE_EXECUTE_READWRITE = 0x40

code = bytes([
    0x48, 0x85, 0xd2,                         # test rdx, rdx
    0x74, 0x1d,                               # jz done (+29)
    # loop:
    0x0f, 0xb6, 0x01,                         # movzx eax, byte [rcx]
    0x66, 0x41, 0x33, 0xc0,                   # xor ax, r8w
    0x25, 0xff, 0x00, 0x00, 0x00,             # and eax, 0xff
    0x66, 0x41, 0x8b, 0x04, 0x41,             # mov ax, word [r9 + rax*2]
    0x66, 0x41, 0xc1, 0xe8, 0x08,             # shr r8w, 8
    0x66, 0x41, 0x33, 0xc0,                   # xor ax, r8w
    0x41, 0x89, 0xc0,                         # mov r8d, eax
    0x48, 0xff, 0xc1,                         # inc rcx
    0x48, 0xff, 0xca,                         # dec rdx
    0x75, 0xdd,                               # jnz loop (-35)
    # done:
    0x41, 0x0f, 0xb7, 0xc0,                   # movzx eax, r8w
    0xc3                                      # ret
])

addr = kernel32.VirtualAlloc(0, len(code), MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE)
ctypes.memmove(addr, code, len(code))

FUNC_TYPE = ctypes.CFUNCTYPE(ctypes.c_uint16, ctypes.c_char_p, ctypes.c_size_t, ctypes.c_uint16, ctypes.c_void_p)
fast_crc_fn = FUNC_TYPE(addr)

_CRC_TABLE = []
for _i in range(256):
    _c = _i
    for _ in range(8):
        _c = (_c >> 1) ^ 0xA001 if _c & 1 else _c >> 1
    _CRC_TABLE.append(_c)

TableArray = (ctypes.c_uint16 * 256)(*_CRC_TABLE)

def fast_crc16_arc(data: bytes, crc: int = 0) -> int:
    return fast_crc_fn(data, len(data), crc, ctypes.byref(TableArray))

if __name__ == '__main__':
    with open('3210.pac', 'rb') as f:
        data = f.read()
    t0 = time.time()
    res = fast_crc16_arc(data[2124:])
    dt = time.time() - t0
    print(f"Computed CRC in {dt*1000:.2f} ms: 0x{res:04X}")
    assert res == 0x0B55, f"Expected 0x0B55, got 0x{res:04X}"
    print("SUCCESS: CRC-16 ARC is 100% verified!")
