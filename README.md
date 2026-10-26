# Nokia 3210 4G (UMS9117) — Dynamic Smart Launcher & Custom Firmware

[![Release](https://img.shields.io/github/v/release/ELISTE770/nokia-3210-mod?include_prereleases&style=flat-square)](https://github.com/ELISTE770/nokia-3210-mod/releases)
[![License](https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square)](LICENSE)
[![Platform](https://img.shields.io/badge/SoC-Unisoc%20UMS9117%20%2F%20T107-orange?style=flat-square)](#)
[![OS](https://img.shields.io/badge/OS-MOCOR%20RTOS-green?style=flat-square)](#)

A modular, extensible **Dynamic Smart Launcher** and custom firmware decrapifier for the **Nokia 3210 4G (2024)** based on the **Unisoc UMS9117 (T107 / Cortex-A7)** platform.

Transform your feature phone with native ARM C execution, embedded MicroPython, clean 3x3 menu layouts, and direct hardware access — all while preserving 100% of original telephony (VoLTE calls, SMS, and power management).

---

## 🎯 Architecture & Highlights

1. **Keep MOCOR RTOS Running (No OS Replacement)**
   - Preserves proprietary baseband, VoLTE modem, and battery management.
   - Non-destructive execution: returns safely to the stock Nokia menu without rebooting or losing reception.
2. **Dynamic SD Card Launcher (`SD:/nokia/launcher.bin`)**
   - Automatically scans `SD:/nokia/apps/` dynamically.
   - Renders a responsive 3x3 app grid on the 240x320 QVGA display.
   - Apps include icons, manifests (`manifest.json`), and executable binaries or Python scripts (`main.py`).
3. **Embedded MicroPython Engine (`import nokia`)**
   - Scripting runtime tailored for the Cortex-A7 core.
   - Access to screen drawing, keypad events, and file system primitives.
4. **Direct HTTPS / TLS (BearSSL)**
   - Bypasses legacy WAP proxies with modern BearSSL sockets linked directly to RTOS kernel primitives (`sci_sock_send` / `sci_sock_recv`).
5. **Firmware Decrapification & Clean Menu**
   - Removes bloatware, expired demo games, and obsolete WAP links via NVItem record `0x02A8`.
   - Balanced, clean 18-app menu (two full 3x3 pages).

---

## 📁 Repository Structure

```text
├── src/launcher/            # C Source for Smart Launcher (Cortex-A7)
│   ├── main.c               # UI loop, SD app scanning & memory hooks
│   ├── launcher.ld          # Linker script for RAM execution
│   └── start.s              # ARM startup assembly
├── release_sd/nokia/        # Ready-to-use SD card directory structure
│   ├── launcher.bin         # Compiled launcher binary
│   ├── config.txt           # System configuration
│   ├── apps/                # Built-in apps (Gemini AI, File Browser, Snake, etc.)
│   └── lib/                 # Python modules (nokia.py, urequests.py) & J2ME runner
├── tools/                   # Firmware analysis and PAC editing tools
│   ├── nokia_pac.py         # PAC unpacker/builder & NVItem menu editor
│   └── test_nokia_pac.py    # PAC integrity test suite
├── ghidra_analysis_report/  # Reverse-engineering documentation & symbol tables
│   ├── FULL_GHIDRA_PAC_ANALYSIS.md
│   ├── NVITEM_MENU_MAP.json
│   └── PARTITIONS_TABLE.csv
├── bin/                     # Prebuilt BROM / USB tools (spd_dump, fdl1 stubs)
├── flash_clean_nokia.ps1    # Automated script for ResearchDownload flasher
├── test_launcher_ram.ps1    # 0-Risk RAM tester over USB
├── BRIEF.md                 # Architecture brief
└── MASTER_PLAN.md           # Comprehensive implementation roadmap
```

---

## 🚀 Getting Started

### 1. Zero-Risk RAM Testing (No Flashing Required)
You can test the Smart Launcher in RAM over USB before flashing anything:
1. Power off the Nokia 3210 4G.
2. Hold down the **Boot button** (usually the Up Arrow or Center Key).
3. Connect the phone to your PC via USB.
4. Run the PowerShell helper:
   ```powershell
   .\test_launcher_ram.ps1
   ```
5. `spd_dump` detects BROM mode and loads `launcher.bin` directly into phone RAM.

### 2. Preparing the MicroSD Card
1. Format your MicroSD card as **FAT32**.
2. Copy the entire contents of `release_sd/nokia/` into `SD:/nokia/`.
3. Insert the MicroSD card into the phone.

### 3. PAC Firmware Editing & Flashing
To inspect or modify the firmware PAC file:
```bash
# View partition and firmware information
python tools/nokia_pac.py info 3210.pac

# Verify internal CRCs
python tools/nokia_pac.py verify 3210.pac

# Edit NVItem menu items (remove bloatware)
python tools/nokia_pac.py menu-edit nvitem.bin nvitem_clean.bin --remove 04,18,19,1F

# Rebuild PAC firmware
python tools/nokia_pac.py build 3210.pac 3210_clean.pac --replace NV=nvitem_clean.bin
```

---

## 📦 Releases & Stock Firmware

Original stock firmware and release archives are provided on the [**GitHub Releases**](https://github.com/ELISTE770/nokia-3210-mod/releases) page:

- **Release v1.0.0**:
  - `3210.pac` — Original untouched factory firmware for Nokia 3210 4G (UMS9117 / T107).
  - SHA256: `BF4E04070E2474773551C1EB26DCC4F8A93FCC38216E13C0ACDD076604589F28`
  - File Size: `51,745,348 bytes`

---

## 🛡️ Disclaimer

This software is for research and educational purposes. Modifying or flashing device firmware carries inherent risks. Always keep a backup of your original firmware and NVRAM partitions before performing any flash operation.

---

## 📄 License
Released under the [MIT License](LICENSE).
