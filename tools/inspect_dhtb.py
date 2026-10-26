import os
import struct

path = os.path.join('out', 'EXEC_USER_IMAGE.bin')
with open(path, 'rb') as f:
    data = f.read()

print(f"Total size: {len(data)} bytes")
# Check last 512 bytes
tail = data[-512:]
print("Last 256 bytes hex preview (potential RSA signature):")
print(data[-256:][:32].hex(' '))

# Let's inspect DHTB header at byte 0..512
header = data[:512]
print("DHTB Header first 64 bytes:")
print(header[:64].hex(' '))

# Unpack first integers of DHTB
# DHTB struct in Spreadtrum:
# char magic[4]; // 'DHTB'
# uint32 version;
# ...
vals = struct.unpack('<4sIIIIIIII', header[:36])
print("DHTB fields:", vals)
