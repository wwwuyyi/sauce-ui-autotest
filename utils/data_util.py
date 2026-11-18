# -*- coding: utf-8 -*-
"""
data_util.py —— 测试数据工具（工具层）

职责：提供用例层共用的 YAML 数据访问辅助函数（商品表查询等），
     避免同一份映射逻辑在多份用例文件中复制漂移。

使用：from utils.data_util import get_product
"""
from utils.config_util import get_effective_config

# 环境配置（模块内独立副本；YamlUtil 文件缓存保证无重复 IO）
CONFIG = get_effective_config()


def get_product(product_id: int) -> dict:
    """按商品 id 从 YAML 商品表中取商品数据（返回 slug/name/price 等完整条目）

    :raises KeyError: products 表中不存在该 id 时抛出带中文说明的错误
    """
    for product in CONFIG["products"]:
        if product["id"] == product_id:
            return product
    raise KeyError(f"products 表中不存在 id={product_id} 的商品")