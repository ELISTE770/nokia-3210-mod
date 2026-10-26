#!/usr/bin/env python3
"""
render_launcher_screenshot.py - Pixel-perfect renderer of the Nokia 3210 4G
Smart Launcher framebuffer directly from the C implementation specifications.
"""

import os
from PIL import Image, ImageDraw, ImageFont

# Screen dimensions
W, H = 240, 320

def rgb565_to_rgb888(c):
    r = ((c >> 11) & 0x1F) * 255 // 31
    g = ((c >> 5) & 0x3F) * 255 // 63
    b = (c & 0x1F) * 255 // 31
    return (r, g, b)

# Palette
COLOR_BLACK       = rgb565_to_rgb888(0x0000)
COLOR_WHITE       = rgb565_to_rgb888(0xFFFF)
COLOR_GRAY        = rgb565_to_rgb888(0x8410)
COLOR_DARK_GRAY   = rgb565_to_rgb888(0x2104)
COLOR_NOKIA_BLUE  = rgb565_to_rgb888(0x1116)
COLOR_LIGHT_BLUE  = rgb565_to_rgb888(0x4D3F)
COLOR_GREEN       = rgb565_to_rgb888(0x07E0)
COLOR_RED         = rgb565_to_rgb888(0xF800)
COLOR_YELLOW      = rgb565_to_rgb888(0xFFE0)
COLOR_CYAN        = rgb565_to_rgb888(0x07FF)
COLOR_ORANGE      = rgb565_to_rgb888(0xFC00)
COLOR_BG          = rgb565_to_rgb888(0x0842)
COLOR_SELECTION   = rgb565_to_rgb888(0x03FF)

