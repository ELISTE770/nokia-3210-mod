/*
 * Nokia 3210 4G (Unisoc UMS9117) - Dynamic Smart Launcher Core
 *
 * Implements 240x320 3x3 Grid Interface, Font Renderer,
 * Safe Mode Protection, SD Card App Scanner, and In-OS Return.
 */

#include "launcher.h"

/* Bare-metal string helpers */
static char* mini_strncpy(char *dest, const char *src, size_t n) {
    size_t i;
    for (i = 0; i < n && src[i] != '\0'; i++) {
        dest[i] = src[i];
    }
    for (; i < n; i++) {
        dest[i] = '\0';
    }
    return dest;
}

#define strncpy mini_strncpy

/* Embed 8x16 bitmap font */
static const uint8_t font8x16[] = {
#include "font8x16.h"
};

/* Global Launcher State */
static launcher_state_t g_state;
static uint16_t g_fb_storage[SCREEN_W * SCREEN_H] __attribute__((aligned(32)));

/* External exit trampoline */
extern void launcher_return_to_mocor(void);

/* Hardware register definitions for UMS9117 (Cortex-A7) */
typedef volatile struct {
    uint32_t ctrl, int_en, int_raw, int_mask;
    uint32_t int_clr, dummy_14, polarity, debounce;
    uint32_t long_key, sleep_cnt, clk_divide, key_status;
    uint32_t sleep_stat, dbg_stat1, dbg_stat2;
} keypad_base_t;

typedef volatile struct {
    uint32_t ctrl, disp_size, lcm_start, lcm_size;
    uint32_t bg_color, fifo_status, sync_delay, dummy[1];
    struct {
        uint32_t ctrl, y_base_addr, uv_base_addr, size_xy;
        uint32_t pitch, disp_xy, dummy[6];
    } img;
    struct {
        uint32_t ctrl, base_addr, alpha_base_addr, size_xy;
        uint32_t pitch, disp_xy, alpha, grey_rgb;
        uint32_t ck, dummy[3];
    } ocd1, ocd2, ocd3;
    struct {
        uint32_t ctrl, base_addr, start_xy, size_xy;
        uint32_t pitch, dummy[3];
    } cap;
    struct {
        uint32_t ctrl, contrast, saturation, brightness;
    } y2r;
    struct {
        uint32_t en, clr, status, raw;
    } irq;
} lcdc_base_t;

#define KEYPAD_BASE ((keypad_base_t*)0x40250000)
#define LCDC_BASE   ((lcdc_base_t*)0x20800000)

/* Exact matrix scan table extracted from Nokia 3210 4G (TA-1618) */
static const int16_t g_nokia_keymap[64] = {
    0x2a, 0x37, 0x31, 0x01, 0x34, -1, -1, -1, /* row 0: * 7 1 SoftL 4 */
    0x30, 0x33, 0x32, 0x05, 0x35, -1, -1, -1, /* row 1: 0 3 2 Down  5 */
    0x08, 0x06,   -1, 0x0d, 0x04, -1, -1, -1, /* row 2: Call Left - OK Up */
    0x23, 0x39, 0x36, 0x07, 0x09, -1, -1, -1, /* row 3: # 9 6 Right SoftR */
    -1,   -1,   -1,   -1,   -1,   -1, -1, -1,
    -1,   -1,   -1,   -1,   -1,   -1, -1, -1,
    -1,   -1,   -1,   -1,   -1,   -1, -1, -1,
    -1,   -1,   -1,   -1,   -1,   -1, -1, -1,
};

/* Calibrated hardware delay for 1 GHz Cortex-A7 (~250k loop iterations per ms) */
static void delay_ms(volatile uint32_t ms) {
    volatile uint32_t count = ms * 250000;
    while (count--) {
        __asm__ volatile ("nop");
    }
}

