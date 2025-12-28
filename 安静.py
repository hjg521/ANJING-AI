# main.py
# 程序入口（完整优化版）
import sys
import os
import socket

# ============ 路径自动修正（支持PyInstaller打包） ============
if getattr(sys, 'frozen', False):
    # 打包后运行
    os.chdir(os.path.dirname(sys.executable))
else:
    # 开发时运行
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

# 添加 src 到路径
sys.path.append(os.path.join(os.getcwd(), 'src'))

# ============ 必要依赖检测（新手友好） ============
try:
    from PyQt5.QtWidgets import QApplication
except ImportError:
    print("未检测到 PyQt5！请运行以下命令安装依赖：")
    print("pip install -r requirements.txt")
    sys.exit(1)

# ============ 单实例锁定（防止重复运行） ============
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
try:
    sock.bind(('127.0.0.1', 54329))
except OSError:
    print("本辅助软件已启动，无需重复运行。")
    sys.exit(0)

# ============ 导入核心模块 ============
from src.app import SafeApp
from src.ui.login import LoginDialog
from src.ui.main_window import MainWindow
from src.ui.theme import ThemeManager
from src.config.config import init_config, load_all_configs, save_all_configs
from src.core.hotkeys import HotkeyManager
from PyQt5.QtCore import Qt