# Load font8x16
font_path = os.path.join(os.path.dirname(__file__), "../src/launcher/font8x16.h")
font_bytes = []
with open(font_path, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        parts = line.split("/*")[0].split(",")
        for p in parts:
            p = p.strip()
            if p.startswith("0x"):
                font_bytes.append(int(p, 16))

def create_screenshot(selected_index=0):
    img = Image.new("RGB", (W, H), COLOR_BG)
    draw = ImageDraw.Draw(img)

    def draw_char(x, y, char, fg, bg=None):
        ascii_code = ord(char)
        if ascii_code < 32 or ascii_code > 126:
            ascii_code = ord('?')
        offset = (ascii_code - 32) * 16
        for row in range(16):
            if y + row >= H:
                continue
            bits = font_bytes[offset + row]
            for col in range(8):
                if x + col >= W:
                    continue
                if bits & (0x80 >> col):
                    img.putpixel((x + col, y + row), fg)
                elif bg:
                    img.putpixel((x + col, y + row), bg)

    def draw_string(x, y, s, fg, bg=None):
        cur_x = x
        for c in s:
            draw_char(cur_x, y, c, fg, bg)
            cur_x += 8

    def draw_string_centered(y, s, fg, bg=None):
        w = len(s) * 8
        x = max(0, (W - w) // 2)
        draw_string(x, y, s, fg, bg)

    # 1. Header (Deep Nokia Navy)
    draw.rectangle([0, 0, W, 24], fill=COLOR_NOKIA_BLUE)
    draw_string(8, 4, "12:30", COLOR_WHITE)

    # SD pill (green)
    draw.rectangle([138, 4, 164, 19], fill=COLOR_GREEN)
    draw_string(142, 4, "SD", COLOR_BLACK)

    # Battery pill
    draw_string(185, 4, "[85%]", COLOR_CYAN)

    # Header divider
    draw.line([0, 24, W, 24], fill=COLOR_LIGHT_BLUE, width=2)

    # 2. Grid Apps Definition
    apps = [
        {"name": "Gemini", "type": 0, "color": rgb565_to_rgb888(0x2A1F)}, # Gemini AI
        {"name": "Weathr", "type": 1, "color": rgb565_to_rgb888(0x051F)}, # Weather
        {"name": "Files",  "type": 2, "color": rgb565_to_rgb888(0xFBE0)}, # File Manager
        {"name": "Snake+", "type": 3, "color": rgb565_to_rgb888(0x07E0)}, # Snake Pro
        {"name": "Bounce", "type": 5, "color": rgb565_to_rgb888(0xFA00)}, # Bounce Tales J2ME
        {"name": "Linux",  "type": 6, "color": COLOR_DARK_GRAY},           # Alpine Linux Tux
        {"name": "PyREPL", "type": 4, "color": rgb565_to_rgb888(0x319F)}, # Python REPL
        {"name": "Notes",  "type": 1, "color": rgb565_to_rgb888(0xFD20)}, # Notes
        {"name": "CamPro", "type": 0, "color": rgb565_to_rgb888(0x8010)}, # Camera Pro
    ]

    col_x = [15, 95, 175]
    row_y = [36, 122, 208]

    for i, app in enumerate(apps):
        col = i % 3
        row = i // 3
        x = col_x[col]
        y = row_y[row]
        is_sel = (i == selected_index)

        # Highlight frame
        if is_sel:
            draw.rectangle([x - 5, y - 4, x + 47, y + 64], fill=COLOR_DARK_GRAY)
            draw.rectangle([x - 5, y - 4, x + 47, y + 64], outline=COLOR_SELECTION, width=2)
            draw.rectangle([x - 6, y - 5, x + 48, y + 65], outline=COLOR_WHITE, width=1)

        # Icon box
        color = app["color"]
        draw.rounded_rectangle([x, y, x + 40, y + 40], radius=8, fill=color)

        # Inner glyph
        itype = app["type"]
        if itype == 0: # Gemini Sparkle
            draw.rectangle([x + 18, y + 8, x + 22, y + 32], fill=COLOR_WHITE)
            draw.rectangle([x + 8, y + 18, x + 32, y + 22], fill=COLOR_WHITE)
            draw.rectangle([x + 14, y + 14, x + 26, y + 26], fill=COLOR_WHITE)
        elif itype == 1: # Weather Sun/Cloud
            draw.ellipse([x + 12, y + 10, x + 26, y + 24], fill=COLOR_YELLOW)
            draw.rounded_rectangle([x + 10, y + 18, x + 30, y + 30], radius=4, fill=COLOR_WHITE)
        elif itype == 2: # Files
            draw.rectangle([x + 8, y + 12, x + 18, y + 16], fill=COLOR_WHITE)
            draw.rectangle([x + 8, y + 16, x + 32, y + 32], fill=COLOR_WHITE)
            draw.rectangle([x + 11, y + 19, x + 29, y + 29], fill=color)
        elif itype == 3: # Snake Game
            draw.rectangle([x + 10, y + 12, x + 18, y + 20], fill=COLOR_WHITE)
            draw.rectangle([x + 18, y + 18, x + 26, y + 26], fill=COLOR_WHITE)
            draw.rectangle([x + 22, y + 24, x + 30, y + 32], fill=COLOR_WHITE)
        elif itype == 4: # Python 'Py'
            draw_char(x + 10, y + 12, 'P', COLOR_WHITE)
            draw_char(x + 20, y + 12, 'y', COLOR_WHITE)
        elif itype == 5: # Java Cup ☕
            draw.rectangle([x + 11, y + 15, x + 25, y + 29], fill=COLOR_WHITE) # Cup
            draw.rectangle([x + 25, y + 18, x + 29, y + 26], fill=COLOR_WHITE) # Handle
            draw.rectangle([x + 8, y + 30, x + 30, y + 32], fill=COLOR_WHITE)  # Saucer
            draw.line([x + 14, y + 8, x + 14, y + 12], fill=COLOR_YELLOW, width=2) # Steam
            draw.line([x + 19, y + 6, x + 19, y + 12], fill=COLOR_YELLOW, width=2)
        elif itype == 6: # Linux Tux 🐧
            draw.ellipse([x + 10, y + 10, x + 30, y + 32], fill=COLOR_BLACK) # Body
            draw.ellipse([x + 13, y + 16, x + 27, y + 30], fill=COLOR_WHITE) # Belly
            draw.polygon([(x + 17, y + 15), (x + 23, y + 15), (x + 20, y + 19)], fill=COLOR_YELLOW) # Beak
            draw.ellipse([x + 10, y + 29, x + 19, y + 33], fill=COLOR_ORANGE) # Left foot
            draw.ellipse([x + 21, y + 29, x + 30, y + 33], fill=COLOR_ORANGE) # Right foot

        # App Label
        label = app["name"][:6]
        text_x = x - 2
        text_col = COLOR_YELLOW if is_sel else COLOR_WHITE
        draw_string(text_x, y + 46, label, text_col)

    # 3. Footer
    draw.line([0, 294, W, 294], fill=COLOR_LIGHT_BLUE, width=2)
    draw.rectangle([0, 296, W, H], fill=COLOR_NOKIA_BLUE)
    draw_string(8, 300, "Select", COLOR_WHITE)
    draw_string(195, 300, "Exit", COLOR_WHITE)

    return img

def create_phone_mockup(screen_img):
    """Embeds the screenshot inside a realistic Nokia 3210 4G chassis"""
    SCALE = 2
    sw, sh = W * SCALE, H * SCALE
    screen_scaled = screen_img.resize((sw, sh), Image.NEAREST)

    # Chassis dimensions
    pw, ph = sw + 120, sh + 420
    phone = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
    pdraw = ImageDraw.Draw(phone)

    # Nokia body (Signature Nokia Retro Cyan/Blue Body)
    BODY_COLOR = (18, 52, 86)
    BEZEL_COLOR = (12, 16, 22)
    KEY_COLOR = (28, 36, 46)
    TEXT_COLOR = (220, 230, 242)

    # Rounded chassis
    pdraw.rounded_rectangle([10, 10, pw - 10, ph - 10], radius=45, fill=BODY_COLOR, outline=(40, 80, 120), width=4)

    # Earpiece speaker slit
    pdraw.rounded_rectangle([pw // 2 - 35, 35, pw // 2 + 35, 42], radius=3, fill=(10, 15, 20))

    # Screen Bezel
    bx = (pw - sw) // 2
    by = 70
    pdraw.rounded_rectangle([bx - 12, by - 12, bx + sw + 12, by + sh + 12], radius=16, fill=BEZEL_COLOR, outline=(60, 90, 120), width=2)

    # Paste screen
    phone.paste(screen_scaled, (bx, by))

    # Nokia Logo under screen
    logo_y = by + sh + 20
    # Center text roughly
    font_large = None
    # Draw simple NOKIA text
    pdraw.text((pw // 2 - 35, logo_y), "NOKIA", fill=(180, 200, 220))

    # Keypad Area
    ky_start = logo_y + 40
    # D-Pad in center
    cx, cy = pw // 2, ky_start + 40
    pdraw.ellipse([cx - 40, cy - 40, cx + 40, cy + 40], fill=(45, 60, 75), outline=(90, 120, 150), width=2)
    pdraw.ellipse([cx - 18, cy - 18, cx + 18, cy + 18], fill=(70, 95, 120)) # Center Select key

    # Softkeys
    pdraw.rounded_rectangle([bx, ky_start + 5, bx + 65, ky_start + 35], radius=6, fill=KEY_COLOR, outline=(60, 80, 100)) # Left Soft
    pdraw.text((bx + 15, ky_start + 12), "---", fill=TEXT_COLOR)

    pdraw.rounded_rectangle([bx + sw - 65, ky_start + 5, bx + sw, ky_start + 35], radius=6, fill=KEY_COLOR, outline=(60, 80, 100)) # Right Soft
    pdraw.text((bx + sw - 50, ky_start + 12), "---", fill=TEXT_COLOR)

    # Call / End keys
    pdraw.rounded_rectangle([bx, ky_start + 45, bx + 65, ky_start + 75], radius=6, fill=(20, 80, 40), outline=(40, 120, 60)) # Green Call
    pdraw.text((bx + 20, ky_start + 52), "TALK", fill=COLOR_WHITE)

    pdraw.rounded_rectangle([bx + sw - 65, ky_start + 45, bx + sw, ky_start + 75], radius=6, fill=(110, 25, 25), outline=(160, 40, 40)) # Red End
    pdraw.text((bx + sw - 48, ky_start + 52), "END", fill=COLOR_WHITE)

    # T9 Numeric Keypad (4 rows x 3 columns)
    num_y = ky_start + 95
    t9_keys = [
        ["1", "2 abc", "3 def"],
        ["4 ghi", "5 jkl", "6 mno"],
        ["7 pqrs", "8 tuv", "9 wxyz"],
        ["*", "0", "#"]
    ]
    col_w = (sw - 20) // 3
    for r_idx, row in enumerate(t9_keys):
        for c_idx, k_label in enumerate(row):
            kx = bx + c_idx * (col_w + 10)
            ky = num_y + r_idx * 48
            pdraw.rounded_rectangle([kx, ky, kx + col_w, ky + 40], radius=8, fill=KEY_COLOR, outline=(50, 70, 90))
            pdraw.text((kx + col_w // 2 - len(k_label) * 3, ky + 12), k_label, fill=TEXT_COLOR)

    return phone

if __name__ == "__main__":
    out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    artifact_dir = "C:/Users/Eli/.gemini/antigravity/brain/3be6fd3b-a95c-469e-a3ad-4697f8aaf3bf"

    screen = create_screenshot(selected_index=0) # Gemini selected
    screen_path_ws = os.path.join(out_dir, "launcher_screenshot_qvga.png")
    screen.save(screen_path_ws)

    # Upscaled 2x
    screen_2x = screen.resize((W * 2, H * 2), Image.NEAREST)
    screen_2x_path = os.path.join(out_dir, "launcher_screenshot.png")
    screen_2x.save(screen_2x_path)

    # Full Phone Chassis Mockup
    mockup = create_phone_mockup(screen)
    mockup_path_ws = os.path.join(out_dir, "nokia_3210_launcher_mockup.png")
    mockup.save(mockup_path_ws)

    if os.path.exists(artifact_dir):
        screen.save(os.path.join(artifact_dir, "launcher_screenshot_qvga.png"))
        screen_2x.save(os.path.join(artifact_dir, "launcher_screenshot.png"))
        mockup.save(os.path.join(artifact_dir, "nokia_3210_launcher_mockup.png"))

    print("Screenshots generated:")
    print(" - 1:1 QVGA:", screen_path_ws)
    print(" - 2x Scale:", screen_2x_path)
    print(" - Phone Mockup:", mockup_path_ws)
