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
import json
import logging
from decimal import Decimal
from typing import Optional

import allure
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By

from base.base_page import BasePage
from pages import locators

logger = logging.getLogger(__name__)


class InventoryPage(BasePage):
    """商品列表页对象：商品展示/排序/加购/移除/购物车角标"""

    # 加购后等待按钮切换的快速预算（秒）：前端状态变更应秒级完成，超时即进入多级兜底
    ADD_CONFIRM_TIMEOUT = 10

    # ===================== 元素定位 =====================
    PRODUCT_SORT = (By.CSS_SELECTOR, "select[data-test='product-sort-container']")  # 排序下拉框
    INVENTORY_LIST = locators.INVENTORY_LIST                             # 商品列表容器
    INVENTORY_ITEM = locators.INVENTORY_ITEM                             # 商品块
    INVENTORY_ITEM_NAME = locators.INVENTORY_ITEM_NAME                   # 商品名称
    INVENTORY_ITEM_PRICE = (By.CSS_SELECTOR, ".inventory_item_price")   # 商品价格
    INVENTORY_ITEM_DESC = (By.CSS_SELECTOR, ".inventory_item_desc")     # 商品描述
    INVENTORY_ITEM_IMG = locators.INVENTORY_ITEM_IMG                     # 商品图片
    ITEM_IMG_ALT = (By.CSS_SELECTOR, ".inventory_item_img")             # 图片元素（alt 属性断言）
    BADGE = locators.BADGE                                               # 购物车角标（归零后从 DOM 移除）
    CART_LINK = locators.CART_LINK                                       # 购物车图标
    PRIMARY_HEADER = locators.PRIMARY_HEADER                             # 顶部 header
    ADD_ANY = locators.ADD_TO_CART_ANY                                   # 所有加购按钮
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

    def wait_inventory_loaded(self, timeout: Optional[int] = None) -> None:
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
        return self.get_attribute(self.PRODUCT_SORT, "value") or ""

    def sort_and_wait_names(self, value: str, expected_names: list, timeout: Optional[int] = None) -> None:
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

    def wait_product_images_loaded(self, timeout: Optional[int] = None) -> None:
        """等待 6 张商品图片全部完成解码（naturalWidth 断言的前置等待，防采样竞态）"""
        self.wait_all_images_loaded(self.INVENTORY_ITEM_IMG, timeout)

    # ===================== 业务方法：加购 / 移除 / 角标 =====================

    def click_add_button(self, slug: str) -> None:
        """仅点击加购按钮（error_user 场景加购可能无响应，不做状态等待）"""
        self.click(self.add_button(slug))

    def add_to_cart(self, slug: str, retries: int = 1) -> None:
        """加购单个商品并等待按钮切换为 Remove（功能正常站点）

        健壮性（按失效成因逐级兜底，每级均带独立等待预算）：
        1. 原生 click 未被前端响应（CI 无头 Chrome 偶发：点击命令成功但 React 未处理）：
           改用 JS 直接派发 click 事件，绕过输入坐标/命中测试链路；
        2. 已入车但商品卡片未重渲染（前端状态树不同步）：刷新页面从 localStorage 取回状态；
        3. 点击彻底丢失：加购按钮仍在时重试点击（默认 1 次）。
        全部兜底仍失败时采集现场诊断（坐标/命中元素/购物车存储）并附件进 Allure。
        """

        def _refresh_and_recheck() -> bool:
            """兜底二：刷新页面复核（覆盖"已入车但按钮未重渲染"的前端不同步）"""
            logger.warning("加购[%s]仍未生效，刷新页面重渲染后复核", slug)
            self.refresh()
            self.wait_inventory_loaded()
            return self.is_element_visible(self.remove_button(slug), timeout=3)

        self.click_robust(
            self.add_button(slug),
            lambda: self.is_element_visible(self.remove_button(slug), timeout=0),
            timeout=self.ADD_CONFIRM_TIMEOUT,
            js_timeout=5,
            retries=retries,
            post_js_recheck=_refresh_and_recheck,
            retry_allowed=lambda: not self.is_add_button_absent(slug),
            on_final_failure=lambda: self._attach_add_diagnostics(slug),
            fail_message=f"加购[{slug}]失败：原生点击/JS 点击/刷新复核均未生效",
        )

    def _attach_add_diagnostics(self, slug: str) -> None:
        """采集加购失败现场诊断（按钮坐标/命中元素/购物车存储/按钮清单）并附件进 Allure"""
        selector = self.add_button(slug)[1]
        script = """
        const s = arguments[0];
        const el = document.querySelector(s);
        const out = {selector: s, url: location.href,
                     scrollX: window.scrollX, scrollY: window.scrollY,
                     dpr: window.devicePixelRatio,
                     cart: (() => { try { return localStorage.getItem('cart-contents'); }
                                    catch (e) { return 'ERR:' + e.name; } })()};
        if (!el) { out.found = false; return out; }
        const r = el.getBoundingClientRect();
        const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
        const hit = document.elementFromPoint(cx, cy);
        out.found = true;
        out.rect = {x: r.x, y: r.y, width: r.width, height: r.height};
        out.hit = hit ? {tag: hit.tagName, cls: String(hit.className || ''),
                         test: hit.getAttribute('data-test')} : null;
        out.addButtons = Array.from(document.querySelectorAll("[data-test^='add-to-cart-']"))
                              .map(b => b.getAttribute('data-test'));
        out.removeButtons = Array.from(document.querySelectorAll("[data-test^='remove-']"))
                                 .map(b => b.getAttribute('data-test'));
        return out;
        """
        try:
            info = self.execute_script(script, selector)
            logger.error("加购失败现场诊断: %s", json.dumps(info, ensure_ascii=False))
            allure.attach(json.dumps(info, ensure_ascii=False, indent=2),
                          name=f"加购失败诊断_{slug}",
                          attachment_type=allure.attachment_type.JSON)
        except Exception as exc:  # 诊断失败不影响原异常抛出
            logger.warning("加购失败诊断采集异常: %s", exc)

    def remove_from_cart(self, slug: str, retries: int = 1) -> None:
        """移除单个商品并等待按钮恢复为加购（兜底顺序与加购一致）

        原生点击 → JS 派发 click（CI 无头 Chrome 偶发输入事件丢失）→ 重试点击（默认 1 次）。
        """
        self.click_robust(
            self.remove_button(slug),
            lambda: self.is_element_visible(self.add_button(slug), timeout=0),
            timeout=10,
            js_timeout=5,
            retries=retries,
            retry_allowed=lambda: not self.is_remove_button_absent(slug),
            fail_message=f"移除[{slug}]失败：原生点击/JS 点击均未生效",
        )

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
        """等待购物车角标数字精确变为指定值（避免 '1' 子串匹配 '12'）"""
        self.wait_text_equals(self.BADGE, text)

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

    def wait_badge_disappear(self, timeout: Optional[int] = None) -> None:
        """等待角标从 DOM 移除（清空/重置后的确定性等待，替代短轮询断言）"""
        self.wait_element_disappear(self.BADGE, timeout)

    def wait_buttons_reset(self, expected_add_count: int = 6, timeout: Optional[int] = None) -> None:
        """等待加购/移除按钮状态复位（Reset App State 后渲染完成的确定性等待）"""
        self.wait_until(
            lambda _: (self.get_add_button_count() == expected_add_count
                       and self.get_remove_button_count() == 0),
            timeout=timeout,
            fail_message="Reset 后按钮状态未恢复为全部加购")

    def wait_buttons_restored_after_reset(self, expected_add_count: int = 6,
                                          timeout: Optional[int] = None) -> None:
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

    def click_product_link(self, product_id: int, retries: int = 1) -> None:
        """点击商品标题进入详情页

        健壮性：与 Checkout/Logout 同类——CI 无头 Chrome 偶发输入事件丢失
        （点击成功但详情页不加载）。兜底顺序：原生点击 → JS 派发 click →
        重试原生点击（默认 1 次）。标题链接消失 = 已离开列表页。
        """
        link = self.product_title_link(product_id)
        self.click_robust(
            link,
            lambda: not self.is_element_visible(link, timeout=0),
            timeout=10,
            js_timeout=5,
            retries=retries,
            retry_allowed=lambda: self.get_element_count_immediate(link) > 0,
            fail_message=f"点击商品[{product_id}]后未离开列表页（原生/JS 点击均无效）",
        )

    def open_cart(self, retries: int = 1, fallback_url: Optional[str] = None) -> None:
        """点击购物车图标进入购物车页（URL 进入购物车页为成功标志）

        健壮性：新版站点为 React SPA，购物车图标只绑定客户端路由 push，CI 无头
        Chrome 偶发"点击后路由不跳转"（与 Add 按钮同类的输入事件丢失）。
        兜底顺序：原生点击 → JS 派发 click → 重试原生点击（默认 1 次）→
        fallback_url URL 直达——购物车状态存于 localStorage，直达与点击导航等价。
        """

        def _url_fallback() -> bool:
            """重试用尽仍未跳转时 URL 直达（无 fallback_url 则交给统一异常）"""
            if not fallback_url:
                return False
            logger.warning("重试用尽仍未跳转，改用 URL 直达购物车页: %s", fallback_url)
            self.open_url(fallback_url)
            return True

        self.click_robust(
            self.CART_LINK,
            lambda: "/cart.html" in self.get_current_url(),
            timeout=10,
            js_timeout=5,
            retries=retries,
            on_final_failure=_url_fallback,
            fail_message="点击购物车图标后未进入购物车页（原生/JS 点击均无效）",
        )

    def get_shopping_cart_rect(self) -> dict:
        """购物车图标位置矩形（visual_user 布局偏移探针基线采集用）"""
        return self.get_element_rect(self.CART_LINK)

    def get_primary_header_rect(self) -> dict:
        """顶部 header 位置矩形（布局偏移探针基线采集用）"""
        return self.get_element_rect(self.PRIMARY_HEADER)

    def is_cart_link_present(self) -> bool:
        """购物车图标是否存在于 DOM"""
        return self.is_element_present(self.CART_LINK, timeout=3)