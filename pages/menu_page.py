# -*- coding: utf-8 -*-
"""
menu_page.py —— 侧边栏菜单页对象（Page 对象层）

职责：侧边栏菜单元素定位 + 业务方法（开合/四个菜单项/遮罩状态），
     只调用 BasePage 底层能力。

定位来源：汉堡按钮 (By.ID, 'react-burger-menu-btn')、
          四个菜单项 [data-test='inventory-sidebar-link' / 'about-sidebar-link'
          / 'reset-sidebar-link' / 'logout-sidebar-link']、
          菜单容器 .bm-menu-wrap（aria-hidden 状态断言）、遮罩 .bm-overlay。

注意：菜单收起后元素仍可能被 Selenium 判定为"可见"（transform 移出画布
      不影响可见性判定），因此开合状态一律以 aria-hidden 属性为权威依据。
"""
import logging

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By

from base.base_page import BasePage
from pages import locators
from pages.login_page import LoginPage

logger = logging.getLogger(__name__)


class MenuPage(BasePage):
    """侧边栏菜单对象：打开/关闭/四个菜单项"""

    # 菜单开合专用等待预算（秒）：滑块动画在低负载机器/CI 下可能超过默认显式等待预算，
    # 借鉴 glitch 账号"超时上浮"思路，与默认 10s 解耦
    MENU_TIMEOUT = 20

    # ===================== 元素定位 =====================
    BURGER_BTN = (By.ID, "react-burger-menu-btn")            # 汉堡菜单按钮
    CROSS_BTN = (By.ID, "react-burger-cross-btn")            # 菜单关闭按钮
    MENU_WRAP = (By.CSS_SELECTOR, ".bm-menu-wrap")           # 菜单容器（aria-hidden 权威状态）
    INVENTORY_LIST = locators.INVENTORY_LIST                 # 商品列表容器（All Items 成功标志）
    OVERLAY = (By.CSS_SELECTOR, ".bm-overlay")               # 遮罩层
    ALL_ITEMS = (By.CSS_SELECTOR, "[data-test='inventory-sidebar-link']")  # All Items
    ABOUT = (By.CSS_SELECTOR, "[data-test='about-sidebar-link']")          # About（外链新窗口）
    RESET = (By.CSS_SELECTOR, "[data-test='reset-sidebar-link']")          # Reset App State
    LOGOUT = (By.CSS_SELECTOR, "[data-test='logout-sidebar-link']")        # Logout

    # ===================== 业务方法 =====================

    def open_menu(self, timeout: int = None) -> None:
        """点击汉堡按钮打开侧边栏：等待展开动画完成后，关闭按钮与四个菜单项全部可见

        强化说明：
        1. aria-hidden 是该站点菜单展开/收起的权威信号（transform 移出画布不影响
           Selenium 可见性判定，不能依赖 is_displayed 判断开合）；
        2. 菜单为滑块动画，aria 翻转的瞬间菜单项尚未就位，必须等元素可见后再断言；
        3. 遮罩层（.bm-overlay）在新版本站点已不再渲染，不作为打开态的必备条件，
           由用例层做"存在性"软校验。
        """
        self.click(self.BURGER_BTN)
        wait_time = timeout or self.MENU_TIMEOUT
        try:
            self.wait_attribute_equals(self.MENU_WRAP, "aria-hidden", "false",
                                       min(wait_time, 10))
        except TimeoutException:
            # CI 无头 Chrome 偶发输入事件丢失（与加购按钮同类）：JS 直接派发 click
            logger.warning("点击汉堡按钮后菜单未展开，改用 JS 触发点击复核")
            self.js_click(self.BURGER_BTN)
            self.wait_attribute_equals(self.MENU_WRAP, "aria-hidden", "false", wait_time)
        # 谓词全部使用 timeout=0 的即时探测（单次 is_displayed 判定），
        # 避免内层阻塞等待拖慢外层轮询节奏，让 0.5s 每次的轮询覆盖整个动画窗口
        self.wait_until(
            lambda _: (self.is_element_visible(self.CROSS_BTN, timeout=0)
                       and all(self.is_element_visible(locator, timeout=0)
                               for locator in (self.ALL_ITEMS, self.ABOUT,
                                               self.RESET, self.LOGOUT))),
            timeout=wait_time,
            fail_message="侧边栏展开后关键要素未全部可见",
        )

    def close_menu(self, timeout: int = None) -> None:
        """点击关闭按钮收起侧边栏，等待菜单容器进入收起态（JS 点击兜底）"""
        wait_time = timeout or self.MENU_TIMEOUT
        self.click(self.CROSS_BTN)
        try:
            self.wait_attribute_equals(self.MENU_WRAP, "aria-hidden", "true",
                                       min(wait_time, 10))
        except TimeoutException:
            logger.warning("点击关闭按钮后菜单未收起，改用 JS 触发点击复核")
            self.js_click(self.CROSS_BTN)
            self.wait_attribute_equals(self.MENU_WRAP, "aria-hidden", "true", wait_time)

    def get_menu_aria_hidden(self) -> str:
        """回读菜单容器 aria-hidden（'false'=展开 / 'true'=收起）"""
        return self.get_attribute(self.MENU_WRAP, "aria-hidden")

    def is_menu_closed(self) -> bool:
        """菜单是否处于收起态"""
        return self.get_menu_aria_hidden() == "true"

    def is_menu_visible(self) -> bool:
        """菜单容器是否可见"""
        return self.is_element_visible(self.MENU_WRAP)

    def is_overlay_present(self) -> bool:
        """遮罩层是否存在于 DOM（新版本站点已不再渲染 .bm-overlay，以存在性为权威依据）"""
        return self.get_element_count_immediate(self.OVERLAY) > 0

    def is_overlay_visible(self) -> bool:
        """遮罩层是否可见（仅在元素存在时调用，用于老版本站点断言）"""
        return self.is_element_visible(self.OVERLAY)

    def is_cross_visible(self) -> bool:
        """关闭按钮是否可见"""
        return self.is_element_visible(self.CROSS_BTN)

    def are_menu_items_visible(self) -> bool:
        """四个菜单项是否全部可见"""
        for locator in (self.ALL_ITEMS, self.ABOUT, self.RESET, self.LOGOUT):
            if not self.is_element_visible(locator):
                return False
        return True

    # -- 四个菜单项操作 --

    def click_all_items(self) -> None:
        """点击 All Items（回到商品列表页；原生点击 → JS 兜底）"""
        self.click_until(self.ALL_ITEMS, self._is_inventory_visible,
                         fail_message="点击 All Items 后未回到商品列表")

    def _is_inventory_visible(self) -> bool:
        return self.is_element_visible(self.INVENTORY_LIST, timeout=0)

    def click_about(self) -> None:
        """点击 About（跳转 Sauce Labs 官网，站点实现可能为新窗口或同窗口跳转）"""
        self.click(self.ABOUT)

    def open_about_and_navigate(self, url_prefix: str, timeout: int = None) -> bool:
        """点击 About 并进入外链页（兼容"新开窗口"与"同窗口跳转"两种实现）

        :param url_prefix: 外链 URL 前缀（来自 config/env.yaml，页面层不读配置）
        :return: True=新开窗口（调用方负责关闭并切回主窗口）；False=同窗口跳转
        """
        self.click_about()
        wait_time = timeout or self.MENU_TIMEOUT
        try:
            # 原文档约定的 target=_blank 行为：等待第二个窗口出现
            self.wait_window_count(2, timeout=wait_time)
            self.switch_to_new_window()
            return True
        except TimeoutException:
            # 站点已改为同窗口跳转：等待当前窗口 URL 变化到外链域名
            self.wait_url_contains(url_prefix, timeout=wait_time)
            return False

    def click_reset(self) -> None:
        """点击 Reset App State（重置购物车与按钮状态）"""
        self.click(self.RESET)

    def click_logout(self, retries: int = 1, fallback_url: str = None) -> None:
        """点击 Logout（退出登录回到登录页）

        健壮性：公共演示站偶发"点击后导航无响应"；CI headless 环境下站点前端 JS 卡死时
        点击 Logout 根本不会触发跳转。点击后等待【登录页 user-name 输入框可见】作为跳转
        生效的权威标志；超时且仍停留在商品页时重试点击（默认 1 次，保留原预警日志）。
        重试耗尽仍未跳转且调用方提供 fallback_url 时兜底：删除全部 Cookie + 强制打开
        登录页 URL（HTTP 直达，绕开卡死的页面 JS 导航依赖），再等待 user-name 可见。
        退出是幂等操作，兜底无副作用；未提供 fallback_url 时原样抛出最后一次超时。
        """
        def _reopen_menu_if_closed() -> None:
            """首次点击后菜单已自动收起（Logout 仍在 DOM 但移出画布不可点击），补点前重新展开"""
            if self.is_menu_closed():
                self.open_menu()

        def _cookie_fallback() -> bool:
            """兜底：删除会话 Cookie 后直开登录页 URL，强制导航回登录页，再等待输入框可见"""
            if not fallback_url:
                return False
            logger.warning("点击 Logout 重试用尽仍未回到登录页（站点 JS 卡死/导航无响应），"
                           "兜底：清除 Cookie 并直达登录页 URL: %s", fallback_url)
            self.delete_all_cookies()
            self.open_url(fallback_url)
            self.find_element(LoginPage.USERNAME_INPUT)
            return True

        self.click_robust(
            self.LOGOUT,
            # 主路径：登录页 user-name 输入框可见 = 已成功跳转回登录页（唯一权威校验）
            lambda: self.is_element_visible(LoginPage.USERNAME_INPUT, timeout=0),
            timeout=self.timeout,
            js_timeout=5,
            retries=retries,
            # 仍停留在商品页（菜单容器还在 DOM）时才重试点击
            retry_allowed=lambda: self.get_element_count_immediate(self.MENU_WRAP) > 0,
            before_retry=_reopen_menu_if_closed,
            on_final_failure=_cookie_fallback,
            fail_message="点击 Logout 后未跳转回登录页（原生/JS 点击均无效）",
        )