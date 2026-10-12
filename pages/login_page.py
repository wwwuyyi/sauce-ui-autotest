# -*- coding: utf-8 -*-
"""
login_page.py —— 登录页面对象（Page 对象层）

职责：
1. 元素定位：集中管理登录表单及“登录结果校验”相关元素的 By.XXX 定位器；
2. 业务方法：组合 BasePage 底层能力形成登录流程（输入账号/密码/点击登录）
   与登录结果校验方法，供用例层直接调用断言。

分层约定：
- 本层只允许出现“元素定位常量”与“业务方法组合”，禁止出现 driver 直接操作、
  显式等待等底层代码（全部复用 BasePage）；
- 登录模块用例的预期结果落在商品列表页（inventory），为保持目录结构内聚，
  登录结果校验的定位与方法统一收口在本页面类中。

原始定位来源（《自动化执行注意事项》§1.2）：
- data-test 属性优先：h3[data-test='error']、[data-test='shopping-cart-link'] 等；
- 登录三要素官方推荐直接用 ID：user-name / password / login-button。
"""
import logging
import time

from selenium.webdriver.common.by import By

from base.base_page import BasePage

logger = logging.getLogger(__name__)


class LoginPage(BasePage):
    """登录页对象：登录表单操作 + 登录结果校验"""

    # ===================== 一、登录表单元素（By.XXX 标准语法） =====================
    USERNAME_INPUT = (By.ID, "user-name")                           # 用户名输入框
    PASSWORD_INPUT = (By.ID, "password")                            # 密码输入框
    LOGIN_BUTTON = (By.ID, "login-button")                          # 登录按钮
    ERROR_MESSAGE = (By.CSS_SELECTOR, "h3[data-test='error']")      # 错误提示文案（登录/结算/未登录共用）
    ERROR_CONTAINER = (By.CSS_SELECTOR, ".error-message-container") # 错误提示容器

    # ===================== 二、登录结果校验元素（商品列表页） =====================
    INVENTORY_LIST = (By.CSS_SELECTOR, ".inventory_list")             # 商品列表容器
    INVENTORY_ITEM = (By.CSS_SELECTOR, ".inventory_item")             # 商品块
    INVENTORY_ITEM_NAME = (By.CSS_SELECTOR, ".inventory_item_name")   # 商品名称
    INVENTORY_ITEM_IMG = (By.CSS_SELECTOR, "img.inventory_item_img")  # 商品图片
    PRODUCTS_TITLE = (By.CSS_SELECTOR, ".title")                      # 页面主标题（Products）
    ADD_TO_CART_BTN = (By.CSS_SELECTOR, "[data-test^='add-to-cart-']")    # 所有加购按钮
    SHOPPING_CART_LINK = (By.CSS_SELECTOR, "[data-test='shopping-cart-link']")  # 购物车图标
    PRIMARY_HEADER = (By.CSS_SELECTOR, ".primary_header")             # 顶部 header

    # ===================== 一、登录表单业务方法 =====================

    def input_username(self, username: str) -> None:
        """输入用户名"""
        self.input_text(self.USERNAME_INPUT, username)

    def input_password(self, password: str) -> None:
        """输入密码"""
        self.input_text(self.PASSWORD_INPUT, password)

    def click_login(self) -> None:
        """点击登录按钮"""
        self.click(self.LOGIN_BUTTON)

    def login(self, username: str, password: str) -> None:
        """核心业务流：输入账号密码并提交登录（登录成功/失败判定由用例层完成）"""
        logger.info("执行登录业务流: 用户名=%s", username)
        self.input_username(username)
        self.input_password(password)
        self.click_login()

    def get_username_value(self) -> str:
        """回读用户名输入框当前值（用于校验登录失败后输入未被清空）"""
        return self.get_attribute(self.USERNAME_INPUT, "value")

    def get_error_message(self) -> str:
        """获取登录错误提示文案文本"""
        return self.get_text(self.ERROR_MESSAGE)

    def is_error_container_displayed(self) -> bool:
        """错误提示容器是否可见"""
        return self.is_element_visible(self.ERROR_CONTAINER)

    def is_error_message_absent(self) -> bool:
        """错误提示是否不存在（登录成功场景：不应出现任何报错）"""
        return not self.is_element_present(self.ERROR_MESSAGE, timeout=2)

    def is_login_form_displayed(self) -> bool:
        """登录表单是否可见（登录失败停留页面的判定与可重试依据）"""
        return self.is_element_visible(self.LOGIN_BUTTON)

    def is_login_button_enabled(self) -> bool:
        """登录按钮是否可点击（可再次提交）"""
        return self.is_element_enabled(self.LOGIN_BUTTON)

    def is_login_form_gone(self) -> bool:
        """登录表单是否已从页面销毁（登录成功跳转后表单应消失）"""
        return not self.is_element_present(self.LOGIN_BUTTON, timeout=2)

    def is_inventory_absent(self) -> bool:
        """商品列表是否未出现（登录失败时不应进入商品列表页）"""
        return not self.is_element_present(self.INVENTORY_LIST, timeout=2)

    # ===================== 二、登录结果校验业务方法 =====================

    def wait_inventory_loaded(self, timeout: int = None) -> None:
        """等待商品列表页加载完成（列表容器可见即视为加载成功）"""
        self.find_element(self.INVENTORY_LIST, timeout)

    def login_and_measure_inventory_load(self, username: str, password: str,
                                         timeout: int = None) -> float:
        """登录并测量商品列表加载耗时（性能类用例：计时与断言分离）

        使用 time.monotonic() 单调时钟计时（不受系统时间调整影响），
        全程无 time.sleep；耗时 = “点击登录 → 列表可见”的真实渲染时长。
        """
        t0 = time.monotonic()            # 计时起点：点击登录前
        self.login(username, password)
        self.wait_inventory_loaded(timeout)
        elapsed = time.monotonic() - t0  # 计时终点：列表加载完成
        logger.info("登录到商品列表加载耗时: %.2f 秒", elapsed)
        return elapsed

    def get_inventory_item_count(self) -> int:
        """商品列表页商品总数"""
        return len(self.find_elements(self.INVENTORY_ITEM))

    def get_product_names(self) -> list:
        """按 DOM 顺序返回商品名称列表"""
        return [element.text for element in self.find_elements(self.INVENTORY_ITEM_NAME)]

    def get_product_image_srcs(self) -> list:
        """按 DOM 顺序返回商品图片 src 列表（problem_user 图片异常断言用）"""
        return [element.get_attribute("src") for element in self.find_elements(self.INVENTORY_ITEM_IMG)]

    def get_page_title_text(self) -> str:
        """页面主标题文本（商品列表页应为 Products）"""
        return self.get_text(self.PRODUCTS_TITLE)

    def get_add_to_cart_button_count(self) -> int:
        """加购按钮数量（error_user 用例校验登录后页面壳层完整性）"""
        return len(self.find_elements(self.ADD_TO_CART_BTN))

    def is_shopping_cart_link_present(self) -> bool:
        """购物车图标是否存在于 DOM（visual_user 布局错位但元素不丢失）"""
        return self.is_element_present(self.SHOPPING_CART_LINK, timeout=3)

    def get_shopping_cart_rect(self) -> dict:
        """购物车图标位置矩形 {x, y, width, height}（布局偏移探针用）"""
        return self.get_element_rect(self.SHOPPING_CART_LINK)

    def get_primary_header_rect(self) -> dict:
        """顶部 header 位置矩形（布局偏移探针用）"""
        return self.get_element_rect(self.PRIMARY_HEADER)