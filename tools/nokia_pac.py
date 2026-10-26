#!/usr/bin/env python3
"""
nokia_pac.py — inspect and rebuild Spreadtrum/Unisoc PAC firmware, and edit the
main-menu record inside the Nokia 3210 4G (UMS9117 / MOCOR) nvitem file.

Everything encoded here was measured against 3210.pac (MOCOR_20A_MP_W22.04.6_P5,
product UMS9117) rather than taken from documentation:

  PAC container
    - header is 2124 bytes; magic 0xFFFAFFFA at 2116
    - crc1 (u16 @2120) = CRC-16/ARC over bytes [0, 2120)
    - crc2 (u16 @2122) = CRC-16/ARC over bytes [2124, EOF)
    - partition table follows the header, 2580 bytes per entry
    - payload is packed contiguously right after the table, no padding

  nvitem
    - records are <id:u16><len:u16><data:len>, each starting on a 4-byte
      boundary, first record at offset 4
    - record 0x02A8 (680) holds the main menu, 408 bytes:
        dword 0     count for the 3x3 grid
        dword 1     count for the 1x1 list
        dword 2..51   3x3 entries  (50 slots, 26 used in stock)
        dword 52..101 1x1 entries  (50 slots, 26 used in stock)

Usage:
    nokia_pac.py info      <pac>
    nokia_pac.py extract   <pac> <outdir>
    nokia_pac.py verify    <pac>
    nokia_pac.py nv-records <nvitem> [--id 0x2A8]
    nokia_pac.py menu-show <nvitem>
    nokia_pac.py menu-edit <nvitem> <out-nvitem> --remove 04,18
    nokia_pac.py build     <pac> <out-pac> --replace NV=<file> [--replace MMIRes=<file>]
"""

from __future__ import annotations

import argparse
import os
import struct
import sys
from dataclasses import dataclass, field

# Reconfigure stdout/stderr for UTF-8 in Windows console to support Hebrew menu names
if hasattr(sys.stdout, 'reconfigure') and sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure') and sys.stderr.encoding and sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# --------------------------------------------------------------------------
# PAC layout constants
# --------------------------------------------------------------------------

HDR_SIZE      = 2124
MAGIC_OFF     = 2116
MAGIC         = 0xFFFAFFFA
CRC1_OFF      = 2120
CRC2_OFF      = 2122
OFF_TOTALSIZE = 0x30
OFF_COUNT     = 0x434
OFF_LISTSTART = 0x438

ENTRY_SIZE    = 2580
E_ID          = 4       # 512 bytes, UTF-16LE
E_NAME        = 516     # 512 bytes, UTF-16LE
E_FIELDS      = 0x5FC   # 8 u32: hiSize hiOff loSize flag check loOff omit addrN

# --------------------------------------------------------------------------
# nvitem layout constants
# --------------------------------------------------------------------------

NV_FIRST_REC  = 4
NV_MENU_ID    = 0x02A8
MENU_SLOTS    = 50      # capacity of each of the two lists

# Codes documented by the mitmachim.top community for this exact model.
# Unlisted codes are left as "?" on purpose — guessing them would be worse
# than showing the gap.
MENU_NAMES = {
    0x01: "טלפון",
    0x02: "אנשי קשר",
    0x04: "אינטרנט",
    0x05: "הודעות",
    0x06: "מצלמה",
    0x08: "רדיו",
    0x09: "שעון",
    0x0A: "מוזיקה",
    0x0C: "הגדרות",
    0x0D: "קבצים",
    0x0E: "תוספות",
    0x14: "ענן / Puffin",
    0x18: "משחק מרוצים",
    0x19: "משחק DOOD",
    0x1D: "סנייק",
    0x1F: "משחק BLAC",
}


def menu_name(code: int) -> str:
    return MENU_NAMES.get(code, "?")


# --------------------------------------------------------------------------
# CRC-16/ARC  (poly 0x8005, init 0x0000, reflected in/out, xorout 0x0000)
# --------------------------------------------------------------------------

_CRC_TABLE = []
for _i in range(256):
    _c = _i
    for _ in range(8):
        _c = (_c >> 1) ^ 0xA001 if _c & 1 else _c >> 1
    _CRC_TABLE.append(_c)


def crc16_arc(data: bytes, crc: int = 0) -> int:
    for b in data:
        crc = (crc >> 8) ^ _CRC_TABLE[(crc ^ b) & 0xFF]
    return crc


