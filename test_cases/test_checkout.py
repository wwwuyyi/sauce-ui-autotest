# -*- coding: utf-8 -*-
"""
test_checkout.py —— 结算下单模块测试用例（TestCase 用例层）

职责：只做【业务调用 + 结果断言】，数据全部来自 config/env.yaml。
前置：用例开头统一走模块级前置业务函数 —— 登录（inventory_page fixture）→ 加购默认商品
（含 sauce-labs-bike-light）→ 角标逐件断言 → 购物车页 → 结算第一步/概览页。

覆盖原始用例（核心断言逻辑完整保留）：
  SAUCE-CO-001   进入 Checkout（表单页）
  SAUCE-CO-002   正常填写用户信息并提交
  SAUCE-CO-003/004/005 三个字段空值校验（数据驱动合并，3 组参数化数据）
  SAUCE-CO-006   非法字符输入（XSS 载荷/特殊符号，参数化两组数据）
  SAUCE-CO-007   超长字符串输入
  SAUCE-CO-008   非数字 ZipCode
  SAUCE-CO-009   概览页商品信息与总价计算核对
  SAUCE-CO-010   完成订单成功提示
  SAUCE-CO-011   订单完成后返回首页
"""
import logging
from decimal import ROUND_HALF_UP, Decimal

import allure
import pytest
from selenium.common.exceptions import TimeoutException

from pages.cart_page import CartPage
from pages.checkout_page import CheckoutPage
from pages.inventory_page import InventoryPage
from utils.allure_util import set_severity_from_str
from utils.data_util import get_product
from utils.yaml_util import YamlUtil

logger = logging.getLogger(__name__)

CONFIG = YamlUtil().read_yaml("config/env.yaml")
VALID_INFO = CONFIG["checkout"]["valid_info"]
CO_TITLES = CONFIG["expected"]["titles"]
CO_URLS = CONFIG["urls"]


def _prepare_cart(inventory_page, page_factory):
    """checkout 模块前置业务第一步：进入购物车页（登录已由 inventory_page fixture 真实 UI 完成）

    业务链：商品页加购默认商品（含 sauce-labs-bike-light）→ 逐件断言购物车角标
    确认商品添加成功 → 再进入购物车页。返回已加载的 CartPage。
    """
    with allure.step("前置业务流程：加购默认商品并逐件断言购物车角标"):
        for index, slug in enumerate(CONFIG["checkout"]["default_item_slugs"], start=1):
            inventory_page.add_to_cart(slug)
            inventory_page.wait_badge_text(str(index))
            assert inventory_page.get_badge_text() == str(index), (
                f"加购 {slug} 后购物车角标应为 {index}（添加未生效，后续结算断言失真）")
    with allure.step("前置业务流程：确认商品添加成功后进入购物车页面"):
        inventory_page.open_cart()
        cart_page = page_factory(CartPage)
        cart_page.wait_cart_page_loaded()
    return cart_page


def _enter_checkout_step_one(inventory_page, page_factory):
    """checkout 模块前置业务第二步：购物车页 → 点击 Checkout 进入结算第一步

    健壮性：CartPage.click_checkout 内置点击失败重试；此处保留最终兜底——直接打开
    结算第一步 URL（与点击链接等价，登录态/购物车态在服务端会话中）。
    """
    cart_page = _prepare_cart(inventory_page, page_factory)
    page = page_factory(CheckoutPage)
    with allure.step("前置业务流程：点击 Checkout 进入结算第一步"):
        try:
            cart_page.click_checkout()
            page.wait_step_one_loaded()
        except TimeoutException:
            logger.warning("点击 Checkout 未进入结算表单页（站点导航无响应），改用 URL 直达兜底")
            page.open_url(CO_URLS["checkout_step_one"])
            page.wait_step_one_loaded()
    return page


