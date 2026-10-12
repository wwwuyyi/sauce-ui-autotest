# -*- coding: utf-8 -*-
"""
allure_util.py —— Allure 报告工具（工具层）

职责：提供与 Allure 报告相关的通用能力，供各模块用例层共用。

设计要点：
- 严重级别映射集中维护：YAML 数据里用字符串（blocker/critical/normal/minor），
  运行时统一转换为 allure 严重级别枚举，数据与代码解耦；
- 各用例模块无需重复编写映射字典，避免多份拷贝漂移。
"""
import allure

# 严重级别字符串 -> allure 严重级别枚举（数据驱动动态指定用例级别）
SEVERITY_MAP = {
    "blocker": allure.severity_level.BLOCKER,
    "critical": allure.severity_level.CRITICAL,
    "normal": allure.severity_level.NORMAL,
    "minor": allure.severity_level.MINOR,
}


def set_severity_from_str(level: str) -> None:
    """按字符串动态设置当前用例的严重级别（配合 pytest.mark.parametrize 数据驱动使用）"""
    allure.dynamic.severity(SEVERITY_MAP.get(level, allure.severity_level.NORMAL))


def attach_text(content: str, name: str = "附件") -> None:
    """向 Allure 报告附加文本附件（记录耗时/坐标/行为计数等软断言采样值）"""
    allure.attach(content, name, allure.attachment_type.TEXT)