# -*- coding: utf-8 -*-
"""
test_item.py —— 商品详情页模块测试用例（TestCase 用例层）

职责：只做【业务调用 + 结果断言】，数据全部来自 config/env.yaml。

覆盖原始用例（核心断言逻辑完整保留）：
  SAUCE-DTL-001  点击商品名进入详情页
  SAUCE-DTL-002  详情信息与列表页核对一致
  SAUCE-DTL-003  详情页添加购物车
  SAUCE-DTL-004  详情页移除购物车
  SAUCE-DTL-005  详情页返回商品列表
"""
import logging

import allure

from pages.item_page import ItemPage
from utils.data_util import get_product
from utils.yaml_util import YamlUtil

logger = logging.getLogger(__name__)

CONFIG = YamlUtil().read_yaml("config/env.yaml")


@allure.epic("Sauce Demo 商城")
@allure.feature("商品详情页模块")
class TestItemDetail:
    """商品详情页模块测试用例集合"""

    def _enter_detail(self, inventory_page, page_factory, product_id):
        """通用前置：从列表页点击商品标题进入详情页（返回 ItemPage）"""
        inventory_page.click_product_link(product_id)
        inventory_page.wait_url_contains(f"/inventory-item.html?id={product_id}")
        item_page = page_factory(ItemPage)
        item_page.wait_detail_loaded()
        return item_page

    # ===================== SAUCE-DTL-001 进入详情页 =====================

    @allure.story("详情页跳转")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("SAUCE-DTL-001 点击商品名进入详情页")
    @allure.description("点击 Backpack 名称链接跳转详情页：URL/详情要素齐全，列表容器销毁")
    def test_enter_detail_page(self, inventory_page, page_factory):
        backpack = get_product(4)
        item_page = self._enter_detail(inventory_page, page_factory, backpack["id"])

        with allure.step("断言1-URL 跳转到 Backpack 详情页"):
            assert item_page.get_current_url() == CONFIG["urls"]["item_detail"]

        with allure.step("断言2-详情容器/名称/返回按钮均可见"):
            assert item_page.is_element_visible(item_page.DETAILS_CONTAINER)
            assert item_page.is_element_visible(item_page.DETAILS_NAME)
            assert item_page.is_back_button_visible()

        with allure.step("断言3-详情页商品名称为 Sauce Labs Backpack"):
            assert item_page.get_detail_name() == backpack["name"]

        with allure.step("断言4-列表容器已从 DOM 销毁"):
            assert item_page.is_inventory_list_absent()

    # ===================== SAUCE-DTL-002 详情信息与列表页核对 =====================

    @allure.story("详情页跳转")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("SAUCE-DTL-002 详情信息与列表页核对一致")
    @allure.description("详情页名称/描述/价格与列表页抓取值完全一致，图片真实渲染")
    def test_detail_info_consistency(self, inventory_page, page_factory):
        backpack = get_product(4)

        with allure.step("从列表页抓取 Backpack 名称/描述/价格"):
            list_names = inventory_page.get_product_names()
            list_descs = inventory_page.get_product_descriptions()
            list_prices = inventory_page.get_product_prices()
            index = list_names.index(backpack["name"])

        item_page = self._enter_detail(inventory_page, page_factory, backpack["id"])

        with allure.step("断言1-名称与列表页一致"):
            assert item_page.get_detail_name() == list_names[index]

        with allure.step("断言2-描述与列表页一致且非空"):
            assert item_page.get_detail_desc() == list_descs[index]
            assert list_descs[index].strip() != ""

        with allure.step("断言3-价格与列表页一致"):
            assert item_page.get_detail_price() == list_prices[index]

        with allure.step("等待详情图片完成解码"):
            item_page.wait_detail_image_loaded()

        with allure.step("断言4-详情图片真实渲染（naturalWidth>0）"):
            assert item_page.get_detail_image_natural_width() > 0

        with allure.step("断言5-名称/描述/价格三要素全部可见"):
            assert item_page.are_detail_fields_visible()

    # ===================== SAUCE-DTL-003 详情页加购 =====================

    @allure.story("详情页加购")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("SAUCE-DTL-003 详情页添加购物车")
    @allure.description("详情页点击加购：按钮切换为 Remove、加购按钮消失、角标+1、URL 不跳页")
    def test_add_to_cart_from_detail(self, inventory_page, page_factory):
        backpack = get_product(4)
        item_page = self._enter_detail(inventory_page, page_factory, backpack["id"])

        with allure.step("详情页点击加购并等待按钮切换"):
            item_page.add_to_cart()

        with allure.step("断言1-按钮切换为 Remove"):
            assert item_page.get_text(item_page.REMOVE_BTN) == "Remove"

        with allure.step("断言2-加购按钮已从 DOM 消失"):
            assert item_page.is_add_button_absent()

        with allure.step("断言3-购物车角标为 1"):
            item_page.wait_badge_text("1")
            assert item_page.get_badge_text() == "1"

        with allure.step("断言4-加购不跳页（URL 保持详情页）"):
            assert item_page.get_current_url() == CONFIG["urls"]["item_detail"]

    # ===================== SAUCE-DTL-004 详情页移除 =====================

    @allure.story("详情页加购")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("SAUCE-DTL-004 详情页移除购物车")
    @allure.description("详情页点击 Remove：按钮恢复 Add to cart、角标消失、URL 保持详情页")
    def test_remove_from_cart_from_detail(self, inventory_page, page_factory):
        backpack = get_product(4)
        item_page = self._enter_detail(inventory_page, page_factory, backpack["id"])

        with allure.step("预置：详情页先加购"):
            item_page.add_to_cart()

        with allure.step("详情页点击移除并等待按钮恢复"):
            item_page.remove_from_cart()

        with allure.step("断言1-按钮恢复为 Add to cart"):
            assert item_page.get_text(item_page.ADD_BTN) == "Add to cart"

        with allure.step("断言2-角标归零后从 DOM 移除"):
            item_page.wait_badge_disappear()
            assert item_page.is_badge_absent()

        with allure.step("断言3-URL 保持详情页"):
            assert item_page.get_current_url() == CONFIG["urls"]["item_detail"]

    # ===================== SAUCE-DTL-005 返回商品列表 =====================

    @allure.story("详情页跳转")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("SAUCE-DTL-005 详情页返回商品列表")
    @allure.description("点击 Back to products 返回列表页：URL 正确、列表可见、6 个商品")
    def test_back_to_products(self, inventory_page, page_factory):
        backpack = get_product(4)
        item_page = self._enter_detail(inventory_page, page_factory, backpack["id"])

        with allure.step("点击返回列表按钮"):
            item_page.back_to_products()
            inventory_page.wait_inventory_loaded()

        with allure.step("断言1-URL 回到商品列表页"):
            assert inventory_page.get_current_url() == CONFIG["urls"]["inventory"]

        with allure.step("断言2-商品列表可见且仍为 6 个商品"):
            assert inventory_page.is_element_visible(inventory_page.INVENTORY_LIST)
            assert inventory_page.get_product_count() == CONFIG["expected"]["inventory_item_count"]