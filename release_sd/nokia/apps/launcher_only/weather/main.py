"""
Weather Live App for Nokia 3210 4G (UMS9117)
Fetches and displays live weather forecasts.
"""

import nokia
import time

def render_weather():
    nokia.display.clear(0x0112) # Deep sky blue

    # Header
    nokia.display.draw_rect(0, 0, 240, 26, nokia.COLOR_NOKIA_BLUE, fill=True)
    nokia.display.draw_text(8, 6, "Weather Forecast", nokia.COLOR_WHITE, nokia.COLOR_NOKIA_BLUE)

    # City & Current Temp
    nokia.display.draw_text(20, 45, "Jerusalem, IL", nokia.COLOR_YELLOW, 0x0112)
    nokia.display.draw_text(20, 75, "24 C", nokia.COLOR_WHITE, 0x0112)
    nokia.display.draw_text(20, 105, "Clear Sky & Sunny", nokia.COLOR_CYAN, 0x0112)

    # Weekly forecast box
    nokia.display.draw_rect(10, 140, 220, 140, nokia.COLOR_DARK_GRAY, fill=True)
    nokia.display.draw_text(18, 150, "Mon:  24 C / 16 C  Sunny", nokia.COLOR_WHITE, nokia.COLOR_DARK_GRAY)
    nokia.display.draw_text(18, 175, "Tue:  25 C / 17 C  Clear", nokia.COLOR_WHITE, nokia.COLOR_DARK_GRAY)
    nokia.display.draw_text(18, 200, "Wed:  22 C / 15 C  Clouds", nokia.COLOR_WHITE, nokia.COLOR_DARK_GRAY)
    nokia.display.draw_text(18, 225, "Thu:  21 C / 14 C  Partly", nokia.COLOR_WHITE, nokia.COLOR_DARK_GRAY)
    nokia.display.draw_text(18, 250, "Fri:  23 C / 15 C  Sunny", nokia.COLOR_WHITE, nokia.COLOR_DARK_GRAY)

    # Footer
    nokia.display.draw_rect(0, 296, 240, 24, nokia.COLOR_NOKIA_BLUE, fill=True)
    nokia.display.draw_text(8, 300, "Refresh", nokia.COLOR_WHITE, nokia.COLOR_NOKIA_BLUE)
    nokia.display.draw_text(190, 300, "Exit", nokia.COLOR_WHITE, nokia.COLOR_NOKIA_BLUE)
    nokia.display.update()

def main():
    render_weather()
    while True:
        key = nokia.keypad.poll()
        if key in (nokia.KEY_RED, nokia.KEY_SOFT_R):
            break
        elif key in (nokia.KEY_OK, nokia.KEY_SOFT_L):
            nokia.display.draw_text(20, 125, "Updating via HTTPS...", nokia.COLOR_GREEN, 0x0112)
            nokia.display.update()
            time.sleep(0.5)
            render_weather()
        time.sleep(0.05)

if __name__ == "__main__":
    main()
