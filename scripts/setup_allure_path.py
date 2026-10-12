# -*- coding: utf-8 -*-
"""
setup_allure_path.py —— 将 Allure CLI 注册到当前用户的 PATH 环境变量

用途：本机安装 Allure Commandline 后执行一次，即可在任意新终端直接使用 allure 命令。
实现：直接通过 winreg 写入注册表 Environment 键（用户级 PATH），
      与系统"环境变量"设置面板效果完全一致；写完后广播 WM_SETTINGCHANGE
      通知系统刷新，新开的终端立即生效（当前已打开的终端需重启）。

执行方式：
    python scripts/setup_allure_path.py
"""
import ctypes
import winreg

# Allure CLI 的 bin 目录（本机最终安装位置：D 盘）
ALLURE_BIN = r"D:\tools\allure-2.46.1\bin"
# 历史安装位置前缀：注册时自动清理旧条目，避免 PATH 里残留失效路径
STALE_PATH_PREFIXES = (r"C:\Users\admin\tools",)
ENV_SUBKEY = "Environment"
WM_SETTINGCHANGE = 0x001A
HWND_BROADCAST = 0xFFFF


def _open_env_key():
    """打开用户级 Environment 注册表键（读写）"""
    return winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, ENV_SUBKEY, 0,
        winreg.KEY_READ | winreg.KEY_WRITE)


def _broadcast_env_change():
    """广播环境变量变更消息，使资源管理器与新终端感知新 PATH"""
    ctypes.windll.user32.SendMessageTimeoutW(
        HWND_BROADCAST, WM_SETTINGCHANGE, 0, ENV_SUBKEY, 0x0002, 5000, None)


def main():
    key = _open_env_key()
    try:
        current_path, _ = winreg.QueryValueEx(key, "Path")
    except FileNotFoundError:  # 该用户从未设置过 PATH
        current_path = ""
    winreg.CloseKey(key)

    segments = [seg for seg in current_path.split(";") if seg]

    # 1. 清理历史位置的失效条目
    cleaned = [seg for seg in segments
               if not seg.startswith(STALE_PATH_PREFIXES)]
    if len(cleaned) != len(segments):
        stale_removed = [seg for seg in segments if seg not in cleaned]
        print("[OK] 已从 PATH 清理历史条目: " + "; ".join(stale_removed))
        segments = cleaned

    # 2. 注册当前安装位置
    if ALLURE_BIN in segments:
        print("[OK] PATH 中已包含 Allure，无需重复注册")
        return

    new_path = ";".join(segments + [ALLURE_BIN])
    key = _open_env_key()
    winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path)
    winreg.CloseKey(key)
    _broadcast_env_change()
    print("[OK] 已写入用户 PATH: " + ALLURE_BIN)
    print("    提示：新开一个终端窗口，执行 allure --version 验证")


if __name__ == "__main__":
    main()