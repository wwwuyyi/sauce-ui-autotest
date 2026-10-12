# -*- coding: utf-8 -*-
"""
test_cart.py —— 购物车模块测试用例（TestCase 用例层）

职责：只做【业务调用 + 结果断言】，数据全部来自 config/env.yaml。
前置：cart_page fixture 预置购物车 2 件默认商品（Backpack + Bike Light，角标=2）。

覆盖原始用例（核心断言逻辑完整保留）：
  SAUCE-CART-001  购物车页面跳转
  SAUCE-CART-002  购物车内商品信息核对
  SAUCE-CART-003  购物车删除商品（角标联动）
  SAUCE-CART-004  继续购物按钮
"""
import logging

import allure
import pytest

from pages.inventory_page import InventoryPage
from utils.data_util import get_product
from utils.yaml_util import YamlUtil

logger = logging.getLogger(__name__)

CONFIG = YamlUtil().read_yaml("config/env.yaml")


@allure.epic("Sauce Demo 商城")
@allure.feature("购物车模块")
class TestCart:
    """购物车模块测试用例集合"""

    # ===================== SAUCE-CART-001 购物车页面跳转 =====================

    @allure.story("购物车导航")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("SAUCE-CART-001 购物车页面跳转")
    @allure.description("点击购物车图标跳转购物车页：URL 正确、列表可见、标题 Your Cart")
    @pytest.mark.smoke
    def test_cart_page_navigation(self, cart_page):
        with allure.step("断言1-URL 为购物车页"):
            assert cart_page.get_current_url() == CONFIG["urls"]["cart"]

        with allure.step("断言2-购物车列表容器可见"):
            assert cart_page.is_element_visible(cart_page.CART_LIST)

        with allure.step("断言3-顶部购物车图标仍在页面可见"):
            assert cart_page.is_element_visible(cart_page.CART_LINK)

        with allure.step("断言4-页面标题为 Your Cart"):
            assert cart_page.get_title_text() == CONFIG["expected"]["titles"]["cart"]

    # ===================== SAUCE-CART-002 商品信息核对 =====================

    @allure.story("购物车内容")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("SAUCE-CART-002 购物车内商品信息核对")
    @allure.description("预置 Backpack + Bike Light：行数/名称/价格/数量/角标与添加时完全一致")
    def test_cart_item_info_consistency(self, cart_page):
        backpack = get_product(4)
        bike_light = get_product(0)

        with allure.step("断言1-购物车共 2 件商品"):
            assert cart_page.get_cart_item_count() == 2

        with allure.step("断言2-商品名称与添加时一致"):
            assert cart_page.get_cart_item_names() == [backpack["name"], bike_light["name"]]

        with allure.step("断言3-商品价格与添加时一致"):
            assert cart_page.get_cart_item_prices() == [f"${backpack['price']}", f"${bike_light['price']}"]

        with allure.step("断言4-每件商品数量均为 1"):
            assert cart_page.get_cart_quantities() == ["1", "1"]

        with allure.step("断言5-角标数字为 2"):
            assert cart_page.get_badge_text() == "2"

        with allure.step("断言6-商品信息区链接存在"):
            assert cart_page.get_cart_item_label_count() == 2

    # ===================== SAUCE-CART-003 删除商品 =====================

    @allure.story("购物车内容")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("SAUCE-CART-003 购物车删除商品（角标联动）")
    @allure.description("删除 Backpack 后行数降低/剩余商品正确/角标降为 1；连锁清空后角标消失")
    def test_remove_item_from_cart_page(self, cart_page):
        backpack = get_product(4)
        bike_light = get_product(0)

        with allure.step("删除 Backpack"):
            cart_page.remove_item(backpack["slug"])

        with allure.step("断言1-购物车仅剩 1 件商品"):
            assert cart_page.get_cart_item_count() == 1

        with allure.step("断言2-剩余商品为 Bike Light"):
            assert cart_page.get_cart_item_names() == [bike_light["name"]]

        with allure.step("断言3-角标数字降为 1"):
            assert cart_page.get_badge_text() == "1"

        with allure.step("连锁清空：再删除 Bike Light"):
            cart_page.remove_item(bike_light["slug"])

        with allure.step("断言4-购物车为空且角标从 DOM 移除"):
            assert cart_page.get_cart_item_count() == 0
            assert cart_page.is_badge_absent()

    # ===================== SAUCE-CART-004 继续购物 =====================

    @allure.story("购物车导航")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("SAUCE-CART-004 继续购物按钮")
    @allure.description("点击 Continue Shopping 跳回商品列表页，列表可见且 6 个商品")
    def test_continue_shopping(self, cart_page, page_factory):
        with allure.step("点击继续购物按钮"):
            cart_page.continue_shopping()
            inventory_page = page_factory(InventoryPage)
            inventory_page.wait_inventory_loaded()

        with allure.step("断言1-URL 回到商品列表页"):
            assert inventory_page.get_current_url() == CONFIG["urls"]["inventory"]

        with allure.step("断言2-商品列表可见且 6 个商品"):
            assert inventory_page.is_element_visible(inventory_page.INVENTORY_LIST)
            assert inventory_page.get_product_count() == CONFIG["expected"]["inventory_item_count"]