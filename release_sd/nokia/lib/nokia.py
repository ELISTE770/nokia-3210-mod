"""
nokia.py - MicroPython Hardware Module for Nokia 3210 4G (UMS9117)
Provides Display, Keypad, Network (HTTPS), and System control.
"""

import sys
import time

# Display Dimensions
SCREEN_WIDTH = 240
SCREEN_HEIGHT = 320

# Colors (RGB565)
COLOR_BLACK = 0x0000
COLOR_WHITE = 0xFFFF
COLOR_NOKIA_BLUE = 0x1116
COLOR_CYAN = 0x07FF
COLOR_YELLOW = 0xFFE0
COLOR_GREEN = 0x07E0
COLOR_RED = 0xF800
COLOR_DARK_GRAY = 0x2104

# Keys
KEY_UP = 0x04
KEY_DOWN = 0x05
KEY_LEFT = 0x06
KEY_RIGHT = 0x07
KEY_OK = 0x0D
KEY_SOFT_L = 0x01
KEY_SOFT_R = 0x02
KEY_RED = 0x1B
KEY_0 = 0x30
KEY_1 = 0x31
KEY_2 = 0x32
KEY_3 = 0x33
KEY_4 = 0x34
KEY_5 = 0x35
KEY_6 = 0x36
KEY_7 = 0x37
KEY_8 = 0x38
KEY_9 = 0x39
KEY_STAR = 0x2A
KEY_HASH = 0x23

class Display:
    """Controls the 240x320 QVGA Portrait LCD"""
    def __init__(self):
        self.width = SCREEN_WIDTH
        self.height = SCREEN_HEIGHT

    def clear(self, color=COLOR_BLACK):
        """Clears the screen with given RGB565 color"""
        pass

    def draw_text(self, x, y, text, fg=COLOR_WHITE, bg=COLOR_BLACK):
        """Draws ASCII / Hebrew text at coordinate (x, y)"""
        print(f"[LCD] ({x},{y}): {text}")

    def draw_rect(self, x, y, w, h, color=COLOR_WHITE, fill=False):
        """Draws or fills a rectangle"""
        pass

    def update(self):
        """Refreshes the physical screen buffer"""
        pass

class Keypad:
    """Manages T9 numeric and D-Pad navigation keys"""
    def __init__(self):
        self._queue = []

    def queue_key(self, key_code):
        self._queue.append(key_code)

    def poll(self):
        """Returns the pressed key code or None if no key pressed"""
        if self._queue:
            return self._queue.pop(0)
        return None

    def wait_key(self, timeout_ms=0):
        """Blocks until a key is pressed"""
        start = time.time()
        while True:
            k = self.poll()
            if k is not None:
                return k
            if timeout_ms > 0 and (time.time() - start) * 1000 > timeout_ms:
                return None
            time.sleep(0.05)

class Network:
    """Handles direct HTTPS requests over MOCOR RTOS cellular/WiFi sockets"""
    def get(self, url, headers=None):
        import urequests
        return urequests.get(url, headers=headers)

    def post(self, url, json_data=None, headers=None):
        import urequests
        return urequests.post(url, json=json_data, headers=headers)

class System:
    """Phone system state and control"""
    def get_battery_percentage(self):
        return 85

    def get_time_string(self):
        return "12:35"

    def exit_to_phone(self):
        """Non-destructively exits the launcher back to Nokia MOCOR OS"""
        sys.exit(0)

display = Display()
keypad = Keypad()
net = Network()
system = System()
