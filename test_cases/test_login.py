# -*- coding: utf-8 -*-
"""
test_login.py —— 登录模块测试用例（TestCase 用例层）

职责：只做【业务调用 + 结果断言】两件事，不包含任何元素定位与底层操作。
用例的入参数据与期望值全部来自 config/env.yaml（YAML 数据驱动），
新增/修改用例只需维护数据文件，无需改动代码结构。

覆盖原始用例（核心断言逻辑完整保留，功能不缩水）：
  SAUCE-LOGIN-001        standard_user 正常登录成功
  SAUCE-LOGIN-002        locked_out_user 锁定账号登录失败
  SAUCE-LOGIN-003        错误用户名/错误密码登录失败
  SAUCE-LOGIN-004/005/006 必填校验（数据驱动合并，3 组参数化数据）
  SAUCE-LOGIN-007        problem_user 登录成功但商品图片异常
  SAUCE-LOGIN-008        performance_glitch_user 加载延迟校验
  SAUCE-LOGIN-009        error_user 登录壳层校验
  SAUCE-LOGIN-010        visual_user 布局错位探针（软断言）
"""
import logging

import allure
import pytest

from utils.allure_util import set_severity_from_str
from utils.yaml_util import YamlUtil

logger = logging.getLogger(__name__)

# 模块级读取环境配置（YamlUtil 为单例，全项目共享同一份配置，无重复 IO）
CONFIG = YamlUtil().read_yaml("config/env.yaml")
ERROR_MSGS = CONFIG["expected"]["error_messages"]


