# Alpine Linux for Nokia 3210 4G (Unisoc UMS9117 / fplinux)

This directory contains the Alpine Linux environment for the Nokia 3210 4G:
- `manifest.json`: App metadata for the Smart Launcher.
- `boot_linux.bin`: ARMv7-A Cortex-A7 bootloader that sets up ATAGS (64MB RAM, LCD console) and launches the kernel.
- `cmdline.txt`: Linux kernel command line (`console=tty0 fbcon=rotate:0 root=/dev/ram0 rdinit=/init quiet loglevel=3`).
- `zImage`: Linux kernel for UMS9117 (place your compiled zImage here).
- `initramfs.cpio.gz`: Minimal Alpine Linux rootfs with busybox and shell.

### Return to Nokia Phone System:
To return from Linux back to the standard Nokia phone system:
Simply run in the Linux terminal:
```sh
reboot
```
The phone will reboot within 3 seconds and return cleanly to standard Nokia MOCOR OS with full VoLTE cellular connectivity!