# --------------------------------------------------------------------------
# PAC
# --------------------------------------------------------------------------


def _wstr(raw: bytes) -> str:
    return raw.decode("utf-16-le", "replace").split("\x00")[0]


def _wstr_pack(s: str, size: int) -> bytes:
    raw = s.encode("utf-16-le")
    if len(raw) > size - 2:
        raise ValueError(f"string too long for {size}-byte field: {s!r}")
    return raw + b"\x00" * (size - len(raw))


@dataclass
class Partition:
    index: int
    file_id: str
    file_name: str
    size: int
    offset: int
    flag: int
    check: int
    omit: int
    addrs: list = field(default_factory=list)
    raw_entry: bytes = b""

    @property
    def has_data(self) -> bool:
        return self.size > 0 and bool(self.file_name)


class Pac:
    def __init__(self, blob: bytes, path: str = "<memory>"):
        self.blob = blob
        self.path = path
        if len(blob) < HDR_SIZE:
            raise ValueError("file is smaller than a PAC header")
        magic = struct.unpack_from("<I", blob, MAGIC_OFF)[0]
        if magic != MAGIC:
            raise ValueError(f"bad PAC magic 0x{magic:08X} (expected 0x{MAGIC:08X})")

        self.version   = _wstr(blob[0:48])
        self.declared  = struct.unpack_from("<I", blob, OFF_TOTALSIZE)[0]
        self.product   = _wstr(blob[0x34:0x34 + 512])
        self.firmware  = _wstr(blob[0x234:0x234 + 512])
        self.count     = struct.unpack_from("<I", blob, OFF_COUNT)[0]
        self.liststart = struct.unpack_from("<I", blob, OFF_LISTSTART)[0]
        self.crc1, self.crc2 = struct.unpack_from("<HH", blob, CRC1_OFF)

        self.parts: list[Partition] = []
        for i in range(self.count):
            base = self.liststart + i * ENTRY_SIZE
            ent = blob[base:base + ENTRY_SIZE]
            if len(ent) != ENTRY_SIZE:
                raise ValueError(f"partition entry {i} is truncated")
            (_hi_size, _hi_off, size, flag, check,
             offset, omit, addr_n) = struct.unpack_from("<8I", ent, E_FIELDS)
            addrs = list(struct.unpack_from("<5I", ent, E_FIELDS + 32))[:addr_n]
            self.parts.append(Partition(
                index=i,
                file_id=_wstr(ent[E_ID:E_ID + 512]),
                file_name=_wstr(ent[E_NAME:E_NAME + 512]),
                size=size, offset=offset, flag=flag, check=check,
                omit=omit, addrs=addrs, raw_entry=ent,
            ))

    # -- integrity ---------------------------------------------------------

    def check_crcs(self) -> tuple[bool, bool, int, int]:
        c1 = crc16_arc(self.blob[:CRC1_OFF])
        c2 = crc16_arc(self.blob[HDR_SIZE:])
        return c1 == self.crc1, c2 == self.crc2, c1, c2

    def data_of(self, p: Partition) -> bytes:
        return self.blob[p.offset:p.offset + p.size]

    # -- rebuild -----------------------------------------------------------

    def rebuild(self, replacements: dict[str, bytes]) -> bytes:
        """
        Emit a fresh PAC with some partitions swapped out.

        Keys of `replacements` match a partition by file_id first, then by
        file_name, so both `NV=...` and `apn.bin=...` work. Offsets, sizes, the
        total-size field and both CRCs are recomputed, so a replacement of a
        different length is fine.
        """
        unused = set(replacements)
        table = bytearray()
        payload = bytearray()
        data_start = self.liststart + self.count * ENTRY_SIZE

        for p in self.parts:
            ent = bytearray(p.raw_entry)

            new_data = None
            for key in (p.file_id, p.file_name):
                if key and key in replacements:
                    new_data = replacements[key]
                    unused.discard(key)
                    break

            if new_data is None:
                new_data = self.data_of(p) if p.has_data else b""

            if new_data:
                offset = data_start + len(payload)
                payload += new_data
            else:
                offset = 0

            struct.pack_into("<I", ent, E_FIELDS + 8, len(new_data))   # loSize
            struct.pack_into("<I", ent, E_FIELDS + 20, offset)         # loOffset
            table += ent

        if unused:
            raise KeyError(f"no partition matched: {', '.join(sorted(unused))}")

        out = bytearray(self.blob[:self.liststart])
        out += table
        out += payload
        struct.pack_into("<I", out, OFF_TOTALSIZE, len(out))
        struct.pack_into("<H", out, CRC1_OFF, crc16_arc(bytes(out[:CRC1_OFF])))
        struct.pack_into("<H", out, CRC2_OFF, crc16_arc(bytes(out[HDR_SIZE:])))
        return bytes(out)