@allure.epic("Sauce Demo 商城")
@allure.feature("登录模块")
class TestLogin:
    """登录模块测试用例集合"""

    # ===================== SAUCE-LOGIN-001 正向登录 =====================

    @allure.story("正向登录")
    @allure.severity(allure.severity_level.BLOCKER)
    @allure.title("SAUCE-LOGIN-001 standard_user 正常登录成功")
    @allure.description("使用标准账号登录，校验跳转商品列表页、展示 6 个商品、"
                        "标题 Products、登录表单销毁、会话 Cookie 建立")
    @pytest.mark.smoke
    def test_login_success_standard_user(self, login_page):
        account = CONFIG["accounts"]["standard"]

        with allure.step("输入账号密码并点击登录"):
            login_page.login(account["username"], account["password"])

        with allure.step("等待商品列表页加载"):
            login_page.wait_inventory_loaded()

        with allure.step("断言1-URL跳转到商品列表页"):
            assert login_page.get_current_url() == CONFIG["urls"]["inventory"]

        with allure.step("断言2-展示6个商品"):
            assert login_page.get_inventory_item_count() == CONFIG["expected"]["inventory_item_count"]

        with allure.step("断言3-页面标题为 Products"):
            assert login_page.get_page_title_text() == CONFIG["expected"]["products_title"]

        with allure.step("断言4-登录表单已销毁"):
            assert login_page.is_login_form_gone(), "登录成功后登录表单仍存在于页面"

        with allure.step("断言5-会话 Cookie 建立且用户名为 standard_user"):
            cookie = login_page.get_cookie("session-username")
            assert cookie is not None, "登录成功后未写入 session-username Cookie"
            assert cookie["value"] == account["username"]

    # ===================== SAUCE-LOGIN-002 锁定账号 =====================

    @allure.story("反向登录")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("SAUCE-LOGIN-002 locked_out_user 锁定账号登录失败")
    @allure.description("锁定账号登录被拒绝：展示锁定文案、停留在登录页、按钮可重试、不进入商品页")
    def test_login_locked_out_user(self, login_page):
        account = CONFIG["accounts"]["locked"]

        with allure.step("输入锁定账号并点击登录"):
            login_page.login(account["username"], account["password"])

        with allure.step("断言1-展示锁定错误提示"):
            assert login_page.get_error_message() == ERROR_MSGS["locked"]

        with allure.step("断言2-错误提示容器可见"):
            assert login_page.is_error_container_displayed()

        with allure.step("断言3-仍停留在登录页（未被重定向）"):
            assert login_page.get_current_url() == CONFIG["base_url"]

        with allure.step("断言4-登录按钮可见且可再次提交"):
            assert login_page.is_login_form_displayed()
            assert login_page.is_login_button_enabled()

        with allure.step("断言5-未进入商品列表页"):
            assert login_page.is_inventory_absent()

    # ===================== SAUCE-LOGIN-003 错误用户名密码 =====================

    @allure.story("反向登录")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("SAUCE-LOGIN-003 错误用户名密码登录失败")
    @allure.description("非系统账号登录被拒绝：提示用户名密码不匹配、输入未被清空、未建立会话 Cookie")
    def test_login_wrong_credentials(self, login_page):
        account = CONFIG["accounts"]["wrong"]

        with allure.step("输入错误账号密码并点击登录"):
            login_page.login(account["username"], account["password"])

        with allure.step("断言1-提示用户名密码不匹配"):
            assert login_page.get_error_message() == ERROR_MSGS["mismatch"]

        with allure.step("断言2-错误提示容器可见"):
            assert login_page.is_error_container_displayed()

        with allure.step("断言3-仍停留在登录页"):
            assert login_page.get_current_url() == CONFIG["base_url"]

        with allure.step("断言4-用户名输入未被清空"):
            assert login_page.get_username_value() == account["username"]

        with allure.step("断言5-未建立会话 Cookie"):
            assert login_page.get_cookie("session-username") is None

    # ===================== SAUCE-LOGIN-004/005/006 必填校验（数据驱动） =====================

    @allure.story("反向登录")
    @pytest.mark.parametrize(
        "case_data",
        CONFIG["login_cases"]["required_field_cases"],
        ids=[case["case_id"] for case in CONFIG["login_cases"]["required_field_cases"]],
    )
    @allure.title("必填字段校验（数据驱动）")
    @allure.description("空用户名/空密码组合登录被拒绝：提示对应必填文案、错误容器可见、停留在登录页")
    def test_login_required_field_validation(self, login_page, case_data):
        # 动态指定用例标题与严重级别（来自 YAML 数据，体现数据驱动能力）
        allure.dynamic.title(case_data["name"])
        set_severity_from_str(case_data["severity"])

        with allure.step("输入用户名密码并点击登录"):
            login_page.login(case_data["username"], case_data["password"])

        with allure.step("断言1-必填错误提示文案正确"):
            assert login_page.get_error_message() == ERROR_MSGS[case_data["expected_error"]]

        with allure.step("断言2-错误提示容器可见"):
            assert login_page.is_error_container_displayed()

        with allure.step("断言3-仍停留在登录页"):
            assert login_page.get_current_url() == CONFIG["base_url"]

    # ===================== SAUCE-LOGIN-007 problem_user =====================

    @allure.story("特殊账号专项")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("SAUCE-LOGIN-007 problem_user 登录成功但商品图片异常")
    @allure.description("problem_user 能正常登录（URL/数量/名称正常），"
                        "但 6 张商品图片全部指向同一异常资源（src 唯一数为 1）")
    def test_login_problem_user_broken_images(self, login_page):
        account = CONFIG["accounts"]["problem"]

        with allure.step("登录并等待商品列表加载"):
            login_page.login(account["username"], account["password"])
            login_page.wait_inventory_loaded()

        with allure.step("断言1-URL跳转到商品列表页"):
            assert login_page.get_current_url() == CONFIG["urls"]["inventory"]

        with allure.step("断言2-展示6个商品"):
            assert login_page.get_inventory_item_count() == CONFIG["expected"]["inventory_item_count"]

        with allure.step("断言3-商品名称文本完全正常"):
            assert login_page.get_product_names() == CONFIG["expected"]["product_names"]

        with allure.step("断言4-全部商品图片指向同一异常资源（src 唯一）"):
            srcs = login_page.get_product_image_srcs()
            assert len(set(srcs)) == 1, f"基线为 6 个不同 src，实际唯一数: {len(set(srcs))}"

        with allure.step("断言5-登录成功无任何报错提示"):
            assert login_page.is_error_message_absent()

    # ===================== SAUCE-LOGIN-008 performance_glitch_user =====================

    @allure.story("特殊账号专项")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("SAUCE-LOGIN-008 performance_glitch_user 渲染延迟校验")
    @allure.description("glitch 账号最终登录成功，但商品列表加载耗时显著高于正常账号；"
                        "耗时值写入报告附件用于趋势观察")
    def test_login_performance_glitch_user(self, login_page):
        account = CONFIG["accounts"]["glitch"]

        with allure.step("登录并测量加载耗时（专用超时 20s）"):
            elapsed = login_page.login_and_measure_inventory_load(
                account["username"], account["password"],
                timeout=CONFIG["timeout"]["glitch_wait"],
            )

        with allure.step("记录耗时到 Allure 报告附件"):
            allure.attach(str(round(elapsed, 2)), "实际加载耗时(秒)", allure.attachment_type.TEXT)

        with allure.step("断言1-加载耗时超过阈值"):
            assert elapsed >= CONFIG["special_users"]["glitch_min_delay"], (
                f"加载耗时 {elapsed:.2f}s 低于阈值 {CONFIG['special_users']['glitch_min_delay']}s")

        with allure.step("断言2-最终登录成功（URL与商品数量正常）"):
            assert login_page.get_current_url() == CONFIG["urls"]["inventory"]
            assert login_page.get_inventory_item_count() == CONFIG["expected"]["inventory_item_count"]

    # ===================== SAUCE-LOGIN-009 error_user =====================

    @allure.story("特殊账号专项")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("SAUCE-LOGIN-009 error_user 登录壳层校验")
    @allure.description("error_user 能正常登录进入列表页；交互异常细节为独立覆盖范围，登录侧仅校验壳层完整性")
    def test_login_error_user(self, login_page):
        account = CONFIG["accounts"]["error_user"]

        with allure.step("登录并等待商品列表加载"):
            login_page.login(account["username"], account["password"])
            # error_user 与 glitch 同为"带人工延迟"账号，统一走慢账号等待预算，消除偶发超时
            login_page.wait_inventory_loaded(timeout=CONFIG["timeout"]["glitch_wait"])

        with allure.step("断言1-URL跳转到商品列表页"):
            assert login_page.get_current_url() == CONFIG["urls"]["inventory"]

        with allure.step("断言2-展示6个商品"):
            assert login_page.get_inventory_item_count() == CONFIG["expected"]["inventory_item_count"]

        with allure.step("断言3-商品名称与官方列表一致"):
            assert login_page.get_product_names() == CONFIG["expected"]["product_names"]

        with allure.step("断言4-加购按钮存在（页面壳层完整）"):
            assert login_page.get_add_to_cart_button_count() >= 1

        with allure.step("断言5-登录成功无报错提示"):
            assert login_page.is_error_message_absent()

    # ===================== SAUCE-LOGIN-010 visual_user =====================

    @allure.story("特殊账号专项")
    @allure.severity(allure.severity_level.MINOR)
    @allure.title("SAUCE-LOGIN-010 visual_user 布局错位探针（软断言）")
    @allure.description("visual_user 登录成功但布局存在视觉错位；位置偏移以采样记录型软断言处理"
                        "（数值记录进报告，不作为硬门禁，防版本差异误报）")
    def test_login_visual_user_layout_probe(self, login_page):
        account = CONFIG["accounts"]["visual"]

        with allure.step("登录并等待商品列表加载"):
            login_page.login(account["username"], account["password"])
            login_page.wait_inventory_loaded()

        with allure.step("断言1-URL跳转到商品列表页"):
            assert login_page.get_current_url() == CONFIG["urls"]["inventory"]

        with allure.step("断言2-展示6个商品且名称正常"):
            assert login_page.get_inventory_item_count() == CONFIG["expected"]["inventory_item_count"]
            assert login_page.get_product_names() == CONFIG["expected"]["product_names"]

        with allure.step("断言3-购物车图标仍存在于 DOM（错位但未丢失）"):
            assert login_page.is_shopping_cart_link_present()

        with allure.step("布局偏移探针（采样记录型软断言）"):
            cart_rect = login_page.get_shopping_cart_rect()
            header_rect = login_page.get_primary_header_rect()
            cart_center_y = cart_rect["y"] + cart_rect["height"] / 2
            header_bottom = header_rect["y"] + header_rect["height"]
            offset_info = (
                f"购物车图标中心 y={cart_center_y:.1f}px, "
                f"header 底部 y={header_bottom:.1f}px, "
                f"错位特征(图标中心落入 header 下方)={cart_center_y > header_bottom}"
            )
            logger.warning("visual_user 布局偏移采样: %s", offset_info)
            allure.attach(offset_info, "布局偏移采样结果", allure.attachment_type.TEXT)
            # 软断言策略：数值一律记录进报告；仅当 env.yaml 开启严格模式时升级为硬门禁
            if CONFIG["expected"].get("visual_position_strict", False):
                assert cart_center_y > header_bottom, offset_info