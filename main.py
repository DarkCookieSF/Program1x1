import ctypes
import sys
import time
from PIL import Image
import cv2
import numpy as np
import win32gui
import win32ui

PW_RENDERFULLCONTENT = 2  # needed for GPU-accelerated windows (games, browsers, etc.)
user32 = ctypes.windll.user32

def find_window(title_substring: str):
    matches = []

    def enum_handler(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        title = win32gui.GetWindowText(hwnd)
        if title and title_substring.lower() in title.lower():
            matches.append(hwnd)

    win32gui.EnumWindows(enum_handler, None)
    return matches[0] if matches else None

def capture_window(hwnd):
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    width, height = right - left, bottom - top
    if width <= 0 or height <= 0:
        return None

    hwnd_dc = win32gui.GetWindowDC(hwnd)
    mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
    save_dc = mfc_dc.CreateCompatibleDC()

    bitmap = win32ui.CreateBitmap()
    bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
    save_dc.SelectObject(bitmap)

    result = user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), PW_RENDERFULLCONTENT)

    frame = None
    if result == 1:
        bmp_info = bitmap.GetInfo()
        bmp_bits = bitmap.GetBitmapBits(True)
        frame = np.frombuffer(bmp_bits, dtype=np.uint8)
        frame.shape = (bmp_info["bmHeight"], bmp_info["bmWidth"], 4)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

    win32gui.DeleteObject(bitmap.GetHandle())
    save_dc.DeleteDC()
    mfc_dc.DeleteDC()
    win32gui.ReleaseDC(hwnd, hwnd_dc)

    return frame

def main():
    if len(sys.argv) < 2:
        print('Usage: python mirror_window.py "Window Title Substring"')
        sys.exit(1)

    title_substring = sys.argv[1]

    hwnd = find_window(title_substring)
    if hwnd is None:
        print(f"No visible window found matching: {title_substring!r}")
        sys.exit(1)

    print(f"Mirroring hwnd={hwnd} ({win32gui.GetWindowText(hwnd)!r})")

    while True:
        if not win32gui.IsWindow(hwnd):
            print("Target window closed. Exiting.")
            break

        frame = capture_window(hwnd)

        resize_frame = cv2.resize(frame, dsize=(1, 1))

        if frame is not None:
            cv2.imshow("Mirror", cv2.resize(resize_frame, dsize=(720, 720)))
            cv2.setWindowProperty("Mirror", cv2.WND_PROP_TOPMOST, 1)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

        time.sleep(1 / 144)

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()