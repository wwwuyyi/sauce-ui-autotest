# -*- coding: utf-8 -*-
"""
test_common.py —— 页面通用场景模块测试用例（TestCase 用例层）

职责：只做【业务调用 + 结果断言】，数据全部来自 config/env.yaml。

覆盖原始用例（核心断言逻辑完整保留）：
  SAUCE-COM-001  浏览器刷新后状态与登录态保持
  SAUCE-COM-002  浏览器前进/后退导航
  SAUCE-COM-003  会话失效/未登录直接访问内部页面（重定向校验，4 组参数化 URL）
"""
import logging

import allure
import pytest

from pages.item_page import ItemPage
from utils.data_util import get_product
from utils.yaml_util import YamlUtil

logger = logging.getLogger(__name__)

CONFIG = YamlUtil().read_yaml("config/env.yaml")
NOT_LOGIN_SUBS = CONFIG["expected"]["error_messages"]["not_login_substrings"]


@allure.epic("Sauce Demo 商城")
@allure.feature("页面通用场景模块")
class TestCommon:
    """页面通用场景模块测试用例集合"""

    # ===================== SAUCE-COM-001 刷新保持 =====================

    @allure.story("浏览器行为")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("SAUCE-COM-001 浏览器刷新后状态与登录态保持")
    @allure.description("刷新后回到商品列表页：登录态与购物车状态（角标/按钮）保持，Cookie 仍存在")
    def test_refresh_keeps_state(self, inventory_page, config):
        with allure.step("前置：加购 2 件商品（角标=2）"):
            inventory_page.add_items_to_cart(config["checkout"]["default_item_slugs"])

        with allure.step("刷新页面并等待列表重新加载"):
            inventory_page.refresh()
            inventory_page.wait_inventory_loaded()

        with allure.step("断言1-刷新后仍在商品列表页"):
            assert inventory_page.get_current_url() == CONFIG["urls"]["inventory"]

        with allure.step("断言2-列表重新可见"):
            assert inventory_page.is_element_visible(inventory_page.INVENTORY_LIST)

        with allure.step("断言3-角标状态保持（重新定位后仍为 2）"):
            inventory_page.wait_badge_text("2")
            assert inventory_page.get_badge_text() == "2"

        with allure.step("断言4-移除按钮状态保持（2 个 remove 按钮仍在）"):
            assert inventory_page.get_remove_button_count() == 2

        with allure.step("断言5-登录态 Cookie 仍存在"):
            assert inventory_page.get_cookie("session-username") is not None

    # ===================== SAUCE-COM-002 前进/后退 =====================

    @allure.story("浏览器行为")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("SAUCE-COM-002 浏览器前进/后退导航")
    @allure.description("列表页→详情页：后退回列表页、前进回详情页，各页要素断言正确")
    def test_back_forward_navigation(self, inventory_page, page_factory):
        with allure.step("前置：进入 Backpack 详情页"):
            backpack = get_product(4)
            inventory_page.click_product_link(backpack["id"])
            item_page = page_factory(ItemPage)
            item_page.wait_detail_loaded()

        with allure.step("后退回到商品列表页"):
            item_page.back()
            inventory_page.wait_inventory_loaded()

        with allure.step("断言1-后退后 URL 为列表页且列表可见"):
            assert inventory_page.get_current_url() == CONFIG["urls"]["inventory"]
            assert inventory_page.is_element_visible(inventory_page.INVENTORY_LIST)

        with allure.step("断言2-后退后详情容器已不在 DOM"):
            assert item_page.is_details_container_absent()

        with allure.step("前进回到详情页"):
            item_page.forward()
            item_page.wait_detail_loaded()

        with allure.step("断言3-前进后 URL 为详情页且详情要素可见"):
            assert item_page.get_current_url() == CONFIG["urls"]["item_detail"]
            assert item_page.is_element_visible(item_page.DETAILS_NAME)

    # ===================== SAUCE-COM-003 未登录重定向（数据驱动） =====================

    @allure.story("会话与权限")
    @pytest.mark.parametrize(
        "internal_path",
        CONFIG["internal_pages"],
        ids=[path.strip("/").replace("/", "_") for path in CONFIG["internal_pages"]],
    )
    @allure.title("SAUCE-COM-003 未登录访问内部页面被重定向（数据驱动）")
    @allure.description("全新无 Cookie 会话直接访问内页：一律重定向回登录页并给出提示")
    def test_redirect_when_not_logged_in(self, login_page, internal_path):
        from utils.allure_util import set_severity_from_str
        allure.dynamic.title(f"SAUCE-COM-003 未登录访问 {internal_path} 被重定向")
        set_severity_from_str("critical")

        with allure.step(f"未登录直接访问内页: {internal_path}"):
            login_page.open_url(CONFIG["base_url"].rstrip("/") + internal_path)

        with allure.step("断言1-被重定向回登录页"):
            login_page.wait_url_to_be(CONFIG["base_url"])

        with allure.step("断言2-重定向提示文案完整"):
            message = login_page.get_error_message()
            for substring in NOT_LOGIN_SUBS:
                assert substring in message, f"提示缺少关键文案[{substring}]: {message}"

        with allure.step("断言3-登录按钮可见"):
            assert login_page.is_login_form_displayed()

        with allure.step("断言4-未建立会话 Cookie"):
            assert login_page.get_cookie("session-username") is None