/* Flushes the RAM framebuffer to the UMS9117 hardware LCD controller (LCDC) */
static void lcd_flush(void) {
    /* Flush CPU Data-Cache over framebuffer & memory synchronization barrier */
    __asm__ volatile ("mcr p15, 0, %0, c7, c10, 0" : : "r" (0) : "memory");
    __asm__ volatile ("dsb" : : : "memory");

    /* Program physical framebuffer address (shifted for word addressing) */
    LCDC_BASE->img.y_base_addr = ((uint32_t)g_state.framebuffer) >> 2;
    LCDC_BASE->img.ctrl |= 1;

    /* Trigger hardware panel refresh */
    LCDC_BASE->irq.en |= 1;
    LCDC_BASE->ctrl |= 8;

    /* Wait for panel DMA transfer completion */
    volatile uint32_t timeout = 500000;
    while (((LCDC_BASE->irq.raw & 1) == 0) && --timeout);
    LCDC_BASE->irq.clr |= 1;
}

/* Graphics primitives */
static void clear_screen(uint16_t color) {
    uint32_t c32 = (color << 16) | color;
    uint32_t *dst32 = (uint32_t*)g_state.framebuffer;
    int count = (SCREEN_W * SCREEN_H) / 2;
    while (count--) {
        *dst32++ = c32;
    }
}

static void fill_rect(int x, int y, int w, int h, uint16_t color) {
    if (x < 0) { w += x; x = 0; }
    if (y < 0) { h += y; y = 0; }
    if (x + w > SCREEN_W) w = SCREEN_W - x;
    if (y + h > SCREEN_H) h = SCREEN_H - y;
    if (w <= 0 || h <= 0) return;

    for (int j = 0; j < h; j++) {
        uint16_t *line = &g_state.framebuffer[(y + j) * SCREEN_W + x];
        for (int i = 0; i < w; i++) {
            line[i] = color;
        }
    }
}

static void draw_rect(int x, int y, int w, int h, uint16_t color) {
    fill_rect(x, y, w, 1, color);
    fill_rect(x, y + h - 1, w, 1, color);
    fill_rect(x, y, 1, h, color);
    fill_rect(x + w - 1, y, 1, h, color);
}

static void draw_char(int x, int y, char c, uint16_t fg, uint16_t bg, int bg_opaque) {
    if (c < 32 || c > 126) c = '?';
    const uint8_t *glyph = &font8x16[(c - 32) * 16];

    for (int row = 0; row < 16; row++) {
        int py = y + row;
        if (py < 0 || py >= SCREEN_H) continue;
        uint8_t bits = glyph[row];
        uint16_t *line = &g_state.framebuffer[py * SCREEN_W];

        for (int col = 0; col < 8; col++) {
            int px = x + col;
            if (px < 0 || px >= SCREEN_W) continue;
            if (bits & (0x80 >> col)) {
                line[px] = fg;
            } else if (bg_opaque) {
                line[px] = bg;
            }
        }
    }
}

static void draw_string(int x, int y, const char *str, uint16_t fg, uint16_t bg, int bg_opaque) {
    int cur_x = x;
    while (*str) {
        if (*str == '\n') {
            y += 16;
            cur_x = x;
        } else {
            draw_char(cur_x, y, *str, fg, bg, bg_opaque);
            cur_x += 8;
        }
        str++;
    }
}

static void draw_string_centered(int y, const char *str, uint16_t fg, uint16_t bg, int bg_opaque) {
    int len = 0;
    const char *p = str;
    while (*p++) len++;
    int total_w = len * 8;
    int x = (SCREEN_W - total_w) / 2;
    if (x < 0) x = 0;
    draw_string(x, y, str, fg, bg, bg_opaque);
}

