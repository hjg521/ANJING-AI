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