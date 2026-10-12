# -*- coding: utf-8 -*-
"""
log_util.py —— 日志工具（工具层）

职责：提供全项目唯一的日志配置，控制台 + 文件双输出：
    1. 控制台输出：本地/CI 实时观测执行过程；
    2. 文件输出：按"天"滚动（automation.log.2026-10-10.log 格式），保留 15 天，
       便于失败回溯与问题定位。

设计要点：
- 幂等初始化：根 logger 只配置一次，重复调用不会叠加重复 handler；
- 分级日志：DEBUG / INFO / WARNING / ERROR，业务流程动作打 INFO，
  异常现场打 ERROR，排障细节打 DEBUG；
- 三级降噪分级：
    a. 项目自身代码（base/ pages/ test_cases/ utils/）→ 保持 INFO/DEBUG 中文业务日志；
    b. 第三方库（selenium / urllib3 / requests 等）→ 统一显式 WARNING，
       屏蔽其内部英文 DEBUG/INFO 冗余输出（如 Selenium Manager 驱动发现日志、
       urllib3 连接池重试信息），只保留真正需要关注的告警与错误；
    c. 原理：子 logger 未显式设置级别时，生效级别向最近的上层 logger 回溯，
       因此只需给库的包根 logger 设置 WARNING，即可覆盖其整棵命名空间树；
- 各业务模块通过 logging.getLogger(__name__) 获取子 logger，
  日志自动携带模块名（如 base.base_page），可直接定位出问题的代码层。
"""
import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

# 项目根目录（本文件位于 utils/ 下，上级目录即项目根目录）
PROJECT_ROOT = Path(__file__).resolve().parent.parent
# 日志文件目录（运行时自动创建）
LOG_DIR = PROJECT_ROOT / "logs"

# 日志格式与日期格式常量（统一输出风格）
LOG_FORMAT = "%(asctime)s [%(levelname)s] [%(name)s] - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 需要降噪的第三方库 logger 名称（包根级别；新增噪音库时在此追加即可）
QUIET_THIRD_PARTY_LOGGERS = (
    "selenium",            # WebDriver 内部日志：Selenium Manager 驱动发现流程等
    "urllib3",             # HTTP 连接池：重试/复用等 DEBUG 冗余输出
    "requests",            # HTTP 请求库 DEBUG 头信息
    "charset_normalizer",  # requests 依赖的编码探测库（运行期 INFO 探测日志）
)


class LogUtil:
    """日志工具类：负责初始化并维护全局唯一的日志处理器"""

    _initialized = False  # 类变量初始化标记：保证整个进程只配置一次

    @classmethod
    def setup(cls, level: int = logging.DEBUG) -> None:
        """初始化日志系统（幂等：多次调用不会产生重复输出）

        :param level: 全局日志级别，默认 DEBUG（文件记录全部细节）
        """
        if cls._initialized:
            return

        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)

        # 1. 控制台 Handler：实时观察执行过程（只输出业务日志，第三方噪音已降级）
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

        # 2. 文件 Handler：按日期滚动（每天 0 点生成新文件，备份保留 15 天）
        LOG_DIR.mkdir(parents=True, exist_ok=True)  # 日志目录不存在时自动创建
        file_handler = TimedRotatingFileHandler(
            filename=str(LOG_DIR / "automation.log"),
            when="midnight",   # 每天午夜滚动
            interval=1,        # 滚动间隔 1 天
            backupCount=15,    # 最多保留 15 个历史文件
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)      # 文件保留最详细的 DEBUG 细节
        file_handler.suffix = ".%Y-%m-%d.log"     # 滚动文件命名：automation.log.2026-10-10.log
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

        # 3. 第三方库降噪：包根 logger 统一显式 WARNING，屏蔽内部英文 DEBUG/INFO 噪音。
        #    注意必须使用包根名称（如 selenium），子 logger（如
        #    selenium.webdriver.common.driver_finder）级别为 NOTSET 时
        #    自动回溯到此处设置的 WARNING，故无需逐个注册子 logger。
        for package_name in QUIET_THIRD_PARTY_LOGGERS:
            logging.getLogger(package_name).setLevel(logging.WARNING)

        cls._initialized = True

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """获取指定名称的 logger；未初始化时自动完成初始化"""
        cls.setup()
        return logging.getLogger(name)