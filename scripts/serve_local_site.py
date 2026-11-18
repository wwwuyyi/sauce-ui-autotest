# -*- coding: utf-8 -*-
"""
serve_local_site.py —— 本地托管 Swag Labs 静态站点（供 CI / 本地无网络依赖运行）

背景：saucedemo.com 是纯前端静态站点（账号/商品/购物车全部在 JS + localStorage，
无任何后端 API）。公网站点偶发"点击无响应/路由不跳转"会让 CI 因站点抖动变红，
把构建产物固化在 testsite/ 后用本脚本本地托管，测试以
BASE_URL=http://127.0.0.1:8000/ 指向它，即可获得完全确定的执行环境。

特性：
1. 纯标准库（http.server），零第三方依赖；
2. SPA 回退：/cart.html、/checkout-step-one.html 等前端路由路径在磁盘上不存在时
   回退返回 index.html，由浏览器端 React Router 接管（与线上 GitHub Pages 行为一致）；
3. 默认只监听 127.0.0.1（CI / 本地均安全），--verbose 可打开访问日志。

用法：
    python scripts/serve_local_site.py                # 127.0.0.1:8000
    python scripts/serve_local_site.py --port 9000    # 自定义端口
"""
import argparse
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SITE_DIR = PROJECT_ROOT / "testsite"


class LocalSiteServer(ThreadingHTTPServer):
    """静态站点服务：提高连接排队上限

    ThreadingHTTPServer 默认 request_queue_size=5；Chrome 打开页面时会并发请求
    JS/CSS/图片/字体等十几个资源，瞬时连接数可能超过队列上限，Windows 下会直接
    拒绝连接（浏览器报 net::ERR_CONNECTION_REFUSED，页面渲染不完整）。
    """

    allow_reuse_address = True
    daemon_threads = True
    request_queue_size = 128


class SpaRequestHandler(SimpleHTTPRequestHandler):
    """静态文件服务 + SPA 路由回退（未知 *.html 路径返回 index.html）"""

    # HTTP/1.1 启用 keep-alive：浏览器复用连接，减少并发建连压力
    protocol_version = "HTTP/1.1"

    def translate_path(self, path):
        resolved = super().translate_path(path)
        # 前端路由路径（如 /cart.html）磁盘上不存在时回退到 index.html，
        # 交由浏览器端 React Router 渲染；静态资源（/assets/*）缺失仍按 404 处理
        clean = path.split("?", 1)[0].split("#", 1)[0]
        if not Path(resolved).exists() and clean.endswith((".html", "/")):
            return str(SITE_DIR / "index.html")
        return resolved

    def log_message(self, fmt, *args):  # 覆盖父类方法名，默认静默
        if getattr(self.server, "verbose", False):
            super().log_message(fmt, *args)


def main():
    parser = argparse.ArgumentParser(description="本地托管 testsite/ 下的 Swag Labs 静态站点")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址（默认 127.0.0.1）")
    parser.add_argument("--port", type=int, default=8000, help="监听端口（默认 8000）")
    parser.add_argument("--verbose", action="store_true", help="打印访问日志")
    args = parser.parse_args()

    if not (SITE_DIR / "index.html").exists():
        print(f"[错误] 站点目录不完整，未找到 {SITE_DIR / 'index.html'}", file=sys.stderr)
        return 1

    handler = partial(SpaRequestHandler, directory=str(SITE_DIR))
    server = LocalSiteServer((args.host, args.port), handler)
    server.verbose = args.verbose
    print(f"[OK] 本地 Swag Labs 站点已启动: http://{args.host}:{args.port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