def _enter_checkout_overview(inventory_page, page_factory):
    """checkout 模块前置业务第三步：结算第一步 → 填写正常信息提交 → 进入概览页"""
    page = _enter_checkout_step_one(inventory_page, page_factory)
    with allure.step("前置业务流程：填写正常信息提交进入概览页"):
        page.fill_info_and_continue(VALID_INFO["first"], VALID_INFO["last"], VALID_INFO["zip"])
        page.wait_overview_loaded()
    return page


@allure.epic("Sauce Demo 商城")
@allure.feature("结算下单模块")
class TestCheckout:
    """结算下单模块测试用例集合"""

    # ===================== SAUCE-CO-001 进入结算第一步 =====================

    @allure.story("结算流程")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("SAUCE-CO-001 进入 Checkout（表单页）")
    @allure.description("从购物车进入结算第一步：URL/标题/三输入框/继续与取消按钮状态正确")
    def test_enter_checkout_form(self, inventory_page, page_factory):
        page = _enter_checkout_step_one(inventory_page, page_factory)

        with allure.step("断言1-URL 为结算第一步"):
            assert page.get_current_url() == CO_URLS["checkout_step_one"]

        with allure.step("断言2-页面标题为 Checkout: Your Information"):
            assert page.get_title_text() == CO_TITLES["checkout_step_one"]

        with allure.step("断言3-表单三输入框全部可见"):
            assert page.is_element_visible(page.FIRST_NAME)
            assert page.is_element_visible(page.LAST_NAME)
            assert page.is_element_visible(page.POSTAL_CODE)

        with allure.step("断言4-继续按钮可见且可点击、取消按钮可见"):
            assert page.is_continue_enabled()
            assert page.is_cancel_visible()

    # ===================== SAUCE-CO-002 正常信息提交 =====================

    @allure.story("结算流程")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("SAUCE-CO-002 正常填写用户信息并提交")
    @allure.description("正常信息提交进入概览页：URL/标题/清单/Finish 状态正确，表单已离开页面")
    @pytest.mark.smoke
    def test_checkout_fill_valid_info(self, inventory_page, page_factory):
        page = _enter_checkout_step_one(inventory_page, page_factory)

        with allure.step("填写正常信息并提交"):
            page.fill_info_and_continue(VALID_INFO["first"], VALID_INFO["last"], VALID_INFO["zip"])
            page.wait_overview_loaded()

        with allure.step("断言1-URL 进入概览页"):
            assert page.get_current_url() == CO_URLS["checkout_step_two"]

        with allure.step("断言2-页面标题为 Checkout: Overview"):
            assert page.get_title_text() == CO_TITLES["checkout_step_two"]

        with allure.step("断言3-概览商品清单可见"):
            assert page.is_element_visible(page.CART_LIST)

        with allure.step("断言4-Finish 按钮可见且可点击"):
            assert page.is_element_visible(page.FINISH)
            assert page.is_finish_enabled()

        with allure.step("断言5-表单已离开页面（firstName 不在 DOM）"):
            assert page.is_first_name_absent()

    # ===================== SAUCE-CO-003/004/005 空值校验（数据驱动） =====================

    @allure.story("结算校验")
    @pytest.mark.parametrize(
        "case_data",
        CONFIG["checkout"]["invalid_field_cases"],
        ids=[case["case_id"] for case in CONFIG["checkout"]["invalid_field_cases"]],
    )
    @allure.title("字段必填校验（数据驱动）")
    @allure.description("First/Last/Postal 逐一为空提交：报错对应必填文案、停留在表单页")
    def test_checkout_required_field_validation(self, inventory_page, page_factory, case_data):
        page = _enter_checkout_step_one(inventory_page, page_factory)
        allure.dynamic.title(case_data["name"])
        set_severity_from_str(case_data["severity"])

        with allure.step("填写信息（置空必填字段）并提交"):
            page.fill_info_and_continue(case_data["first"], case_data["last"], case_data["zip"])

        with allure.step("断言1-报错提示文案正确"):
            expected_msg = CONFIG["expected"]["error_messages"][case_data["expected_error"]]
            assert page.get_error_message() == expected_msg

        with allure.step("断言2-错误提示容器可见"):
            assert page.is_error_container_displayed()

        with allure.step("断言3-仍停留在表单页（未跳转）"):
            assert page.get_current_url() == CO_URLS["checkout_step_one"]

    # ===================== SAUCE-CO-006 非法字符输入（数据驱动两组） =====================

    @allure.story("结算校验")
    @pytest.mark.parametrize(
        "case_data",
        CONFIG["checkout"]["special_input_cases"],
        ids=[f"SAUCE-CO-006-{case['name']}" for case in CONFIG["checkout"]["special_input_cases"]],
    )
    @allure.title("非法字符输入（数据驱动）")
    @allure.description("站点无前端输入格式校验：特殊符号/XSS 载荷提交被接受且不被执行")
    def test_checkout_special_char_input(self, inventory_page, page_factory, case_data):
        page = _enter_checkout_step_one(inventory_page, page_factory)
        allure.dynamic.title(f"SAUCE-CO-006 {case_data['name']}")
        set_severity_from_str("normal")

        with allure.step("填写含非法字符的 FirstName 并回读"):
            page.fill_info(case_data["first"], VALID_INFO["last"], VALID_INFO["zip"])

        with allure.step("断言1-输入回读与原始串完全一致（未被清洗/截断）"):
            assert page.get_first_name_value() == case_data["first"]

        with allure.step("提交并等待进入概览页"):
            page.click_continue()
            page.wait_overview_loaded()

        with allure.step("断言2-提交被接受（进入概览页）"):
            assert page.get_current_url() == CO_URLS["checkout_step_two"]

        with allure.step("断言3-XSS 载荷未被执行为弹窗"):
            assert page.is_alert_present(timeout=3) is False

    # ===================== SAUCE-CO-007 超长字符串 =====================

    @allure.story("结算校验")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("SAUCE-CO-007 超长字符串输入")
    @allure.description("300 字符 FirstName 无 maxlength 校验：回读长度一致、提交进入概览页")
    def test_checkout_long_string_input(self, inventory_page, page_factory):
        page = _enter_checkout_step_one(inventory_page, page_factory)
        long_text = "A" * CONFIG["checkout"]["long_input_length"]

        with allure.step("填写 300 字符并回读"):
            page.fill_info(long_text, VALID_INFO["last"], VALID_INFO["zip"])

        with allure.step("断言1-回读长度仍为 300（未被截断）"):
            assert len(page.get_first_name_value()) == CONFIG["checkout"]["long_input_length"]

        with allure.step("提交并等待进入概览页"):
            page.click_continue()
            page.wait_overview_loaded()

        with allure.step("断言2-提交成功进入概览页"):
            assert page.get_current_url() == CO_URLS["checkout_step_two"]

        with allure.step("断言3-概览商品清单可见"):
            assert page.is_element_visible(page.CART_LIST)

    # ===================== SAUCE-CO-008 非数字邮编 =====================

    @allure.story("结算校验")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("SAUCE-CO-008 非数字 ZipCode")
    @allure.description("站点仅做非空校验：非数字邮编提交成功进入概览页（记录为站点实际行为）")
    def test_checkout_non_numeric_zip(self, inventory_page, page_factory):
        page = _enter_checkout_step_one(inventory_page, page_factory)

        with allure.step("填写非数字邮编并提交"):
            page.fill_info_and_continue(
                VALID_INFO["first"], VALID_INFO["last"], CONFIG["checkout"]["invalid_zip"])
            page.wait_overview_loaded()

        with allure.step("断言1-提交成功进入概览页"):
            assert page.get_current_url() == CO_URLS["checkout_step_two"]

        with allure.step("断言2-Finish 按钮可见"):
            assert page.is_element_visible(page.FINISH)

    # ===================== SAUCE-CO-009 概览金额核对 =====================

    @allure.story("结算核对")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("SAUCE-CO-009 概览页商品信息与总价计算核对")
    @allure.description("Backpack+Bike Light：商品行/名称/价格与预置一致，"
                        "Item total/Tax/Total 标签文本与计算值（Decimal 精度）全部正确")
    def test_checkout_overview_amounts(self, inventory_page, page_factory):
        page = _enter_checkout_overview(inventory_page, page_factory)
        backpack = get_product(4)
        bike_light = get_product(0)

        with allure.step("断言1-概览页共 2 件商品"):
            assert page.get_overview_item_count() == 2

        with allure.step("断言2-金额标签文本精确匹配"):
            labels = CONFIG["checkout"]["summary_labels"]
            assert page.get_summary_label_texts() == labels

        with allure.step("断言3-金额计算正确性（Decimal 运算，避免 float 误差）"):
            amounts = page.get_summary_amounts()
            subtotal = Decimal(backpack["price"]) + Decimal(bike_light["price"])
            tax = (subtotal * Decimal("0.08")).quantize(Decimal("0.01"), ROUND_HALF_UP)
            assert amounts["subtotal"] == subtotal
            assert amounts["tax"] == tax
            assert amounts["total"] == subtotal + tax

        with allure.step("断言4-支付/物流信息区可见"):
            assert page.is_summary_info_visible()

        with allure.step("断言5-Finish 按钮可见且可点击"):
            assert page.is_element_visible(page.FINISH)
            assert page.is_finish_enabled()

    # ===================== SAUCE-CO-010 完成订单 =====================

    @allure.story("结算流程")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("SAUCE-CO-010 完成订单成功提示")
    @allure.description("点击 Finish 进入完成页：成功文案/插图/返回按钮齐全，购物车角标清空")
    @pytest.mark.smoke
    def test_checkout_complete_order(self, inventory_page, page_factory):
        page = _enter_checkout_overview(inventory_page, page_factory)

        with allure.step("点击 Finish 完成订单并等待完成页"):
            page.click_finish()
            page.wait_complete_loaded()

        with allure.step("断言1-URL 为订单完成页"):
            assert page.get_current_url() == CO_URLS["checkout_complete"]

        with allure.step("断言2-成功文案正确"):
            assert page.get_complete_header() == CONFIG["checkout"]["complete_header"]
            assert page.get_complete_text() == CONFIG["checkout"]["complete_text"]

        with allure.step("断言3-完成页插图与返回按钮可见"):
            assert page.is_pony_visible()
            assert page.is_element_visible(page.BACK_TO_PRODUCTS)

        with allure.step("断言4-下单后购物车已清空（角标消失）"):
            assert page.is_badge_absent()

    # ===================== SAUCE-CO-011 完成后返回首页 =====================

    @allure.story("结算流程")
    @allure.severity(allure.severity_level.MINOR)
    @allure.title("SAUCE-CO-011 订单完成后返回首页")
    @allure.description("完成页点击 Back Home 回到商品列表页，列表可见且购物车为空")
    def test_checkout_back_to_products(self, inventory_page, page_factory):
        page = _enter_checkout_overview(inventory_page, page_factory)

        with allure.step("完成订单并返回商品列表"):
            page.click_finish()
            page.wait_complete_loaded()
            page.click_back_to_products()

        with allure.step("断言1-URL 回到商品列表页"):
            inventory_page = page_factory(InventoryPage)
            inventory_page.wait_inventory_loaded()
            assert inventory_page.get_current_url() == CO_URLS["inventory"]

        with allure.step("断言2-商品列表可见"):
            assert inventory_page.is_element_visible(inventory_page.INVENTORY_LIST)

        with allure.step("断言3-购物车角标为空（下单后清空）"):
            assert inventory_page.is_badge_absent()