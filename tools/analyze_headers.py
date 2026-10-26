import struct
import os

files_to_check = ['fdl1.bin', 'fdl2.bin', 'boot0.bin', 'boot1.bin', 'EXEC_USER_IMAGE.bin', 'EXEC_KERNEL_IMAGE.bin']

for fname in files_to_check:
    path = os.path.join('out', fname)
    if not os.path.exists(path):
        continue
    with open(path, 'rb') as f:
        data = f.read(1024)
    magic = data[:4]
    print(f"=== {fname} ({os.path.getsize(path):,} bytes) ===")
    print(f"First 16 bytes: {data[:16].hex(' ')}")
    if magic == b'DHTB':
        # DHTB header parsing
        # Standard Spreadtrum DHTB header:
        # 0x00: Magic 'DHTB'
        # 0x04: Version/flags
        # 0x08: Load Address or Header length
        # 0x0C: Total size / payload size
        fields = struct.unpack('<4sIIIIIIII', data[:36])
        print(f"DHTB: {fields}")
        # Look at byte 512 where payload begins
        payload_start = data[512:544]
        print(f"Payload start (offset 512): {payload_start[:16].hex(' ')}")
    else:
        # Check ARM reset vectors or initial instructions
        v = struct.unpack('<IIII', data[:16])
        print(f"Values as uint32 LE: {[hex(x) for x in v]}")
