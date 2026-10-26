#!/usr/bin/env python3
"""
build_launcher.py - Compiles Nokia 3210 4G Smart Launcher
using arm-none-eabi-gcc into release_sd/nokia/launcher.bin
"""

import os
import subprocess
import sys
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
import struct

ROOT = "N:" if os.path.exists("N:/src/launcher") else os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
TOOLCHAIN_BIN = os.path.join(ROOT, "toolchain", "bin")
CC = os.path.join(TOOLCHAIN_BIN, "arm-none-eabi-gcc.exe")
OBJCOPY = os.path.join(TOOLCHAIN_BIN, "arm-none-eabi-objcopy.exe")
OBJDUMP = os.path.join(TOOLCHAIN_BIN, "arm-none-eabi-objdump.exe")

SRC_DIR = os.path.join(ROOT, "src", "launcher")
OUT_DIR = os.path.join(ROOT, "release_sd", "nokia")
BUILD_DIR = os.path.join(SRC_DIR, "build")

os.makedirs(BUILD_DIR, exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)

SRCS = [
    os.path.join(SRC_DIR, "start.s"),
    os.path.join(SRC_DIR, "main.c"),
]

ELF_OUT = os.path.join(BUILD_DIR, "launcher.elf")
BIN_OUT = os.path.join(OUT_DIR, "launcher.bin")
LDSCRIPT = os.path.join(SRC_DIR, "launcher.ld")

CFLAGS = [
    "-mcpu=cortex-a7",
    "-mthumb",
    "-mthumb-interwork",
    "-Os",
    "-Wall",
    "-Wextra",
    "-fno-builtin",
    "-fomit-frame-pointer",
    "-ffunction-sections",
    "-fdata-sections",
    "-I" + SRC_DIR,
]

LFLAGS = [
    "-nostartfiles",
    "-nodefaultlibs",
    "-nostdlib",
    "-Wl,-T," + LDSCRIPT,
    "-Wl,--gc-sections",
    "-Wl,-Map=" + os.path.join(BUILD_DIR, "launcher.map"),
]

def compile_launcher():
    print("Compiling Nokia Smart Launcher (Cortex-A7)...")
    cmd = [CC] + CFLAGS + SRCS + LFLAGS + ["-o", ELF_OUT]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
    if res.returncode != 0:
        print("Compilation failed:")
        print(res.stderr)
        sys.exit(1)
    print("Compilation successful ->", ELF_OUT)

    print("Generating binary ->", BIN_OUT)
    cmd_bin = [OBJCOPY, "-O", "binary", ELF_OUT, BIN_OUT]
    res_bin = subprocess.run(cmd_bin, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
    if res_bin.returncode != 0:
        print("Objcopy failed:", res_bin.stderr)
        sys.exit(1)

    bin_size = os.path.getsize(BIN_OUT)
    print(f"Generated launcher.bin: {bin_size:,} bytes")

    # Verify DHTB header
    with open(BIN_OUT, "rb") as f:
        magic = f.read(4)
        if magic == b"DHTB":
            print("[OK] DHTB Header verified successfully!")
        else:
            print("[WARN] DHTB header missing (expected b'DHTB')")

if __name__ == "__main__":
    compile_launcher()
