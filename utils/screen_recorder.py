# -*- coding: utf-8 -*-
"""
screen_recorder.py —— 用例级屏幕录制器（工具层）

职责：用例执行期间在后台线程按固定间隔周期截图（环形缓冲只保留最近 N 帧），
用例【失败】时把保留帧合成为 GIF 动画并附件进 Allure 报告——
失败现场从"单张静态截图"升级为"可回放的操作过程"，几乎零人工复现。

设计要点：
1. 零侵入：后台 daemon 线程截图，与主线程业务操作并发执行，不阻塞用例；
2. 录制失败绝不反噬用例：截图异常一律吞掉（driver 忙/操作与截图并发偶发冲突），
   缺失若干帧后 GIF 依然可用；
3. 环形缓冲：deque(maxlen=N) 只保留最近 N 帧，无论用例跑多久内存占用恒定，
   覆盖"失败前最后 N×interval 秒"的过程（与失败定位的黄金窗口吻合）；
4. 延迟导入 Pillow：录制全程不依赖 Pillow，仅在合成 GIF 的一刻才 import，
   未安装 Pillow 时优雅降级（返回 False，仅保留静态截图）；
5. 体积控制：合成时等比缩放到 gif_width 宽（默认 640px），控制 GIF 体积，
   内嵌 Allure/HTML 报告与 Pages 发布都不臃肿。
"""
import logging
import threading
import time
from collections import deque
from io import BytesIO

logger = logging.getLogger(__name__)


class ScreenRecorder:
    """后台线程周期截屏，失败时把保留帧合成 GIF（每用例一个实例，随 driver 生命周期）"""

    def __init__(self, driver, interval: float = 0.5, max_frames: int = 40,
                 gif_width: int = 640):
        """
        :param driver: Selenium WebDriver 实例（与用例共享同一实例）
        :param interval: 截图间隔（秒）；max_frames × interval 即可回放时长
        :param max_frames: 环形缓冲保留的最大帧数（超出丢弃最旧帧）
        :param gif_width: GIF 输出宽度（像素，等比缩放；控制体积用）
        """
        self._driver = driver
        self._interval = interval
        self._max_frames = max_frames
        self._gif_width = gif_width
        self._frames = deque(maxlen=max_frames)   # 环形缓冲：只留最近 N 帧 PNG bytes
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        """启动后台截图线程（driver fixture 创建后调用）"""
        self._thread.start()

    def stop(self) -> None:
        """停止截图线程并等待其退出（driver quit 前调用）"""
        self._stop_event.set()
        if self._thread.is_alive():
            self._thread.join(timeout=self._interval + 1)

    def _run(self) -> None:
        """后台主循环：每 interval 秒截一张图入环形缓冲

        用 0.05s 小步长分段休眠而非单次大休眠：stop() 后最多 0.05s 即退出，
        不会因正在截图/休眠而拖慢用例收尾。
        """
        while not self._stop_event.is_set():
            try:
                self._frames.append(self._driver.get_screenshot_as_png())
            except Exception:
                pass  # 录制失败绝不反噬用例主流程（并发忙/窗口关闭等一律忽略）
            for _ in range(int(self._interval / 0.05)):
                if self._stop_event.is_set():
                    return
                time.sleep(0.05)

    def save_gif(self, path: str) -> bool:
        """把保留帧合成 GIF 保存到 path；少于 2 帧或 Pillow 缺失时返回 False

        :param path: 输出 GIF 文件路径（建议放 reports/screenshots/，与静态截图同目录）
        :return: True=GIF 已生成；False=条件不满足（调用方降级为仅静态截图）
        """
        if len(self._frames) < 2:
            logger.warning("录制帧数不足（%d），跳过 GIF 合成", len(self._frames))
            return False
        try:
            from PIL import Image  # 延迟导入：未安装 Pillow 不影响用例执行，只影响 GIF
        except ImportError:
            logger.warning("未安装 Pillow，跳过 GIF 合成（仅保留静态截图）。"
                           "安装：pip install Pillow")
            return False

        try:
            images = [Image.open(BytesIO(data)).convert("RGB") for data in self._frames]
            width = self._gif_width
            scaled = [img.resize((width, max(1, int(img.height * width / img.width))))
                      for img in images]
            scaled[0].save(
                path,
                save_all=True,
                append_images=scaled[1:],
                duration=int(self._interval * 1000),  # 帧间隔还原录制节奏
                loop=0,                               # 无限循环播放
                optimize=True,
            )
        except Exception as exc:
            logger.error("GIF 合成失败: %s", exc)
            return False

        logger.info("失败录屏 GIF 已生成: %s（%d 帧，约 %.1fs）",
                    path, len(self._frames), len(self._frames) * self._interval)
        return True

    @property
    def frame_count(self) -> int:
        """当前缓冲帧数（排查用）"""
        return len(self._frames)