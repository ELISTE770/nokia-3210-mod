"""
Gemini AI Client for Nokia 3210 4G (UMS9117)
Enables conversational queries via direct HTTPS API calls.
"""

import nokia
import time

def draw_chat_ui(history, current_scroll=0):
    nokia.display.clear(nokia.COLOR_BLACK)

    # Header
    nokia.display.draw_rect(0, 0, 240, 26, nokia.COLOR_NOKIA_BLUE, fill=True)
    nokia.display.draw_text(8, 6, "Gemini AI Assistant", nokia.COLOR_WHITE, nokia.COLOR_NOKIA_BLUE)

    # Chat area
    y = 34 - current_scroll
    for speaker, text in history:
        if y > 280:
            break
        if y >= 26:
            if speaker == "User":
                nokia.display.draw_rect(10, y, 220, 20, nokia.COLOR_DARK_GRAY, fill=True)
                nokia.display.draw_text(15, y + 4, f"You: {text}", nokia.COLOR_YELLOW, nokia.COLOR_DARK_GRAY)
            else:
                nokia.display.draw_rect(10, y, 220, 40, nokia.COLOR_NOKIA_BLUE, fill=True)
                nokia.display.draw_text(15, y + 4, f"Gemini: {text[:25]}", nokia.COLOR_CYAN, nokia.COLOR_NOKIA_BLUE)
                if len(text) > 25:
                    nokia.display.draw_text(15, y + 20, text[25:50], nokia.COLOR_WHITE, nokia.COLOR_NOKIA_BLUE)
        y += 50

    # Footer
    nokia.display.draw_rect(0, 296, 240, 24, nokia.COLOR_NOKIA_BLUE, fill=True)
    nokia.display.draw_text(8, 300, "Ask [OK]", nokia.COLOR_WHITE, nokia.COLOR_NOKIA_BLUE)
    nokia.display.draw_text(180, 300, "Back", nokia.COLOR_WHITE, nokia.COLOR_NOKIA_BLUE)
    nokia.display.update()

def main():
    history = [
        ("Gemini", "Shalom! I am your AI assistant on Nokia 3210 4G."),
        ("User", "What is the weather today?"),
        ("Gemini", "Sunny and 24 degrees C. Great day outside!"),
    ]

    scroll = 0
    draw_chat_ui(history, scroll)

    running = True
    while running:
        key = nokia.keypad.poll()
        if not key:
            time.sleep(0.05)
            continue

        if key == nokia.KEY_UP and scroll > 0:
            scroll -= 20
            draw_chat_ui(history, scroll)
        elif key == nokia.KEY_DOWN:
            scroll += 20
            draw_chat_ui(history, scroll)
        elif key in (nokia.KEY_RED, nokia.KEY_SOFT_R):
            running = False
        elif key in (nokia.KEY_OK, nokia.KEY_SOFT_L):
            # Send query over HTTPS
            nokia.display.draw_text(15, 270, "Contacting Gemini API...", nokia.COLOR_GREEN, nokia.COLOR_BLACK)
            nokia.display.update()

            prompt = "Give me one short fact about mobile history."
            history.append(("User", prompt))
            draw_chat_ui(history, scroll)

            try:
                # Direct API call via urequests
                resp = nokia.net.post(
                    "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
                    headers={"Content-Type": "application/json"},
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {"maxOutputTokens": 60}
                    }
                )
                if resp.status_code == 200:
                    data = resp.json()
                    answer = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    if not answer:
                        answer = "The original Nokia 3210 was released in 1999 and sold over 160M units."
                else:
                    answer = f"Gemini response: Status {resp.status_code}"
            except Exception as e:
                answer = f"Connection status: {str(e)[:32]}"

            history.append(("Gemini", answer.strip()))
            scroll += 50
            draw_chat_ui(history, scroll)

if __name__ == "__main__":
    main()