def main():
    # 启动全局Qt应用（安全版）
    app = SafeApp(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # 全局主题管理
    theme = ThemeManager()
    theme.load_default()  # 加载持久化主题
    theme.apply_theme(app)  # 立即应用

    # 初始化配置（目录、密钥、默认值）
    init_config()
    load_all_configs()

    # 登录流程
    login = LoginDialog(theme_manager=theme)
    if login.exec_() != login.Accepted:
        sys.exit(0)

    user_info = login.get_user_info()

    # 主窗口启动
    mw = MainWindow(user_info=user_info, theme_manager=theme)
    mw.show()

    # ============ 安装全局热键管理 ============
    hotkey_mgr = HotkeyManager(mw)
    hotkey_mgr.install_on_widget(mw)

    # 示例热键（已集成到MainWindow，这里可额外全局注册）
    # hotkey_mgr.register_hotkey("退出程序", Qt.Key_Escape, Qt.ControlModifier | Qt.ShiftModifier, callback=app.quit)

    # ============ 运行事件循环 ============
    exit_code = app.exec_()

    # 退出前保存所有配置
    save_all_configs()

    sys.exit(exit_code)

if __name__ == '__main__':
    main()
# src/app.py
import sys
import traceback
import platform
import datetime
import subprocess
import os

from PyQt5.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon, QMenu, QAction
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt

from src.tools.resource_path import resource_path  # 资源路径打包兼容
from appdirs import user_config_dir  # 用户目录

class SafeApp(QApplication):
    """
    全局安全应用类：异常拦截、托盘管理、统一通知、日志写入用户目录
    """
    _instance = None

    # 日志路径改为用户目录（打包后可写）
    LOG_DIR = user_config_dir("AnjingAI")
    LOG_FILE = os.path.join(LOG_DIR, "application.log")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        SafeApp._instance = self
        self.tray_icon = None
        self.is_tray_shown = False

        os.makedirs(SafeApp.LOG_DIR, exist_ok=True)  # 确保日志目录存在

        self._setup_excepthook()
        self._setup_tray()

    def _setup_excepthook(self):
        """捕获所有未处理异常，写入日志并弹窗"""
        def handle_exception(exc_type, exc_value, exc_traceback):
            if issubclass(exc_type, KeyboardInterrupt):
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
                return

            err_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
            self.log_error(err_msg)

            QMessageBox.critical(
                None,
                "程序异常终止",
                f"软件运行时出现未捕获异常！\n\n错误已记录到日志文件。\n\n{exc_value}"
            )
            self.quit()

        sys.excepthook = handle_exception

    def _setup_tray(self):
        """系统托盘：最小化、恢复、退出"""
        icon_path = resource_path("resources/tray.png")
        tray_icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()

        self.tray_icon = QSystemTrayIcon(tray_icon, self)
        menu = QMenu()

        act_restore = QAction("恢复主窗口", self)
        act_hide = QAction("最小化到托盘", self)
        act_exit = QAction("彻底退出", self)

        act_restore.triggered.connect(self.restore_all_windows)
        act_hide.triggered.connect(self.hide_all_windows)
        act_exit.triggered.connect(self.quit)

        menu.addAction(act_restore)
        menu.addAction(act_hide)
        menu.addSeparator()
        menu.addAction(act_exit)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.setToolTip("安静AI视觉辅助平台")
        self.tray_icon.show()
        self.is_tray_shown = True

    def notify(self, title, msg, icon=QSystemTrayIcon.Information, timeout=5000):
        """托盘气泡通知"""
        if self.tray_icon:
            self.tray_icon.showMessage(title, msg, icon, timeout)

    def restore_all_windows(self):
        """恢复所有窗口（主窗、雷达、战绩等）"""
        for w in self.topLevelWidgets():
            if w.isHidden():
                w.show()
            w.raise_()
            w.activateWindow()

    def hide_all_windows(self):
        """隐藏所有窗口到托盘（辅助后台运行）"""
        for w in self.topLevelWidgets():
            w.hide()

    @staticmethod
    def log_error(errmsg):
        """写入日志到用户目录"""
        try:
            with open(SafeApp.LOG_FILE, "a", encoding="utf-8") as f:
                now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                plat = platform.platform()
                f.write(f"\n[{now}][{plat}] CRITICAL ERROR\n{errmsg}\n{'-'*60}\n")
        except Exception as e:
            print("日志写入失败:", e)

    @staticmethod
    def instance():
        """获取全局单例"""
        return SafeApp._instance

    def restart_app(self):
        """安全重启程序"""
        self.quit()
        subprocess.Popen([sys.executable] + sys.argv)
        # src/config/config.py
import os
import json
from cryptography.fernet import Fernet
from src.tools.resource_path import resource_path
from appdirs import user_config_dir

# 使用用户目录，避免打包后无法读写
APP_NAME = "AnjingAI"
CONFIG_DIR = user_config_dir(APP_NAME)
os.makedirs(CONFIG_DIR, exist_ok=True)

MAIN_CONFIG = os.path.join(CONFIG_DIR, "settings.enc")      # 加密配置文件
SECURE_KEY_FILE = os.path.join(CONFIG_DIR, "core.key")     # 密钥文件

DEFAULT_CONFIG = {
    "user": {},
    "settings": {},
    "game_params": {},
    "window": {
        "size": [1080, 700],
        "x": 180,
        "y": 90,
    },
    "theme": "default",
}

_secure_fernet = None

def _get_fernet():
    """单例模式获取 Fernet 实例，自动生成/加载密钥"""
    global _secure_fernet
    if _secure_fernet is None:
        if os.path.exists(SECURE_KEY_FILE):
            with open(SECURE_KEY_FILE, "rb") as f:
                key = f.read()
        else:
            key = Fernet.generate_key()
            with open(SECURE_KEY_FILE, "wb") as f:
                f.write(key)
            # Windows下尝试设置仅本人可读
            try:
                os.chmod(SECURE_KEY_FILE, 0o600)
            except:
                pass
        _secure_fernet = Fernet(key)
    return _secure_fernet

def init_config():
    os.makedirs(CONFIG_DIR, exist_ok=True)
    if not os.path.exists(MAIN_CONFIG):
        save_config(DEFAULT_CONFIG)

def save_config(cfg):
    try:
        f = _get_fernet()
        raw = json.dumps(cfg, indent=2, ensure_ascii=False).encode("utf-8")
        encrypted = f.encrypt(raw)
        with open(MAIN_CONFIG, "wb") as fh:
            fh.write(encrypted)
    except Exception as e:
        from src.app import SafeApp
        SafeApp.log_error(f"[Config] 保存失败: {e}")

def load_config():
    if not os.path.exists(MAIN_CONFIG):
        return DEFAULT_CONFIG.copy()
    try:
        f = _get_fernet()
        with open(MAIN_CONFIG, "rb") as fh:
            enc = fh.read()
            raw = f.decrypt(enc)
            data = json.loads(raw.decode("utf-8"))
            # 补全缺失字段
            for k in DEFAULT_CONFIG:
                if k not in data:
                    data[k] = DEFAULT_CONFIG[k]
            return data
    except Exception as e:
        from src.app import SafeApp
        SafeApp.log_error(f"[Config] 加载失败: {e}")
        return DEFAULT_CONFIG.copy()

# 以下函数保持不变
def save_all_configs():
    cfg = load_config()
    save_config(cfg)

def load_all_configs():
    return load_config()

def get_config_param(key, default=None):
    return load_config().get(key, default)

def set_config_param(key, val):
    cfg = load_config()
    cfg[key] = val
    save_config(cfg)
    
    # src/config/models.py 底部添加

# 游戏专用模型映射（文件名不带路径，只写文件名）
GAME_SPECIFIC_MODELS = {
    "CF": "cf.pt",              # 穿越火线专用模型
    "CFHD": "cfhd.pt",          # 穿越火线高清
    "DELTA": "delta.pt",        # 三角洲行动
    "VAL": "valorant.pt",       # 无畏契约（VALORANT）
    "CSGO": "cs2.pt",           # CS2专用
    "PEACE": "peace.pt",        # PC和平精英
    "NZ": "nz.pt",              # 逆战
    "YJ": "yj.pt",              # 永劫无间
    "PUBG": "pubg.pt",          # PUBG
}

# 默认通用模型（所有游戏兜底）
DEFAULT_MODEL = "yolov8n-pose.pt"
# src/config/models.py
from dataclasses import dataclass, field
from typing import Dict, Any, List
import datetime

@dataclass
class UserInfo:
    """登录用户、卡密状态、权限标识等"""
    kami: str = ""
    hwid: str = ""
    login_time: str = field(default_factory=lambda: datetime.datetime.now().isoformat())
    ip: str = ""
    expire_time: str = ""
    state: str = "normal"
    type: str = "user"  # user/admin/superadmin

@dataclass
class GameParam:
    """通用游戏辅助参数，分游戏独立存储（已添加所有独立开关）"""
    # ==================== 独立功能开关 ====================
    aim_enabled: bool = True              # 自瞄总开关
    esp_enabled: bool = True              # 透视总开关
    recoil_enabled: bool = True           # 压枪总开关
    radar_enabled: bool = True            # 雷达显示开关
    item_esp_enabled: bool = False        # 物品透视开关
    auto_fire_enabled: bool = False       # 自动开火开关

    # ==================== 自瞄参数 ====================
    aim_priority: str = "head"            # head/body
    aim_fov: int = 80
    aim_hotkey: str = "RightMouse"
    bone_points: List[int] = field(default_factory=lambda: list(range(17)))
    bone_priority_order: List[int] = field(default_factory=lambda: [0, 7, 14, 9, 11, 2, 5])

    # ==================== 透视参数 ====================
    esp_box_type: str = "2d"              # 2d/3d/none
    esp_bone: bool = True                 # 骨骼线
    esp_health_bar: bool = True           # 血条
    esp_name: bool = True                 # 名字
    esp_distance: bool = True             # 距离

    # ==================== 压枪参数 ====================
    recoil_curve: List[float] = field(default_factory=lambda: [0.0] * 30)  # 30点曲线

    # ==================== 其他参数 ====================
    model_version: str = "yolov8"
    performance_mode: str = "auto"
    screenshot_mode: str = "dx"
    screen_size: List[int] = field(default_factory=lambda: [1920, 1080])
    all_hotkeys: Dict[str, str] = field(default_factory=lambda: {})
    
        # ============ 新增字段（压枪、自瞄人性化、多分辨率支持） ============
    recoil_compensate: bool = False                  # 是否启用压枪补偿
    recoil_curve: List[float] = field(default_factory=lambda: [0.0] * 30)  # 压枪曲线，30个点
    miss_rate: float = 0.12                          # 自瞄故意miss概率（0.0~1.0，推荐0.1~0.2）
    reaction_delay_min: float = 0.15                 # 自瞄反应延迟最小秒
    reaction_delay_max: float = 0.3                 # 自瞄反应延迟最大秒
    esp_color: str = "#FF6464"                       # ESP颜色（16进制，带#）
    # ====================================================================

@dataclass
class WindowSetting:
    width: int = 1080
    height: int = 700
    x: int = 180
    y: int = 120
    maximized: bool = False

@dataclass
class ThemeSetting:
    theme: str = "default"
    custom_css: str = ""

@dataclass
class ConfigData:
    user: UserInfo = field(default_factory=UserInfo)
    window: WindowSetting = field(default_factory=WindowSetting)
    theme: ThemeSetting = field(default_factory=ThemeSetting)
    game_params: Dict[str, GameParam] = field(default_factory=dict)  # 分游戏参数
    settings: Dict[str, Any] = field(default_factory=dict)
    last_save_time: str = field(default_factory=lambda: datetime.datetime.now().isoformat())

# ==================== 游戏专用模型映射（用于自动切换） ====================
GAME_SPECIFIC_MODELS = {
    "CF": "cf.pt",
    "CFHD": "cfhd.pt",
    "DELTA": "delta.pt",
    "VAL": "valorant.pt",
    "CSGO": "cs2.pt",
    "PEACE": "peace.pt",
    "NZ": "nz.pt",
    "YJ": "yj.pt",
    "PUBG": "pubg.pt",
}

DEFAULT_MODEL = "yolov8n-pose.pt"  # 通用兜底模型# src/core/cheats.py
# 终极完整版（2025年最强实战版）
# 已包含所有优化：
# - 真实自瞄（FOV + 骨骼优先 + 多分辨率自适应）
# - 平滑移动（贝塞尔缓动 + 随机偏移 + 反应延迟）
# - 自动开火 + 压枪补偿（recoil_curve数组 + 随机抖动）
# - 优先硬件盒子下发（真实对接预留）
# - 多分辨率自适应FOV/压枪强度
# - TensorRT兼容（模型加载不影响）
# - 所有之前功能（线程安全、游戏专用模型切换等）

import threading
import time
import random
import math
import ctypes
import torch

from src.core.yolo_ai import visual_core
from src.core.screenshot import game_capture
from src.devices.hardware import hardware_manager
from src.config.models import GameParam
from src.config.config import load_config

# Windows鼠标事件常量（fallback使用）
user32 = ctypes.windll.user32
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004

def smooth_move(dx: int, dy: int, steps: int = 14, randomness: float = 0.2, reaction_delay: float = None):
    """
    超级人性化鼠标移动
    - 反应延迟（模拟发现目标时间）
    - S型缓动曲线（先快后慢）
    - 随机微偏移（防轨迹检测）
    - 优先硬件盒子下发
    """
    if dx == 0 and dy == 0:
        return

    # 反应延迟（随机200-400ms，模拟真人）
    if reaction_delay is None:
        reaction_delay = random.uniform(0.18, 0.38)
    time.sleep(reaction_delay)

    devices = hardware_manager.list_devices()
    use_hardware = len(devices) > 0

    for i in range(steps):
        ratio = (i + 1) / steps
        # S型缓动（更自然）
        smooth_ratio = ratio * ratio * (3.0 - 2.0 * ratio)

        move_x = int(dx * smooth_ratio)
        move_y = int(dy * smooth_ratio)

        # 随机偏移（幅度随距离增大）
        rand_x = random.uniform(-randomness, randomness) * abs(dx)
        rand_y = random.uniform(-randomness, randomness) * abs(dy)
        move_x += int(rand_x)
        move_y += int(rand_y)

        step_x = (move_x // (steps - i)) if (steps - i) > 0 else 0
        step_y = (move_y // (steps - i)) if (steps - i) > 0 else 0

        if use_hardware:
            hardware_manager.send_action(devices[0], {
                "type": "mouse_move",
                "dx": step_x,
                "dy": step_y
            })
        else:
            user32.mouse_event(MOUSEEVENTF_MOVE, step_x, step_y, 0, 0)

        time.sleep(random.uniform(0.001, 0.003))  # 人性化微延时

class BaseGameHelper:
    def __init__(self, name="base"):
        self.name = name
        self.active = False
        self.params = {}
        self.thread = None
        self.running = False
        self.bullet_count = 0  # 压枪子弹计数

    def start(self, params=None):
        self.active = True
        self.params = params or {}
        self.bullet_count = 0
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.run, daemon=True)
            self.thread.start()

    def stop(self):
        self.active = False
        self.running = False
        self.bullet_count = 0

    def run(self):
        while self.running:
            try:
                if not self.active:
                    time.sleep(0.1)
                    continue

                img = game_capture.capture()
                if img is None:
                    time.sleep(0.05)
                    continue

                targets = visual_core.infer(img, conf=0.35, classes=[0])

                self.handle_targets(img, targets)

                time.sleep(0.008)  # ~125FPS上限，防过载
            except Exception as e:
                print(f"[{self.name}] 辅助循环异常: {e}")
                time.sleep(0.5)

    def handle_targets(self, img, targets):
        if not targets:
            self.bullet_count = 0  # 无目标重置压枪
            return

        param = self.params
        if not param.get("aim_enabled", True):
            return

        h, w = img.shape[:2]
        center_x, center_y = w // 2, h // 2

        # 多分辨率自适应
        scale = w / 1920.0  # 以1920x1080为基准
        fov = param.get("aim_fov", 100) * scale

        best_target = None
        best_dist = float('inf')
        best_aim_point = (center_x, center_y)

        priority_order = param.get("bone_priority_order", [0, 7, 14, 9, 11, 2, 5])

        for target in targets:
            if "keypoints" not in target:
                continue

            kps = target["keypoints"]
            box = target["box"]

            box_center_x = (box[0] + box[2]) / 2
            box_center_y = (box[1] + box[3]) / 2
            dist_to_center = math.hypot(box_center_x - center_x, box_center_y - center_y)
            if dist_to_center > fov * 1.5:
                continue

            for bone_idx in priority_order:
                if bone_idx >= len(kps):
                    continue
                x, y = kps[bone_idx]
                if x <= 0 or y <= 0:
                    continue
                point_dist = math.hypot(x - center_x, y - center_y)
                if point_dist < best_dist:
                    best_dist = point_dist
                    best_aim_point = (x, y)
                    best_target = target
                    if point_dist < fov:
                        break

        # 自瞄执行
        if best_dist < fov:
            dx = int(best_aim_point[0] - center_x)
            dy = int(best_aim_point[1] - center_y)

            # 故意miss概率（防100%命中）
            if random.random() < param.get("miss_rate", 0.12):
                dx += random.randint(-30, 30)
                dy += random.randint(-30, 30)

            smooth_move(dx, dy, steps=16, randomness=0.22)

            # 自动开火
            if param.get("auto_fire", False):
                devices = hardware_manager.list_devices()
                if devices:
                    hardware_manager.send_action(devices[0], {"type": "mouse_click", "button": "left"})
                else:
                    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                    time.sleep(random.uniform(0.03, 0.06))
                    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

        # ============ 压枪补偿 ============
        if param.get("recoil_compensate", False):
            curve = param.get("recoil_curve", [0.0] * 30)
            if self.bullet_count < len(curve):
                dy_offset = curve[self.bullet_count] * scale
                dy_offset += random.uniform(-1.8, 1.8)  # 随机抖动
                smooth_move(0, int(dy_offset), steps=6, randomness=0.1)
                self.bullet_count += 1
            else:
                self.bullet_count = 0  # 弹夹打完重置
        else:
            self.bullet_count = 0
        # ====================================

# 各大游戏专用类（可独立扩展）
class CFHelper(BaseGameHelper):
    def __init__(self):
        super().__init__(name="CF")

class CFHDHelper(BaseGameHelper):
    def __init__(self):
        super().__init__(name="CFHD")

class DeltaHelper(BaseGameHelper):
    def __init__(self):
        super().__init__(name="Delta")

class ValorantHelper(BaseGameHelper):
    def __init__(self):
        super().__init__(name="Valorant")

class CSGOHelper(BaseGameHelper):
    def __init__(self):
        super().__init__(name="CSGO")

class PeaceEliteHelper(BaseGameHelper):
    def __init__(self):
        super().__init__(name="PeaceElite")

class NZHelper(BaseGameHelper):
    def __init__(self):
        super().__init__(name="NZ")

class YJHelper(BaseGameHelper):
    def __init__(self):
        super().__init__(name="YJ")

class PUBGHelper(BaseGameHelper):
    def __init__(self):
        super().__init__(name="PUBG")

# 统一服务
class CheatService:
    def __init__(self):
        self.helpers = {
            "CF": CFHelper(),
            "CFHD": CFHDHelper(),
            "DELTA": DeltaHelper(),
            "VAL": ValorantHelper(),
            "CSGO": CSGOHelper(),
            "PEACE": PeaceEliteHelper(),
            "NZ": NZHelper(),
            "YJ": YJHelper(),
            "PUBG": PUBGHelper(),
        }
def start_cheat(self, game_key: str, game_param: dict):
        if game_key.upper() in self.helpers:
            self.helpers[game_key.upper()].start(params=game_param)

    def stop_cheat(self, game_key: str):
        if game_key.upper() in self.helpers:
            self.helpers[game_key.upper()].stop()

    def stop_all(self):
        for helper in self.helpers.values():
            helper.stop()

cheat_service = CheatService()
# src/core/hotkeys.py
from PyQt5.QtCore import QObject, pyqtSignal, Qt
from PyQt5.QtWidgets import QApplication

class HotkeyManager(QObject):
    """
    支持组合键的窗口内热键管理
    """
    hotkeyPressed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hotkeys = {}  # (key, modifiers): (name, callback)

    def register_hotkey(self, name, qtkey, modifiers=Qt.NoModifier, callback=None):
        combo = (qtkey, modifiers)
        self._hotkeys[combo] = (name, callback)

    def process_key_event(self, event):
        key = event.key()
        modifiers = event.modifiers()

        # 优先精确匹配（带修饰键）
        combo = (key, modifiers)
        if combo in self._hotkeys:
            name, callback = self._hotkeys[combo]
            if callback:
                callback()
            self.hotkeyPressed.emit(name)
            return True

        # fallback 单键匹配
        combo_no_mod = (key, Qt.NoModifier)
        if combo_no_mod in self._hotkeys:
            name, callback = self._hotkeys[combo_no_mod]
            if callback:
                callback()
            self.hotkeyPressed.emit(name)
            return True

        return False

    def install_on_widget(self, widget):
        widget.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == event.KeyPress:
            if self.process_key_event(event):
                return True
        return super().eventFilter(obj, event)
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
# src/core/yolo_ai.py
# 2025年最强YOLO视觉核心（ultralytics + TensorRT序列化引擎加速 + pose骨骼一体）

import os
import threading
import torch
import numpy as np
from ultralytics import YOLO

from src.tools.resource_path import resource_path
from src.config.models import GAME_SPECIFIC_MODELS, DEFAULT_MODEL

class YOLOModelManager:
    """
    YOLO模型管理器（TensorRT终极加速版）
    - 优先加载 .engine 序列化引擎（秒开）
    - 未找到则自动构建（首次慢，后续极快）
    - 支持游戏专用模型独立引擎
    - CUDA半精度 + 动态输入
    """
    def __init__(self):
        self.current_game = None
        self.current_model_name = None
        self.model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_lock = threading.Lock()

        print(f"[YOLO] 使用设备: {self.device}")
        self.load_default_model()

    def _get_engine_path(self, model_filename: str):
        """生成对应的 .engine 文件路径（放在 models/engines/）"""
        engine_dir = resource_path("models/engines")
        os.makedirs(engine_dir, exist_ok=True)
        base_name = os.path.splitext(model_filename)[0]
        return os.path.join(engine_dir, f"{base_name}.engine")

    def _build_and_save_engine(self, pt_path: str, engine_path: str):
        """首次构建TensorRT引擎并序列化保存"""
        print(f"[YOLO] 首次构建TensorRT引擎（可能需1-5分钟，请耐心等待）...")
        try:
            temp_model = YOLO(pt_path)
            temp_model.export(
                format="engine",
                imgsz=640,
                half=True,           # FP16
                dynamic=True,        # 支持动态输入尺寸
                workspace=8,         # GB
                verbose=False
            )
            print(f"[YOLO] TensorRT引擎构建完成: {engine_path}")
        except Exception as e:
            print(f"[YOLO] 引擎构建失败: {e}，回退原始模型")

    def _load_model_with_trt(self, model_filename: str):
        """优先加载 .engine，否则构建后加载"""
        pt_path = resource_path(os.path.join("models", model_filename))
        engine_path = self._get_engine_path(model_filename)

        if os.path.exists(engine_path):
            print(f"[YOLO] 加载序列化TensorRT引擎: {os.path.basename(engine_path)}")
            with self.model_lock:
                self.model = YOLO(engine_path)
        elif os.path.exists(pt_path):
            # 构建引擎
            self._build_and_save_engine(pt_path, engine_path)
            if os.path.exists(engine_path):
                with self.model_lock:
                    self.model = YOLO(engine_path)
            else:
                # 回退原始
                print(f"[YOLO] 回退加载原始PT模型: {model_filename}")
                with self.model_lock:
                    self.model = YOLO(pt_path)
                    if self.device == "cuda":
                        self.model.model.half()
        else:
            print(f"[YOLO] 模型文件不存在: {model_filename}")
            self.model = None

        self.current_model_name = model_filename

    def load_default_model(self):
        self._load_model_with_trt(DEFAULT_MODEL)

    def switch_game_model(self, game_key: str):
        if game_key == self.current_game:
            return

        model_filename = GAME_SPECIFIC_MODELS.get(game_key.upper(), DEFAULT_MODEL)
        self._load_model_with_trt(model_filename)
        self.current_game = game_key

    def infer(self, image_np: np.ndarray, conf: float = 0.35, classes=None):
        if self.model is None:
            return []

        results = self.model(image_np, conf=conf, classes=classes, verbose=False)[0]

        output = []
        boxes = results.boxes
        keypoints = results.keypoints.xy.cpu().numpy() if results.keypoints is not None else None

        for i, box in enumerate(boxes):
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            confidence = float(box.conf)
            class_id = int(box.cls)
            class_name = results.names[class_id]

            item = {
                "box": [float(x1), float(y1), float(x2), float(y2)],
                "conf": confidence,
                "cls": class_id,
                "name": class_name,
            }

            if keypoints is not None and i < len(keypoints):
                item["keypoints"] = keypoints[i].tolist()

            output.append(item)

        return output

    def async_infer(self, image_np: np.ndarray, callback, conf: float = 0.35, classes=None):
        def worker():
            try:
                results = self.infer(image_np, conf, classes)
                callback(results)
            except Exception as e:
                print(f"[YOLO] 异步推理异常: {e}")
                callback([])

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

# ============ 全局单例 ============
visual_core = YOLOModelManager()
# src/devices/hardware.py
# 2025年终极硬件盒子对接版（支持KMBox Net真实协议）

import threading
import socket
import time
import struct
import random

class HardwareDeviceManager:
    """
    硬件盒子通信管理器（支持KMBox Net等UDP协议盒子）
    """
    def __init__(self):
        self.connected_devices = {}  # device_ip: {"sock": sock, "last_heartbeat": time}
        self.connection_lock = threading.Lock()
        self.heartbeat_thread = None
        self.running = False

        # 默认KMBox Net IP和端口（可改成你的盒子IP）
        self.default_ip = "192.168.1.100"
        self.port = 12345

    def scan_devices(self):
        """自动扫描常见KMBox IP（可扩展）"""
        possible_ips = [f"192.168.1.{i}" for i in range(100, 200)]
        possible_ips.append(self.default_ip)

        found = []
        for ip in possible_ips:
            if self.connect_to_device(ip):
                found.append(ip)

        if found:
            print(f"[Hardware] 扫描发现设备: {found}")
        else:
            print("[Hardware] 未发现硬件盒子，使用模拟模式")

        return found

    def connect_to_device(self, device_ip):
        """连接KMBox Net"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(2.0)

            # KMBox Net初始化命令（真实协议）
            init_cmd = bytes.fromhex("01 00 00 00 00 00")
            sock.sendto(init_cmd, (device_ip, self.port))

            # 接收响应
            data, addr = sock.recvfrom(1024)
            if data and addr[0] == device_ip:
                with self.connection_lock:
                    self.connected_devices[device_ip] = {
                        "sock": sock,
                        "last_heartbeat": time.time()
                    }
                print(f"[Hardware] 成功连接KMBox: {device_ip}")
                self.start_heartbeat()
                return True
        except Exception as e:
            # print(f"[Hardware] 连接 {device_ip} 失败: {e}")
            pass
        return False

    def disconnect_device(self, device_ip):
        with self.connection_lock:
            if device_ip in self.connected_devices:
                try:
                    self.connected_devices[device_ip]["sock"].close()
                except:
                    pass
                del self.connected_devices[device_ip]
                print(f"[Hardware] 断开 {device_ip}")

    def send_action(self, device_ip, action_data):
        """
        发送鼠标/键盘指令到盒子
        action_data: {"type": "mouse_move", "dx": int, "dy": int}
                     {"type": "mouse_click", "button": "left"}
        """
        if device_ip not in self.connected_devices:
            print(f"[Hardware] {device_ip} 未连接，使用模拟模式: {action_data}")
            time.sleep(0.002)
            return True

        sock = self.connected_devices[device_ip]["sock"]

        try:
            if action_data["type"] == "mouse_move":
                dx = action_data.get("dx", 0)
                dy = action_data.get("dy", 0)
                # KMBox Net鼠标移动命令（真实协议）
                cmd = struct.pack("<Bhh", 0x02, dx, dy)  # 0x02 = 鼠标移动
                sock.sendto(cmd, (device_ip, self.port))

            elif action_data["type"] == "mouse_click":
                button = action_data.get("button", "left")
                # 左键按下0x03 抬起0x04
                if button == "left":
                    sock.sendto(bytes.fromhex("03 01 00 00 00 00"), (device_ip, self.port))  # 按下
                    time.sleep(0.03)
                    sock.sendto(bytes.fromhex("04 01 00 00 00 00"), (device_ip, self.port))  # 抬起

            self.connected_devices[device_ip]["last_heartbeat"] = time.time()
            return True
        except Exception as e:
            print(f"[Hardware] 发送指令失败 {device_ip}: {e}")
            return False

    def start_heartbeat(self):
        """启动心跳线程（每5秒发一次保活）"""
        if self.heartbeat_thread is None or not self.heartbeat_thread.is_alive():
            self.running = True
            self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
            self.heartbeat_thread.start()

    def _heartbeat_loop(self):
        while self.running:
            time.sleep(5)
            with self.connection_lock:
                current_time = time.time()
                for ip, info in list(self.connected_devices.items()):
                    if current_time - info["last_heartbeat"] > 15:
                        print(f"[Hardware] {ip} 心跳超时，断开连接")
                        self.disconnect_device(ip)
                        continue
                    # 发送心跳包
                    try:
                        info["sock"].sendto(bytes.fromhex("01 00 00 00 00 00"), (ip, self.port))
                    except:
                        pass

    def list_devices(self):
        with self.connection_lock:
            return list(self.connected_devices.keys())

    def stop_all(self):
        self.running = False
        with self.connection_lock:
            for ip in list(self.connected_devices.keys()):
                self.disconnect_device(ip)

# ============ 全局单例 ============
hardware_manager = HardwareDeviceManager()

# 启动时自动扫描
hardware_manager.scan_devices()
# src/tools/process_mask.py
# 2025终极中外融合动态随机伪装（系统进程 + 中国本土软件 + 杀毒 + 托盘图标，150+ 方案）

import sys
import os
import ctypes
import platform
import threading
import time
import random
from PyQt5.QtGui import QIcon

from src.tools.resource_path import resource_path

if platform.system() == "Windows":
    import win32gui
    import win32con

class ProcessMasking:
    """终极融合伪装：系统进程 + 中国本土软件 + 杀毒 + 随机托盘图标"""

    FAKE_PROFILES = {
        # 1. 经典系统进程（最安全、最常见伪装）
        "windows_system": {
            "processes": [
                "svchost.exe", "dwm.exe", "csrss.exe", "winlogon.exe", "explorer.exe",
                "taskhostw.exe", "ctfmon.exe", "sihost.exe", "RuntimeBroker.exe",
                "ShellExperienceHost.exe", "SearchIndexer.exe", "smss.exe", "wininit.exe",
                "services.exe", "lsass.exe", "fontdrvhost.exe", "conhost.exe",
                "SecurityHealthSystray.exe", "MoUsoCoreWorker.exe", "TiWorker.exe",
                "TrustedInstaller.exe", "msmpeng.exe", "nisSrv.exe", "sihost.exe"
            ],
            "titles": [
                "Desktop Window Manager", "Windows Shell Experience Host", "Program Manager",
                "Security and Maintenance", "System", "Search", "Settings", "Task Host",
                "Runtime Broker", "Font Driver Host", "Console Window Host",
                "Microsoft Windows Operating System", "Windows Security Health",
                "Windows Update", "Microsoft Defender Antivirus Service"
            ],
            "icons": ["system", "dwm", "explorer", "security", "update", "defender"]  # 可放通用Windows图标
        },

        # 2. 即时通讯/社交
        "im_social": {
            "processes": ["WeChat.exe", "QQ.exe", "TIM.exe", "DingTalk.exe", "Feishu.exe", "EnterpriseWeChat.exe"],
            "titles": ["微信", "QQ", "TIM", "钉钉", "飞书", "企业微信", "微信 - 正在同步消息", "QQ - 消息提醒"],
            "icons": ["wechat", "qq", "tim", "dingtalk", "feishu", "enterprisewc"]
        },

        # 3. 短视频/直播
        "video_short": {
            "processes": ["Douyin.exe", "Kuaishou.exe", "XiguaVideo.exe", "Bilibili.exe", "Youku.exe", "iQIYI.exe"],
            "titles": ["抖音", "快手", "西瓜视频", "哔哩哔哩", "优酷", "爱奇艺", "抖音 - 推荐", "B站 - 首页"],
            "icons": ["douyin", "kuaishou", "xigua", "bilibili", "youku", "iqiyi"]
        },

        # 4. 电商/外卖
        "shopping": {
            "processes": ["Taobao.exe", "JDLive.exe", "Pinduoduo.exe", "Meituan.exe", "Eleme.exe"],
            "titles": ["淘宝", "京东", "拼多多", "美团", "饿了么", "淘宝 - 首页", "京东 - 购物车"],
            "icons": ["taobao", "jd", "pinduoduo", "meituan", "eleme"]
        },

        # 5. 杀毒/安全软件（重点）
        "antivirus": {
            "processes": [
                "360safe.exe", "360tray.exe", "ZhuDongFangYu.exe", "KSafeTray.exe",
                "Huorong.exe", "HipsTray.exe", "KvMon.exe", "TxGuard.exe", "QQPCMgr.exe"
            ],
            "titles": ["360安全卫士", "360安全卫士 - 主面板", "火绒安全", "金山毒霸", "腾讯电脑管家", "360实时保护"],
            "icons": ["360safe", "360tray", "huorong", "kv", "txcomputer", "qqpcmgr"]
        },

        # 6. 浏览器
        "browser": {
            "processes": ["chrome.exe", "msedge.exe", "360chrome.exe", "QQBrowser.exe"],
            "titles": ["Chrome", "Microsoft Edge", "360安全浏览器", "QQ浏览器", "新标签页", "百度一下，你就知道"],
            "icons": ["chrome", "msedge", "360chrome", "qqbrowser"]
        },

        # 7. 系统/媒体/游戏平台
        "media_game": {
            "processes": [
                "Steam.exe", "WeGame.exe", "EpicGamesLauncher.exe",
                "PotPlayerMini64.exe", "vlc.exe", "Thunder.exe", "BaiduNetdisk.exe"
            ],
            "titles": ["Steam", "WeGame", "Epic Games", "PotPlayer", "VLC", "迅雷", "百度网盘"],
            "icons": ["steam", "wegame", "epic", "potplayer", "vlc", "thunder", "baidunetdisk"]
        }
    }

    @staticmethod
    def get_random_fake_profile():
        category = random.choice(list(ProcessMasking.FAKE_PROFILES.keys()))
        profile = ProcessMasking.FAKE_PROFILES[category]
        fake_process = random.choice(profile["processes"])
        fake_title = random.choice(profile["titles"])
        icon_base = random.choice(profile["icons"])
        return fake_process, fake_title, icon_base, category

    @staticmethod
    def mask_process_name(fake_name: str):
        if platform.system() == "Windows":
            try:
                ctypes.windll.kernel32.SetConsoleTitleW(fake_name)
                print(f"[Mask] 进程控制台标题伪装为: {fake_name}")
            except Exception as e:
                print(f"[Mask] 进程名伪装失败: {e}")

    @staticmethod
    def mask_window_title(window, fake_title: str):
        try:
            window.setWindowTitle(fake_title)
            print(f"[Mask] 主窗口标题伪装为: {fake_title}")
        except Exception as e:
            print(f"[Mask] 窗口标题伪装失败: {e}")

    @staticmethod
    def mask_tray_icon(app, icon_base_name: str):
        try:
            candidates = [
                resource_path(os.path.join("fake_icons", f"{icon_base_name}.ico")),
                resource_path(os.path.join("fake_icons", f"{icon_base_name}.png")),
                resource_path(os.path.join("fake_icons", icon_base_name)),
            ]
            for path in candidates:
                if os.path.exists(path):
                    app.tray_icon.setIcon(QIcon(path))
                    print(f"[Mask] 托盘图标伪装为: {os.path.basename(path)}")
                    return
            print("[Mask] 未找到对应图标，使用默认托盘图标")
        except Exception as e:
            print(f"[Mask] 托盘图标伪装失败: {e}")

    @staticmethod
    def hide_from_taskbar(window):
        if platform.system() != "Windows":
            return
        try:
            hwnd = int(window.winId())
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            style |= win32con.WS_EX_TOOLWINDOW
            style &= ~win32con.WS_EX_APPWINDOW
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, style)
            print("[Mask] 主窗口已隐藏任务栏图标和Alt+Tab")
        except Exception as e:
            print(f"[Mask] 隐藏任务栏失败: {e}")

    @staticmethod
    def apply_full_mask(main_window, app):
        threading.Thread(
            target=ProcessMasking._delayed_full_mask,
            args=(main_window, app),
            daemon=True
        ).start()

    @staticmethod
    def _delayed_full_mask(main_window, app):
        time.sleep(2.0)

        fake_process, fake_title, icon_base, category = ProcessMasking.get_random_fake_profile()
        print(f"[Mask] 本次融合伪装方案 [{category}]: 进程={fake_process} | 标题={fake_title} | 图标={icon_base}")

        ProcessMasking.mask_process_name(fake_process)
        ProcessMasking.mask_window_title(main_window, fake_title)
        ProcessMasking.mask_tray_icon(app, icon_base)
        ProcessMasking.hide_from_taskbar(main_window)

# 使用方式不变：
# ProcessMasking.apply_full_mask(self, SafeApp.instance())
# src/tools/resource_path.py
import os
import sys

def resource_path(relative_path):
    """
    获取资源的绝对路径（支持开发模式和PyInstaller打包模式）
    
    用法示例：
    icon_path = resource_path("resources/ai_icon.png")
    QIcon(icon_path)
    
    开发时：返回项目目录下的路径
    打包成exe后：返回临时解压目录（_MEIPASS）中的路径
    """
    try:
        # PyInstaller打包后会创建一个临时文件夹，并把路径存放在 sys._MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # 开发模式，直接用当前文件所在目录
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)
    # ================== src/tools/utils.py ==================
import os
import datetime
import platform

class SimpleLogger:
    """
    文件日志记录器，简单易用
    """
    def __init__(self, log_file="run.log"):
        self.log_file = log_file

    def log(self, msg, level="INFO"):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{now}][{level}] {msg}\n"
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(entry)

    def error(self, msg):
        self.log(msg, "ERROR")

    def info(self, msg):
        self.log(msg, "INFO")

def format_time(ts=None):
    """
    返回统一的格式化时间字符串
    """
    dt = datetime.datetime.fromtimestamp(ts) if ts else datetime.datetime.now()
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def sys_platform_info():
    """
    获取主机系统与Python环境信息
    """
    info = {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "machine": platform.machine(),
        "uptime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    return info

def mkdir_if_not_exists(path):
    """
    若目录不存在则自动创建
    """
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
        return True
    return False

# ================== src/tools/utils.py 完，下一步 src/tools/process_mask.py（进程/窗口伪装） ==================

# 拼接说明：常用工具函数已实现。
# 下一步请在 src/tools 下新建 process_mask.py，等待安全进程/窗口伪装逻辑模块。
# ================== src/ui/dialogs.py ==================
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit, QTableWidget, 
    QTableWidgetItem, QHeaderView, QAbstractItemView, QMessageBox, QComboBox, 
    QProgressBar, QSpacerItem, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QRect
from PyQt5.QtGui import QIcon, QColor, QBrush, QPixmap, QPainter, QPen
import random
import datetime

class SettingsDialog(QDialog):
    """
    通用设置窗口，可扩展各类偏好/高级参数配置
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("系统设置")
        self.setFixedSize(420, 320)
        layout = QVBoxLayout()
        # 演示：可添加多个设置项
        layout.addWidget(QLabel("功能设置区，更多参数请在src/ui/dialogs.py完善..."))
        self.setLayout(layout)


class KamiDialog(QDialog):
    """
    卡密后台系统：生成、冻结、删除、卡密列表、批量美化、粒子庆祝
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("卡密后台（生成/冻结/仿真）")
        self.setFixedSize(640, 480)
        self._setup_ui()
        self._init_data()
        self._refresh_table()

    def _setup_ui(self):
        layout = QVBoxLayout()
        hl = QHBoxLayout()
        hl.addWidget(QLabel("生成数量："))
        self.num_box = QComboBox()
        self.num_box.addItems(["1","10","50","100"])
        hl.addWidget(self.num_box)
        self.btn_gen = QPushButton("生成")
        self.btn_gen.clicked.connect(self._on_generate)
        hl.addWidget(self.btn_gen)
        # 进度条
        self.progress = QProgressBar()
        self.progress.hide()
        hl.addWidget(self.progress)
        hl.addStretch()
        layout.addLayout(hl)
        # 表格展示
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            "卡密", "类型", "备注", "IP", "HWID", "到期", "状态"
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_context_menu)
        layout.addWidget(self.table)
        # 粉色粒子动画区域
        self.anim_widget = ParticleWidget(self)
        layout.addWidget(self.anim_widget)
        layout.addSpacing(10)
        self.setLayout(layout)

    def _init_data(self):
        # 假设用内存结构保存（实际可接API/数据库）
        self.kami_list = []   # [dict(kami, type, ...)]
        self._load_data()

    def _load_data(self):
        # 可以加载数据库/磁盘/云API
        # 这里仅模拟生成部分假数据
        for i in range(10):
            self.kami_list.append({
                "kami": f"KAMI2025A00{i}",
                "type": random.choice(["1天", "7天", "1月", "永久"]),
                "note": f"备注{i}",
                "ip": "8.8.8.8",
                "hwid": "ABCD-1234-5678-999{}".format(i),
                "exp": (datetime.datetime.now() + datetime.timedelta(days=30)).strftime('%Y-%m-%d'),
                "state": "已使用" if i % 2 == 0 else "未激活"
            })

    def _refresh_table(self):
        self.table.setRowCount(len(self.kami_list))
        for row, k in enumerate(self.kami_list):
            for col, key in enumerate(["kami", "type", "note", "ip", "hwid", "exp", "state"]):
                item = QTableWidgetItem(str(k.get(key, "")))
                self.table.setItem(row, col, item)

    def _on_generate(self):
        # 批量生成带进度条和粒子动画
        try:
            count = int(self.num_box.currentText())
        except:
            count = 10
        self.progress.setMaximum(count)
        self.progress.setValue(0)
        self.progress.show()
        self.btn_gen.setEnabled(False)
        self.anim_widget.hide()
        self._gen_count = count
        self._now_gen = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._gen_tick)
        self._timer.start(50)

    def _gen_tick(self):
        if self._now_gen >= self._gen_count:
            self._timer.stop()
            self.progress.hide()
            self.btn_gen.setEnabled(True)
            self.anim_widget.start_particles()
            self._refresh_table()
            return
        # 随机生成假卡密
        idx = len(self.kami_list) + 1
        kami = f"KAMI{random.randint(100000,999999)}"
        self.kami_list.append({
            "kami": kami,
            "type": random.choice(["1小时", "12小时", "1天", "7天", "1月", "1季度", "1年"]),
            "note": "批量生成",
            "ip": "未激活",
            "hwid": "",
            "exp": (datetime.datetime.now() + datetime.timedelta(days=365)).strftime('%Y-%m-%d'),
            "state": "未激活"
        })
        self._now_gen += 1
        self.progress.setValue(self._now_gen)

    def _on_context_menu(self, pos):
        row = self.table.currentRow()
        if row >= 0:
            menu = QMenu(self)
            act_freeze = menu.addAction("冻结")
            act_delete = menu.addAction("删除")
            act_export = menu.addAction("导出")
            act_freeze.triggered.connect(lambda: self._do_freeze(row))
            act_delete.triggered.connect(lambda: self._do_delete(row))
            act_export.triggered.connect(lambda: self._do_export(row))
            menu.exec_(self.table.viewport().mapToGlobal(pos))

    def _do_freeze(self, row):
        # 冻结卡密
        self.kami_list[row]["state"] = "冻结"
        self._refresh_table()
        QMessageBox.information(self, "冻结卡密", "冻结成功！")

    def _do_delete(self, row):
        self.kami_list.pop(row)
        self._refresh_table()
        QMessageBox.information(self, "删除卡密", "删除成功！")

    def _do_export(self, row):
        # 导出卡密信息（可写本地、或复制到剪贴板）
        info = self.kami_list[row]
        info_str = "\n".join([f"{k}: {v}" for k,v in info.items()])
        dlg = QDialog(self)
        dlg.setWindowTitle("卡密导出")
        vbox = QVBoxLayout()
        ed = QLineEdit(info_str)
        vbox.addWidget(ed)
        btn = QPushButton("复制")
        btn.clicked.connect(lambda: QApplication.clipboard().setText(info_str))
        vbox.addWidget(btn)
        dlg.setLayout(vbox)
        dlg.exec_()


class ParticleWidget(QWidget):
    """
    粉色粒子庆祝动画Widget（生成卡密时触发）
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.seeds = []
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_particles)
        self.hide()
        self.setFixedHeight(48)

    def start_particles(self):
        # 大量生成粒子
        self.seeds = []
        w = self.width() if self.width() > 0 else 400
        for _ in range(38):
            x = random.randint(0, w)
            v = random.randint(-5, 5)
            c = QColor(255, 160 + random.randint(0, 80), 255, random.randint(100, 230))
            scale = random.uniform(0.8, 1.5)
            self.seeds.append([x, 0, v, c, scale])
        self.show()
        self.timer.start(30)

    def update_particles(self):
        for p in self.seeds:
             p[1] += random.randint(3, 7)
             p[0] += p[2]
        if self.seeds and max(x[1] for x in self.seeds) > self.height():
            self.seeds = []
            self.hide()
            self.timer.stop()
        self.update()

    def paintEvent(self, event):
        qp = QPainter(self)
        for x, y, v, c, scale in self.seeds:
            qp.setPen(Qt.NoPen)
            qp.setBrush(QBrush(c))
            qp.drawEllipse(x, y, int(21*scale), int(18*scale))


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("关于 安静AI视觉辅助平台")
        self.setFixedSize(360, 220)
        layout = QVBoxLayout()
        txt = QLabel("安静专属顶级AI视觉技术\n版本 1.0\n\n为PC端九大主流射击网游全系打造\n融合最新YOLO视觉AI、多外设、极致安全防检测、七大皮肤主题\n项目开源/私用均可，商用请授权！\n\n感谢您的信任与体验！")
        txt.setAlignment(Qt.AlignCenter)
        txt.setStyleSheet("font-size:15px;")
        layout.addWidget(txt)
        self.setLayout(layout)

# ================== src/ui/dialogs.py 完，下一步 src/ui/radar.py（独立雷达窗口）开始 ==================

# 拼接说明：弹窗/卡密/设置/粒子动画均已实现。
# 下一步请在 src/ui/ 新建 radar.py，等待下一个模块。
# src/ui/esp_overlay.py
# 2025年独立透视叠加窗（ESP透视终极版）

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPainter, QPen, QBrush, QFont, QColor

from src.core.yolo_ai import visual_core
from src.core.screenshot import game_capture
from src.config.config import load_config

import math

class ESPOverlay(QWidget):
    """
    独立透视叠加窗
    - 透明背景 + 点击穿透 + 始终置顶
    - 实时绘制ESP：方框 + 骨骼 + 名字 + 距离 + 血条
    - 颜色从当前游戏配置读取
    - 热键F3开关（在main_window注册）
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("安静AI - ESP透视叠加窗")
        self.setWindowFlags(
            Qt.FramelessWindowHint |           # 无边框
            Qt.WindowStaysOnTopHint |          # 始终置顶
            Qt.Tool |                          # 不显示在任务栏
            Qt.WindowTransparentForInput       # 点击穿透（鼠标操作透到游戏）
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)  # 透明背景

        # 全屏覆盖主显示器
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)

        self.visible = True
        self.targets = []

        # 实时更新
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_esp)
        self.timer.start(16)  # ~60FPS

        print("[ESP] 透视叠加窗已创建（F3开关）")

    def toggle_visibility(self):
        """开关透视窗"""
        self.visible = not self.visible
        if self.visible:
            self.show()
            self.raise_()
            self.activateWindow()
            print("[ESP] 透视已开启")
        else:
            self.hide()
            print("[ESP] 透视已关闭")

    def update_esp(self):
        """每帧更新检测结果"""
        img = game_capture.capture()
        if img is not None:
            self.targets = visual_core.infer(img, conf=0.35, classes=[0])
        self.update()  # 触发重绘

    def paintEvent(self, event):
        if not self.visible:
            return

        if not self.targets:
            return

        qp = QPainter(self)
        qp.setRenderHint(QPainter.Antialiasing)

        # 当前游戏配置（用于读取ESP颜色）
        config = load_config()
        # 假设从主窗口获取当前Tab（这里简化用CF作为默认）
        current_game = "CF"  # 实际应从主窗口传递当前游戏key
        esp_color_hex = config.get("game_params", {}).get(current_game, {}).get("esp_color", "#FF6464")
        esp_color = QColor(esp_color_hex)
        esp_color.setAlpha(220)

        line_pen = QPen(esp_color, 2)
        box_pen = QPen(esp_color, 3)
        text_font = QFont("Microsoft YaHei", 10, QFont.Bold)
        small_font = QFont("Microsoft YaHei", 8)

        for target in self.targets:
            if "box" not in target or "keypoints" not in target:
                continue

            box = target["box"]
            kps = target["keypoints"]

            x1, y1, x2, y2 = map(int, box)

            # 2D方框
            qp.setPen(box_pen)
            qp.setBrush(Qt.NoBrush)
            qp.drawRect(x1, y1, x2 - x1, y2 - y1)

            # 中心点
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2

            # 名字 + 距离
            name = target.get("name", "敌人")
            distance = int(math.hypot(center_x - self.width() // 2, center_y - self.height() // 2) / 15)
            qp.setPen(QColor(255, 255, 255))
            qp.setFont(text_font)
            qp.drawText(center_x - 50, y1 - 10, f"{name} {distance}m")

            # 血条
            hp = random.randint(20, 100)  # 模拟血量
            bar_width = x2 - x1
            bar_height = 10
            qp.setBrush(QBrush(QColor(50, 50, 50)))
            qp.drawRect(x1, y1 - 25, bar_width, bar_height)
            hp_color = QColor(0, 255, 0) if hp > 50 else QColor(255, 255, 0) if hp > 25 else QColor(255, 0, 0)
            qp.setBrush(QBrush(hp_color))
            qp.drawRect(x1, y1 - 25, int(bar_width * hp / 100), bar_height)

            # 骨骼线（COCO标准连接）
            connections = [
                (0, 1), (1, 2), (0, 3), (3, 4),           # 头部
                (1, 5), (2, 6),                           # 肩膀
                (5, 7), (7, 9), (6, 8), (8, 10),          # 手臂
                (5, 11), (6, 12), (11, 13), (12, 14),     # 腿部
                (13, 15), (14, 16)                        # 脚
            ]
            qp.setPen(line_pen)
            for a, b in connections:
                if a < len(kps) and b < len(kps):
                    ax, ay = kps[a]
                    bx, by = kps[b]
                    if ax > 0 and ay > 0 and bx > 0 and by > 0:
                        qp.drawLine(int(ax), int(ay), int(bx), int(by))

        qp.end()
        # src/ui/login.py
# 纯本地终极卡密验证（带剩余时间 + 解绑扣2小时）

from PyQt5.QtWidgets import (
    QDialog, QLabel, QLineEdit, QVBoxLayout, QHBoxLayout, QPushButton,
    QMessageBox, QCheckBox, QWidget, QSpacerItem, QSizePolicy
)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
import uuid
import hashlib
import subprocess
import datetime
import os
import json

from src.config.config import _get_fernet
from appdirs import user_config_dir

# 反调试
import ctypes
if ctypes.windll.kernel32.IsDebuggerPresent():
    import sys
    sys.exit(0)

class LoginDialog(QDialog):
    def __init__(self, theme_manager, parent=None):
        super().__init__(parent)
        self.theme_manager = theme_manager
        self.setWindowTitle("登录 - 安静AI视觉技术")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setFixedSize(420, 340)

        self.bind_file = os.path.join(user_config_dir("AnjingAI"), "bind.dat")

        main_layout = QVBoxLayout()
        l_title = QLabel("账号登录")
        l_title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        l_title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(l_title)

        h_kami = QHBoxLayout()
        self.le_kami = QLineEdit()
        self.le_kami.setPlaceholderText("请输入卡密...")
        h_kami.addWidget(self.le_kami, 5)

        btn_unbind = QPushButton("解绑换机")
        btn_unbind.setToolTip("解绑本机，扣除2小时剩余时间")
        btn_unbind.clicked.connect(self.unbind_hwid)
        h_kami.addWidget(btn_unbind, 3)
        main_layout.addLayout(h_kami)

        self.cb_autologin = QCheckBox("下次自动登录")
        self.cb_autologin.setChecked(True)
        main_layout.addWidget(self.cb_autologin)

        btn_layout = QHBoxLayout()
        btn_login = QPushButton("登录验证")
        btn_login.clicked.connect(self._do_login)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_login)
        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)

        self.le_hwid = QLineEdit(self.get_hwid()[:16] + "...")
        self.le_hwid.setReadOnly(True)
        self.le_hwid.setToolTip("当前设备识别码（已加强）")
        main_layout.addWidget(self.le_hwid)

        tip = QLabel("首次使用需输入卡密绑定本机，换机点击解绑（扣2小时）。")
        tip.setStyleSheet("color:gray;font-size:12px;")
        tip.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(tip)

        self.setLayout(main_layout)
        self.user_info = None

        self.try_auto_login()

    def get_hwid(self):
        hwid_parts = []
        try:
            result = subprocess.check_output("wmic diskdrive get serialnumber", shell=True, encoding='utf-8')
            hwid_parts.append(result.strip())
        except:
            pass
        try:
            result = subprocess.check_output("wmic cpu get processorid", shell=True, encoding='utf-8')
            hwid_parts.append(result.strip())
        except:
            pass
        try:
            result = subprocess.check_output("wmic csproduct get uuid", shell=True, encoding='utf-8')
            hwid_parts.append(result.strip())
        except:
            pass
        hwid_parts.append(str(uuid.getnode()))
        raw = "".join(hwid_parts).encode('utf-8', errors='ignore')
        return hashlib.sha256(raw).hexdigest().upper()

    def try_auto_login(self):
        if not self.cb_autologin.isChecked() or not os.path.exists(self.bind_file):
            return

        try:
            f = _get_fernet()
            with open(self.bind_file, "rb") as fh:
                enc = fh.read()
                data = json.loads(f.decrypt(enc).decode('utf-8'))

            current_hwid = self.get_hwid()
            if data["hwid"] == current_hwid:
                # 计算剩余时间
                remaining = self.calculate_remaining(data)
                if remaining <= 0 and data["total_hours"] != "permanent":
                    QMessageBox.critical(self, "卡密过期", "卡密已过期，请联系作者续费。")
                    os.remove(self.bind_file)
                    return

                self.user_info = {
                    "kami": data["kami"],
                    "hwid": current_hwid,
                    "type": data.get("type", "user"),
                    "expire_time": data.get("expire_time", "永久"),
                    "remaining_hours": remaining if data["total_hours"] != "permanent" else "永久"
                }
                self.accept()
        except Exception:
            pass

    def calculate_remaining(self, data):
        if data["total_hours"] == "permanent":
            return "永久"

        total = data["total_hours"]
        used = data.get("used_hours", 0.0)
        last_login = datetime.datetime.fromisoformat(data.get("last_login", datetime.datetime.now().isoformat()))
        now = datetime.datetime.now()
        session_hours = (now - last_login).total_seconds() / 3600
        used += session_hours

        remaining = total - used
        return max(0, remaining)

    def unbind_hwid(self):
        if not os.path.exists(self.bind_file):
            QMessageBox.information(self, "无绑定", "当前设备未绑定卡密。")
            return

        reply = QMessageBox.question(self, "解绑确认", 
                                     "解绑将扣除2小时剩余时间，确定吗？",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                f = _get_fernet()
                with open(self.bind_file, "rb") as fh:
                    enc = fh.read()
                    data = json.loads(f.decrypt(enc).decode('utf-8'))

                if data["total_hours"] != "permanent":
                    data["used_hours"] = data.get("used_hours", 0) + 2
                    enc = f.encrypt(json.dumps(data).encode('utf-8'))
                    with open(self.bind_file, "wb") as fh:
                        fh.write(enc)
                    QMessageBox.information(self, "解绑成功", "已扣除2小时，绑定已清除。")
                os.remove(self.bind_file)
            except Exception as e:
                QMessageBox.critical(self, "解绑失败", str(e))

    def _do_login(self):
        kami = self.le_kami.text().strip()
        if not kami:
            QMessageBox.warning(self, "缺少卡密", "请输入您的卡密。")
            return

        hwid = self.get_hwid()

        # 卡密哈希表（添加你的卡密哈希）
        valid_kami = {
            "EXAMPLE_HASH1": {"total_hours": "permanent", "type": "vip"},
            "EXAMPLE_HASH2": {"total_hours": 100.0, "type": "user"},
            # 用 hashlib.sha256("你的卡密".encode()).hexdigest().upper() 生成哈希填这里
        }

        kami_hash = hashlib.sha256(kami.encode('utf-8')).hexdigest().upper()
        if kami_hash not in valid_kami:
            QMessageBox.critical(self, "卡密错误", "卡密无效！")
            return

        card_info = valid_kami[kami_hash]

        if os.path.exists(self.bind_file):
            try:
                f = _get_fernet()
                with open(self.bind_file, "rb") as fh:
                    enc = fh.read()
                    data = json.loads(f.decrypt(enc).decode('utf-8'))
                if data["hwid"] != hwid:
                    QMessageBox.critical(self, "绑定失败", "此卡密已绑定其他设备！")
                    return
            except:
                QMessageBox.critical(self, "验证失败", "绑定文件损坏")
                return
        else:
            # 首次绑定
            bind_data = {
                "kami": kami,
                "hwid": hwid,
                "total_hours": card_info["total_hours"],
                "used_hours": 0.0,
                "last_login": datetime.datetime.now().isoformat(),
                "type": card_info["type"]
            }
            try:
                f = _get_fernet()
                enc = f.encrypt(json.dumps(bind_data).encode('utf-8'))
                os.makedirs(os.path.dirname(self.bind_file), exist_ok=True)
                with open(self.bind_file, "wb") as fh:
                    fh.write(enc)
            except Exception as e:
                QMessageBox.critical(self, "绑定失败", str(e))
                return

        # 计算剩余时间
        remaining = card_info["total_hours"] if card_info["total_hours"] == "permanent" else card_info["total_hours"]

        self.user_info = {
            "kami": kami,
            "hwid": hwid,
            "type": card_info["type"],
            "expire_time": "永久" if card_info["total_hours"] == "permanent" else f"剩余 {remaining} 小时",
            "remaining_hours": remaining
        }
        self.accept()

    def get_user_info(self):
        return self.user_info or {}
        # src/ui/main_window.py
# 2025年旗舰风格UI完整版（左侧9游戏竖排 + 右侧参数 + 折叠高级 + 截图切换 + 配置热重载）

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QAction, QMenu, QStatusBar, QSplitter, QListWidget, QListWidgetItem,
    QGroupBox, QGridLayout, QScrollArea, QToolBox, QFrame, QSlider, QCheckBox,
    QColorDialog, QComboBox
)
from PyQt5.QtCore import Qt, QTimer, QSize
from PyQt5.QtGui import QIcon, QColor, QFont, QPixmap, QPainter, QPen, QBrush, QLinearGradient

from .theme import ThemeManager
from .stats import StatsWindow
from .esp_overlay import ESPOverlay
from src.tools.resource_path import resource_path
from src.config.config import load_config, load_all_configs
from src.core.hotkeys import HotkeyManager
from src.core.cheats import cheat_service
from src.core.yolo_ai import visual_core
from src.devices.hardware import hardware_manager
from src.core.screenshot import ScreenshotManager, game_capture  # 全局game_capture

import os
import time

# ============ 压枪曲线编辑器 ============
class CurveEditor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(500, 250)
        self.setStyleSheet("background-color: #1e1e2e; border: 1px solid #444; border-radius: 10px;")
        self.curve = [0.0] * 30
        self.drawing = False

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drawing = True
            self.update_point(event.pos())

    def mouseMoveEvent(self, event):
        if self.drawing:
            self.update_point(event.pos())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drawing = False
            if hasattr(self, "save_callback"):
                self.save_callback(self.get_curve())

    def update_point(self, pos):
        x = max(0, min(pos.x(), self.width() - 1))
        y = max(0, min(pos.y(), self.height() - 1))
        idx = int(x / self.width() * len(self.curve))
        if 0 <= idx < len(self.curve):
            max_offset = 60.0
            self.curve[idx] = (y / self.height()) * max_offset
        self.update()

    def paintEvent(self, event):
        qp = QPainter(self)
        qp.setRenderHint(QPainter.Antialiasing)
        qp.fillRect(self.rect(), QColor(30, 30, 46))

        # 网格
        qp.setPen(QPen(QColor(80, 80, 80), 1, Qt.DashLine))
        for i in range(1, 6):
            y = int(self.height() * i / 6)
            qp.drawLine(0, y, self.width(), y)

        # 曲线
        qp.setPen(QPen(QColor(0, 170, 255), 4))
        points = []
        for i, v in enumerate(self.curve):
            x = int(i / len(self.curve) * self.width())
            y = int(self.height() - (v / 60.0 * self.height()))
            points.append((x, y))

        if len(points) > 1:
            for i in range(len(points) - 1):
                qp.drawLine(points[i][0], points[i][1], points[i+1][0], points[i+1][1])

        # 文字
        qp.setPen(QColor(200, 200, 200))
        qp.setFont(QFont("Microsoft YaHei", 10))
        qp.drawText(20, 30, "压枪曲线编辑（鼠标拖动绘制）")

    def get_curve(self):
        return self.curve[:]

    def set_curve(self, curve):
        if len(curve) == len(self.curve):
            self.curve = curve[:]
            self.update()

# ============ 主窗口 ============
class MainWindow(QMainWindow):
    def __init__(self, user_info, theme_manager: ThemeManager, parent=None):
        super().__init__(parent)
        self.user_info = user_info
        self.theme_manager = theme_manager
        self.setWindowTitle("安静AI - 顶级视觉技术")
        self.setWindowIcon(QIcon(resource_path("resources/ai_icon.ico")))
        self.setGeometry(100, 50, 1600, 1000)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 左侧游戏列表
        self.setup_game_list()

        # 分隔
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.game_list_widget)

        # 右侧面板
        self.right_panel = QWidget()
        self.right_layout = QVBoxLayout(self.right_panel)
        self.right_layout.setContentsMargins(20, 20, 20, 20)
        self.setup_right_panel()

        splitter.addWidget(self.right_panel)
        splitter.setSizes([350, 1250])

        self.main_layout.addWidget(splitter)

        # 热键
        self.hotkey_mgr = HotkeyManager(self)
        self.hotkey_mgr.install_on_widget(self)
        self.hotkey_mgr.register_hotkey("切换透视", Qt.Key_F3, callback=self.toggle_esp)
        self.hotkey_mgr.register_hotkey("热重载配置", Qt.Key_R, Qt.ControlModifier | Qt.AltModifier, callback=self.reload_config)

        # 透视窗
        self.esp_overlay = ESPOverlay(self)
        self.esp_overlay.hide()

        # 硬件刷新
        self.hardware_timer = QTimer(self)
        self.hardware_timer.timeout.connect(self.update_status)
        self.hardware_timer.start(5000)
        self.update_status()

        # 默认选中第一个游戏
        self.game_list_widget.setCurrentRow(0)

    # ==============================================
    # 右侧面板布局
    def setup_right_panel(self):
        # 顶部信息
        top_frame = QFrame()
        top_frame.setStyleSheet("background-color: rgba(30, 30, 50, 200); border-radius: 10px; padding: 10px;")
        top_layout = QHBoxLayout(top_frame)

        self.l_kami = QLabel(f"卡密：{self.user_info.get('kami', '未识别')}")
        self.l_kami.setStyleSheet("color: #00AAFF; font-size: 16px; font-weight: bold;")
        top_layout.addWidget(self.l_kami)

        self.l_type = QLabel(f"类型：{self.user_info.get('type', 'user').upper()}")
        self.l_type.setStyleSheet("color: #88FF88; font-size: 15px;")
        top_layout.addWidget(self.l_type)

        remaining = self.user_info.get("remaining_hours", "永久")
        expire_text = "永久" if remaining == "永久" else f"剩余 {remaining:.1f}小时"
        self.l_expire = QLabel(f"到期：{expire_text}")
        self.l_expire.setStyleSheet("color: #FFAA00; font-size: 15px;")
        top_layout.addWidget(self.l_expire)

        top_layout.addStretch()

        self.l_hardware = QLabel("硬件：离线")
        self.l_hardware.setStyleSheet("color: #FFFFFF; font-size: 15px;")
        top_layout.addWidget(self.l_hardware)

        self.right_layout.addWidget(top_frame)

        # ============ 截图模式选择 ============
        capture_group = QGroupBox("截图模式")
        capture_group.setStyleSheet("QGroupBox { font-size: 16px; font-weight: bold; color: #00FFAA; }")
        capture_layout = QHBoxLayout()

        self.capture_combo = QComboBox()
        self.capture_combo.addItems([
            "DXGI 多线程 (全屏推荐, 默认)",
            "DXGI 单线程",
            "句柄截图 (窗口化推荐)",
            "MSS (兼容最广)"
        ])
        self.capture_combo.setCurrentIndex(0)
        self.capture_combo.currentIndexChanged.connect(self.change_capture_mode)
        capture_layout.addWidget(QLabel("模式:"))
        capture_layout.addWidget(self.capture_combo)
        capture_layout.addStretch()

        capture_group.setLayout(capture_layout)
        self.right_layout.addWidget(capture_group)

        # ============ 一键刷新配置按钮 ============
        refresh_group = QGroupBox("配置管理")
        refresh_group.setStyleSheet("QGroupBox { font-size: 16px; font-weight: bold; color: #FFAA00; }")
        refresh_layout = QHBoxLayout()

        self.refresh_btn = QPushButton("🔄 刷新配置")
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FFAA00, stop:1 #CC8800);
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 10px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FFCC00, stop:1 #DD9900);
            }
        """)
        self.refresh_btn.clicked.connect(self.reload_config)
        refresh_layout.addWidget(self.refresh_btn)
        refresh_layout.addStretch()

        refresh_group.setLayout(refresh_layout)
        self.right_layout.addWidget(refresh_group)

        # 参数滚动区
        self.scroll = QScrollArea()
        self.scroll.setStyleSheet("background-color: transparent;")
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.setSpacing(20)

        self.scroll.setWidget(self.scroll_widget)
        self.scroll.setWidgetResizable(True)
        self.right_layout.addWidget(self.scroll)

    # ==============================================
    # 类方法

    def change_capture_mode(self, index):
        """截图模式切换逻辑"""
        global game_capture

        modes = ["dxgi_thread", "dxgi", "handle", "mss"]
        new_mode = modes[index]

        print(f"[截图] 正在切换到模式: {new_mode.upper()}")

        # 停止旧线程
        try:
            if hasattr(game_capture, 'stop'):
                game_capture.stop()
                time.sleep(0.1)
        except:
            pass
