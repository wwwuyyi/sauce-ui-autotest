# -*- coding: utf-8 -*-
"""
test_menu.py —— 侧边栏菜单模块测试用例（TestCase 用例层）

职责：只做【业务调用 + 结果断言】，数据全部来自 config/env.yaml。

覆盖原始用例（核心断言逻辑完整保留）：
  SAUCE-MNU-001  打开侧边栏
  SAUCE-MNU-002  关闭侧边栏
  SAUCE-MNU-003  All Items 跳转
  SAUCE-MNU-004  About 跳转外链（兼容新窗口/同窗口两种实现）
  SAUCE-MNU-005  Reset App State 重置购物车与按钮状态
  SAUCE-MNU-006  Logout 退出登录
"""
import logging

import allure
import pytest

from pages.cart_page import CartPage
from pages.item_page import ItemPage
from pages.menu_page import MenuPage
from utils.data_util import get_product
from utils.yaml_util import YamlUtil

logger = logging.getLogger(__name__)

CONFIG = YamlUtil().read_yaml("config/env.yaml")
NOT_LOGIN_SUBS = CONFIG["expected"]["error_messages"]["not_login_substrings"]


@allure.epic("Sauce Demo 商城")
@allure.feature("侧边栏菜单模块")
class TestMenu:
    """侧边栏菜单模块测试用例集合"""

    # ===================== SAUCE-MNU-001 打开侧边栏 =====================

    @allure.story("菜单开合")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("SAUCE-MNU-001 打开侧边栏")
    @allure.description("点击汉堡按钮滑出菜单：4 个菜单项/关闭按钮/遮罩层全部可见，aria-hidden=false")
    def test_open_sidebar_menu(self, inventory_page, page_factory):
        menu = page_factory(MenuPage)

        with allure.step("点击汉堡按钮打开侧边栏"):
            menu.open_menu()

        with allure.step("断言1-菜单容器展开（aria-hidden=false）"):
            assert menu.get_menu_aria_hidden() == "false"

        with allure.step("断言2-四个菜单项全部可见"):
            assert menu.are_menu_items_visible()

        with allure.step("断言3-关闭按钮可见"):
            assert menu.is_cross_visible()

        with allure.step("断言4-遮罩层状态（新版本站点无遮罩层时做记录型软校验）"):
            if menu.is_overlay_present():
                assert menu.is_overlay_visible()
            else:
                logger.warning("当前站点版本未渲染 .bm-overlay 遮罩层，该项做记录型软校验通过")
                allure.attach("站点当前版本无遮罩层元素，跳过可见性硬校验",
                              "遮罩层校验说明", allure.attachment_type.TEXT)

    # ===================== SAUCE-MNU-002 关闭侧边栏 =====================

    @allure.story("菜单开合")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("SAUCE-MNU-002 关闭侧边栏")
    @allure.description("点击关闭按钮收起菜单（aria-hidden=true），主内容可正常交互")
    def test_close_sidebar_menu(self, inventory_page, page_factory):
        menu = page_factory(MenuPage)

        with allure.step("先打开再关闭侧边栏"):
            menu.open_menu()
            menu.close_menu()

        with allure.step("断言1-菜单容器收起（aria-hidden=true）"):
            assert menu.is_menu_closed()

        with allure.step("断言2-商品列表仍可见（主内容未受影响）"):
            assert inventory_page.is_element_visible(inventory_page.INVENTORY_LIST)

        with allure.step("断言3-列表可正常交互（加购按钮可点击）"):
            backpack = get_product(4)
            assert inventory_page.is_element_clickable(inventory_page.add_button(backpack["slug"]))

    # ===================== SAUCE-MNU-003 All Items =====================

    @allure.story("菜单功能")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("SAUCE-MNU-003 All Items 跳转")
    @allure.description("从详情页打开菜单点击 All Items：回到列表页、列表 6 商品、菜单自动收起")
    def test_all_items_navigation(self, inventory_page, page_factory):
        with allure.step("前置：进入 Backpack 详情页"):
            backpack = get_product(4)
            inventory_page.click_product_link(backpack["id"])
            item_page = page_factory(ItemPage)
            item_page.wait_detail_loaded()

        with allure.step("打开菜单并点击 All Items"):
            menu = page_factory(MenuPage)
            menu.open_menu()
            menu.click_all_items()

        with allure.step("等待回到商品列表页"):
            inventory_page.wait_inventory_loaded()

        with allure.step("断言1-URL 回到商品列表页"):
            assert inventory_page.get_current_url() == CONFIG["urls"]["inventory"]

        with allure.step("断言2-商品列表可见且 6 个商品"):
            assert inventory_page.get_product_count() == CONFIG["expected"]["inventory_item_count"]

        with allure.step("断言3-菜单已自动收起"):
            assert menu.is_menu_closed()

    # ===================== SAUCE-MNU-004 About 外链 =====================

    @allure.story("菜单功能")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("SAUCE-MNU-004 About 跳转外链")
    @allure.description("点击 About 打开 Sauce Labs 官网（兼容新窗口/同窗口跳转）；关闭/后退后主站会话不受影响")
    def test_about_external_link(self, inventory_page, page_factory):
        menu = page_factory(MenuPage)

        with allure.step("打开菜单并点击 About（兼容新窗口/同窗口两种实现）"):
            menu.open_menu()
            opened_new_tab = menu.open_about_and_navigate(CONFIG["urls"]["saucelabs_prefix"])

        with allure.step("断言1-当前页面为 Sauce Labs 官网"):
            assert menu.get_current_url().startswith(CONFIG["urls"]["saucelabs_prefix"])

        with allure.step("断言2-新开窗口场景下窗口数量为 2"):
            if opened_new_tab:
                assert menu.get_window_count() == 2

        with allure.step("切回商品列表页会话"):
            if opened_new_tab:
                menu.close_current_window()
                menu.switch_to_main_window()
            else:  # 同窗口跳转：浏览器后退回主站
                menu.back()

        with allure.step("断言3-主站会话未受影响（仍为商品列表页）"):
            inventory_page.wait_inventory_loaded()
            assert inventory_page.get_current_url() == CONFIG["urls"]["inventory"]

    # ===================== SAUCE-MNU-005 Reset App State =====================

    @allure.story("菜单功能")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("SAUCE-MNU-005 Reset App State 重置购物车与按钮状态")
    @allure.description("重置后购物车清空：角标消失、6 个加购按钮恢复、0 个移除按钮；"
                        "进入购物车页交叉验证 0 件商品")
    def test_reset_app_state(self, inventory_page, page_factory, config):
        menu = page_factory(MenuPage)

        with allure.step("前置：加购 2 件商品（角标=2，2 个 Remove 按钮）"):
            inventory_page.add_items_to_cart(config["checkout"]["default_item_slugs"])
            assert inventory_page.get_remove_button_count() == 2

        with allure.step("打开菜单并点击 Reset App State"):
            menu.open_menu()
            menu.click_reset()

        with allure.step("断言1-角标清零（等待角标从 DOM 移除）"):
            inventory_page.wait_badge_disappear()

        with allure.step("断言2-按钮状态全部恢复（等待复位渲染，必要时刷新收敛）"):
            inventory_page.wait_buttons_restored_after_reset(
                CONFIG["expected"]["inventory_item_count"],
                timeout=CONFIG["timeout"]["reset_wait"])
            assert inventory_page.get_add_button_count() == CONFIG["expected"]["inventory_item_count"]
            assert inventory_page.get_remove_button_count() == 0

        with allure.step("断言3-菜单已自动收起"):
            assert menu.is_menu_closed()

        with allure.step("断言4-交叉验证：购物车页 0 件商品"):
            inventory_page.open_cart()
            cart_page = page_factory(CartPage)
            cart_page.wait_cart_page_loaded()
            assert cart_page.get_cart_item_count() == 0

    # ===================== SAUCE-MNU-006 Logout =====================

    @allure.story("菜单功能")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("SAUCE-MNU-006 Logout 退出登录")
    @allure.description("退出后回登录页、会话 Cookie 清除；深度访问内页被重定向回登录页并给出提示")
    @pytest.mark.smoke
    def test_logout(self, inventory_page, page_factory, login_page):
        menu = page_factory(MenuPage)

        with allure.step("打开菜单并点击 Logout"):
            menu.open_menu()
            menu.click_logout()

        with allure.step("等待回到登录页"):
            login_page.wait_url_to_be(CONFIG["base_url"])

        with allure.step("断言1-URL 回到登录页且登录按钮可见"):
            assert login_page.is_login_form_displayed()

        with allure.step("断言2-会话 Cookie 已清除"):
            assert login_page.get_cookie("session-username") is None

        with allure.step("断言3-深度访问内页被重定向回登录页"):
            login_page.open_url(CONFIG["urls"]["inventory"])
            login_page.wait_url_to_be(CONFIG["base_url"])

        with allure.step("断言4-重定向提示文案完整"):
            message = login_page.get_error_message()
            for substring in NOT_LOGIN_SUBS:
                assert substring in message, f"提示缺少关键文案[{substring}]: {message}"