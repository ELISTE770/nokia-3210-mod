import os
import shutil
import hashlib

# 1. Create backup directory
backup_dir = 'backup_original_firmware'
os.makedirs(backup_dir, exist_ok=True)

pac_orig = '3210.pac'
pac_backup = os.path.join(backup_dir, '3210.pac')

if not os.path.exists(pac_backup):
    print("Backing up 3210.pac...")
    shutil.copy2(pac_orig, pac_backup)
else:
    print("Backup 3210.pac already exists.")

# Verify backup hash matches original
with open(pac_orig, 'rb') as f1, open(pac_backup, 'rb') as f2:
    h1 = hashlib.sha256(f1.read()).hexdigest()
    h2 = hashlib.sha256(f2.read()).hexdigest()
    assert h1 == h2, "Backup verification failed!"
    print(f"Original 3210.pac SHA256 verified: {h1}")

# 2. Modify EXEC_USER_IMAGE.bin signature drastically
user_img_orig = os.path.join('out', 'EXEC_USER_IMAGE.bin')
with open(user_img_orig, 'rb') as f:
    img_data = bytearray(f.read())

total_len = len(img_data)
# Corrupt the entire 256-byte RSA signature at the end
# We'll fill it with alternating 0xDE 0xAD 0xBE 0xEF
corrupt_sig = (b'\xDE\xAD\xBE\xEF' * 64)  # exactly 256 bytes
img_data[-256:] = corrupt_sig

user_img_corrupt = os.path.join('out', 'EXEC_USER_IMAGE_CORRUPT_SIG.bin')
with open(user_img_corrupt, 'wb') as f:
    f.write(img_data)

print(f"Created {user_img_corrupt} with corrupted RSA signature trailer.")
print(f"New trailer last 32 bytes: {img_data[-32:].hex(' ')}")
