/*
 * Nokia 3210 4G (Unisoc UMS9117 / Cortex-A7) Dynamic Smart Launcher
 *
 * Runs non-destructively on top of MOCOR RTOS.
 * Provides 240x320 3x3 Grid UI, FAT32 dynamic app scanner,
 * Safe Mode protection, and MicroPython runner.
 */

#ifndef LAUNCHER_H
#define LAUNCHER_H

#include <stdint.h>
#include <stddef.h>

#define SCREEN_W 240
#define SCREEN_H 320

/* Color definitions RGB565 */
#define COLOR_BLACK       0x0000
#define COLOR_WHITE       0xFFFF
#define COLOR_GRAY        0x8410
#define COLOR_DARK_GRAY   0x2104
#define COLOR_BLUE        0x001F
#define COLOR_NOKIA_BLUE  0x1116  /* Nokia signature blue */
#define COLOR_LIGHT_BLUE  0x4D3F
#define COLOR_GREEN       0x07E0
#define COLOR_RED         0xF800
#define COLOR_YELLOW      0xFFE0
#define COLOR_CYAN        0x07FF
#define COLOR_ORANGE      0xFC00
#define COLOR_BG          0x0842  /* Dark stylish background */
#define COLOR_SELECTION   0x03FF  /* Vibrant selection highlight */

/* Maximum number of launcher apps supported in grid */
#define MAX_APPS 27

/* Keypad codes (MOCOR / UMS9117 / Nokia TA-1618) */
#define KEY_UP        0x04
#define KEY_DOWN      0x05
#define KEY_LEFT      0x06
#define KEY_RIGHT     0x07
#define KEY_CENTER    0x0D   /* D-Pad Select / OK */
#define KEY_SOFT_L    0x01   /* Left Softkey (Open) */
#define KEY_SOFT_R    0x09   /* Right Softkey (Exit/Back on TA-1618) */
#define KEY_SOFT_R_ALT 0x02  /* Alternate softkey code */
#define KEY_CALL      0x08   /* Call key */
#define KEY_RED       0x1B   /* Red Call End / Power */
#define KEY_0         0x30   /* Safe mode key */
#define KEY_1         0x31
#define KEY_2         0x32
#define KEY_3         0x33
#define KEY_4         0x34
#define KEY_5         0x35
#define KEY_6         0x36
#define KEY_7         0x37
#define KEY_8         0x38
#define KEY_9         0x39
#define KEY_STAR      0x2A
#define KEY_HASH      0x23

typedef struct {
    char name[32];
    char path[64];
    char exec[64];
    uint16_t icon_color;
    uint8_t is_python;
    uint8_t is_jar;
    uint8_t is_linux;
    uint8_t is_valid;
} app_entry_t;

typedef struct {
    uint16_t *framebuffer;
    app_entry_t apps[MAX_APPS];
    int app_count;
    int selected_index;
    int current_page;
    int safe_mode;
    int sd_ready;
} launcher_state_t;

void launcher_init(void);
void launcher_run(void);
void launcher_exit(void);

#endif /* LAUNCHER_H */
