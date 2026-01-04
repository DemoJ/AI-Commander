import sys
import os

def resource_path(relative_path):
    """ 
    获取资源的绝对路径。
    用于解决 PyInstaller 打包后无法找到资源文件的问题。
    """
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller 打包后的临时目录
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)
