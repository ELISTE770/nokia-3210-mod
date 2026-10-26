# Gemini on Nokia 3210 4G (UMS9117) — Project Brief & Architecture

## The Core Concept
Transform the Nokia 3210 4G (2024, Unisoc UMS9117 / MOCOR RTOS) into an extensible, modern AI-capable feature phone by hooking a modular **Dynamic Smart Launcher** (`SD:/system/launcher.bin`) directly into the phone's operating system via the **"תוספות" (Extras)** menu item.

This replaces the legacy, slow WAP browser proxy idea with a native, high-performance C + embedded MicroPython architecture.

---

## Key Architectural Decisions

1. **Keep MOCOR RTOS Running (No OS Replacement)**:
   Replacing the OS breaks the proprietary VoLTE modem and power management. By staying inside MOCOR and using an **In-OS Hook / Stub**, regular calls and SMS remain 100% functional.
2. **Dynamic SD Card Launcher (`SD:/system/launcher.bin`)**:
   - The launcher scans `SD:/apps/` dynamically.
   - Any new app added to the SD card (e.g., `SD:/apps/gemini/`, `SD:/apps/calculator/`) is automatically recognized and rendered in a 3x3 Grid UI on the 240x320 screen.
   - Apps include an `icon.bmp`, `manifest.txt`, and executable script (`main.py`) or binary (`app.bin`).
   - Exiting the launcher returns smoothly to the Nokia phone menu without rebooting.
3. **Embedded MicroPython Engine (`import nokia`)**:
   Embedded `libmicropython.a` compiled for ARM Cortex-A7 provides a complete Python scripting runtime for app development.
   The `nokia` module provides:
   - `nokia.clear(color)`, `nokia.text(x, y, str, color)` (with Hebrew RTL support).
   - `nokia.image(x, y, path)`, `nokia.get_key()`, `nokia.update()`.
   - `nokia.https_post(url, data, headers)` for direct API communication.
4. **Direct TLS / HTTPS via BearSSL Hooked into RTOS Sockets**:
   Instead of being restricted to GoDaddy Root CA G2 or plain HTTP proxies, BearSSL is linked directly to kernel socket primitives (`sci_sock_send` / `sci_sock_recv`), enabling direct, secure HTTPS calls to `generativelanguage.googleapis.com`.
5. **Firmware Decrapification (One-time Safe Flash)**:
   Using `tools/nokia_pac.py`, menu record `0x02A8` in the `nvitem` is pruned to remove demo games and bloatware, and the "תוספות" item is linked to the launcher stub.

---

## Detailed Implementation Plan
See [`MASTER_PLAN.md`](file:///c:/Users/Eli/OneDrive%20-%20PCMASTER/Desktop/פרוייקטים/נוקיה/MASTER_PLAN.md) for full phase-by-phase deliverables, memory addresses, and Ghidra analysis.
