# -*- coding: utf-8 -*-
"""
setup_local_env.py —— 注册本机私有环境变量（一次性脚本，不入库敏感信息）

用途：本机网络受限、Selenium Manager 无法自动下载 Edge 驱动时，
      将本地驱动路径注册为当前用户的 EDGE_DRIVER_PATH 环境变量，
      框架在运行期通过 os.environ 读取，仓库与提交内容零机器信息。

只在本机执行一次：
    python scripts/setup_local_env.py
"""
import ctypes
import winreg

# 本机私有值：Edge 驱动绝对路径（不在任何提交内容中出现）
EDGE_DRIVER_PATH = r"D:\tools\msedgedriver\msedgedriver.exe"
ENV_SUBKEY = "Environment"
WM_SETTINGCHANGE = 0x001A
HWND_BROADCAST = 0xFFFF


def _broadcast_env_change():
    """广播环境变量变更，使新启动的进程感知"""
    ctypes.windll.user32.SendMessageTimeoutW(
        HWND_BROADCAST, WM_SETTINGCHANGE, 0, ENV_SUBKEY, 0x0002, 5000, None)


def main():
    key = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, ENV_SUBKEY, 0,
        winreg.KEY_READ | winreg.KEY_WRITE)
    try:
        current, _ = winreg.QueryValueEx(key, "EDGE_DRIVER_PATH")
    except FileNotFoundError:
        current = None
    winreg.CloseKey(key)

    if current == EDGE_DRIVER_PATH:
        print("[OK] EDGE_DRIVER_PATH 已注册，无需重复操作")
        return

    key = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, ENV_SUBKEY, 0,
        winreg.KEY_READ | winreg.KEY_WRITE)
    winreg.SetValueEx(key, "EDGE_DRIVER_PATH", 0, winreg.REG_SZ, EDGE_DRIVER_PATH)
    winreg.CloseKey(key)
    _broadcast_env_change()
    print("[OK] 已注册用户环境变量 EDGE_DRIVER_PATH = " + EDGE_DRIVER_PATH)
    print("    提示：新开终端后 python -m pytest --browser=edge 即可生效")


if __name__ == "__main__":
    main()