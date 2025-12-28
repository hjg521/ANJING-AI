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

DEFAULT_MODEL = "yolov8n-pose.pt"  # 通用兜底模型