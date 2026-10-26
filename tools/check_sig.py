import os

path = os.path.join('out', 'EXEC_USER_IMAGE.bin')
with open(path, 'rb') as f:
    data = f.read()

payload_size = 12229712
trailer = data[512 + payload_size:]
print("Trailer total size:", len(trailer))

# Spreadtrum / Unisoc Secure Boot structure:
# Typically:
# Hash of payload (32 bytes SHA-256)
# Public key structure or certificate chain
# RSA-2048 signature (256 bytes) at the very end
print("Last 256 bytes (RSA signature):")
print(trailer[-256:].hex(' '))

# Let's check if the SHA-256 of data[512:512+payload_size] appears in the trailer
import hashlib
payload_hash = hashlib.sha256(data[512:512+payload_size]).digest()
print("Payload SHA256:", payload_hash.hex())
if payload_hash in trailer:
    idx = trailer.index(payload_hash)
    print(f"Payload hash found in trailer at offset {idx}!")
else:
    print("Payload hash not found directly in trailer (might be hashed with header or encrypted/padded).")
    # check if header+payload is hashed
    full_hash = hashlib.sha256(data[:512+payload_size]).digest()
    print("Full (header+payload) SHA256:", full_hash.hex())
    if full_hash in trailer:
        print(f"Full hash found in trailer at offset {trailer.index(full_hash)}!")
