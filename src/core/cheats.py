# src/core/cheats.py
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