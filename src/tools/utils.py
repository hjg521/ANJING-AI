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