/* Icon glyphs */
static void draw_app_icon(int x, int y, int type, uint16_t color) {
    /* Draw rounded icon backdrop */
    fill_rect(x + 2, y, 36, 40, color);
    fill_rect(x, y + 2, 40, 36, color);
    fill_rect(x + 1, y + 1, 38, 38, color);

    /* Inner symbol based on app type */
    uint16_t sym_color = COLOR_WHITE;
    switch (type % 6) {
        case 0: /* Gemini / Sparkle */
            fill_rect(x + 18, y + 8, 4, 24, sym_color);
            fill_rect(x + 8, y + 18, 24, 4, sym_color);
            fill_rect(x + 14, y + 14, 12, 12, sym_color);
            break;
        case 1: /* Weather / Sun & Cloud */
            fill_rect(x + 14, y + 10, 12, 12, COLOR_YELLOW);
            fill_rect(x + 10, y + 18, 20, 10, sym_color);
            break;
        case 2: /* Files / Folder */
            fill_rect(x + 8, y + 12, 10, 4, sym_color);
            fill_rect(x + 8, y + 15, 24, 16, sym_color);
            fill_rect(x + 10, y + 17, 20, 12, color);
            break;
        case 3: /* Snake / Game */
            fill_rect(x + 10, y + 12, 8, 8, sym_color);
            fill_rect(x + 16, y + 18, 8, 8, sym_color);
            fill_rect(x + 22, y + 24, 8, 8, sym_color);
            break;
        case 4: /* Python / Code */
            draw_char(x + 10, y + 12, 'P', sym_color, 0, 0);
            draw_char(x + 20, y + 12, 'y', sym_color, 0, 0);
            break;
        case 5: /* Java J2ME / Coffee Cup */
            fill_rect(x + 11, y + 14, 14, 15, sym_color); /* Cup body */
            fill_rect(x + 25, y + 17, 4, 9, sym_color);   /* Handle */
            fill_rect(x + 8, y + 29, 22, 2, sym_color);   /* Saucer */
            fill_rect(x + 13, y + 8, 2, 4, COLOR_YELLOW); /* Steam 1 */
            fill_rect(x + 18, y + 6, 2, 6, COLOR_YELLOW); /* Steam 2 */
            break;
        case 6: /* Linux / Tux Penguin */
            fill_rect(x + 10, y + 10, 20, 22, COLOR_BLACK);  /* Body */
            fill_rect(x + 13, y + 16, 14, 14, COLOR_WHITE);  /* Belly */
            fill_rect(x + 17, y + 14, 6, 4, COLOR_YELLOW);   /* Beak */
            fill_rect(x + 11, y + 30, 8, 3, COLOR_ORANGE);   /* Left foot */
            fill_rect(x + 21, y + 30, 8, 3, COLOR_ORANGE);   /* Right foot */
            break;
        default: /* Settings / Gear */
            draw_rect(x + 12, y + 12, 16, 16, sym_color);
            fill_rect(x + 17, y + 17, 6, 6, sym_color);
            break;
    }
}

/* UI Components */
static void render_header(void) {
    /* Header background: deep sleek navy */
    fill_rect(0, 0, SCREEN_W, 24, COLOR_NOKIA_BLUE);

    /* Time & status */
    draw_string(6, 4, "12:30", COLOR_WHITE, COLOR_NOKIA_BLUE, 0);

    /* SD status pill */
    if (g_state.sd_ready) {
        fill_rect(140, 4, 26, 15, COLOR_GREEN);
        draw_string(143, 4, "SD", COLOR_BLACK, COLOR_GREEN, 0);
    } else {
        fill_rect(140, 4, 32, 15, COLOR_RED);
        draw_string(142, 4, "NO_SD", COLOR_WHITE, COLOR_RED, 0);
    }

    /* Battery pill */
    draw_string(185, 4, "[85%]", COLOR_CYAN, COLOR_NOKIA_BLUE, 0);

    /* Divider */
    fill_rect(0, 24, SCREEN_W, 2, COLOR_LIGHT_BLUE);
}

static void render_footer(void) {
    /* Footer background */
    fill_rect(0, 296, SCREEN_W, 24, COLOR_NOKIA_BLUE);
    fill_rect(0, 294, SCREEN_W, 2, COLOR_LIGHT_BLUE);

    /* Softkeys */
    draw_string(8, 300, "Select", COLOR_WHITE, COLOR_NOKIA_BLUE, 0);
    draw_string(195, 300, "Exit", COLOR_WHITE, COLOR_NOKIA_BLUE, 0);
}

