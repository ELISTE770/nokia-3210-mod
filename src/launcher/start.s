/*
 * start.s - Entry point with DHTB header & non-destructive context preservation
 * for Nokia 3210 4G (UMS9117 Cortex-A7)
 */

    .arch armv7-a
    .syntax unified
    .code 32

    .section .text._start, "ax", %progbits
    .global _start
    .global launcher_return_to_mocor
    .type _start, %function

_start:
    /* --- DHTB Container Header (512 bytes / 0x200) --- */
    .ascii "DHTB"
    .long 1
    .org _start + 0x30, 0
    .long __image_size - 0x200
    .org _start + 0x200, 0

    /* --- Code Entry Point at 0x200 --- */
launcher_entry:
    /* Preserve caller registers for non-destructive return to MOCOR RTOS */
    ldr     r12, =saved_context
    stmia   r12, {r4-r11}
    str     sp, [r12, #32]
    str     lr, [r12, #36]

    /* Save caller CPSR */
    mrs     r0, cpsr
    str     r0, [r12, #40]

    /* Setup local launcher stack in high scratch RAM */
    ldr     sp, =__launcher_stack_top

    /* Clear BSS */
    ldr     r0, =__bss_start
    ldr     r1, =__bss_end
    mov     r2, #0
1:
    cmp     r0, r1
    strlt   r2, [r0], #4
    blt     1b

    /* Call C launcher entry point */
    bl      launcher_main

    /* Return seamlessly to caller */
launcher_return_to_mocor:
    ldr     r12, =saved_context
    /* Restore CPSR */
    ldr     r0, [r12, #40]
    msr     cpsr_cxsf, r0

    /* Restore registers and return to Nokia OS safely (ARMv7-A compliant) */
    ldr     sp, [r12, #32]
    ldr     lr, [r12, #36]
    ldmia   r12, {r4-r11}
    bx      lr

    .data
    .align 4
    .global saved_context
saved_context:
    .space 44 /* r4-r11 (32), sp (4), lr (4), cpsr (4) */

    .bss
    .align 4
__launcher_stack_bottom:
    .space 0x8000 /* 32 KB stack */
__launcher_stack_top:

