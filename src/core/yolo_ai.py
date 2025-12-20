# src/core/yolo_ai.py
# 2025年最强YOLO视觉核心（ultralytics版 + pose骨骼一体 + 游戏专用模型自动切换）

import os
import threading
import torch
import numpy as np
from ultralytics import YOLO

from src.tools.resource_path import resource_path
from src.config.models import GAME_SPECIFIC_MODELS, DEFAULT_MODEL

class YOLOModelManager:
    """
    YOLO模型管理器（2025优化版）
    - 支持 ultralytics 官方所有最新模型
    - 默认使用 yolov8n-pose.pt（人框 + 骨骼点一体）
    - 支持游戏专用模型自动切换
    - CUDA半精度加速
    - 异步推理防卡顿
    """
    def __init__(self):
        self.current_game = None          # 当前游戏，如 "CF"
        self.current_model_name = None    # 当前加载的模型文件名
        self.model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_lock = threading.Lock()

        print(f"[YOLO] 使用设备: {self.device}")
        self.load_default_model()  # 启动时加载通用模型

    def load_default_model(self):
        """加载通用默认模型（所有游戏兜底）"""
        model_path = resource_path(os.path.join("models", DEFAULT_MODEL))
        if not os.path.exists(model_path):
            print(f"[YOLO] 警告：默认模型不存在 {model_path}，请放入 models 文件夹！")
            return

        print(f"[YOLO] 加载通用默认模型: {DEFAULT_MODEL}")
        with self.model_lock:
            self.model = YOLO(model_path)
            if self.device == "cuda":
                self.model.model.half()  # 半精度，大幅提速
        self.current_model_name = DEFAULT_MODEL

    def switch_game_model(self, game_key: str):
        """
        主界面切换游戏Tab时调用，自动加载专用模型
        game_key: "CF", "VAL", "CSGO" 等
        """
        if game_key == self.current_game:
            return  # 已加载，无需重复

        model_filename = GAME_SPECIFIC_MODELS.get(game_key.upper())
        if not model_filename:
            print(f"[YOLO] {game_key} 无专用模型配置，使用默认模型")
            self.current_game = game_key
            self.load_default_model()
            return

        model_path = resource_path(os.path.join("models", model_filename))
        if os.path.exists(model_path):
            print(f"[YOLO] 检测到 {game_key} 专用模型，加载: {model_filename}")
            with self.model_lock:
                self.model = YOLO(model_path)
                if self.device == "cuda":
                    self.model.model.half()
            self.current_model_name = model_filename
        else:
            print(f"[YOLO] 未找到专用模型 {model_filename}，回退默认模型")
            self.load_default_model()

        self.current_game = game_key

    def infer(self, image_np: np.ndarray, conf: float = 0.35, classes=None):
        """
        同步推理
        image_np: numpy array (H, W, C) BGR格式
        返回: list[dict] 包含 box, conf, cls, name, keypoints(若模型支持)
        """
        if self.model is None:
            print("[YOLO] 模型未加载，无法推理")
            return []

        # ultralytics推理
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

            # 如果是pose模型，添加17个骨骼点
            if keypoints is not None and i < len(keypoints):
                item["keypoints"] = keypoints[i].tolist()  # [[x,y], ...] 长度17

            output.append(item)

        return output

    def async_infer(self, image_np: np.ndarray, callback, conf: float = 0.35, classes=None):
        """
        异步推理（不卡顿主线程）
        callback: 函数，参数为 results list
        """
        def worker():
            try:
                results = self.infer(image_np, conf, classes)
                callback(results)
            except Exception as e:
                print(f"[YOLO] 异步推理异常: {e}")
                callback([])

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

# ============ 全局单例实例（所有模块共用） ============
visual_core = YOLOModelManager()