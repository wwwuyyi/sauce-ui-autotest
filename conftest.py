# -*- coding: utf-8 -*-
"""
conftest.py —— Pytest 全局配置文件（框架入口的“总调度”）

职责：
1. 注册命令行参数：--browser 选择浏览器类型（chrome / firefox / edge）；
2. config fixture：读取 config/env.yaml，全项目测试数据零硬编码；
3. driver fixture：全局统一管理浏览器启动/关闭生命周期（function 级隔离，
   每个用例独立浏览器实例，登录态/cookie 互不污染）；
4. login_page fixture：注入登录页面对象（driver + 等待策略 + 打开登录页）；
5. 失败自动截图钩子：用例执行阶段失败 → 截图保存 reports/screenshots/
   命名为“用例名_时间戳.png”，同时附件进 Allure 报告；
6. Allure 环境信息：会话开始时写入 environment.properties。
"""
import logging
import os
import platform
from datetime import datetime
from pathlib import Path

import allure
import pytest
from selenium import webdriver

from utils.log_util import LogUtil
from utils.yaml_util import YamlUtil

# ---------------- 全局常量 ----------------
PROJECT_ROOT = Path(__file__).resolve().parent
CONFIG_PATH = PROJECT_ROOT / "config" / "env.yaml"
SCREENSHOT_DIR = PROJECT_ROOT / "reports" / "screenshots"
ALLURE_RESULTS_DIR = PROJECT_ROOT / "reports" / "allure_results"

# 初始化日志系统（conftest 最先被 pytest 加载，保证后续所有模块日志生效；幂等只执行一次）
LogUtil.setup()

logger = logging.getLogger(__name__)

# 会话级读取环境配置（单例 YamlUtil，全会话共享同一份，命令行参数默认值也来源于此）
CONFIG = YamlUtil().read_yaml(CONFIG_PATH)


def pytest_addoption(parser):
    """注册自定义命令行参数：--browser 选择浏览器类型"""
    parser.addoption(
        "--browser",
        action="store",
        default=CONFIG["browser"]["name"],
        choices=["chrome", "firefox", "edge"],
        help="浏览器类型: chrome / firefox / edge（默认取 config/env.yaml 配置）",
    )


def pytest_configure(config):
    """pytest 启动阶段：创建报告目录"""
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    ALLURE_RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def pytest_sessionstart(session):
    """会话开始：向 Allure 结果目录写入环境信息（报告页 Environment 区块展示）"""
    env_file = ALLURE_RESULTS_DIR / "environment.properties"
    content = (
        f"env={CONFIG['env']['name']}\n"
        f"base_url={CONFIG['base_url']}\n"
        f"browser={CONFIG['browser']['name']}\n"
        f"headless={str(CONFIG['browser']['headless']).lower()}\n"
        f"python={platform.python_version()}\n"
    )
    env_file.write_text(content, encoding="utf-8")


# ===================== Fixtures =====================

@pytest.fixture(scope="session")
def config():
    """全局配置 fixture：返回 env.yaml 全部配置（session 级，只读取一次）"""
    return CONFIG


@pytest.fixture(scope="function")
def driver(request, config):
    """driver 生命周期 fixture：用例开始前启动浏览器，用例结束后统一退出

    设计要点：
    - function 级别：每个用例独立浏览器实例，登录态/购物车/cookie 互不污染；
    - 浏览器类型优先级：命令行 --browser > env.yaml 默认值；
    - 全项目不使用隐式等待（implicitly_wait(0)），统一显式等待；
    - Selenium 4.6+ 由 Selenium Manager 自动管理浏览器驱动，无需手配 driver 路径。
    """
    browser_name = request.config.getoption("--browser")
    browser_conf = config["browser"]
    # CI 环境变量覆盖：HEADLESS=true 强制无头模式（本地/提交版默认取 env.yaml 配置）
    headless_env = (os.environ.get("HEADLESS") or "").strip().lower()
    headless = headless_env == "true" if headless_env else browser_conf["headless"]
    page_load_timeout = browser_conf["page_load_timeout"]

    logger.info("=" * 60)
    logger.info("启动浏览器: %s (headless=%s)", browser_name, headless)

    try:
        if browser_name == "chrome":
            options = webdriver.ChromeOptions()
            if headless:
                options.add_argument("--headless=new")  # Chrome 109+ 官方无头模式参数
            if browser_conf.get("window_size"):
                options.add_argument(f"--window-size={browser_conf['window_size']}")
            driver_obj = webdriver.Chrome(options=options)  # Selenium 4 标准构造方式
        elif browser_name == "edge":
            options = webdriver.EdgeOptions()
            if headless:
                options.add_argument("--headless=new")
            if browser_conf.get("window_size"):
                options.add_argument(f"--window-size={browser_conf['window_size']}")
            # Edge 驱动路径：环境变量优先（本机/CI 私有凭据不入库），提交版 env.yaml 保持空串
            edge_driver_path = os.environ.get("EDGE_DRIVER_PATH") or ""
            if edge_driver_path:  # 网络受限下载失败时，启用环境变量指定的本地驱动
                from selenium.webdriver.edge.service import Service as EdgeService
                logger.info("使用本地 Edge 驱动: %s", edge_driver_path)
                driver_obj = webdriver.Edge(
                    options=options,
                    service=EdgeService(executable_path=edge_driver_path))
            else:  # 默认：Selenium Manager 自动下载管理驱动
                driver_obj = webdriver.Edge(options=options)
        else:  # firefox
            options = webdriver.FirefoxOptions()
            if headless:
                options.add_argument("--headless")
            if browser_conf.get("window_size"):
                width, height = browser_conf["window_size"].split(",")
                options.add_argument(f"--width={width}")
                options.add_argument(f"--height={height}")
            driver_obj = webdriver.Firefox(options=options)
    except Exception as exc:
        # 浏览器启动失败兜底：给出可执行的排查建议（含 SessionNotCreated 资源耗尽场景）
        logger.error(
            "浏览器启动失败(%s)。可能原因：1) 本地浏览器未安装或版本过旧；"
            "2) 连续大量启动导致系统资源耗尽(SessionNotCreated)；"
            "3) 驱动下载被网络策略拦截。原始异常: %s", browser_name, exc)
        raise

    # 页面加载超时（Selenium 4 官方 API）
    driver_obj.set_page_load_timeout(page_load_timeout)
    # 明确关闭隐式等待：全项目只用显式等待，避免两种等待混用导致等待时长不可控
    driver_obj.implicitly_wait(0)

    yield driver_obj  # 用例期间共享 driver 实例

    # 无论用例成功或失败，统一退出浏览器
    logger.info("关闭浏览器: %s", browser_name)
    driver_obj.quit()


