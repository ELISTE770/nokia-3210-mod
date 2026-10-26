"""
File Manager App for Nokia 3210 4G (UMS9117)
Browses SD Card files and folders.
"""

import nokia
import time

def render_file_list(files, selected_idx):
    nokia.display.clear(nokia.COLOR_BLACK)

    # Header
    nokia.display.draw_rect(0, 0, 240, 26, nokia.COLOR_NOKIA_BLUE, fill=True)
    nokia.display.draw_text(8, 6, "SD Card Explorer: /nokia", nokia.COLOR_WHITE, nokia.COLOR_NOKIA_BLUE)

    y = 36
    for i, item in enumerate(files):
        is_sel = (i == selected_idx)
        bg = nokia.COLOR_DARK_GRAY if is_sel else nokia.COLOR_BLACK
        fg = nokia.COLOR_YELLOW if is_sel else nokia.COLOR_WHITE

        nokia.display.draw_rect(6, y - 2, 228, 20, bg, fill=True)
        if is_sel:
            nokia.display.draw_rect(6, y - 2, 228, 20, nokia.COLOR_CYAN, fill=False)

        icon = "[DIR]" if item.endswith("/") else "[FILE]"
        nokia.display.draw_text(10, y, f"{icon} {item}", fg, bg)
        y += 24

    # Footer
    nokia.display.draw_rect(0, 296, 240, 24, nokia.COLOR_NOKIA_BLUE, fill=True)
    nokia.display.draw_text(8, 300, "Open", nokia.COLOR_WHITE, nokia.COLOR_NOKIA_BLUE)
    nokia.display.draw_text(190, 300, "Exit", nokia.COLOR_WHITE, nokia.COLOR_NOKIA_BLUE)
    nokia.display.update()

def main():
    files = [
        "../",
        "apps/",
        "lib/",
        "config.txt",
        "launcher.bin",
        "micropython.bin",
    ]
    sel = 0
    render_file_list(files, sel)

    while True:
        key = nokia.keypad.poll()
        if key in (nokia.KEY_RED, nokia.KEY_SOFT_R):
            break
        elif key == nokia.KEY_UP and sel > 0:
            sel -= 1
            render_file_list(files, sel)
        elif key == nokia.KEY_DOWN and sel < len(files) - 1:
            sel += 1
            render_file_list(files, sel)
        time.sleep(0.05)

if __name__ == "__main__":
    main()
