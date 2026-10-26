import os, sys, hashlib, tempfile
sys.path.insert(0, r'C:\Users\Eli\OneDrive - PCMASTER\Desktop\פרוייקטים\נוקיה\tools')
import nokia_pac as N

PAC = r'C:\Users\Eli\OneDrive - PCMASTER\Desktop\פרוייקטים\נוקיה\3210.pac'
BAK = r'C:\Users\Eli\OneDrive - PCMASTER\Desktop\פרוייקטים\נוקיה\גיבוים\_DownloadFiles64E0_A641E99_0'
NVF = os.path.join(BAK, 'FF638V01_64X128_QVGA_CF8_Q3_SKU2_DS_ICON_nvitem_QB_16ICN18HK00.bin')

ok = fail = 0
def check(name, cond, detail=''):
    global ok, fail
    if cond: ok += 1;  print(f"  [PASS] {name}")
    else:    fail += 1; print(f"  [FAIL] {name}  {detail}")

orig = open(PAC, 'rb').read()
pac  = N.Pac(orig, PAC)

print("=== 1. identity rebuild reproduces the input exactly ===")
same = pac.rebuild({})
check('byte-identical', same == orig,
      f"len {len(same)} vs {len(orig)}")
check('same sha256', hashlib.sha256(same).hexdigest() == hashlib.sha256(orig).hexdigest())

print("\n=== 2. replacement that GROWS a partition ===")
nv = open(NVF, 'rb').read()
grown = nv + b'\xAA' * 4096
out = pac.rebuild({'NV': grown})
p2 = N.Pac(out)
ok1, ok2, _, _ = p2.check_crcs()
check('crcs valid', ok1 and ok2)
check('size grew by 4096', len(out) == len(orig) + 4096, f"{len(out)-len(orig)}")
check('size field correct', p2.declared == len(out))
nvp = [p for p in p2.parts if p.file_id == 'NV'][0]
check('NV size updated', nvp.size == len(grown), f"{nvp.size}")
check('NV data matches', p2.data_of(nvp) == grown)
# every later partition must have shifted by exactly 4096
for a, b in zip(pac.parts, p2.parts):
    if not a.has_data: continue
    if a.index <= nvp.index: continue
    if b.offset != a.offset + 4096:
        check(f'partition {a.index} {a.file_id} shifted', False,
              f"{a.offset} -> {b.offset}"); break
else:
    check('all later partitions shifted by 4096', True)
for a, b in zip(pac.parts, p2.parts):
    if a.has_data and a.file_id != 'NV':
        if pac.data_of(a) != p2.data_of(b):
            check(f'{a.file_id} unchanged', False); break
else:
    check('all other partition data unchanged', True)

print("\n=== 3. replacement that SHRINKS a partition ===")
shrunk = nv[:-8192]
out = pac.rebuild({'NV': shrunk})
p3 = N.Pac(out)
ok1, ok2, _, _ = p3.check_crcs()
check('crcs valid', ok1 and ok2)
check('size shrank by 8192', len(out) == len(orig) - 8192, f"{len(out)-len(orig)}")
nvp3 = [p for p in p3.parts if p.file_id == 'NV'][0]
check('NV data matches', p3.data_of(nvp3) == shrunk)

print("\n=== 4. match by filename as well as by id ===")
out = pac.rebuild({'apn.bin': b'\x01\x02\x03\x04'})
p4 = N.Pac(out)
apn = [p for p in p4.parts if p.file_name == 'apn.bin'][0]
check('matched by filename', p4.data_of(apn) == b'\x01\x02\x03\x04')

print("\n=== 5. unknown key is rejected, not silently ignored ===")
try:
    pac.rebuild({'NoSuchThing': b'x'})
    check('raises on unknown key', False)
except KeyError as e:
    check('raises on unknown key', True)

print("\n=== 6. menu edit round-trips through a rebuilt PAC ===")
nvobj = N.NvItem(nv)
grid, lst, _ = nvobj.read_menu()
check('stock menu is 26 items', len(grid) == 26 and len(lst) == 26)
check('browser 0x04 present', 0x04 in grid)
nvobj.write_menu([c for c in grid if c != 0x04], [c for c in lst if c != 0x04])
edited = nvobj.to_bytes()
check('nv size unchanged by edit', len(edited) == len(nv), f"{len(edited)} vs {len(nv)}")

out = pac.rebuild({'NV': edited})
p6 = N.Pac(out)
nvp6 = [p for p in p6.parts if p.file_id == 'NV'][0]
g2, l2, _ = N.NvItem(p6.data_of(nvp6)).read_menu()
check('browser gone from 3x3', 0x04 not in g2)
check('browser gone from 1x1', 0x04 not in l2)
check('counts now 25', len(g2) == 25 and len(l2) == 25, f"{len(g2)}/{len(l2)}")
check('order otherwise preserved', g2 == [c for c in grid if c != 0x04])
ok1, ok2, _, _ = p6.check_crcs()
check('rebuilt crcs valid', ok1 and ok2)

print("\n=== 7. NV record table integrity after edit ===")
before = N.NvItem(nv); after = N.NvItem(edited)
check('same record count', len(before.records) == len(after.records),
      f"{len(before.records)} vs {len(after.records)}")
check('same ids in same order',
      [r.rec_id for r in before.records] == [r.rec_id for r in after.records])
check('same offsets', [r.offset for r in before.records] == [r.offset for r in after.records])
diffs = [i for i in range(len(nv)) if nv[i] != edited[i]]
lo, hi = min(diffs), max(diffs)
menu = before.find(N.NV_MENU_ID)
check('only the menu record changed',
      lo >= menu.data_offset and hi < menu.data_offset + menu.length,
      f"bytes 0x{lo:X}..0x{hi:X}, record is 0x{menu.data_offset:X}..0x{menu.data_offset+menu.length:X}")

print("\n=== 8. guards ===")
try:
    N.NvItem(nv).write_menu([], [1]); check('rejects empty menu', False)
except ValueError: check('rejects empty menu', True)
try:
    N.NvItem(nv).write_menu(list(range(60)), [1]); check('rejects over-capacity', False)
except ValueError: check('rejects over-capacity', True)

print("\n" + "=" * 40)
print(f"PASSED: {ok}   FAILED: {fail}")
sys.exit(1 if fail else 0)