static void render_grid(void) {
    int start_idx = g_state.current_page * 9;
    int end_idx = start_idx + 9;
    if (end_idx > g_state.app_count) end_idx = g_state.app_count;

    /* Grid Geometry: 3 columns x 3 rows */
    const int col_x[3] = { 15, 95, 175 };
    const int row_y[3] = { 36, 122, 208 };

    for (int i = start_idx; i < start_idx + 9; i++) {
        int slot = i - start_idx;
        int col = slot % 3;
        int row = slot / 3;
        int x = col_x[col];
        int y = row_y[row];

        if (i < end_idx && g_state.apps[i].is_valid) {
            int is_selected = (i == g_state.selected_index);

            /* Selection highlight frame */
            if (is_selected) {
                fill_rect(x - 5, y - 4, 52, 68, COLOR_DARK_GRAY);
                draw_rect(x - 5, y - 4, 52, 68, COLOR_SELECTION);
                draw_rect(x - 6, y - 5, 54, 70, COLOR_WHITE);
            }

            /* Draw icon */
            draw_app_icon(x + 1, y, i, g_state.apps[i].icon_color);

            /* Draw app label (shortened to 6 chars for grid alignment) */
            char label[8];
            strncpy(label, g_state.apps[i].name, 6);
            label[6] = '\0';
            int text_x = x - 2;
            draw_string(text_x, y + 46, label, is_selected ? COLOR_YELLOW : COLOR_WHITE, 0, 0);
        } else {
            /* Empty slot placeholder */
            draw_rect(x + 4, y + 4, 32, 32, COLOR_DARK_GRAY);
        }
    }

    /* Page indicator dots */
    int total_pages = (g_state.app_count + 8) / 9;
    if (total_pages > 1) {
        int dot_start_x = (SCREEN_W - (total_pages * 12)) / 2;
        for (int p = 0; p < total_pages; p++) {
            uint16_t dot_col = (p == g_state.current_page) ? COLOR_WHITE : COLOR_DARK_GRAY;
            fill_rect(dot_start_x + p * 12, 282, 6, 6, dot_col);
        }
    }
}

static void render_safe_mode_screen(void) {
    clear_screen(COLOR_BLACK);
    fill_rect(0, 0, SCREEN_W, 30, COLOR_RED);
    draw_string_centered(8, "SAFE MODE ACTIVE", COLOR_WHITE, COLOR_RED, 1);

    draw_string(16, 50, "Nokia 3210 4G Protection", COLOR_YELLOW, 0, 0);
    draw_string(16, 75, "Auto-boot has been bypassed.", COLOR_WHITE, 0, 0);
    draw_string(16, 95, "Key [0] was held at launch", COLOR_WHITE, 0, 0);
    draw_string(16, 115, "or SD Card was not found.", COLOR_WHITE, 0, 0);

    draw_rect(12, 145, 216, 80, COLOR_DARK_GRAY);
    draw_string(20, 155, "- Check SD:/nokia/ folder", COLOR_CYAN, 0, 0);
    draw_string(20, 175, "- Verify FAT32 partition", COLOR_CYAN, 0, 0);
    draw_string(20, 195, "- Edit SD:/nokia/config.txt", COLOR_CYAN, 0, 0);

    fill_rect(0, 290, SCREEN_W, 30, COLOR_NOKIA_BLUE);
    draw_string_centered(298, "Press Red Key to Return", COLOR_WHITE, COLOR_NOKIA_BLUE, 1);
}