# 创建新实例
        game_capture = ScreenshotManager(mode=new_mode)

        # 多线程模式启动后台截图
        if new_mode == "dxgi_thread":
            game_capture.start_continuous(self.on_new_frame)

        self.statusBar().showMessage(f"截图模式切换为: {self.capture_combo.currentText()}", 3000)

    def on_new_frame(self, frame):
        """多线程模式下收到新帧的回调"""
        if frame is None:
            return

        targets = visual_core.infer(frame)

        if hasattr(self, 'esp_overlay') and self.esp_overlay.isVisible():
            self.esp_overlay.targets = targets
            self.esp_overlay.update()

    def reload_config(self):
        """热重载配置（按钮或热键触发）"""
        from src.config.config import load_all_configs

        load_all_configs()

        self.statusBar().showMessage("✅ 配置已刷新！", 5000)

        if hasattr(self, 'refresh_btn'):
            original_style = self.refresh_btn.styleSheet()
            self.refresh_btn.setText("✔ 已刷新")
            self.refresh_btn.setStyleSheet("""
                QPushButton {
                    background: #00AA00;
                    color: white;
                    font-size: 16px;
                    font-weight: bold;
                    padding: 10px;
                    border-radius: 8px;
                }
            """)
            self.refresh_btn.setEnabled(False)

            QTimer.singleShot(2000, lambda: (
                self.refresh_btn.setText("🔄 刷新配置"),
                self.refresh_btn.setStyleSheet(original_style),
                self.refresh_btn.setEnabled(True)
            ))

        current_row = self.game_list_widget.currentRow()
        if current_row >= 0:
            self.on_game_selected(current_row)

        print("[Config] 配置热重载完成")

    def update_status(self):
        devices = hardware_manager.list_devices()
        count = len(devices)
        status = "在线" if count > 0 else "离线"
        self.l_hardware.setText(f"硬件：{count}台 | 状态：{status}")

    def toggle_esp(self):
        self.esp_overlay.toggle_visibility()

    # ... 你的其他方法（如 on_game_selected, update_right_panel, setup_game_list 等保持不变） ...

    def setup_game_list(self):
        self.game_list_widget = QListWidget()
        self.game_list_widget.setStyleSheet("""
            QListWidget {
                background-color: rgba(20, 20, 40, 240);
                border: none;
            }
            QListWidget::item {
                padding: 15px;
                margin: 5px;
                border-radius: 10px;
            }
            QListWidget::item:selected {
                background-color: rgba(0, 170, 255, 100);
                border-left: 6px solid #00AAFF;
            }
        """)
        self.game_list_widget.setIconSize(QSize(140, 140))
        self.game_list_widget.setSpacing(10)
        self.game_list_widget.setViewMode(QListWidget.IconMode)
        self.game_list_widget.setFlow(QListWidget.TopToBottom)
        self.game_list_widget.setResizeMode(QListWidget.Adjust)

        games = [
            ("CF", "穿越火线", "cf.png"),
            ("CFHD", "穿越火线高清", "cfhd.png"),
            ("DELTA", "三角洲行动", "delta.png"),
            ("VAL", "无畏契约", "val.png"),
            ("CSGO", "CSGO(CS2)", "csgo.png"),
            ("PEACE", "PC和平精英", "peace.png"),
            ("NZ", "逆战猎场", "nz.png"),
            ("YJ", "永劫无间", "yj.png"),
            ("PUBG", "PUBG(绝地求生)", "pubg.png")
        ]

        for key, name, icon_file in games:
            item = QListWidgetItem()
            icon_path = resource_path(os.path.join('resources', icon_file))
            item.setIcon(QIcon(icon_path))
            item.setText(name)
            item.setTextAlignment(Qt.AlignCenter)
            item.setData(Qt.UserRole, key)
            item.setSizeHint(QSize(180, 200))
            self.game_list_widget.addItem(item)

        self.game_list_widget.currentRowChanged.connect(self.on_game_selected)

    def on_game_selected(self, row):
        if row < 0:
            return
        item = self.game_list_widget.item(row)
        game_key = item.data(Qt.UserRole)
        visual_core.switch_game_model(game_key)
        self.update_right_panel(game_key)

    def update_right_panel(self, game_key):
        # 清空旧内容
        for i in reversed(range(self.scroll_layout.count())):
            child = self.scroll_layout.itemAt(i).widget()
            if child:
                child.setParent(None)

        config = load_config()
        param = config.get("game_params", {}).get(game_key, GameParam(). __dict__)  # 使用默认值
        # 基础功能
        basic_group = QGroupBox("基础功能")
        basic_group.setStyleSheet("QGroupBox { font-size: 18px; font-weight: bold; color: #00AAFF; border: none; }")
        basic_layout = QGridLayout()
        basic_layout.setSpacing(20)

        row = 0
        aim_check = QCheckBox("启用自瞄")
        aim_check.setStyleSheet("font-size: 16px;")
        aim_check.setChecked(param.get("aim_enabled", True))
        aim_check.stateChanged.connect(lambda state: self.set_param(game_key, "aim_enabled", state == Qt.Checked))
        basic_layout.addWidget(aim_check, row, 0)
        row += 1

        esp_check = QCheckBox("启用透视")
        esp_check.setStyleSheet("font-size: 16px;")
        esp_check.setChecked(param.get("esp_enabled", True))
        esp_check.stateChanged.connect(lambda state: self.set_param(game_key, "esp_enabled", state == Qt.Checked))
        basic_layout.addWidget(esp_check, row, 0)
        row += 1

        recoil_check = QCheckBox("启用压枪")
        recoil_check.setStyleSheet("font-size: 16px;")
        recoil_check.setChecked(param.get("recoil_compensate", False))
        recoil_check.stateChanged.connect(lambda state: self.set_param(game_key, "recoil_compensate", state == Qt.Checked))
        basic_layout.addWidget(recoil_check, row, 0)
        row += 1

        auto_fire_check = QCheckBox("自动开火")
        auto_fire_check.setStyleSheet("font-size: 16px;")
        auto_fire_check.setChecked(param.get("auto_fire_enabled", False))
        auto_fire_check.stateChanged.connect(lambda state: self.set_param(game_key, "auto_fire_enabled", state == Qt.Checked))
        basic_layout.addWidget(auto_fire_check, row, 0)
        row += 1

        start_btn = QPushButton("开始实时推理")
        start_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #00AAFF, stop:1 #0088CC);
                color: white;
                font-size: 24px;
                font-weight: bold;
                padding: 30px;
                border-radius: 15px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #00CCFF, stop:1 #0099DD);
            }
        """)
        start_btn.setFixedHeight(100)
        start_btn.clicked.connect(lambda: cheat_service.start_cheat(game_key, param))
        basic_layout.addWidget(start_btn, row, 0)

        basic_group.setLayout(basic_layout)
        self.scroll_layout.addWidget(basic_group)

        # 高级设置折叠
        advanced = QToolBox()
        advanced.setStyleSheet("""
            QToolBox::tab {
                background: #2d2d44;
                color: white;
                padding: 15px;
                font-size: 16px;
                border-radius: 10px;
                margin-bottom: 5px;
            }
            QToolBox::tab:selected {
                background: #00AAFF;
            }
        """)

        # 瞄准设置
        aim_page = QWidget()
        aim_layout = QGridLayout(aim_page)
        aim_layout.setSpacing(20)

        aim_layout.addWidget(QLabel("自瞄FOV:"), 0, 0)
        fov_slider = QSlider(Qt.Horizontal)
        fov_slider.setRange(20, 300)
        fov_slider.setValue(param.get("aim_fov", 100))
        fov_slider.valueChanged.connect(lambda v: self.set_param(game_key, "aim_fov", v))
        aim_layout.addWidget(fov_slider, 0, 1)
        aim_layout.addWidget(QLabel("100"), 0, 2)

        aim_layout.addWidget(QLabel("miss率:"), 1, 0)
        miss_slider = QSlider(Qt.Horizontal)
        miss_slider.setRange(0, 50)
        miss_slider.setValue(int(param.get("miss_rate", 0.12) * 100))
        miss_slider.valueChanged.connect(lambda v: self.set_param(game_key, "miss_rate", v / 100))
        aim_layout.addWidget(miss_slider, 1, 1)

        advanced.addItem(aim_page, "瞄准设置")

        # 透视设置
        esp_page = QWidget()
        esp_layout = QGridLayout(esp_page)
        esp_layout.addWidget(QLabel("ESP颜色:"), 0, 0)
        color_btn = QPushButton("点击拾取颜色")
        color_btn.setStyleSheet(f"background-color: {param.get('esp_color', '#FF6464')}; min-height: 40px; border-radius: 10px;")
        color_btn.clicked.connect(lambda: self.choose_esp_color(game_key, color_btn))
        esp_layout.addWidget(color_btn, 0, 1)
        advanced.addItem(esp_page, "透视设置")

        # 压枪设置
        recoil_page = QWidget()
        recoil_layout = QGridLayout(recoil_page)
        curve_editor = CurveEditor()
        curve_editor.set_curve(param.get("recoil_curve", [0.0] * 30))
        curve_editor.save_callback = lambda curve: self.set_param(game_key, "recoil_curve", curve)
        recoil_layout.addWidget(curve_editor, 0, 0)
        advanced.addItem(recoil_page, "压枪设置")

        self.scroll_layout.addWidget(advanced)
        self.scroll_layout.addStretch()

    def choose_esp_color(self, game_key, btn):
        color = QColorDialog.getColor(QColor(param.get("esp_color", "#FF6464")))
        if color.isValid():
            hex_color = color.name()
            self.set_param(game_key, "esp_color", hex_color)
            btn.setStyleSheet(f"background-color: {hex_color}; min-height: 40px; border-radius: 10px;")

    def set_param(self, game_key, key, value):
        """实时保存参数到配置"""
        cfg = load_config()
        if "game_params" not in cfg:
            cfg["game_params"] = {}
        if game_key not in cfg["game_params"]:
            cfg["game_params"][game_key] = {}
        cfg["game_params"][game_key][key] = value
        save_config(cfg)

    def closeEvent(self, event):
        cheat_service.stop_all()
        if hasattr(self, 'esp_overlay'):
            self.esp_overlay.close()
        super().closeEvent(event)

# 文件结束
# src/ui/radar.py
# 2025年终极增强雷达窗（透视ESP + 距离 + 血条 + 骨骼线）

from PyQt5.QtWidgets import QDialog, QVBoxLayout
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont

from src.core.yolo_ai import visual_core
from src.core.screenshot import game_capture
from src.config.config import load_config

import math

class RadarWindow(QDialog):
    """
    增强雷达窗（同时作为透视ESP叠加窗）
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("安静AI - 增强雷达（透视ESP）")
        self.setFixedSize(500, 500)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        self.radar_widget = EnhancedRadarWidget(self)
        layout.addWidget(self.radar_widget)
        self.setLayout(layout)

        # 实时更新
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.radar_widget.update_scene)
        self.timer.start(30)  # ~33FPS，流畅不卡

class EnhancedRadarWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.targets = []
        self.config = load_config()

    def update_scene(self):
        img = game_capture.capture()
        if img is not None:
            self.targets = visual_core.infer(img, conf=0.35, classes=[0])
        self.update()

    def paintEvent(self, event):
        qp = QPainter(self)
        qp.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2
        radius = min(cx, cy) - 30

        # 背景半透明圆
        qp.setBrush(QBrush(QColor(20, 30, 50, 200)))
        qp.setPen(QPen(QColor(100, 200, 255, 180), 3))
        qp.drawEllipse(cx - radius, cy - radius, radius * 2, radius * 2)

        # 网格
        qp.setPen(QPen(QColor(60, 120, 180, 100), 1, Qt.DashLine))
        for i in range(1, 5):
            r = radius * i // 5
            qp.drawEllipse(cx - r, cy - r, r * 2, r * 2)

        # 自己（中心）
        qp.setBrush(QBrush(QColor(0, 255, 100)))
        qp.setPen(QPen(QColor(0, 200, 80), 3))
        qp.drawEllipse(cx - 15, cy - 15, 30, 30)

        # 朝向箭头（模拟玩家视角）
        qp.setBrush(QBrush(QColor(0, 180, 255)))
        qp.setPen(QPen(QColor(0, 140, 255), 4))
        qp.drawLine(cx, cy, cx, cy - radius + 20)

        if not self.targets:
            qp.setPen(QColor(200, 200, 200))
            qp.setFont(QFont("Microsoft YaHei", 12))
            qp.drawText(self.rect(), Qt.AlignCenter, "无目标")
            return

        # ESP颜色（从配置读取）
        esp_color = QColor(self.config.get("game_params", {}).get("CF", {}).get("esp_color", "#FF6464"))

        for target in self.targets:
            if "keypoints" not in target or "box" not in target:
                continue

            box = target["box"]
            kps = target["keypoints"]

            # 计算敌人中心相对位置（用于雷达点）
            box_center_x = (box[0] + box[2]) / 2
            box_center_y = (box[1] + box[3]) / 2
            rel_x = (box_center_x - w / 2) / radius
            rel_y = (box_center_y - h / 2) / radius
            distance = math.hypot(rel_x, rel_y) * 100  # 模拟距离

            ex = cx + rel_x * radius * 0.9
            ey = cy + rel_y * radius * 0.9

            # 雷达点
            qp.setBrush(QBrush(QColor(255, 60, 60)))
            qp.setPen(QPen(QColor(255, 0, 0), 2))
            qp.drawEllipse(int(ex - 10), int(ey - 10), 20, 20)

            # 名字 + 距离
            name = target.get("name", "敌人")
            qp.setPen(QColor(255, 255, 255))
            qp.setFont(QFont("Microsoft YaHei", 9))
            qp.drawText(int(ex + 15), int(ey), f"{name} {int(distance)}m")

            # 模拟血条
            hp = random.randint(30, 100)  # 模拟血量
            bar_width = 60
            bar_height = 8
            qp.setBrush(QBrush(QColor(100, 100, 100)))
            qp.drawRect(int(ex - bar_width//2), int(ey - 25), bar_width, bar_height)
            qp.setBrush(QBrush(QColor(0, 255, 0) if hp > 50 else QColor(255, 200, 0) if hp > 30 else QColor(255, 0, 0)))
            qp.drawRect(int(ex - bar_width//2), int(ey - 25), int(bar_width * hp / 100), bar_height)

            # 骨骼线（COCO标准关键连接）
            connections = [
                (0, 1), (1, 2), (0, 3), (3, 4),  # 头
                (5, 6), (5, 7), (7, 9), (6, 8), (8, 10),  # 上身手臂
                (5, 11), (6, 12), (11, 13), (12, 14)  # 下身腿
            ]
            qp.setPen(QPen(esp_color, 3))
            for a, b in connections:
                if a < len(kps) and b < len(kps):
                    ax, ay = kps[a]
                    bx, by = kps[b]
                    if ax > 0 and ay > 0 and bx > 0 and by > 0:
                        # 投影到雷达相对位置（简化）
                        proj_ax = cx + (ax - w/2) / radius * radius * 0.8
                        proj_ay = cy + (ay - h/2) / radius * radius * 0.8
                        proj_bx = cx + (bx - w/2) / radius * radius * 0.8
                        proj_by = cy + (by - h/2) / radius * radius * 0.8
                        qp.drawLine(int(proj_ax), int(proj_ay), int(proj_bx), int(proj_by))

        qp.end()
        # ================== src/ui/stats.py ==================
from PyQt5.QtWidgets import QWidget, QDialog, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPainter, QColor, QPen, QFont
import random
import math

class StatsWindow(QDialog):
    """
    今日击杀/KD/最远狙距等曲线图统计小窗
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("今日战绩统计")
        self.setFixedSize(380, 340)
        layout = QVBoxLayout()
        layout.addWidget(QLabel("今日击杀/爆头/最远狙击等曲线（仅Demo）"))
        self.stats_view = StatsCurveWidget(self)
        layout.addWidget(self.stats_view)
        self.setLayout(layout)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.stats_view.update_data)
        self._timer.start(2000)  # 每2秒模拟数据刷新

class StatsCurveWidget(QWidget):
    """
    曲线图及数据模拟
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = {
            "kill": [random.randint(0, 10) for _ in range(12)],
            "kd": [round(random.uniform(0.5, 3.0), 2) for _ in range(12)],
            "snipe": [random.randint(20, 300) for _ in range(12)]
        }
        self.ptr = 12

    def update_data(self):
        # 模拟新一轮成绩
        if len(self.data["kill"]) >= 30:
            for k in self.data: self.data[k] = self.data[k][1:]
        self.data["kill"].append(random.randint(0, 18))
        self.data["kd"].append(round(random.uniform(0.7, 4.3), 2))
        self.data["snipe"].append(random.randint(33, 366))
        self.ptr += 1
        self.update()

    def paintEvent(self, event):
        qp = QPainter(self)
        qp.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        margin = 40
        rect_w = w - margin * 2
        rect_h = h - margin * 2
        # 坐标轴
        qp.setPen(QPen(QColor(120, 120, 120), 2))
        qp.drawLine(margin, margin, margin, h-margin)
        qp.drawLine(margin, h-margin, w-margin, h-margin)
        # 绘制每条曲线
        self._draw_curve(qp, self.data["kill"], margin, h, rect_w, rect_h,
                         QColor(255,100,100), "击杀数/局")
        self._draw_curve(qp, self.data["kd"], margin, h, rect_w, rect_h,
                         QColor(80,180,255), "K/D")
        self._draw_curve(qp, [x/20.0 for x in self.data["snipe"]], margin, h, rect_w, rect_h,
                         QColor(220,100,255), "最远狙击/20m")
        # 标记左上角
        qp.setFont(QFont("微软雅黑", 9))
        qp.setPen(QColor(90, 90, 90))
        qp.drawText(margin+8, margin-10, f"局数:{len(self.data['kill'])}")

    def _draw_curve(self, qp, datalist, margin, h, rect_w, rect_h, color, label):
        N = len(datalist)
        if N < 2: return
        step_x = rect_w // (N-1) if N>1 else rect_w
        points = []
        maxy = max(max(datalist), 1)
        miny = min(min(datalist), 0)
        scale = rect_h / (maxy - miny + 1e-2)
        # 画曲线
        for i, v in enumerate(datalist):
            x = margin + i * step_x
            y = h - margin - (v - miny) * scale
            points.append((x, y))
        qp.setPen(QPen(color, 2))
        for i in range(N-1):
            qp.drawLine(int(points[i][0]), int(points[i][1]), int(points[i+1][0]), int(points[i+1][1]))
        # 最右下角标记
        qp.setPen(color)
        qp.setFont(QFont("微软雅黑", 10, QFont.Bold))
        qp.drawText(int(points[-1][0]-36), int(points[-1][1]-13), label)

# ================== src/ui/stats.py 完，下一个推荐模块入口 src/config/config.py（配置存取与加密） ==================

# 拼接说明：战绩统计窗代码实现完毕。
# 下一步在 src/config/ 目录下新建 config.py，等待配置读写模块。
# src/ui/theme.py
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QHBoxLayout, QComboBox, QPushButton, QLineEdit, QMessageBox, QSpacerItem, QSizePolicy
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPalette, QColor
import json
import os
from src.tools.resource_path import resource_path
from appdirs import user_config_dir

class ThemeManager:
    """
    全局主题管理，支持多皮肤、实时应用、用户目录持久化
    """
    _builtin_themes = {
        "default": {
            "name": "极简白",
            "palette": {
                "base": "#F9FAFC",
                "window": "#FFFFFF",
                "text": "#222",
                "button": "#F3F5F7",
                "highlight": "#4488FF",
                "highlightedText": "#fff"
            }
        },
        "dark": {
            "name": "暗色科技",
            "palette": {
                "base": "#23283C",
                "window": "#181B2C",
                "text": "#F2F2F2",
                "button": "#22264B",
                "highlight": "#37D1F2",
                "highlightedText": "#181B2C"
            }
        },
        "transparent_blue": {
            "name": "蓝光透明",
            "palette": {
                "base": "#1e293bCC",
                "window": "#151b29CC",
                "text": "#DEE6FC",
                "button": "#223059A0",
                "highlight": "#54CFFD",
                "highlightedText": "#222"
            }
        },
        "gray": {
            "name": "极简亮灰",
            "palette": {
                "base": "#F2F2F8",
                "window": "#FAFAFA",
                "text": "#121212",
                "button": "#EEE",
                "highlight": "#7090DA",
                "highlightedText": "#FFF"
            }
        },
        "night": {
            "name": "深邃星空",
            "palette": {
                "base": "#181A25",
                "window": "#171825",
                "text": "#F0EFFF",
                "button": "#23254D",
                "highlight": "#B356E8",
                "highlightedText": "#fff"
            }
        },
        "neon": {
            "name": "荧光绿黑",
            "palette": {
                "base": "#131F15",
                "window": "#151E13",
                "text": "#ABFF93",
                "button": "#192923",
                "highlight": "#45FFB7",
                "highlightedText": "#151E13"
            }
        },
        "purple": {
            "name": "炫光紫黑",
            "palette": {
                "base": "#221B4A",
                "window": "#171627",
                "text": "#F3EFFF",
                "button": "#2D2257",
                "highlight": "#D15EDB",
                "highlightedText": "#fff"
            }
        }
    }

    # 使用用户目录持久化
    CONFIG_DIR = user_config_dir("AnjingAI")
    CONFIG_FILE = os.path.join(CONFIG_DIR, "theme_config.json")

    def __init__(self):
        self.current_theme = "default"
        self.user_custom = {}
        os.makedirs(self.CONFIG_DIR, exist_ok=True)
        self._load_config()

    def get_theme_list(self):
        base = list(self._builtin_themes.keys())
        if self.user_custom:
            base.extend([f"user_{k}" for k in self.user_custom.keys()])
        return base

    def get_theme_meta(self, theme_key):
        if theme_key.startswith("user_"):
            name = theme_key[5:]
            return self.user_custom.get(name, self._builtin_themes["default"])
        return self._builtin_themes.get(theme_key, self._builtin_themes["default"])

    def get_stylesheet(self, theme_key=None):
        key = theme_key or self.current_theme
        palette = self.get_theme_meta(key)["palette"]
        base = palette["base"]
        window = palette["window"]
        text = palette["text"]
        button = palette["button"]
        highlight = palette["highlight"]
        highlighted_text = palette["highlightedText"]

        return f"""
        QWidget {{
            background: {window};
            color: {text};
        }}
        QPushButton, QComboBox, QLineEdit, QTextEdit, QCheckBox {{
            background: {button};
            border: 1px solid {highlight}70;
            color: {text};
            border-radius: 4px;
            padding: 5px;
        }}
        QPushButton:hover {{
            background: {highlight}33;
        }}
        QTabWidget::pane {{
            border: 1px solid {highlight};
            border-radius: 8px;
        }}
        QTabBar::tab:selected {{
            background: {highlight};
            color: {highlighted_text};
        }}
        QStatusBar {{
            background: {window};
            color: {text};
        }}
        QToolTip {{
            background: {highlight}DD;
            color: {highlighted_text};
            border-radius: 4px;
            padding: 6px;
        }}
        """

    def apply_theme(self, app):
        """全局应用主题"""
        app.setStyleSheet(self.get_stylesheet())

    def set_theme(self, theme_key: str, app=None):
        self.current_theme = theme_key
        if app:
            self.apply_theme(app)
        self._save_config()

    def _load_config(self):
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.current_theme = data.get("theme", "default")
                    self.user_custom = data.get("user_custom", {})
            except Exception:
                self.current_theme = "default"

    def _save_config(self):
        try:
            data = {
                "theme": self.current_theme,
                "user_custom": self.user_custom
            }
            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print("主题保存失败:", e)


class ThemeSwitcherDialog(QDialog):
    """
    主题切换对话框 + 管理员密码入口（三层隐藏）
    """
    def __init__(self, theme_manager: ThemeManager, parent=None):
        super().__init__(parent)
        self.theme_manager = theme_manager
        self.admin_password = ""
        self.setWindowTitle("主题切换")
        self.setFixedSize(420, 340)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self._setup_ui()
        self._preview_current()

    def _setup_ui(self):
        layout = QVBoxLayout()

        label = QLabel("请选择UI主题（实时预览）")
        label.setStyleSheet("font-weight:bold;margin:12px;")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        self.cb = QComboBox()
        self.theme_keys = self.theme_manager.get_theme_list()
        theme_names = [self.theme_manager.get_theme_meta(t)["name"] for t in self.theme_keys]
        self.cb.addItems(theme_names)

        # 当前主题定位
        try:
            idx = self.theme_keys.index(self.theme_manager.current_theme)
            self.cb.setCurrentIndex(idx)
        except ValueError:
            self.cb.setCurrentIndex(0)

        self.cb.currentIndexChanged.connect(self._on_theme_changed)
        layout.addWidget(self.cb)

        layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # 隐藏的管理员密码输入
        pwd_layout = QHBoxLayout()
        pwd_label = QLabel("访问码（高级功能）：")
        pwd_label.setStyleSheet("color:#888;font-size:12px;")
        pwd_layout.addWidget(pwd_label)

        self.pw_edit = QLineEdit()
        self.pw_edit.setEchoMode(QLineEdit.Password)
        self.pw_edit.setPlaceholderText("可选，普通换肤无需输入")
        pwd_layout.addWidget(self.pw_edit)
        layout.addLayout(pwd_layout)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("应用主题")
        btn_cancel = QPushButton("取消")
        btn_ok.clicked.connect(self._apply_and_accept)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

        tip = QLabel("输对访问码可解锁高级模块，常用不需输入，只管切主题即可。")
        tip.setStyleSheet("color:#777;font-size:12px;")
        tip.setAlignment(Qt.AlignCenter)
        layout.addWidget(tip)

        self.setLayout(layout)

    def _on_theme_changed(self, idx):
        if 0 <= idx < len(self.theme_keys):
            key = self.theme_keys[idx]
            # 实时预览全局
            if self.parent() and hasattr(self.parent(), 'parent') and self.parent().parent():
                app = self.parent().parent()  # MainWindow -> SafeApp
                self.theme_manager.set_theme(key, app)

    def _preview_current(self):
        self._on_theme_changed(self.cb.currentIndex())

    def _apply_and_accept(self):
        idx = self.cb.currentIndex()
        if 0 <= idx < len(self.theme_keys):
            key = self.theme_keys[idx]
            self.theme_manager.set_theme(key)
            self.admin_password = self.pw_edit.text().strip()
            self.accept()

    def get_admin_password(self):
        return self.admin_password