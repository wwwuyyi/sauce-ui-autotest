# -*- coding: utf-8 -*-
"""
test_e2e.py —— 下单全链路端到端冒烟（TestCase 用例层）

职责：单条用例在一个浏览器会话内串起下单主链路，逐节点业务操作 + 断言，
     补齐 smoke 集合的链路闭环缺口（节点间数据传递一致性由断言而非 fixture 保证）。
数据全部来自 config/env.yaml，零硬编码。

覆盖用例：
  SAUCE-E2E-001  下单全链路冒烟：
      登录(真实UI) → 加购2件(角标联动) → 购物车核对 → 结算表单提交
      → 概览金额核对(Decimal计算) → 完成订单(成功页+角标清空)

与节点级 smoke 用例（LOGIN-001 / INV-001 / CART-001 / CO-002 / CO-010）的关系：
节点级用例各管一段、靠 fixture 前置链到达现场；本用例一条从登录走到完成页，
任一节断言失败即可定位链路断点。
"""
import logging
from decimal import ROUND_HALF_UP, Decimal

import allure
import pytest

from pages.cart_page import CartPage
from pages.checkout_page import CheckoutPage
from utils.data_util import get_product
from utils.yaml_util import YamlUtil

logger = logging.getLogger(__name__)

CONFIG = YamlUtil().read_yaml("config/env.yaml")
URLS = CONFIG["urls"]
TITLES = CONFIG["expected"]["titles"]
DEFAULT_SLUGS = CONFIG["checkout"]["default_item_slugs"]


@allure.epic("Sauce Demo 商城")
@allure.feature("下单全链路")
class TestEndToEnd:
    """下单全链路端到端冒烟用例集合"""

    # ===================== SAUCE-E2E-001 下单全链路 =====================

    @allure.story("全链路冒烟")
    @allure.severity(allure.severity_level.BLOCKER)
    @allure.title("SAUCE-E2E-001 下单全链路冒烟（登录→加购→购物车→结算→完成）")
    @allure.description("一个会话内顺序执行下单主链路各环节并逐节点断言："
                        "商品跨节点数据传递一致（名称/价格/数量），"
                        "概览金额=商品价合计+8%税（Decimal 计算），"
                        "完成订单后购物车角标清空")
    @pytest.mark.smoke
    def test_full_order_flow_smoke(self, inventory_page, page_factory):
        backpack = get_product(4)
        bike_light = get_product(0)
        expected_products = [backpack, bike_light]

        # -------- 节点1-登录与商品列表（inventory_page fixture 已完成真实 UI 登录） --------
        with allure.step("断言1-登录成功进入商品列表页且 6 个商品可见"):
            assert inventory_page.get_current_url() == URLS["inventory"]
            assert inventory_page.is_element_visible(inventory_page.INVENTORY_LIST)
            assert inventory_page.get_product_count() == CONFIG["expected"]["inventory_item_count"]

        # -------- 节点2-加购 --------
        with allure.step("加购默认两件商品（每加一件校验角标累计）"):
            inventory_page.add_items_to_cart(DEFAULT_SLUGS)

        with allure.step("断言2-两件商品按钮均切换为 Remove，角标累计为 2"):
            for product in expected_products:
                slug = product["slug"]
                assert inventory_page.get_button_text(
                    inventory_page.remove_button(slug)) == "Remove"
                assert inventory_page.is_add_button_absent(slug)
            assert inventory_page.get_badge_text() == str(len(expected_products))

        # -------- 节点3-购物车核对 --------
        with allure.step("进入购物车页"):
            inventory_page.open_cart()
            cart = page_factory(CartPage)
            cart.wait_cart_page_loaded()

        with allure.step("断言3-购物车 2 件商品与加购完全一致（名称/价格/数量/角标/标题）"):
            assert cart.get_current_url() == URLS["cart"]
            assert cart.get_title_text() == TITLES["cart"]
            assert cart.get_cart_item_count() == 2
            assert cart.get_cart_item_names() == [p["name"] for p in expected_products]
            assert cart.get_cart_item_prices() == [f"${p['price']}" for p in expected_products]
            assert cart.get_cart_quantities() == ["1", "1"]
            assert cart.get_badge_text() == "2"

        # -------- 节点4-结算信息表单 --------
        with allure.step("点击去结算，进入信息表单页"):
            cart.click_checkout()
            checkout = page_factory(CheckoutPage)
            checkout.wait_step_one_loaded()

        with allure.step("断言4-表单页 URL/标题正确且三输入框可见"):
            assert checkout.get_current_url() == URLS["checkout_step_one"]
            assert checkout.get_title_text() == TITLES["checkout_step_one"]
            assert checkout.is_element_visible(checkout.FIRST_NAME)
            assert checkout.is_element_visible(checkout.LAST_NAME)
            assert checkout.is_element_visible(checkout.POSTAL_CODE)

        valid_info = CONFIG["checkout"]["valid_info"]
        with allure.step("填写正常用户信息并提交"):
            checkout.fill_info_and_continue(
                valid_info["first"], valid_info["last"], valid_info["zip"])
            checkout.wait_overview_loaded()

        # -------- 节点5-概览页金额核对 --------
        with allure.step("断言5-概览页商品清单与购物车两件商品一致"):
            assert checkout.get_current_url() == URLS["checkout_step_two"]
            assert checkout.get_title_text() == TITLES["checkout_step_two"]
            assert checkout.get_overview_item_count() == 2

        with allure.step("断言6-金额计算正确性（Decimal 运算，商品价合计+8%税）"):
            amounts = checkout.get_summary_amounts()
            subtotal = Decimal(backpack["price"]) + Decimal(bike_light["price"])
            tax = (subtotal * Decimal("0.08")).quantize(Decimal("0.01"), ROUND_HALF_UP)
            assert amounts["subtotal"] == subtotal
            assert amounts["tax"] == tax
            assert amounts["total"] == subtotal + tax

        with allure.step("断言7-Finish 按钮可见且可点击"):
            assert checkout.is_element_visible(checkout.FINISH)
            assert checkout.is_finish_enabled()

        # -------- 节点6-完成订单 --------
        with allure.step("点击 Finish 完成订单并等待完成页"):
            checkout.click_finish()
            checkout.wait_complete_loaded()

        with allure.step("断言8-完成页 URL/成功文案/插图/返回按钮齐全"):
            assert checkout.get_current_url() == URLS["checkout_complete"]
            assert checkout.get_complete_header() == CONFIG["checkout"]["complete_header"]
            assert checkout.get_complete_text() == CONFIG["checkout"]["complete_text"]
            assert checkout.is_pony_visible()
            assert checkout.is_element_visible(checkout.BACK_TO_PRODUCTS)

        with allure.step("断言9-下单后购物车已清空（角标消失，链路终态）"):
            assert checkout.is_badge_absent()
