# src/core/screenshot.py
# 2025终极截图管理器（DXGI多线程 + DXGI单线程 + 句柄 + MSS，四种模式UI切换）

import numpy as np
import cv2
import mss
import threading
import time
import win32gui
import win32ui
import win32con
import win32api

class ScreenshotManager:
    """
    统一截图管理器
    mode: "dxgi_thread" (默认推荐) / "dxgi" / "handle" / "mss"
    """
    def __init__(self, mode="dxgi_thread", window_title=None):
        self.mode = mode.lower()
        self.window_title = window_title
        self.hwnd = self._find_window_hwnd()

        self.running = False
        self.latest_frame = None
        self.lock = threading.Lock()

        self.sct = mss.mss() if "mss" in self.mode else None
        self.monitor = None

        if "mss" in self.mode or self.mode == "handle":
            self._setup_fallback()

    def _find_window_hwnd(self):
        if not self.window_title:
            return None
        hwnds = []
        def enum_handler(hwnd, ctx):
            if win32gui.IsWindowVisible(hwnd) and self.window_title in win32gui.GetWindowText(hwnd):
                ctx.append(hwnd)
        win32gui.EnumWindows(enum_handler, hwnds)
        return hwnds[0] if hwnds else None

    def _setup_fallback(self):
        if self.hwnd:
            try:
                rect = win32gui.GetClientRect(self.hwnd)
                pos = win32gui.ClientToScreen(self.hwnd, (0, 0))
                self.monitor = {"top": pos[1], "left": pos[0], "width": rect[2], "height": rect[3]}
            except:
                self.monitor = self.sct.monitors[1]
        else:
            self.monitor = self.sct.monitors[1]

    def capture(self):
        """单次截图（用于单线程模式）"""
        if self.mode == "dxgi_thread":
            # 多线程模式下，用最新帧
            return self.get_latest_frame()
        elif self.mode == "dxgi":
            return self._capture_dxcam()
        elif self.mode == "handle":
            return self._capture_handle()
        elif self.mode == "mss":
            return self._capture_mss()
        return None

    def _capture_dxcam(self):
        """DXGI 单线程（用 dxcam，免费、高性能）"""
        try:
            import dxcam
            camera = dxcam.create(output_idx=0, max_buffer_len=1)
            frame = camera.grab()
            return frame
        except:
            print("[DXGI] dxcam失败，回退MSS")
            return self._capture_mss()

    def _capture_handle(self):
        if not self.hwnd or not win32gui.IsWindow(self.hwnd):
            return None
        try:
            left, top, right, bot = win32gui.GetClientRect(self.hwnd)
            w, h = right - left, bot - top
            hwndDC = win32gui.GetWindowDC(self.hwnd)
            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()
            bitmap = win32ui.CreateBitmap()
            bitmap.CreateCompatibleBitmap(mfcDC, w, h)
            saveDC.SelectObject(bitmap)
            win32gui.BitBlt(saveDC.GetSafeHandle(), 0, 0, w, h, mfcDC.GetSafeHandle(), 0, 0, win32con.SRCCOPY)
            bmpinfo = bitmap.GetInfo()
            bmpstr = bitmap.GetBitmapBits(True)
            img = np.frombuffer(bmpstr, dtype='uint8').reshape((h, w, 4))
            img = img[..., :3][..., ::-1]  # BGRA -> BGR
            # 清理
            win32gui.DeleteObject(bitmap.GetHandle())
            saveDC.DeleteDC()
            mfcDC.DeleteDC()
            win32gui.ReleaseDC(self.hwnd, hwndDC)
            return img
        except:
            return None

    def _capture_mss(self):
        try:
            sct_img = self.sct.grab(self.monitor or self.sct.monitors[1])
            img = np.array(sct_img)
            return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        except:
            return None

    def start_continuous(self, callback):
        """启动多线程持续截图（仅 dxgi_thread 模式）"""
        if self.mode != "dxgi_thread":
            return

        def loop():
            try:
                import dxcam
                camera = dxcam.create(output_idx=0, max_buffer_len=1)
                while self.running:
                    frame = camera.grab()
                    if frame is not None:
                        with self.lock:
                            self.latest_frame = frame
                        callback(frame)
                    time.sleep(0.008)  # ~125FPS
            except Exception as e:
                print(f"[DXGI Thread] 异常: {e}, 回退单次捕获")
                while self.running:
                    frame = self._capture_mss()
                    if frame is not None:
                        callback(frame)
                    time.sleep(0.016)

        self.running = True
        threading.Thread(target=loop, daemon=True).start()

    def get_latest_frame(self):
        with self.lock:
            return self.latest_frame.copy() if self.latest_frame is not None else None

    def stop(self):
        self.running = False

# ============ 全局实例（默认 DXGI 多线程） ============
game_capture = ScreenshotManager(mode="dxgi_thread")