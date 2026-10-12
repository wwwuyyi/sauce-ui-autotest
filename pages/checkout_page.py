# -*- coding: utf-8 -*-
"""
checkout_page.py —— 结算下单页对象（Page 对象层）

职责：结算三步（信息表单 / 概览核对 / 完成页）的元素定位 + 业务方法，
     只调用 BasePage 底层能力。

定位来源：表单三要素 [data-test='firstName'/'lastName'/'postalCode']、
          [data-test='continue'/'cancel'/'finish']、错误提示 h3[data-test='error']、
          金额汇总 .summary_subtotal_label/_tax_label/_total_label、
          完成页 [data-test='complete-header']/.complete-text/img.pony_express。
金额断言约定：金额提取与计算全程使用 decimal.Decimal，避免 float 精度误差。
"""
import logging
from decimal import Decimal

from selenium.webdriver.common.by import By

from base.base_page import BasePage
from pages.inventory_page import InventoryPage

logger = logging.getLogger(__name__)


class CheckoutPage(BasePage):
    """结算下单页对象：表单填写 / 金额核对 / 完成订单"""

    # ===================== 元素定位 =====================
    # -- 第一步：用户信息表单 --
    FIRST_NAME = (By.CSS_SELECTOR, "[data-test='firstName']")
    LAST_NAME = (By.CSS_SELECTOR, "[data-test='lastName']")
    POSTAL_CODE = (By.CSS_SELECTOR, "[data-test='postalCode']")
    CONTINUE = (By.CSS_SELECTOR, "[data-test='continue']")
    CANCEL = (By.CSS_SELECTOR, "[data-test='cancel']")
    # -- 错误提示（登录/结算共用） --
    ERROR_MESSAGE = (By.CSS_SELECTOR, "h3[data-test='error']")
    ERROR_CONTAINER = (By.CSS_SELECTOR, ".error-message-container")
    # -- 第二步：概览页 --
    CART_LIST = (By.CSS_SELECTOR, ".cart_list")
    CART_ITEM = (By.CSS_SELECTOR, ".cart_item")
    FINISH = (By.CSS_SELECTOR, "[data-test='finish']")
    SUMMARY_INFO = (By.CSS_SELECTOR, ".summary_info")
    SUMMARY_SUBTOTAL = (By.CSS_SELECTOR, ".summary_subtotal_label")
    SUMMARY_TAX = (By.CSS_SELECTOR, ".summary_tax_label")
    SUMMARY_TOTAL = (By.CSS_SELECTOR, ".summary_total_label")
    # -- 公共 --
    TITLE = (By.CSS_SELECTOR, ".title")
    BADGE = InventoryPage.BADGE      # 购物车角标（下单完成后应清空）
    # -- 第三步：完成页 --
    COMPLETE_HEADER = (By.CSS_SELECTOR, "[data-test='complete-header']")
    COMPLETE_TEXT = (By.CSS_SELECTOR, ".complete-text")
    PONY_EXPRESS = (By.CSS_SELECTOR, "img.pony_express")
    BACK_TO_PRODUCTS = (By.CSS_SELECTOR, "[data-test='back-to-products']")

    # ===================== 业务方法：第一步（信息表单） =====================

    def wait_step_one_loaded(self, timeout: int = None) -> None:
        """等待结算第一步加载完成（表单出现）"""
        self.find_element(self.FIRST_NAME, timeout)

    def fill_info(self, first: str, last: str, zip_code: str) -> None:
        """填写用户信息表单（三字段一次写入）"""
        self.input_text(self.FIRST_NAME, first)
        self.input_text(self.LAST_NAME, last)
        self.input_text(self.POSTAL_CODE, zip_code)

    def fill_info_and_continue(self, first: str, last: str, zip_code: str) -> None:
        """填写表单并提交（正常结算主流程）"""
        self.fill_info(first, last, zip_code)
        self.click_continue()

    def click_continue(self) -> None:
        """点击继续按钮"""
        self.click(self.CONTINUE)

    def click_cancel(self) -> None:
        """点击取消按钮"""
        self.click(self.CANCEL)

    def get_first_name_value(self) -> str:
        """回读 FirstName 输入框当前值（输入未被清洗/截断断言用）"""
        return self.get_attribute(self.FIRST_NAME, "value")

    def is_first_name_absent(self) -> bool:
        """表单是否已离开页面（提交成功后表单应消失）"""
        return not self.is_element_present(self.FIRST_NAME, timeout=2)

    def get_error_message(self) -> str:
        """获取错误提示文案"""
        return self.get_text(self.ERROR_MESSAGE)

    def is_error_container_displayed(self) -> bool:
        """错误提示容器是否可见"""
        return self.is_element_visible(self.ERROR_CONTAINER)

    def is_continue_enabled(self) -> bool:
        """继续按钮是否可点击"""
        return self.is_element_enabled(self.CONTINUE)

    def is_cancel_visible(self) -> bool:
        """取消按钮是否可见"""
        return self.is_element_visible(self.CANCEL)

    def get_title_text(self) -> str:
        """页面主标题文本"""
        return self.get_text(self.TITLE)

    # ===================== 业务方法：第二步（概览页） =====================

    def wait_overview_loaded(self, timeout: int = None) -> None:
        """等待概览页加载完成（Finish 按钮与商品清单可见）"""
        self.find_element(self.FINISH, timeout)
        self.find_element(self.CART_LIST, timeout)

    def get_overview_item_count(self) -> int:
        """概览页商品行数（即时统计，与商品行数变化类断言语义一致）"""
        return self.get_element_count_immediate(self.CART_ITEM)

    def is_finish_enabled(self) -> bool:
        """完成按钮是否可点击"""
        return self.is_element_enabled(self.FINISH)

    def is_summary_info_visible(self) -> bool:
        """支付/物流信息区是否可见"""
        return self.is_element_visible(self.SUMMARY_INFO)

    def get_summary_label_texts(self) -> dict:
        """金额标签文本（字符串精确断言基准）：subtotal / tax / total"""
        return {
            "subtotal": self.get_text(self.SUMMARY_SUBTOTAL),
            "tax": self.get_text(self.SUMMARY_TAX),
            "total": self.get_text(self.SUMMARY_TOTAL),
        }

    def get_summary_amounts(self) -> dict:
        """金额数值（Decimal，用于计算正确性断言）"""
        labels = self.get_summary_label_texts()
        return {key: Decimal(text.split("$")[-1]) for key, text in labels.items()}

    # ===================== 业务方法：第三步（完成页）与返回 =====================

    def click_finish(self) -> None:
        """点击完成订单按钮"""
        self.click(self.FINISH)

    def wait_complete_loaded(self, timeout: int = None) -> None:
        """等待订单完成页加载完成"""
        self.find_element(self.COMPLETE_HEADER, timeout)

    def get_complete_header(self) -> str:
        """完成页标题文案"""
        return self.get_text(self.COMPLETE_HEADER)

    def get_complete_text(self) -> str:
        """完成页说明文案"""
        return self.get_text(self.COMPLETE_TEXT)

    def is_pony_visible(self) -> bool:
        """完成页插图是否可见"""
        return self.is_element_visible(self.PONY_EXPRESS)

    def is_badge_absent(self) -> bool:
        """购物车角标是否已清空（下单完成后）"""
        return not self.is_element_present(self.BADGE, timeout=2)

    def click_back_to_products(self) -> None:
        """点击返回商品列表按钮"""
        self.click(self.BACK_TO_PRODUCTS)