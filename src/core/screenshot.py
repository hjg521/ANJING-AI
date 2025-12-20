# src/core/screenshot.py
import mss
import numpy as np
import cv2
import win32gui
import win32con
import time

class GameCapture:
    """
    Windows专用高速截图
    优先mss全屏截图，支持指定窗口区域
    """
    def __init__(self, window_title_contains=None):
        self.sct = mss.mss()
        self.window_title = window_title_contains
        self.monitor = None
        self.find_game_window()

    def find_game_window(self):
        """
        自动查找游戏窗口（标题包含关键字）
        """
        if not self.window_title:
            # 默认全屏
            self.monitor = self.sct.monitors[1]  # 主显示器
            return

        def enum_handler(hwnd, ctx):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if self.window_title in title:
                    ctx.append(hwnd)

        hwnds = []
        win32gui.EnumWindows(enum_handler, hwnds)
        if hwnds:
            hwnd = hwnds[0]
            rect = win32gui.GetWindowRect(hwnd)
            # 去掉标题栏和边框，只截客户区（近似）
            client_rect = win32gui.GetClientRect(hwnd)
            client_pos = win32gui.ClientToScreen(hwnd, (0, 0))
            x = client_pos[0]
            y = client_pos[1]
            w = client_rect[2]
            h = client_rect[3]
            self.monitor = {"top": y, "left": x, "width": w, "height": h}
            print(f"[Capture] 找到游戏窗口: {win32gui.GetWindowText(hwnd)}")
        else:
            self.monitor = self.sct.monitors[1]
            print("[Capture] 未找到指定窗口，使用全屏")

    def capture(self):
        """
        返回 OpenCV 格式 BGR numpy array
        """
        sct_img = self.sct.grab(self.monitor)
        img = np.array(sct_img)
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        return img

    def capture_continuous(self, callback, interval=0.016):  # ~60FPS
        """
        持续截图并回调（在新线程中）
        """
        import threading
        def loop():
            while True:
                frame = self.capture()
                callback(frame)
                time.sleep(interval)
        t = threading.Thread(target=loop, daemon=True)
        t.start()

# 全局实例（可根据游戏不同标题初始化）
game_capture = GameCapture(window_title_contains="穿越火线")  # 可在UI中动态设置