import time
import sys
sys.path.insert(0, r'C:\Users\Eli\OneDrive - PCMASTER\Desktop\פרוייקטים\נוקיה\tools')
import nokia_pac as N

t0 = time.time()
print("Loading 3210.pac...")
with open('3210.pac', 'rb') as f:
    orig = f.read()
print(f"Loaded in {time.time() - t0:.2f}s")

t0 = time.time()
print("Calculating crc16_arc over 51MB...")
crc = N.crc16_arc(orig[2124:])
print(f"Computed CRC in {time.time() - t0:.2f}s: 0x{crc:04X}")
