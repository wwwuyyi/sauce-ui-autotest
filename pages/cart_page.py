# -*- coding: utf-8 -*-
"""
cart_page.py —— 购物车页对象（Page 对象层）

职责：购物车页元素定位 + 业务方法（商品核对/删除/继续购物/去结算），
     只调用 BasePage 底层能力。

定位来源：.cart_list/.cart_item/.cart_quantity、[data-test='continue-shopping']、
          [data-test='checkout']、行内删除按钮 [data-test='remove-{slug}']。
"""
import logging

from selenium.webdriver.common.by import By

from base.base_page import BasePage
from pages.inventory_page import InventoryPage

logger = logging.getLogger(__name__)


class CartPage(BasePage):
    """购物车页对象：商品核对 / 删除 / 继续购物 / 去结算"""

    # ===================== 元素定位 =====================
    CART_LIST = (By.CSS_SELECTOR, ".cart_list")                     # 购物车列表容器
    CART_ITEM = (By.CSS_SELECTOR, ".cart_item")                     # 购物车商品行
    CART_ITEM_NAME = (By.CSS_SELECTOR, ".cart_item .inventory_item_name")   # 行内商品名称
    CART_ITEM_PRICE = (By.CSS_SELECTOR, ".cart_item .inventory_item_price") # 行内商品价格
    CART_QUANTITY = (By.CSS_SELECTOR, ".cart_quantity")             # 行内数量
    CART_ITEM_LABEL = (By.CSS_SELECTOR, ".cart_item_label")         # 行内商品信息区
    TITLE = (By.CSS_SELECTOR, ".title")                             # 页面主标题
    CONTINUE_SHOPPING = (By.CSS_SELECTOR, "[data-test='continue-shopping']")  # 继续购物按钮
    CHECKOUT = (By.CSS_SELECTOR, "[data-test='checkout']")          # 去结算按钮
    CART_LINK = InventoryPage.CART_LINK                             # 顶部购物车图标
    BADGE = InventoryPage.BADGE                                     # 购物车角标
    # 必须 staticmethod 包装：直接赋值会把普通函数绑定为本类方法，多传 self 参数
    remove_button = staticmethod(InventoryPage.remove_button)

    # ===================== 业务方法 =====================

    def wait_cart_page_loaded(self, timeout: int = None) -> None:
        """等待购物车页加载完成（列表容器可见）"""
        self.find_element(self.CART_LIST, timeout)

    def get_cart_item_count(self) -> int:
        """购物车商品行数（即时统计：删除全部商品后为 0，不能用带等待的 find_elements）"""
        return self.get_element_count_immediate(self.CART_ITEM)

    def get_cart_item_names(self) -> list:
        """按 DOM 顺序返回购物车内商品名称"""
        return [element.text for element in self.find_elements(self.CART_ITEM_NAME)]

    def get_cart_item_prices(self) -> list:
        """按 DOM 顺序返回购物车内商品价格"""
        return [element.text for element in self.find_elements(self.CART_ITEM_PRICE)]

    def get_cart_quantities(self) -> list:
        """返回每件商品的数量文本"""
        return [element.text for element in self.find_elements(self.CART_QUANTITY)]

    def get_cart_item_label_count(self) -> int:
        """商品信息区数量（信息区内商品链接存在性断言，即时统计）"""
        return self.get_element_count_immediate(self.CART_ITEM_LABEL)

    def get_title_text(self) -> str:
        """页面主标题（购物车页应为 Your Cart）"""
        return self.get_text(self.TITLE)

    def get_badge_text(self) -> str:
        """购物车角标数字"""
        return self.get_text(self.BADGE)

    def is_badge_absent(self) -> bool:
        """角标是否已从 DOM 移除"""
        return not self.is_element_present(self.BADGE, timeout=2)

    def wait_badge_disappear(self, timeout: int = None) -> None:
        """等待角标从 DOM 移除（删除商品后角标异步刷新，确定性等待）"""
        self.wait_element_disappear(self.BADGE, timeout)

    def wait_item_removed(self, slug: str) -> None:
        """等待某商品的移除按钮（即该商品行）从页面消失"""
        self.wait_element_disappear(self.remove_button(slug))

    def remove_item(self, slug: str) -> None:
        """删除购物车中的商品"""
        self.click(self.remove_button(slug))
        self.wait_item_removed(slug)

    def continue_shopping(self) -> None:
        """点击继续购物按钮（返回商品列表页）"""
        self.click(self.CONTINUE_SHOPPING)

    def click_checkout(self) -> None:
        """点击去结算按钮（进入结算第一步）"""
        self.click(self.CHECKOUT)