# --------------------------------------------------------------------------
# nvitem
# --------------------------------------------------------------------------


@dataclass
class NvRecord:
    offset: int      # offset of the record header inside the file
    rec_id: int
    length: int
    data: bytes

    @property
    def data_offset(self) -> int:
        return self.offset + 4


class NvItem:
    def __init__(self, blob: bytes, path: str = "<memory>"):
        self.blob = bytearray(blob)
        self.path = path
        if len(blob) >= HDR_SIZE:
            magic = struct.unpack_from("<I", blob, MAGIC_OFF)[0]
            if magic == MAGIC:
                raise ValueError(f"'{path}' is a PAC container file, not an extracted nvitem binary! "
                                 f"Extract partition 2 (NV) first with: nokia_pac.py extract <pac> <outdir>")
        self.records: list[NvRecord] = []
        off = NV_FIRST_REC
        while off + 4 <= len(blob):
            rec_id, length = struct.unpack_from("<HH", blob, off)
            if rec_id == 0xFFFF and length == 0xFFFF:
                break
            if off + 4 + length > len(blob):
                break
            self.records.append(NvRecord(off, rec_id, length, bytes(blob[off + 4:off + 4 + length])))
            off = (off + 4 + length + 3) // 4 * 4
        self.end = off
        if not self.records:
            raise ValueError("no NV records found — is this really an nvitem file?")

    def find(self, rec_id: int) -> NvRecord:
        for r in self.records:
            if r.rec_id == rec_id:
                return r
        raise KeyError(f"NV record 0x{rec_id:04X} not found")

    # -- menu --------------------------------------------------------------

    def read_menu(self) -> tuple[list[int], list[int], NvRecord]:
        rec = self.find(NV_MENU_ID)
        need = (2 + MENU_SLOTS * 2) * 4
        if rec.length < need:
            raise ValueError(f"menu record is {rec.length} bytes, expected at least {need}")
        words = list(struct.unpack_from(f"<{rec.length // 4}I", rec.data, 0))
        n_grid, n_list = words[0], words[1]
        for n in (n_grid, n_list):
            if n > MENU_SLOTS:
                raise ValueError(f"menu count {n} exceeds the {MENU_SLOTS}-slot capacity")
        grid = words[2:2 + n_grid]
        lst  = words[2 + MENU_SLOTS:2 + MENU_SLOTS + n_list]
        return grid, lst, rec

    def write_menu(self, grid: list[int], lst: list[int]) -> None:
        rec = self.find(NV_MENU_ID)
        for name, items in (("3x3", grid), ("1x1", lst)):
            if len(items) > MENU_SLOTS:
                raise ValueError(f"{name} list has {len(items)} items, capacity is {MENU_SLOTS}")
            if not items:
                raise ValueError(f"{name} list would be empty — refusing")

        words = list(struct.unpack_from(f"<{rec.length // 4}I", rec.data, 0))
        words[0] = len(grid)
        words[1] = len(lst)
        for i in range(MENU_SLOTS):
            words[2 + i]              = grid[i] if i < len(grid) else 0
            words[2 + MENU_SLOTS + i] = lst[i]  if i < len(lst)  else 0

        packed = struct.pack(f"<{len(words)}I", *words)
        self.blob[rec.data_offset:rec.data_offset + rec.length] = packed
        rec.data = packed

    def to_bytes(self) -> bytes:
        return bytes(self.blob)


# --------------------------------------------------------------------------
# commands
# --------------------------------------------------------------------------


def _load(path: str) -> bytes:
    with open(path, "rb") as fh:
        return fh.read()


def _save(path: str, blob: bytes) -> None:
    if os.path.exists(path):
        raise SystemExit(f"refusing to overwrite existing file: {path}")
    with open(path, "wb") as fh:
        fh.write(blob)
    print(f"wrote {path}  ({len(blob):,} bytes)")


