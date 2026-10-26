/*
 * launcher.ld - Linker script for Nokia 3210 4G (UMS9117 Cortex-A7)
 * Targets DDR RAM execution at 0x80100000
 */

OUTPUT_FORMAT("elf32-littlearm")
OUTPUT_ARCH(arm)

ENTRY(_start)

IMAGE_BASE = 0x80100000;
IMAGE_MAX_SIZE = 0x00400000; /* 4 MB */

SECTIONS {
    . = IMAGE_BASE;

    .text : {
        __image_start = .;
        *(.text._start)
        *(.text .text.*)
        *(.rodata .rodata.*)
        . = ALIGN(4);
    }

    .data : {
        *(.data .data.*)
        . = ALIGN(4);
        __image_end = .;
    }

    __image_size = __image_end - __image_start;

    .bss (NOLOAD) : {
        . = ALIGN(4);
        __bss_start = .;
        *(.bss .bss.*)
        *(COMMON)
        . = ALIGN(4);
        __bss_end = .;
    }

    __bss_size = __bss_end - __bss_start;

    /DISCARD/ : {
        *(.ARM.exidx .ARM.exidx.*)
        *(.comment)
        *(.note.*)
    }
}
