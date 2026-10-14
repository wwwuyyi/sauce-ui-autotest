# -*- coding: utf-8 -*-
"""
test_special_users.py —— 边界与异常（特殊账号专项）测试用例（TestCase 用例层）

职责：只做【业务调用 + 结果断言】，数据全部来自 config/env.yaml。

重要约定（《自动化执行注意事项》§3）：
- 特殊账号用例在同一测试内按需多次真实 UI 登录，per-test 独立 driver，互不污染；
- "行为差异"类用例断言的是"与标准基线存在可测差异"（如加购成功数<6、排序未生效），
  不写死具体失效商品，防版本差异误报；
- 耗时/坐标/行为计数的采样值一律写进 Allure 报告附件，便于趋势观察。

覆盖原始用例（核心断言逻辑完整保留）：
  SAUCE-SPC-001  performance_glitch_user 加载延迟阈值校验（绝对+相对基线）
  SAUCE-SPC-002  visual_user 视觉异常校验（图片正常+位置偏移容忍）
  SAUCE-SPC-003  error_user 交互异常校验（行为不一致性断言）
  SAUCE-SPC-004  problem_user 图片资源与排序异常校验
"""
import logging
from decimal import Decimal

import allure

from pages.inventory_page import InventoryPage
from pages.menu_page import MenuPage
from utils.allure_util import attach_text
from utils.yaml_util import YamlUtil

logger = logging.getLogger(__name__)

CONFIG = YamlUtil().read_yaml("config/env.yaml")
SPECIAL = CONFIG["special_users"]


def _expected_prices(prices_key: str) -> list:
    """期望价格序列转换为 Decimal 列表"""
    return [Decimal(price.replace("$", ""))
            for price in CONFIG["sort_expected"][prices_key]]


def _login_as(login_page, page_factory, account_key: str):
    """以指定账号真实 UI 登录，返回已加载的 InventoryPage（登录被拒自动重试）"""
    account = CONFIG["accounts"][account_key]
    # 特殊账号（error_user/glitch）带人工渲染延迟：统一使用慢账号等待预算，消除偶发超时
    login_page.login_and_wait_inventory(
        account["username"], account["password"],
        timeout=CONFIG["timeout"]["glitch_wait"])
    return page_factory(InventoryPage)


def _logout(login_page, page_factory):
    """通过侧边栏菜单退出登录，返回登录页"""
    menu = page_factory(MenuPage)
    menu.open_menu()
    menu.click_logout()
    login_page.wait_url_to_be(CONFIG["base_url"])
    assert login_page.is_login_form_displayed(), "退出登录后未回到登录页"
    return login_page


