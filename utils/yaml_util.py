# -*- coding: utf-8 -*-
"""
yaml_util.py —— YAML 读取工具（工具层）

职责：全项目统一的 YAML 配置/数据读取入口。

设计要点：
- 单例模式：全局只有一个 YamlUtil 实例，配置只加载一次；
- 文件缓存：同一文件只解析一次，重复读取直接命中内存，测试执行零额外 IO；
- 相对路径自动归一化：传相对路径时统一基于项目根目录解析，
  无论从哪个目录启动 pytest 都能正确定位 config/env.yaml；
- safe_load 防注入：禁止 yaml.load 的任意对象反序列化风险；
- 异常友好化：文件不存在/解析失败/内容为空时抛出带中文说明的明确错误，
  而不是晦涩的底层 IO 异常堆栈。
"""
from pathlib import Path
from typing import Any

import yaml

# 项目根目录（本文件位于 utils/ 下，上级目录即项目根目录）
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class YamlUtil:
    """YAML 读取工具类（单例模式 + 文件缓存）"""

    _instance = None  # 单例实例

    def __new__(cls, *args, **kwargs):
        """单例实现：保证全局只有一个实例，配置/数据只加载一次"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # __init__ 每次构造都会被调用，需防止缓存被重复初始化清空
        if not hasattr(self, "_cache"):
            self._cache = {}

    def read_yaml(self, file_path) -> Any:
        """读取 YAML 文件并转换为 Python 对象（带缓存，重复读取直接命中内存）

        :param file_path: 文件路径（支持绝对路径或基于项目根目录的相对路径）
        :raises FileNotFoundError: 文件不存在（带中文说明）
        :raises ValueError: YAML 语法错误或内容为空（带中文说明）
        """
        path = Path(file_path)
        if not path.is_absolute():
            path = PROJECT_ROOT / path

        key = str(path.resolve())
        if key not in self._cache:  # 缓存未命中才真正打开文件解析
            if not path.exists():
                raise FileNotFoundError(
                    f"[数据层错误] YAML 文件不存在: {path}，请检查路径或先创建配置文件")
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self._cache[key] = yaml.safe_load(f)  # safe_load：安全解析，防注入
            except yaml.YAMLError as exc:
                raise ValueError(
                    f"[数据层错误] YAML 解析失败: {path}，请检查缩进/引号/中英文标点。"
                    f"原始错误: {exc}") from exc

        data = self._cache[key]
        if data is None:
            raise ValueError(f"[数据层错误] YAML 文件内容为空: {path}")
        return data

    def write_yaml(self, file_path, data) -> None:
        """将数据写回 YAML 文件（用于数据备份/动态调整场景）"""
        path = Path(file_path)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
        # 写回后使缓存失效，保证下次读取拿到最新内容
        self._cache.pop(str(path.resolve()), None)