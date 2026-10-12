# -*- coding: utf-8 -*-
"""
inventory_page.py —— 商品列表页对象（Page 对象层）

职责：元素定位 + 业务方法组合（商品列表/排序/加购/移除/角标/购物车入口/布局坐标），
     只调用 BasePage 底层能力，禁止 driver 直接操作。

定位来源（《自动化执行注意事项》§1.2/§1.3）：
- data-test 优先：[data-test='shopping-cart-badge']、[data-test^='add-to-cart-'] 等；
- 商品块无 data-test，使用 .inventory_item 系列 class；
- 加购/移除按钮的 data-test 值由商品 slug 动态拼接。
"""
import logging
from decimal import Decimal

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By

from base.base_page import BasePage

logger = logging.getLogger(__name__)


class InventoryPage(BasePage):
    """商品列表页对象：商品展示/排序/加购/移除/购物车角标"""

    # ===================== 元素定位 =====================
    PRODUCT_SORT = (By.CSS_SELECTOR, "select[data-test='product-sort-container']")  # 排序下拉框
    INVENTORY_LIST = (By.CSS_SELECTOR, ".inventory_list")               # 商品列表容器
    INVENTORY_ITEM = (By.CSS_SELECTOR, ".inventory_item")               # 商品块
    INVENTORY_ITEM_NAME = (By.CSS_SELECTOR, ".inventory_item_name")     # 商品名称
    INVENTORY_ITEM_PRICE = (By.CSS_SELECTOR, ".inventory_item_price")   # 商品价格
    INVENTORY_ITEM_DESC = (By.CSS_SELECTOR, ".inventory_item_desc")     # 商品描述
    INVENTORY_ITEM_IMG = (By.CSS_SELECTOR, "img.inventory_item_img")    # 商品图片
    ITEM_IMG_ALT = (By.CSS_SELECTOR, ".inventory_item_img")             # 图片元素（alt 属性断言）
    BADGE = (By.CSS_SELECTOR, "[data-test='shopping-cart-badge']")      # 购物车角标（归零后从 DOM 移除）
    CART_LINK = (By.CSS_SELECTOR, "[data-test='shopping-cart-link']")   # 购物车图标
    PRIMARY_HEADER = (By.CSS_SELECTOR, ".primary_header")               # 顶部 header
    ADD_ANY = (By.CSS_SELECTOR, "[data-test^='add-to-cart-']")          # 所有加购按钮
    REMOVE_ANY = (By.CSS_SELECTOR, "[data-test^='remove-']")            # 所有移除按钮

    @staticmethod
    def add_button(slug: str) -> tuple:
        """加购按钮定位器（data-test 值由商品 slug 动态拼接）"""
        return (By.CSS_SELECTOR, f"[data-test='add-to-cart-{slug}']")

    @staticmethod
    def remove_button(slug: str) -> tuple:
        """移除按钮定位器"""
        return (By.CSS_SELECTOR, f"[data-test='remove-{slug}']")

    @staticmethod
    def product_title_link(product_id: int) -> tuple:
        """商品标题链接定位器（进入详情页，data-test 值由商品 id 拼接）"""
        return (By.CSS_SELECTOR, f"a[data-test='item-{product_id}-title-link']")

    # ===================== 业务方法：加载与读取 =====================

    def wait_inventory_loaded(self, timeout: int = None) -> None:
        """等待商品列表页加载完成（列表容器可见即视为加载成功）"""
        self.find_element(self.INVENTORY_LIST, timeout)

    def get_product_count(self) -> int:
        """商品总数"""
        return len(self.find_elements(self.INVENTORY_ITEM))

    def get_product_names(self) -> list:
        """按 DOM 顺序返回商品名称列表"""
        return [element.text for element in self.find_elements(self.INVENTORY_ITEM_NAME)]

    def get_product_prices(self) -> list:
        """按 DOM 顺序返回商品价格文本列表（如 '$29.99'）"""
        return [element.text for element in self.find_elements(self.INVENTORY_ITEM_PRICE)]

    def get_price_numbers(self) -> list:
        """价格转换为 Decimal 列表（金额类断言全程避免 float 精度误差）"""
        return [Decimal(price.replace("$", "")) for price in self.get_product_prices()]

    def get_product_descriptions(self) -> list:
        """按 DOM 顺序返回商品描述列表（详情页与列表页一致性核对用）"""
        return [element.text for element in self.find_elements(self.INVENTORY_ITEM_DESC)]

    def get_product_image_srcs(self) -> list:
        """商品图片 src 列表（problem_user 图片异常断言用）"""
        return [element.get_attribute("src") for element in self.find_elements(self.INVENTORY_ITEM_IMG)]

    def get_image_natural_widths(self) -> list:
        """商品图片解码宽度列表（naturalWidth>0 表示图片真实渲染，区别于 404 图）"""
        return [int(element.get_attribute("naturalWidth") or 0)
                for element in self.find_elements(self.INVENTORY_ITEM_IMG)]

    def get_image_alts(self) -> list:
        """商品图片 alt 属性列表"""
        return [element.get_attribute("alt") or "" for element in self.find_elements(self.ITEM_IMG_ALT)]

    # ===================== 业务方法：排序 =====================

    def sort_by(self, value: str) -> None:
        """按 value 排序（az / za / lohi / hilo）"""
        self.select_by_value(self.PRODUCT_SORT, value)

    def get_sort_value(self) -> str:
        """回读当前下拉框选中值（排序生效的判定依据）"""
        return self.get_attribute(self.PRODUCT_SORT, "value")

    def sort_and_wait_names(self, value: str, expected_names: list, timeout: int = None) -> None:
        """排序并等待商品顺序变为期望序列（功能正常站点的确定性等待）"""
        self.sort_by(value)
        base_timeout = timeout or self.timeout
        self.wait_until(
            lambda _: self.get_product_names() == expected_names,
            timeout=base_timeout,
            fail_message=f"排序 {value} 未在超时内生效",
        )

    def sort_and_wait_settle(self, value: str, base_names: list, timeout: int = 3) -> None:
        """排序并有限等待重排（异常账号场景：排序可能失效，等待 3s 未变化即按当前 DOM 断言）"""
        self.sort_by(value)
        try:
            self.wait_until(
                lambda _: self.get_product_names() != base_names,
                timeout=timeout,
                fail_message=f"排序 {value} 后商品顺序未变化",
            )
        except TimeoutException:
            logger.warning("排序后商品顺序未变化（可能为 special_user 类异常行为，按当前 DOM 断言）")

    def sort_and_tolerate_alert(self, value: str) -> None:
        """排序并容忍站点异常弹窗（error_user 排序崩溃会触发原生 alert
        'Sorting is broken!'；不处理会污染后续所有 WebDriver 命令）"""
        self.sort_by(value)
        if self.is_alert_present(timeout=2):
            logger.warning("排序触发站点原生弹窗（异常账号特征），已自动点击确定")
            self.alert_accept()

    def wait_product_images_loaded(self, timeout: int = None) -> None:
        """等待 6 张商品图片全部完成解码（naturalWidth 断言的前置等待，防采样竞态）"""
        self.wait_all_images_loaded(self.INVENTORY_ITEM_IMG, timeout)

    # ===================== 业务方法：加购 / 移除 / 角标 =====================

    def click_add_button(self, slug: str) -> None:
        """仅点击加购按钮（error_user 场景加购可能无响应，不做状态等待）"""
        self.click(self.add_button(slug))

    def add_to_cart(self, slug: str) -> None:
        """加购单个商品并等待按钮切换为 Remove（功能正常站点）"""
        self.click(self.add_button(slug))
        self.find_element(self.remove_button(slug))

    def remove_from_cart(self, slug: str) -> None:
        """移除单个商品并等待按钮恢复为加购"""
        self.click(self.remove_button(slug))
        self.find_element(self.add_button(slug))

    def wait_remove_visible(self, slug: str) -> None:
        """等待移除按钮出现（加购成功标志）"""
        self.find_element(self.remove_button(slug))

    def wait_add_visible(self, slug: str) -> None:
        """等待加购按钮恢复（移除成功标志）"""
        self.find_element(self.add_button(slug))

    def is_add_button_absent(self, slug: str) -> bool:
        """加购按钮是否已不在 DOM（按钮状态切换断言）"""
        return not self.is_element_present(self.add_button(slug), timeout=2)

    def is_remove_button_absent(self, slug: str) -> bool:
        """移除按钮是否已不在 DOM"""
        return not self.is_element_present(self.remove_button(slug), timeout=2)

    def get_button_text(self, locator) -> str:
        """获取按钮文本（如 'Add to cart' / 'Remove'）"""
        return self.get_text(locator)

    def get_add_button_count(self) -> int:
        """当前加购按钮总数（即时统计：按钮数可能为 0，不能用带等待的 find_elements）"""
        return self.get_element_count_immediate(self.ADD_ANY)

    def get_remove_button_count(self) -> int:
        """当前移除按钮总数（即时统计：购物车重置后为 0）"""
        return self.get_element_count_immediate(self.REMOVE_ANY)

    def add_items_to_cart(self, slugs: list) -> None:
        """批量加购多个商品，每加一件校验角标累计（购物车预置 fixture 的核心方法）"""
        for index, slug in enumerate(slugs, start=1):
            self.add_to_cart(slug)
            self.wait_badge_text(str(index))
        logger.info("预置购物车完成，共 %d 件商品", len(slugs))

    def wait_badge_text(self, text: str) -> None:
        """等待购物车角标数字变为指定值"""
        self.wait_text_present(self.BADGE, text)

    def get_badge_text(self) -> str:
        """获取角标数字文本"""
        return self.get_text(self.BADGE)

    def get_badge_text_or_empty(self) -> str:
        """获取角标数字；角标不存在（购物车为空）时返回 '0'，不抛异常"""
        if self.is_element_present(self.BADGE, timeout=2):
            return self.get_text(self.BADGE)
        return "0"

    def is_badge_absent(self) -> bool:
        """角标是否已从 DOM 移除（购物车清空标志）"""
        return not self.is_element_present(self.BADGE, timeout=2)

    def wait_badge_disappear(self, timeout: int = None) -> None:
        """等待角标从 DOM 移除（清空/重置后的确定性等待，替代短轮询断言）"""
        self.wait_element_disappear(self.BADGE, timeout)

    def wait_buttons_reset(self, expected_add_count: int = 6, timeout: int = None) -> None:
        """等待加购/移除按钮状态复位（Reset App State 后渲染完成的确定性等待）"""
        self.wait_until(
            lambda _: (self.get_add_button_count() == expected_add_count
                       and self.get_remove_button_count() == 0),
            timeout=timeout,
            fail_message="Reset 后按钮状态未恢复为全部加购")

    def wait_buttons_restored_after_reset(self, expected_add_count: int = 6,
                                          timeout: int = None) -> None:
        """Reset 后等待按钮复位，带自动刷新兜底

        实测发现：当前站点版本 Reset App State 清除购物车（角标消失）后，
        商品按钮状态可能不会在原页即时重渲染；刷新页面后状态即可恢复。
        策略：先原地短等（5s），未复位则刷新后按完整预算重等，仍失败才抛错。
        """
        try:
            self.wait_buttons_reset(expected_add_count, timeout=5)
            return
        except TimeoutException:
            logger.warning("Reset 后按钮未在原页复位，刷新页面后重新等待（站点版本行为差异）")
            self.refresh()
            self.wait_inventory_loaded()
            self.wait_buttons_reset(expected_add_count, timeout=timeout)

    # ===================== 业务方法：入口跳转与布局坐标 =====================

    def click_product_link(self, product_id: int) -> None:
        """点击商品标题进入详情页"""
        self.click(self.product_title_link(product_id))

    def open_cart(self) -> None:
        """点击购物车图标进入购物车页"""
        self.click(self.CART_LINK)

    def get_shopping_cart_rect(self) -> dict:
        """购物车图标位置矩形（visual_user 布局偏移探针基线采集用）"""
        return self.get_element_rect(self.CART_LINK)

    def get_primary_header_rect(self) -> dict:
        """顶部 header 位置矩形（布局偏移探针基线采集用）"""
        return self.get_element_rect(self.PRIMARY_HEADER)

    def is_cart_link_present(self) -> bool:
        """购物车图标是否存在于 DOM"""
        return self.is_element_present(self.CART_LINK, timeout=3)