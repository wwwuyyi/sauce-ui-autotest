# -*- coding: utf-8 -*-
"""
config_util.py —— 环境配置读取与环境变量覆写（工具层，唯一显式入口）

职责：全项目读取 env.yaml 的统一入口。相比直接使用 YamlUtil，本模块额外完成
环境变量覆写，并保证每次调用返回的是独立副本：

- WAIT_TIMEOUT=<数字>  -> timeout.explicit_wait 上浮；
  CI 环境未显式设置时默认上浮到 30s（GitHub Actions 等平台恒设 CI=true）。
- BASE_URL=<地址>      -> base_url 与 urls.* 中以原域名开头的地址同步替换。
- HEADLESS / RECORDING / EDGE_DRIVER_PATH：供 conftest 的 driver fixture 读取，
  以辅助函数形式集中在此，行为与历史内联实现完全一致。

由于覆写在读取时完成，模块级 CONFIG 不再依赖 conftest 的加载顺序；
又因为每次读取都返回深拷贝，任一模块/用例修改自己的配置都不会污染其他参与者。
"""
import os
from pathlib import Path

from utils.yaml_util import YamlUtil

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "env.yaml"


def get_effective_config(file_path=CONFIG_PATH) -> dict:
    """读取 env.yaml 并应用环境变量覆写，返回独立的完整配置副本"""
    config = YamlUtil().read_yaml(file_path)  # read_yaml 已返回深拷贝
    _apply_wait_timeout(config)
    _apply_base_url(config)
    return config


def _apply_wait_timeout(config: dict) -> None:
    """WAIT_TIMEOUT 数字优先；CI 环境未显式设置时全局等待上浮到 30s（本地保持 env.yaml）"""
    wait_timeout_env = (os.environ.get("WAIT_TIMEOUT") or "").strip()
    if wait_timeout_env.isdigit():
        config["timeout"]["explicit_wait"] = int(wait_timeout_env)
    elif os.environ.get("CI"):
        config["timeout"]["explicit_wait"] = 30


def _apply_base_url(config: dict) -> None:
    """BASE_URL 覆盖测试目标，并同步派生 urls 中所有同域地址（保留页面路径与参数）"""
    base_url_env = (os.environ.get("BASE_URL") or "").strip()
    if not base_url_env:
        return
    old_base = str(config["base_url"]).rstrip("/")
    new_base = base_url_env.rstrip("/")
    config["base_url"] = new_base + "/"
    for url_key, url_value in config.get("urls", {}).items():
        if isinstance(url_value, str) and url_value.startswith(old_base):
            config["urls"][url_key] = new_base + url_value[len(old_base):]


def is_headless(browser_conf: dict) -> bool:
    """HEADLESS=true/false 覆盖浏览器无头开关；未设置时取 env.yaml 的 headless"""
    headless_env = (os.environ.get("HEADLESS") or "").strip().lower()
    return headless_env == "true" if headless_env else browser_conf["headless"]


def is_recording_enabled(recording_conf: dict) -> bool:
    """RECORDING=false 关闭失败录屏线程；其余情况取 env.yaml 的 enabled 开关"""
    recording_env = (os.environ.get("RECORDING") or "").strip().lower()
    return recording_conf.get("enabled", True) and recording_env != "false"


def get_edge_driver_path() -> str:
    """EDGE_DRIVER_PATH 环境变量优先（返回空串表示 Selenium Manager 自动管理）"""
    return os.environ.get("EDGE_DRIVER_PATH") or ""