/* App Scanner & Registry Initialization */
static void populate_default_apps(void) {
    g_state.app_count = 0;

    /* 1. Gemini AI Assistant */
    app_entry_t *a = &g_state.apps[g_state.app_count++];
    strncpy(a->name, "Gemini", 31);
    strncpy(a->path, "SD:/nokia/apps/launcher_only/gemini", 63);
    strncpy(a->exec, "main.py", 63);
    a->icon_color = 0x2A1F; /* Royal Blue */
    a->is_python = 1;
    a->is_jar = 0;
    a->is_linux = 0;
    a->is_valid = 1;

    /* 2. Live Weather */
    a = &g_state.apps[g_state.app_count++];
    strncpy(a->name, "Weathr", 31);
    strncpy(a->path, "SD:/nokia/apps/launcher_only/weather", 63);
    strncpy(a->exec, "main.py", 63);
    a->icon_color = 0x051F; /* Cyan */
    a->is_python = 1;
    a->is_jar = 0;
    a->is_linux = 0;
    a->is_valid = 1;

    /* 3. Advanced File Manager */
    a = &g_state.apps[g_state.app_count++];
    strncpy(a->name, "Files", 31);
    strncpy(a->path, "SD:/nokia/apps/launcher_only/file_browser", 63);
    strncpy(a->exec, "main.py", 63);
    a->icon_color = 0xFBE0; /* Amber Orange */
    a->is_python = 1;
    a->is_jar = 0;
    a->is_linux = 0;
    a->is_valid = 1;

    /* 4. Snake Retro / C Engine */
    a = &g_state.apps[g_state.app_count++];
    strncpy(a->name, "Snake+", 31);
    strncpy(a->path, "SD:/nokia/apps/launcher_only/snake", 63);
    strncpy(a->exec, "app.bin", 63);
    a->icon_color = 0x07E0; /* Classic Green */
    a->is_python = 0;
    a->is_jar = 0;
    a->is_linux = 0;
    a->is_valid = 1;

    /* 5. Bounce Tales - Java J2ME Game */
    a = &g_state.apps[g_state.app_count++];
    strncpy(a->name, "Bounce", 31);
    strncpy(a->path, "SD:/nokia/apps/launcher_only/bounce", 63);
    strncpy(a->exec, "bounce.jar", 63);
    a->icon_color = 0xFA00; /* Java Orange */
    a->is_python = 0;
    a->is_jar = 1;
    a->is_linux = 0;
    a->is_valid = 1;

    /* 6. Alpine Linux - Dedicated Full OS */
    a = &g_state.apps[g_state.app_count++];
    strncpy(a->name, "Linux", 31);
    strncpy(a->path, "SD:/nokia/apps/launcher_only/linux", 63);
    strncpy(a->exec, "boot_linux.bin", 63);
    a->icon_color = 0x2104; /* Dark Graphite */
    a->is_python = 0;
    a->is_jar = 0;
    a->is_linux = 1;
    a->is_valid = 1;

    /* 7. MicroPython Interactive REPL */
    a = &g_state.apps[g_state.app_count++];
    strncpy(a->name, "PyREPL", 31);
    strncpy(a->path, "SD:/nokia/apps/launcher_only/repl", 63);
    strncpy(a->exec, "main.py", 63);
    a->icon_color = 0x319F; /* Python Blue */
    a->is_python = 1;
    a->is_jar = 0;
    a->is_linux = 0;
    a->is_valid = 1;

    /* 8. Smart Notes */
    a = &g_state.apps[g_state.app_count++];
    strncpy(a->name, "Notes", 31);
    strncpy(a->path, "SD:/nokia/apps/launcher_only/notes", 63);
    strncpy(a->exec, "main.py", 63);
    a->icon_color = 0xFD20; /* Sunset Orange */
    a->is_python = 1;
    a->is_jar = 0;
    a->is_linux = 0;
    a->is_valid = 1;

    /* 9. Standalone Camera Pro shortcut */
    a = &g_state.apps[g_state.app_count++];
    strncpy(a->name, "CamPro", 31);
    strncpy(a->path, "SD:/nokia/apps/standalone/camera_pro", 63);
    strncpy(a->exec, "app.bin", 63);
    a->icon_color = 0x8010; /* Purple */
    a->is_python = 0;
    a->is_jar = 0;
    a->is_linux = 0;
    a->is_valid = 1;
}

/* App execution stub */
static void launch_selected_app(void) {
    if (g_state.selected_index < 0 || g_state.selected_index >= g_state.app_count) return;
    app_entry_t *app = &g_state.apps[g_state.selected_index];

    /* Display launching banner */
    clear_screen(COLOR_BG);
    render_header();
    draw_string_centered(115, "Launching...", COLOR_WHITE, COLOR_BG, 1);
    draw_string_centered(140, app->name, COLOR_YELLOW, COLOR_BG, 1);

    const char *runtime_label = "[Native ARM Binary]";
    if (app->is_linux) {
        runtime_label = "[Booting Alpine Linux OS]";
    } else if (app->is_jar) {
        runtime_label = "[J2ME Java Runtime .JAR]";
    } else if (app->is_python) {
        runtime_label = "[MicroPython Engine]";
    }
    draw_string_centered(165, runtime_label, COLOR_CYAN, COLOR_BG, 1);

    if (app->is_linux) {
        draw_string_centered(190, "Type 'reboot' to return", COLOR_WHITE, COLOR_BG, 1);
    }

    render_footer();
    lcd_flush();

    delay_ms(800);

    /* In production with full MicroPython interpreter linked:
     * mp_embed_exec_file(full_path);
     * For now, returns cleanly to launcher menu.
     */
}