def cmd_info(args) -> None:
    pac = Pac(_load(args.pac), args.pac)
    print(f"version    : {pac.version}")
    print(f"product    : {pac.product}")
    print(f"firmware   : {pac.firmware}")
    print(f"partitions : {pac.count}")
    print(f"size field : {pac.declared:,}   actual: {len(pac.blob):,}"
          f"   {'OK' if pac.declared == len(pac.blob) else 'MISMATCH'}")
    ok1, ok2, c1, c2 = pac.check_crcs()
    print(f"crc1       : stored 0x{pac.crc1:04X}  computed 0x{c1:04X}  {'OK' if ok1 else 'BAD'}")
    print(f"crc2       : stored 0x{pac.crc2:04X}  computed 0x{c2:04X}  {'OK' if ok2 else 'BAD'}")
    print()
    print(f"{'#':>3}  {'ID':<22} {'file':<52} {'size':>11} {'offset':>11}")
    for p in pac.parts:
        print(f"{p.index:>3}  {p.file_id:<22} {p.file_name:<52} {p.size:>11,} {p.offset:>11,}")


def cmd_verify(args) -> None:
    pac = Pac(_load(args.pac), args.pac)
    ok1, ok2, c1, c2 = pac.check_crcs()
    size_ok = pac.declared == len(pac.blob)

    problems = []
    if not ok1:
        problems.append(f"crc1 stored 0x{pac.crc1:04X} != computed 0x{c1:04X}")
    if not ok2:
        problems.append(f"crc2 stored 0x{pac.crc2:04X} != computed 0x{c2:04X}")
    if not size_ok:
        problems.append(f"size field {pac.declared:,} != actual {len(pac.blob):,}")

    end = 0
    for p in pac.parts:
        if not p.has_data:
            continue
        if p.offset + p.size > len(pac.blob):
            problems.append(f"[{p.index}] {p.file_id} runs past end of file")
        if p.offset < end:
            problems.append(f"[{p.index}] {p.file_id} overlaps the previous partition")
        end = max(end, p.offset + p.size)

    if problems:
        print("FAILED:")
        for p in problems:
            print("  -", p)
        raise SystemExit(1)
    print(f"{args.pac}: OK — CRCs match, size field correct, {pac.count} partitions, no overlaps")


def cmd_extract(args) -> None:
    pac = Pac(_load(args.pac), args.pac)
    os.makedirs(args.outdir, exist_ok=True)
    for p in pac.parts:
        if not p.has_data:
            continue
        dest = os.path.join(args.outdir, p.file_name)
        with open(dest, "wb") as fh:
            fh.write(pac.data_of(p))
        print(f"{p.file_id:<22} -> {p.file_name}  ({p.size:,} bytes)")


def cmd_nv_records(args) -> None:
    nv = NvItem(_load(args.nvitem), args.nvitem)
    print(f"{len(nv.records)} records, table ends at 0x{nv.end:X} (file 0x{len(nv.blob):X})")
    wanted = int(args.id, 0) if args.id else None
    for r in nv.records:
        if wanted is not None and r.rec_id != wanted:
            continue
        preview = r.data[:16].hex(" ")
        more = " ..." if r.length > 16 else ""
        print(f"  id=0x{r.rec_id:04X} ({r.rec_id:5})  @0x{r.offset:06X}  len={r.length:<5}  {preview}{more}")


def _print_menu(title: str, items: list[int], base_off: int) -> None:
    print(f"\n{title}  ({len(items)} items)")
    for i, code in enumerate(items):
        print(f"  {i + 1:>2}.  0x{code:02X}  @0x{base_off + i * 4:05X}   {menu_name(code)}")


def cmd_menu_show(args) -> None:
    nv = NvItem(_load(args.nvitem), args.nvitem)
    grid, lst, rec = nv.read_menu()
    print(f"menu record 0x{rec.rec_id:04X} @0x{rec.offset:05X}, {rec.length} bytes"
          f"  (capacity {MENU_SLOTS} per list)")
    _print_menu("3x3 grid", grid, rec.data_offset + 8)
    _print_menu("1x1 list", lst,  rec.data_offset + 8 + MENU_SLOTS * 4)
    unknown = sorted({c for c in grid + lst if c not in MENU_NAMES})
    if unknown:
        print("\nunmapped codes: " + ", ".join(f"0x{c:02X}" for c in unknown))


