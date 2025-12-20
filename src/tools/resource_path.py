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