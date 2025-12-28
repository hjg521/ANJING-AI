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