@pytest.fixture(scope="function")
def login_page(driver, config):
    """登录页对象 fixture：启动浏览器后打开登录页，返回注入好等待策略的 LoginPage"""
    from pages.login_page import LoginPage
    page = LoginPage(
        driver,
        timeout=config["timeout"]["explicit_wait"],
        poll_frequency=config["timeout"]["poll_frequency"],
    )
    page.open_url(config["base_url"])
    logger.info("已打开登录页: %s", config["base_url"])
    return page


@pytest.fixture(scope="function")
def page_factory(driver, config):
    """页面对象工厂 fixture：按统一等待策略创建任意页面对象，供用例自由组合

    用法：checkout_page = page_factory(CheckoutPage)
    """
    def _create(page_class, **kwargs):
        return page_class(
            driver,
            timeout=config["timeout"]["explicit_wait"],
            poll_frequency=config["timeout"]["poll_frequency"],
            **kwargs
        )
    return _create


@pytest.fixture(scope="function")
def inventory_page(login_page, page_factory, config):
    """商品列表页 fixture：standard_user 真实 UI 登录后返回 InventoryPage

    覆盖范围：除登录模块与特殊账号专项外的全部用例前置。
    铁律：正式用例一律真实 UI 登录，禁止 cookie 注入式登录。
    """
    from pages.inventory_page import InventoryPage
    account = config["accounts"]["standard"]
    # 登录+等待加载合并执行：登录被站点瞬时拒绝时自动重输重试，吸收偶发抖动
    login_page.login_and_wait_inventory(account["username"], account["password"])
    page = page_factory(InventoryPage)
    page.wait_inventory_loaded()
    return page


@pytest.fixture(scope="function")
def cart_page(inventory_page, page_factory, config):
    """购物车页 fixture：预置购物车 2 件默认商品（Backpack + Bike Light）并进入购物车页"""
    from pages.cart_page import CartPage
    inventory_page.add_items_to_cart(config["checkout"]["default_item_slugs"])
    inventory_page.open_cart()
    page = page_factory(CartPage)
    page.wait_cart_page_loaded()
    return page


@pytest.fixture(scope="function")
def checkout_step_one_page(cart_page, page_factory):
    """结算第一步 fixture：预置购物车后进入结算信息表单页，返回 CheckoutPage"""
    from pages.checkout_page import CheckoutPage
    cart_page.click_checkout()
    page = page_factory(CheckoutPage)
    page.wait_step_one_loaded()
    return page


@pytest.fixture(scope="function")
def checkout_overview_page(checkout_step_one_page, config):
    """结算概览页 fixture：填写正常信息并提交，进入概览页（同一 CheckoutPage 实例）"""
    info = config["checkout"]["valid_info"]
    checkout_step_one_page.fill_info_and_continue(info["first"], info["last"], info["zip"])
    checkout_step_one_page.wait_overview_loaded()
    return checkout_step_one_page


# ===================== Hooks（失败自动截图） =====================

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """用例执行阶段失败时：自动截图（“用例名_时间戳.png”）并附加到 Allure 报告

    关键时机：该钩子在 call 阶段结束、fixture teardown 之前触发，
    此时 driver 仍然存活，可截取到真实的失败现场。
    """
    outcome = yield
    report = outcome.get_result()

    # 只处理用例调用阶段（when == "call"）且结果为失败的情况
    if report.when == "call" and report.failed:
        driver_instance = item.funcargs.get("driver")
        if driver_instance is None:
            logger.warning("用例失败但未获取到 driver，无法截图: %s", item.name)
            return
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_name = f"{item.name}_{timestamp}.png"
        screenshot_path = SCREENSHOT_DIR / screenshot_name
        try:
            driver_instance.save_screenshot(str(screenshot_path))
            logger.error("用例失败，已自动截图: %s", screenshot_path)
            # 将截图附加到 Allure 报告，失败原因一目了然
            with open(screenshot_path, "rb") as f:
                allure.attach(
                    f.read(),
                    name="失败截图",
                    attachment_type=allure.attachment_type.PNG,
                )
        except Exception as exc:  # 截图失败不能影响用例本身的失败状态上报
            logger.error("失败截图生成异常: %s", exc)