@allure.epic("Sauce Demo 商城")
@allure.feature("边界与异常模块")
class TestSpecialUsers:
    """特殊账号专项测试用例集合"""

    # ===================== SAUCE-SPC-001 glitch 延迟校验 =====================

    @allure.story("特殊账号专项")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("SAUCE-SPC-001 performance_glitch_user 加载延迟阈值校验")
    @allure.description("同批次采集 standard_user 基线耗时，glitch 账号耗时满足绝对阈值与相对基线")
    def test_glitch_user_latency(self, login_page, page_factory):
        standard_account = CONFIG["accounts"]["standard"]
        glitch_account = CONFIG["accounts"]["glitch"]

        with allure.step("采集基线：standard_user 登录加载耗时"):
            t_base = login_page.login_and_measure_inventory_load(
                standard_account["username"], standard_account["password"])

        with allure.step("退出并切换 glitch 账号登录计时"):
            _logout(login_page, page_factory)
            t_glitch = login_page.login_and_measure_inventory_load(
                glitch_account["username"], glitch_account["password"],
                timeout=CONFIG["timeout"]["glitch_wait"])

        with allure.step("耗时采样值写入报告附件"):
            attach_text(f"基线耗时={t_base:.2f}s，glitch 耗时={t_glitch:.2f}s", "加载耗时采样")

        with allure.step("断言1-绝对阈值校验（>= 3.0s）"):
            assert t_glitch >= SPECIAL["glitch_min_delay"], (
                f"glitch 耗时 {t_glitch:.2f}s 低于绝对阈值 {SPECIAL['glitch_min_delay']}s")

        with allure.step("断言2-相对基线校验（>= 2 × 基线）"):
            assert t_glitch >= SPECIAL["glitch_relative_factor"] * t_base, (
                f"glitch 耗时 {t_glitch:.2f}s 未达到基线 {t_base:.2f}s 的 "
                f"{SPECIAL['glitch_relative_factor']} 倍")

        with allure.step("断言3-最终登录成功（最终态正常）"):
            assert login_page.get_current_url() == CONFIG["urls"]["inventory"]
            assert page_factory(InventoryPage).get_product_count() == CONFIG["expected"]["inventory_item_count"]

    # ===================== SAUCE-SPC-002 visual_user 偏移 =====================

    @allure.story("特殊账号专项")
    @allure.severity(allure.severity_level.MINOR)
    @allure.title("SAUCE-SPC-002 visual_user 视觉异常校验（图片+位置偏移）")
    @allure.description("图片本身正常加载，购物车图标位置相对 standard_user 基线存在可测偏移；采样记录型软断言")
    def test_visual_user_layout_offset(self, login_page, page_factory):
        with allure.step("采集基线：standard_user 登录并记录购物车图标坐标"):
            base_page = _login_as(login_page, page_factory, "standard")
            base_cart = base_page.get_shopping_cart_rect()
            base_x, base_y = base_cart["x"], base_cart["y"]

        with allure.step("切换 visual_user 登录并采集坐标"):
            _logout(login_page, page_factory)
            visual_page = _login_as(login_page, page_factory, "visual")
            visual_cart = visual_page.get_shopping_cart_rect()

        dx, dy = abs(visual_cart["x"] - base_x), abs(visual_cart["y"] - base_y)
        offset_info = (
            f"基线: x={base_x}, y={base_y} | visual_user: "
            f"x={visual_cart['x']}, y={visual_cart['y']} | "
            f"偏移: dx={dx}px, dy={dy}px "
            f"(阈值 x>{SPECIAL['visual_offset']['x']} 或 y>{SPECIAL['visual_offset']['y']})"
        )
        with allure.step("偏移采样值写入报告附件"):
            logger.warning("visual_user 布局偏移采样: %s", offset_info)
            attach_text(offset_info, "布局偏移采样结果")

        with allure.step("等待 visual_user 商品图片完成解码"):
            visual_page.wait_product_images_loaded()

        with allure.step("断言1-图片本身正常加载（naturalWidth>0）"):
            assert all(width > 0 for width in visual_page.get_image_natural_widths())

        with allure.step("断言2-购物车图标存在（错位但未丢失）且列表完整"):
            assert visual_page.is_cart_link_present()
            assert visual_page.get_product_count() == CONFIG["expected"]["inventory_item_count"]

        with allure.step("断言3-存在可测位置偏移（软断言，可配置开关升级硬门禁）"):
            offset_detected = (dx > SPECIAL["visual_offset"]["x"]
                               or dy > SPECIAL["visual_offset"]["y"])
            if SPECIAL["visual_offset_strict"]:
                assert offset_detected, offset_info
            else:
                logger.warning("布局偏移探针为采样记录型软断言，检测结果: %s", offset_detected)

    # ===================== SAUCE-SPC-003 error_user 交互异常 =====================

    @allure.story("特殊账号专项")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("SAUCE-SPC-003 error_user 交互异常校验（行为不一致性断言）")
    @allure.description("逐一点击 6 个加购按钮统计行为差异：实际成功加购数 < 6（基线 6/6）；hilo 排序失效")
    def test_error_user_interaction_anomaly(self, login_page, page_factory):
        click_logs = []

        with allure.step("登录并等待商品列表加载"):
            inventory_page = _login_as(login_page, page_factory, "error_user")
            assert inventory_page.get_current_url() == CONFIG["urls"]["inventory"]

        with allure.step("逐一点击 6 个加购按钮并记录按钮态"):
            for product in CONFIG["products"]:
                inventory_page.click_add_button(product["slug"])
                removed_now = inventory_page.get_remove_button_count()
                click_logs.append(f"{product['name']}: remove数={removed_now}")

        with allure.step("行为差异明细写入报告附件"):
            attach_text("\n".join(click_logs), "加购行为差异明细")

        with allure.step("断言1-实际加购成功数 < 6（基线 standard_user 为 6/6）"):
            added_count = inventory_page.get_remove_button_count()
            assert added_count < SPECIAL["error_user_max_added"], (
                f"error_user 加购成功数 {added_count}，应小于基线 {SPECIAL['error_user_max_added']}")

        with allure.step("断言2-角标计数与按钮态一致（< 6）"):
            badge_text = inventory_page.get_badge_text_or_empty()
            badge_number = int(badge_text) if badge_text.strip().isdigit() else 0
            assert badge_number < SPECIAL["error_user_max_added"]

        with allure.step("选择价格降序并容忍站点异常弹窗"):
            inventory_page.sort_and_tolerate_alert("hilo")

        with allure.step("断言3-hilo 排序失效（未按期望顺序排列），记录实际顺序"):
            actual_prices = inventory_page.get_price_numbers()
            attach_text(str([str(p) for p in actual_prices]), "hilo 实际价格顺序")
            assert actual_prices != _expected_prices("hilo_prices"), (
                "error_user 排序竟然按期望顺序生效，需重新评估账号特性")

        with allure.step("断言4-登录壳层正常（6 商品）"):
            assert inventory_page.get_product_count() == CONFIG["expected"]["inventory_item_count"]

    # ===================== SAUCE-SPC-004 problem_user 图片+排序异常 =====================

    @allure.story("特殊账号专项")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("SAUCE-SPC-004 problem_user 图片资源与排序异常校验")
    @allure.description("全部商品图片指向同一异常资源（src 唯一数为 1），lohi 排序失效，文本数据健在")
    def test_problem_user_broken_images_and_sort(self, login_page, page_factory):
        with allure.step("登录并等待商品列表加载"):
            inventory_page = _login_as(login_page, page_factory, "problem")
            assert inventory_page.get_current_url() == CONFIG["urls"]["inventory"]

        with allure.step("断言1-全部图片指向同一异常资源（src 唯一数为 1）"):
            srcs = inventory_page.get_product_image_srcs()
            attach_text("\n".join(sorted(set(srcs))), "图片 src 集合")
            assert len(set(srcs)) == 1, (
                f"基线 standard_user 为 6 个唯一 src，实际唯一数: {len(set(srcs))}")

        with allure.step("选择价格升序并等待可能的排序响应"):
            inventory_page.sort_and_wait_settle("lohi", CONFIG["expected"]["product_names"])

        with allure.step("断言2-lohi 排序失效（未按期望顺序排列），记录实际顺序"):
            actual_prices = inventory_page.get_price_numbers()
            attach_text(str([str(p) for p in actual_prices]), "lohi 实际价格顺序")
            assert actual_prices != _expected_prices("lohi_prices")

        with allure.step("断言3-商品名称文本仍与官方列表一致（文本数据健在）"):
            assert inventory_page.get_product_names() == CONFIG["expected"]["product_names"]

        with allure.step("断言4-列表可见且 6 个商品"):
            assert inventory_page.get_product_count() == CONFIG["expected"]["inventory_item_count"]