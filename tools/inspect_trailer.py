import os
import struct

path = os.path.join('out', 'EXEC_USER_IMAGE.bin')
with open(path, 'rb') as f:
    data = f.read()

total_len = len(data)
print(f"Total length: {total_len}")
header = data[:512]

# Let's inspect all non-zero entries in the header
for offset in range(0, 512, 4):
    val = struct.unpack('<I', header[offset:offset+4])[0]
    if val != 0:
        print(f"Header offset 0x{offset:03x} ({offset}): 0x{val:08x} ({val})")

# Let's check trailer
# Notice at offset 0x30 (48): 0x00ba9c50 = 12,229,712 (or 12,230,224)
payload_size = struct.unpack('<I', header[48:52])[0]
print(f"Payload size reported in header: {payload_size} (0x{payload_size:x})")
print(f"512 + payload_size = {512 + payload_size}")
trailer_len = total_len - (512 + payload_size)
print(f"Trailer length: {trailer_len}")
trailer = data[512 + payload_size:]
print(f"Trailer first 32 bytes: {trailer[:32].hex(' ')}")
print(f"Trailer last 32 bytes: {trailer[-32:].hex(' ')}")