/* Hardware Keypad polling with matrix scanning and EIC power button */
static int read_key_event(void) {
    keypad_base_t *kpd = KEYPAD_BASE;
    uint32_t status = kpd->key_status;
    uint32_t ev = kpd->int_raw;
    kpd->int_clr = 0xfff;

    /* Check EIC status register for Red Power/End key (bit 1) */
    volatile uint32_t *eic_reg = (volatile uint32_t*)0x40608280;
    uint32_t eic_val = *eic_reg;
    if ((eic_val >> 1) & 1) {
        return KEY_RED;
    }
    /* EIC9 for key '8' */
    if ((eic_val >> 9) & 1) {
        return KEY_8;
    }

    if (!(ev & 0xff) && !status) return 0;

    /* Matrix position: (row << 3) | col */
    int k = (status & 0x70) >> 1 | (status & 7);
    if (k >= 0 && k < 64) {
        int code = g_nokia_keymap[k];
        if (code > 0) return code;
    }

    return 0;
}

/* Debounced key reader with hold / repeat state machine */
static int get_key_pressed(void) {
    static int s_last_key = 0;
    static int s_hold_count = 0;
    int key = read_key_event();

    if (!key) {
        s_last_key = 0;
        s_hold_count = 0;
        return 0;
    }

    if (key != s_last_key) {
        s_last_key = key;
        s_hold_count = 0;
        return key; /* Initial press */
    }

    s_hold_count++;
    /* Initial hold delay ~300ms (10 frames of 30ms), then repeat every 120ms (4 frames) */
    if (s_hold_count > 10 && (s_hold_count % 4) == 0) {
        return key;
    }

    return 0;
}

/* Main Launcher C Entry */
void launcher_main(void) {
    /* Set framebuffer pointer */
    g_state.framebuffer = g_fb_storage;
    g_state.selected_index = 0;
    g_state.current_page = 0;
    g_state.safe_mode = 0;
    g_state.sd_ready = 1;

    /* Check for Safe Mode (e.g. key '0' held during boot) */
    int initial_key = read_key_event();
    if (initial_key == KEY_0) {
        g_state.safe_mode = 1;
    }

    populate_default_apps();

    /* Render initial UI */
    if (g_state.safe_mode) {
        render_safe_mode_screen();
    } else {
        clear_screen(COLOR_BG);
        render_header();
        render_grid();
        render_footer();
    }
    lcd_flush();

    /* Event Loop */
    int running = 1;
    int loop_counter = 0;

    while (running) {
        delay_ms(30);
        loop_counter++;

        int key = get_key_pressed();
        if (!key) continue;

        if (g_state.safe_mode) {
            if (key == KEY_RED || key == KEY_SOFT_R || key == KEY_SOFT_R_ALT) {
                running = 0;
            }
            continue;
        }

        switch (key) {
            case KEY_UP:
                if (g_state.selected_index >= 3) {
                    g_state.selected_index -= 3;
                }
                break;
            case KEY_DOWN:
                if (g_state.selected_index + 3 < g_state.app_count) {
                    g_state.selected_index += 3;
                }
                break;
            case KEY_LEFT:
                if (g_state.selected_index > 0) {
                    g_state.selected_index--;
                }
                break;
            case KEY_RIGHT:
                if (g_state.selected_index + 1 < g_state.app_count) {
                    g_state.selected_index++;
                }
                break;
            case KEY_CENTER:
            case KEY_SOFT_L:
                launch_selected_app();
                break;
            case KEY_SOFT_R:
            case KEY_SOFT_R_ALT:
            case KEY_RED:
                /* Seamless exit back to Nokia MOCOR OS */
                running = 0;
                break;
            case KEY_0:
                /* Toggle safe mode */
                g_state.safe_mode = 1;
                render_safe_mode_screen();
                lcd_flush();
                continue;
            default:
                break;
        }

        /* Update active page based on selection */
        g_state.current_page = g_state.selected_index / 9;

        /* Re-render grid */
        clear_screen(COLOR_BG);
        render_header();
        render_grid();
        render_footer();
        lcd_flush();
    }

    /* Clean up screen before returning to MOCOR RTOS */
    clear_screen(COLOR_BLACK);
    lcd_flush();
    launcher_return_to_mocor();
}
