# -*- coding: utf-8 -*-
"""
item_page.py —— 商品详情页对象（Page 对象层）

职责：详情页元素定位 + 业务方法（信息读取/加购/移除/返回列表），
     只调用 BasePage 底层能力。

定位来源：详情页容器 .inventory_details_container、名称/描述/价格
          .inventory_details_name/_desc/_price、返回按钮 [data-test='back-to-products']；
          加购/移除按钮 data-test 为通用值（add-to-cart / remove），与列表页
          "add-to-cart-{slug}" 命名规则不同，以实测 DOM 为准。
"""
import logging

from selenium.webdriver.common.by import By

from base.base_page import BasePage
from pages.inventory_page import InventoryPage

logger = logging.getLogger(__name__)


class ItemPage(BasePage):
    """商品详情页对象：详情信息 / 加购移除 / 返回列表"""

    # ===================== 元素定位 =====================
    DETAILS_CONTAINER = (By.CSS_SELECTOR, ".inventory_details_container")   # 详情容器
    DETAILS_NAME = (By.CSS_SELECTOR, ".inventory_details_name")             # 详情页商品名称
    DETAILS_DESC = (By.CSS_SELECTOR, ".inventory_details_desc")             # 详情页商品描述
    DETAILS_PRICE = (By.CSS_SELECTOR, ".inventory_details_price")           # 详情页商品价格
    DETAILS_IMG = (By.CSS_SELECTOR, "img.inventory_details_img")            # 详情页商品图片
    BACK_BTN = (By.CSS_SELECTOR, "[data-test='back-to-products']")          # 返回列表按钮
    INVENTORY_LIST = (By.CSS_SELECTOR, ".inventory_list")                   # 列表容器（详情页应不存在）
    # 详情页加购/移除按钮：data-test 为通用值（add-to-cart / remove）。
    # 实测 DOM：详情页按钮不带商品 slug——与列表页"[data-test='add-to-cart-{slug}']"
    # 命名规则不同；原设计文档"共用同一 data-test"的描述与实际站点不符，以实测为准。
    ADD_BTN = (By.CSS_SELECTOR, "[data-test='add-to-cart']")
    REMOVE_BTN = (By.CSS_SELECTOR, "[data-test='remove']")
    # 与列表页共用组件（定位器常量直接引用，无 descriptor 隐患）
    BADGE = InventoryPage.BADGE

    # ===================== 业务方法：加载与信息读取 =====================

    def wait_detail_loaded(self, timeout: int = None) -> None:
        """等待详情页加载完成（详情容器可见）"""
        self.find_element(self.DETAILS_CONTAINER, timeout)

    def get_detail_name(self) -> str:
        """详情页商品名称文本"""
        return self.get_text(self.DETAILS_NAME)

    def get_detail_desc(self) -> str:
        """详情页商品描述文本（列表页无描述，故详情描述非空即正确来源）"""
        return self.get_text(self.DETAILS_DESC)

    def get_detail_price(self) -> str:
        """详情页商品价格文本"""
        return self.get_text(self.DETAILS_PRICE)

    def get_detail_image_natural_width(self) -> int:
        """详情图片解码宽度（naturalWidth>0 表明图片真实渲染）"""
        element = self.find_element(self.DETAILS_IMG)
        try:
            return int(element.get_attribute("naturalWidth") or 0)
        except ValueError:
            return 0

    def are_detail_fields_visible(self) -> bool:
        """名称/描述/价格三要素是否全部可见"""
        return (self.is_element_visible(self.DETAILS_NAME)
                and self.is_element_visible(self.DETAILS_DESC)
                and self.is_element_visible(self.DETAILS_PRICE))

    def is_back_button_visible(self) -> bool:
        """返回列表按钮是否可见"""
        return self.is_element_visible(self.BACK_BTN)

    def is_inventory_list_absent(self) -> bool:
        """列表容器是否已不在 DOM（已离开列表页）"""
        return not self.is_element_present(self.INVENTORY_LIST, timeout=2)

    # ===================== 业务方法：加购 / 移除 / 返回 =====================

    def add_to_cart(self) -> None:
        """详情页加购并等待按钮切换为 Remove（按钮为通用 data-test，无需 slug）"""
        self.click(self.ADD_BTN)
        self.find_element(self.REMOVE_BTN)

    def remove_from_cart(self) -> None:
        """详情页移除并等待按钮恢复为加购"""
        self.click(self.REMOVE_BTN)
        self.find_element(self.ADD_BTN)

    def is_add_button_absent(self) -> bool:
        """加购按钮是否已不在 DOM"""
        return not self.is_element_present(self.ADD_BTN, timeout=2)

    def wait_badge_text(self, text: str) -> None:
        """等待购物车角标变为指定数字（加购后角标异步刷新，确定性等待）"""
        self.wait_text_present(self.BADGE, text)

    def get_badge_text(self) -> str:
        """购物车角标数字（详情页加购后 +1 断言）"""
        return self.get_text(self.BADGE)

    def wait_badge_disappear(self, timeout: int = None) -> None:
        """等待角标从 DOM 移除（移除购物车后的确定性等待）"""
        self.wait_element_disappear(self.BADGE, timeout)

    def is_badge_absent(self) -> bool:
        """角标是否已从 DOM 移除"""
        return not self.is_element_present(self.BADGE, timeout=2)

    def wait_detail_image_loaded(self, timeout: int = None) -> None:
        """等待详情图片完成解码（naturalWidth 断言的前置等待）"""
        self.wait_all_images_loaded(self.DETAILS_IMG, timeout)

    def back_to_products(self) -> None:
        """点击返回列表按钮"""
        self.click(self.BACK_BTN)

    def is_details_container_absent(self) -> bool:
        """详情容器是否已不在 DOM（后退/跳转后核验）"""
        return not self.is_element_present(self.DETAILS_CONTAINER, timeout=2)