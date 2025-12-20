# ================== src/tools/process_mask.py ==================
import sys
import os
import ctypes
import platform

class ProcessMasking:
    """
    进程/窗口名称伪装，简单防检测
    """
    @staticmethod
    def mask_process_name(new_name):
        """
        修改进程名称（部分操作系统和工具有效）
        """
        try:
            if platform.system() == "Windows":
                ctypes.windll.kernel32.SetConsoleTitleW(new_name)
            elif platform.system() == "Linux":
                sys.argv[0] = new_name
                try:
                    import setproctitle
                    setproctitle.setproctitle(new_name)
                except ImportError:
                    pass
            # macOS 支持类似方案
        except Exception as e:
            print(f"进程伪装失败: {e}")

    @staticmethod
    def mask_window_title(window, fake_title):
        """
        伪装主窗口窗体标题
        """
        try:
            window.setWindowTitle(fake_title)
        except Exception as e:
            print(f"窗口伪装失败: {e}")

    @staticmethod
    def mask_process_info(fake_name=None, fake_desc=None):
        """
        伪装自身进程信息（如exe描述、公司名等，需pe属性编辑/打包阶段处理）
        """
        pass  # 打包时处理，运行时能修改有限（高级版见pyinstaller资源替换）

def is_running_under_virtual_machine():
    """
    检测是否在虚拟机/沙箱中运行
    """
    # Demo: 简单根据部分虚拟机硬件/驱动特征
    suspect_names = [
        "VBOX", "VMWARE", "QEMU", "VIRTUAL", "SANDBOX"
    ]
    raw = (os.environ.get("PROCESSOR_IDENTIFIER","") + os.environ.get("COMPUTERNAME","")).upper()
    for name in suspect_names:
        if name in raw: return True
    return False

# ================== src/tools/process_mask.py 完，所有主干代码及目录已结束 ==================

# 拼接提示：核心目录和代码已生成完毕！