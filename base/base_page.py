# -*- coding: utf-8 -*-
"""
base_page.py —— BasePage 基础层（框架底层，所有页面对象类的父类）

职责：统一封装 Selenium 4 官方底层通用操作，供 pages 层继承复用。
本层只提供“怎么操作浏览器”的原子能力（查找/等待/点击/输入/文本/弹窗/
iframe/窗口/鼠标/JS/截图等），不包含任何业务逻辑。

设计要点：
1. 严格遵守 Selenium 4 标准 API（driver.find_element(By.XXX, ...)），
   全项目禁用 find_element_by_xxx 等已废弃语法；
2. 全项目禁用 time.sleep，统一使用显式等待（WebDriverWait + expected_conditions）；
3. 默认等待元素“可见”，点击前强制等待元素“可点击”，从机制上降低用例偶发失败率；
4. 关键操作失败自动截图 + 抛出异常，保证失败现场可回溯。
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

import allure
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.alert import Alert
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

logger = logging.getLogger(__name__)

# 项目根目录与本层通用常量
PROJECT_ROOT = Path(__file__).resolve().parent.parent
# 截图保存目录：reports/screenshots（用例失败自动截图统一落盘于此）
SCREENSHOT_DIR = PROJECT_ROOT / "reports" / "screenshots"

# 定位器类型别名：全项目统一使用 (By.XXX, "表达式") 元组，如 (By.ID, "user-name")
Locator = Tuple[str, str]


class BasePage:
    """所有页面对象类的父类，封装 Selenium 4 底层通用操作"""

    # 常量：显式等待默认参数（可通过构造参数注入覆盖，真实值来自 config/env.yaml）
    DEFAULT_TIMEOUT = 10          # 默认超时时间（秒）
    DEFAULT_POLL_FREQUENCY = 0.5  # 默认轮询间隔（秒）

    def __init__(self, driver: WebDriver,
                 timeout: int = DEFAULT_TIMEOUT,
                 poll_frequency: float = DEFAULT_POLL_FREQUENCY):
        """初始化页面对象：注入全局共享 driver 与等待策略"""
        self.driver = driver
        self.timeout = timeout
        self.poll_frequency = poll_frequency

    def _wait(self, timeout: Optional[int] = None) -> WebDriverWait:
        """构造显式等待对象（内部私有方法，统一超时与轮询参数）"""
        return WebDriverWait(self.driver, timeout or self.timeout, self.poll_frequency)

    # ===================== 元素查找（显式等待） =====================

    def find_element(self, locator: Locator, timeout: Optional[int] = None) -> WebElement:
        """显式等待元素【可见】后返回该元素（最常用的查找方式）"""
        logger.info("等待元素可见: %s", locator)
        try:
            return self._wait(timeout).until(EC.visibility_of_element_located(locator))
        except TimeoutException as exc:
            logger.error("等待元素可见超时: %s", locator)
            self.save_screenshot("element_timeout")
            # 附加失败时的页面源码，便于离线分析定位原因
            allure.attach(self.driver.page_source, "失败时页面源码", allure.attachment_type.HTML)
            # 重新抛出带清晰中文说明的异常，报错信息直接可读
            raise TimeoutException(
                f"显式等待 {timeout or self.timeout}s 后元素仍不可见: {locator}") from exc

    def find_element_presence(self, locator: Locator, timeout: Optional[int] = None) -> WebElement:
        """显式等待元素【出现在 DOM】（不要求可见）后返回该元素"""
        logger.info("等待元素出现: %s", locator)
        return self._wait(timeout).until(EC.presence_of_element_located(locator))

    def find_element_clickable(self, locator: Locator, timeout: Optional[int] = None) -> WebElement:
        """显式等待元素【可点击】后返回该元素（点击前专用）"""
        logger.info("等待元素可点击: %s", locator)
        return self._wait(timeout).until(EC.element_to_be_clickable(locator))

    def find_elements(self, locator: Locator, timeout: Optional[int] = None) -> List[WebElement]:
        """显式等待【至少一个匹配元素出现在 DOM】后返回全部匹配元素列表"""
        logger.info("查找元素列表: %s", locator)
        self._wait(timeout).until(EC.presence_of_all_elements_located(locator))
        return self.driver.find_elements(*locator)  # Selenium 4 标准语法

    # ===================== 元素状态判断（返回布尔值，不抛异常） =====================

    def is_element_present(self, locator: Locator, timeout: int = 2) -> bool:
        """判断元素是否出现在 DOM 中"""
        try:
            self._wait(timeout).until(EC.presence_of_element_located(locator))
            return True
        except TimeoutException:
            return False

    def is_element_visible(self, locator: Locator, timeout: int = 2) -> bool:
        """判断元素是否可见"""
        try:
            self._wait(timeout).until(EC.visibility_of_element_located(locator))
            return True
        except TimeoutException:
            return False

    def is_element_enabled(self, locator: Locator, timeout: Optional[int] = None) -> bool:
        """判断元素是否可见且可交互（enabled）"""
        return self.find_element(locator, timeout).is_enabled()

    def is_element_clickable(self, locator: Locator, timeout: Optional[int] = None) -> bool:
        """判断元素是否可点击"""
        try:
            self._wait(timeout).until(EC.element_to_be_clickable(locator))
            return True
        except TimeoutException:
            return False

    def wait_element_disappear(self, locator: Locator, timeout: Optional[int] = None) -> None:
        """等待元素从页面消失（不可见或移出 DOM 均满足，常用于等待 loading 遮罩关闭）"""
        logger.info("等待元素消失: %s", locator)
        self._wait(timeout).until(EC.invisibility_of_element_located(locator))

    def wait_text_present(self, locator: Locator, text: str, timeout: Optional[int] = None) -> None:
        """等待元素文本变为指定内容（常用于角标数字变化类断言）"""
        logger.info("等待元素文本变为[%s]: %s", text, locator)
        self._wait(timeout).until(EC.text_to_be_present_in_element(locator, text))

    # ===================== 基础操作：点击 / 输入 / 取值 =====================

    def click(self, locator: Locator, timeout: Optional[int] = None) -> None:
        """等待元素可点击后执行点击（最常用操作，失败自动截图并抛异常）"""
        logger.info("点击元素: %s", locator)
        element = self.find_element_clickable(locator, timeout)
        try:
            element.click()
        except Exception as exc:
            logger.error("点击元素失败: %s, 异常: %s", locator, exc)
            self.save_screenshot("click_fail")
            raise

    def input_text(self, locator: Locator, text: str, clear_first: bool = True) -> None:
        """在元素中输入文本：默认先清空再输入，模拟真实键盘输入

        安全说明：日志中不回显输入内容，避免密码等敏感信息泄露到日志文件。
        异常防护：捕获元素失效/被遮挡等常见注入异常，截图留证并抛出清晰错误。
        """
        logger.info("向元素输入内容: %s", locator)
        element = self.find_element(locator)
        try:
            if clear_first:
                element.clear()
            element.send_keys(text)
        except Exception as exc:
            logger.error("输入内容失败: %s, 异常: %s", locator, exc)
            self.save_screenshot("input_fail")
            raise

    def get_text(self, locator: Locator, timeout: Optional[int] = None) -> str:
        """获取元素可见文本（异常时打 ERROR 日志并原样抛出）"""
        try:
            return self.find_element(locator, timeout).text
        except Exception as exc:
            logger.error("获取元素文本失败: %s, 异常: %s", locator, exc)
            raise

    def get_attribute(self, locator: Locator, attribute: str, timeout: Optional[int] = None) -> str:
        """获取元素属性值（如 value / src / aria-hidden）

        注意：使用"存在性"等待而非"可见性"——隐藏元素（如收起态菜单容器
        .bm-menu-wrap）的属性同样可读，可见性等待会导致读取隐藏元素属性时超时。
        """
        logger.info("获取元素属性[%s]: %s", attribute, locator)
        return self.find_element_presence(locator, timeout).get_attribute(attribute)

    def get_element_rect(self, locator: Locator, timeout: Optional[int] = None) -> dict:
        """获取元素位置矩形 {x, y, width, height}（布局偏移探针用）"""
        return self.find_element(locator, timeout).rect

    # ===================== 键盘操作 =====================

    def press_enter(self, locator: Locator, timeout: Optional[int] = None) -> None:
        """对元素发送回车键（常用于搜索框提交）"""
        self.find_element(locator, timeout).send_keys(Keys.ENTER)

    # ===================== JS 执行与滚动 =====================

    def execute_script(self, script: str, *args):
        """执行 JS 脚本"""
        return self.driver.execute_script(script, *args)

    def js_click(self, locator: Locator, timeout: Optional[int] = None) -> None:
        """JS 方式点击（元素被遮挡导致原生 click 失败时的兜底方案）"""
        element = self.find_element_presence(locator, timeout)
        self.execute_script("arguments[0].click();", element)

    def scroll_to_element(self, locator: Locator, timeout: Optional[int] = None) -> WebElement:
        """滚动页面使元素进入可视区域（常用于长页面底部元素）"""
        element = self.find_element_presence(locator, timeout)
        self.execute_script("arguments[0].scrollIntoView(true);", element)
        return element

    def scroll_to_top(self) -> None:
        """滚动到页面顶部"""
        self.execute_script("window.scrollTo(0, 0);")

    def scroll_to_bottom(self) -> None:
        """滚动到页面底部"""
        self.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    # ===================== 鼠标操作（ActionChains） =====================

    def move_to_element(self, locator: Locator, timeout: Optional[int] = None) -> None:
        """鼠标悬停到元素上（常用于展开下拉菜单/二级导航）"""
        element = self.find_element(locator, timeout)
        ActionChains(self.driver).move_to_element(element).perform()

    def double_click(self, locator: Locator, timeout: Optional[int] = None) -> None:
        """双击元素"""
        element = self.find_element(locator, timeout)
        ActionChains(self.driver).double_click(element).perform()

    def right_click(self, locator: Locator, timeout: Optional[int] = None) -> None:
        """右键点击元素（触发上下文菜单）"""
        element = self.find_element(locator, timeout)
        ActionChains(self.driver).context_click(element).perform()

    def drag_and_drop(self, source_locator: Locator, target_locator: Locator) -> None:
        """将源元素拖拽到目标元素"""
        source = self.find_element(source_locator)
        target = self.find_element(target_locator)
        ActionChains(self.driver).drag_and_drop(source, target).perform()

    # ===================== 弹窗处理（Alert） =====================

    def switch_to_alert(self, timeout: Optional[int] = None) -> Alert:
        """显式等待弹窗出现并切换，返回 Alert 对象"""
        logger.info("等待弹窗出现")
        self._wait(timeout).until(EC.alert_is_present())
        return self.driver.switch_to.alert

    def get_alert_text(self, timeout: Optional[int] = None) -> str:
        """获取弹窗文本"""
        return self.switch_to_alert(timeout).text

    def alert_accept(self, timeout: Optional[int] = None) -> None:
        """点击弹窗【确定】"""
        logger.info("点击弹窗[确定]")
        self.switch_to_alert(timeout).accept()

    def alert_dismiss(self, timeout: Optional[int] = None) -> None:
        """点击弹窗【取消】"""
        logger.info("点击弹窗[取消]")
        self.switch_to_alert(timeout).dismiss()

    def alert_input_text(self, text: str, timeout: Optional[int] = None) -> None:
        """在弹窗输入框中输入文本并点确定（prompt 型弹窗）"""
        alert = self.switch_to_alert(timeout)
        alert.send_keys(text)
        alert.accept()

    # ===================== iframe 切换 =====================

    def switch_to_iframe(self, iframe_reference, timeout: Optional[int] = None) -> None:
        """切换到 iframe：支持定位器元组 (By.XXX, 表达式) 或 iframe 的 name/id 字符串"""
        logger.info("切换到 iframe: %s", iframe_reference)
        self._wait(timeout).until(EC.frame_to_be_available_and_switch_to_it(iframe_reference))

    def switch_to_default_content(self) -> None:
        """从 iframe 切回主文档"""
        self.driver.switch_to.default_content()

    # ===================== 多窗口处理 =====================

    def get_window_count(self) -> int:
        """当前浏览器窗口/标签页数量（外链新开窗口断言用）"""
        return len(self.driver.window_handles)

    def switch_to_new_window(self) -> None:
        """切换到最近新打开的窗口/标签页"""
        handles = self.driver.window_handles
        logger.info("共 %d 个窗口句柄，切换到最新窗口", len(handles))
        self.driver.switch_to.window(handles[-1])

    def switch_to_window(self, index: int) -> None:
        """按索引切换窗口（0 为主窗口）"""
        self.driver.switch_to.window(self.driver.window_handles[index])

    def switch_to_main_window(self) -> None:
        """切回主窗口（第一个句柄）"""
        self.driver.switch_to.window(self.driver.window_handles[0])

    def close_current_window(self) -> None:
        """关闭当前窗口"""
        self.driver.close()

    # ===================== 页面导航 =====================

    def open_url(self, url: str) -> None:
        """打开指定页面"""
        logger.info("打开页面: %s", url)
        self.driver.get(url)

    def get_current_url(self) -> str:
        """获取当前页面 URL"""
        return self.driver.current_url

    def get_page_title(self) -> str:
        """获取当前页面浏览器标题"""
        return self.driver.title

    def refresh(self) -> None:
        """刷新当前页面"""
        logger.info("刷新页面")
        self.driver.refresh()

    def back(self) -> None:
        """浏览器后退"""
        logger.info("浏览器后退")
        self.driver.back()

    def forward(self) -> None:
        """浏览器前进"""
        logger.info("浏览器前进")
        self.driver.forward()

    def wait_url_contains(self, url_part: str, timeout: Optional[int] = None) -> None:
        """等待当前 URL 包含指定片段（页面跳转类断言前置等待）"""
        logger.info("等待 URL 包含: %s", url_part)
        self._wait(timeout).until(EC.url_contains(url_part))

    def wait_url_to_be(self, url: str, timeout: Optional[int] = None) -> None:
        """等待当前 URL 精确等于指定地址"""
        logger.info("等待 URL 精确变为: %s", url)
        self._wait(timeout).until(EC.url_to_be(url))

    # ===================== Cookie 操作 =====================

    def get_cookie(self, name: str) -> Optional[dict]:
        """按名称获取 Cookie，不存在返回 None（登录态断言的权威依据）"""
        return self.driver.get_cookie(name)

    def delete_all_cookies(self) -> None:
        """清空当前会话全部 Cookie（未登录/会话失效用例的前置操作）"""
        logger.info("清空全部 Cookie")
        self.driver.delete_all_cookies()

    # ===================== 下拉框操作（Select） =====================

    def select_by_value(self, locator: Locator, value: str, timeout: Optional[int] = None) -> None:
        """下拉框按 value 选中选项（Select 为 Selenium 标准组件，替代手写点击）"""
        logger.info("下拉选择 value=%s: %s", value, locator)
        element = self.find_element_presence(locator, timeout)
        Select(element).select_by_value(value)

    # ===================== 自定义条件等待（通用工具） =====================

    def wait_until(self, condition, timeout: Optional[int] = None,
                   fail_message: str = "自定义等待条件未满足") -> None:
        """等待自定义条件成立（condition 为可调用对象，接收 driver 参数，返回 True 即通过）"""
        try:
            self._wait(timeout).until(condition)
        except TimeoutException:
            logger.error("等待条件超时: %s", fail_message)
            raise

    def wait_attribute_equals(self, locator: Locator, attribute: str, expected: str,
                              timeout: Optional[int] = None) -> None:
        """等待元素某属性值变为期望值（如侧边栏 aria-hidden == 'true'）"""
        logger.info("等待元素属性[%s]变为[%s]: %s", attribute, expected, locator)

        def _predicate(driver):
            try:
                element = driver.find_element(*locator)
            except NoSuchElementException:
                return False
            return element.get_attribute(attribute) == expected

        self._wait(timeout).until(_predicate)

    def wait_window_count(self, count: int, timeout: Optional[int] = None) -> None:
        """等待浏览器窗口/标签页数量达到指定值（外链新开窗口场景）"""
        logger.info("等待窗口数量达到 %d", count)
        self._wait(timeout).until(lambda d: len(d.window_handles) == count)

    def is_alert_present(self, timeout: int = 3) -> bool:
        """判断是否存在弹窗（返回布尔值，不抛异常）"""
        try:
            self._wait(timeout).until(EC.alert_is_present())
            return True
        except TimeoutException:
            return False

    def get_element_count_immediate(self, locator: Locator) -> int:
        """立即统计匹配元素数量（不做显式等待）

        用途：'期望数量为 0' 的断言场景（购物车清空、角标消失、按钮复位）。
        find_elements 内置的 presence_of_all_elements_located 在元素数为 0 时
        会一直等到超时抛异常，无法表达"零个"，因此零计数必须走即时统计。
        """
        return len(self.driver.find_elements(*locator))

    def wait_all_images_loaded(self, locator: Locator, timeout: Optional[int] = None) -> None:
        """等待匹配元素对应的全部图片完成解码（naturalWidth > 0）

        用途：图片断言（naturalWidth/加载状态）前的前置等待。
        页面刚渲染完成时图片可能尚未解码，直接采样会得到 naturalWidth=0 的误报。
        """
        def _predicate(driver):
            images = driver.find_elements(*locator)
            if not images:
                return False
            return all(int(img.get_attribute("naturalWidth") or 0) > 0 for img in images)

        self._wait(timeout).until(_predicate)

    # ===================== 截图 =====================

    def save_screenshot(self, name: str = "screenshot") -> str:
        """保存当前页面截图，按“名称_时间戳.png”命名到 reports/screenshots/，返回绝对路径"""
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = SCREENSHOT_DIR / f"{name}_{timestamp}.png"
        self.driver.save_screenshot(str(file_path))  # Selenium 4 官方截图 API
        logger.info("截图已保存: %s", file_path)
        return str(file_path)