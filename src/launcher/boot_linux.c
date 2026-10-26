/*
 * boot_linux.c - ARM Linux Kernel Bootloader for Nokia 3210 4G (UMS9117)
 * Sets up ATAGS / Memory map for Cortex-A7 and jumps to Linux kernel (zImage).
 */

#include <stdint.h>
#include <stddef.h>

#define DDR_BASE        0x80000000
#define ATAGS_ADDR      (DDR_BASE + 0x100)
#define KERNEL_ADDR     (DDR_BASE + 0x8000)

/* ATAG tags */
#define ATAG_NONE       0x00000000
#define ATAG_CORE       0x54410001
#define ATAG_MEM        0x54410002
#define ATAG_CMDLINE    0x54410009

struct atag_header {
    uint32_t size; /* in 32-bit words */
    uint32_t tag;
};

struct atag_core {
    uint32_t flags;
    uint32_t pagesize;
    uint32_t rootdev;
};

struct atag_mem {
    uint32_t size;
    uint32_t start;
};

static uint32_t* setup_atags(uint32_t *params, const char *cmdline) {
    /* ATAG_CORE */
    *params++ = 5;
    *params++ = ATAG_CORE;
    *params++ = 1;      /* read-only root */
    *params++ = 4096;   /* 4KB page size */
    *params++ = 0;      /* rootdev */

    /* ATAG_MEM */
    *params++ = 4;
    *params++ = ATAG_MEM;
    *params++ = 64 * 1024 * 1024; /* 64 MB RAM */
    *params++ = DDR_BASE;

    /* ATAG_CMDLINE */
    int len = 0;
    const char *p = cmdline;
    while (*p++) len++;
    int words = (len + 3) / 4 + 2;

    *params++ = words;
    *params++ = ATAG_CMDLINE;
    char *dst = (char*)params;
    for (int i = 0; i < len; i++) {
        dst[i] = cmdline[i];
    }
    dst[len] = '\0';
    params += words - 2;

    /* ATAG_NONE */
    *params++ = 0;
    *params++ = ATAG_NONE;

    return params;
}

void linux_boot_main(void) {
    const char *cmd = "console=tty0 fbcon=rotate:0 root=/dev/ram0 rdinit=/init quiet loglevel=3";

    /* Setup ATAGS */
    setup_atags((uint32_t*)ATAGS_ADDR, cmd);

    /* Clean caches and jump to Linux */
    __asm__ volatile (
        "mov r0, #0\n"
        "mcr p15, #0, r0, c7, c5, #0\n"  /* Invalidate I-Cache */
        "mcr p15, #0, r0, c7, c14, #0\n" /* Clean & Invalidate D-Cache */
        "mcr p15, #0, r0, c8, c7, #0\n"  /* Invalidate TLB */
        "mov r0, #0\n"                   /* r0 = 0 */
        "ldr r1, =0xFFFFFFFF\n"          /* r1 = machine id or DTB flag */
        "ldr r2, =0x80000100\n"          /* r2 = atags pointer */
        "ldr r3, =0x80008000\n"          /* r3 = kernel entry */
        "bx  r3\n"
    );
}