def _parse_codes(text: str) -> list[int]:
    out = []
    for chunk in text.split(","):
        chunk = chunk.strip()
        if chunk:
            out.append(int(chunk, 16))
    return out


def cmd_menu_edit(args) -> None:
    nv = NvItem(_load(args.nvitem), args.nvitem)
    grid, lst, _ = nv.read_menu()

    if args.remove:
        drop = set(_parse_codes(args.remove))
        missing = drop - set(grid) - set(lst)
        if missing:
            raise SystemExit("not present in the menu: "
                             + ", ".join(f"0x{c:02X}" for c in sorted(missing)))
        for code in sorted(drop):
            print(f"removing 0x{code:02X}  ({menu_name(code)})")
        grid = [c for c in grid if c not in drop]
        lst  = [c for c in lst  if c not in drop]
    elif args.set_grid:
        grid = _parse_codes(args.set_grid)
        lst = list(grid)
        print("setting both lists to: " + ", ".join(f"0x{c:02X}" for c in grid))
    else:
        raise SystemExit("nothing to do: pass --remove or --set")

    nv.write_menu(grid, lst)
    _save(args.out, nv.to_bytes())

    check = NvItem(_load(args.out), args.out)
    g2, l2, _ = check.read_menu()
    assert g2 == grid and l2 == lst, "round-trip mismatch"
    print(f"verified: 3x3 now {len(g2)} items, 1x1 now {len(l2)} items")


def cmd_build(args) -> None:
    pac = Pac(_load(args.pac), args.pac)
    ok1, ok2, _, _ = pac.check_crcs()
    if not (ok1 and ok2):
        print("warning: the input PAC does not pass its own CRC check", file=sys.stderr)

    replacements = {}
    for item in args.replace:
        if "=" not in item:
            raise SystemExit(f"--replace expects KEY=path, got {item!r}")
        key, path = item.split("=", 1)
        replacements[key] = _load(path)
        print(f"replacing {key:<10} with {path}  ({len(replacements[key]):,} bytes)")

    out = pac.rebuild(replacements)
    _save(args.out, out)

    rebuilt = Pac(out, args.out)
    ok1, ok2, c1, c2 = rebuilt.check_crcs()
    print(f"crc1 0x{c1:04X} {'OK' if ok1 else 'BAD'}   "
          f"crc2 0x{c2:04X} {'OK' if ok2 else 'BAD'}   "
          f"size field {'OK' if rebuilt.declared == len(out) else 'BAD'}")
    if not (ok1 and ok2):
        raise SystemExit("rebuilt PAC failed verification")

    # every partition we did not touch must come back byte-identical
    changed = set(replacements)
    for a, b in zip(pac.parts, rebuilt.parts):
        if a.file_id in changed or a.file_name in changed:
            continue
        if pac.data_of(a) != rebuilt.data_of(b):
            raise SystemExit(f"untouched partition changed: {a.file_id}")
    print("verified: all untouched partitions are byte-identical")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("info", help="show PAC header and partition table")
    p.add_argument("pac"); p.set_defaults(func=cmd_info)

    p = sub.add_parser("verify", help="check CRCs, size field and partition layout")
    p.add_argument("pac"); p.set_defaults(func=cmd_verify)

    p = sub.add_parser("extract", help="write every partition out to a directory")
    p.add_argument("pac"); p.add_argument("outdir"); p.set_defaults(func=cmd_extract)

    p = sub.add_parser("nv-records", help="list records in an nvitem file")
    p.add_argument("nvitem"); p.add_argument("--id", help="show only this record id, e.g. 0x2A8")
    p.set_defaults(func=cmd_nv_records)

    p = sub.add_parser("menu-show", help="show the main-menu entries")
    p.add_argument("nvitem"); p.set_defaults(func=cmd_menu_show)

    p = sub.add_parser("menu-edit", help="remove or replace main-menu entries")
    p.add_argument("nvitem"); p.add_argument("out")
    p.add_argument("--remove", help="hex codes to drop, e.g. 04,18,1F")
    p.add_argument("--set", dest="set_grid", help="hex codes forming the whole new menu")
    p.set_defaults(func=cmd_menu_edit)

    p = sub.add_parser("build", help="rebuild a PAC with replaced partitions")
    p.add_argument("pac"); p.add_argument("out")
    p.add_argument("--replace", action="append", default=[],
                   metavar="ID=PATH", help="partition id or filename = replacement file")
    p.set_defaults(func=cmd_build)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
