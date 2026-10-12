# 《自动化执行注意事项》— Swag Labs UI 自动化

> 配套《SAUCE_SwagLabs_UI自动化测试用例设计.md》使用，Selenium + Python 技术栈。

---

## 一、关键元素定位建议（data-test 属性优先）

### 1.1 定位优先级原则

`data-test`（官方测试钩子） > `id` > `class`（需复合限定） > `xpath`（尽量避免索引式）

Swag Labs 全站关键元素均带稳定 `data-test` 属性，跨版本最稳，一律优先使用。建议统一封装：

```python
from selenium.webdriver.common.by import By

def dt(name: str) -> tuple:
    """data-test 定位器辅助函数"""
    return (By.CSS_SELECTOR, f"[data-test='{name}']")
```

### 1.2 各模块关键 data-test 清单

| 模块 | 元素 | data-test 值 / 定位方式 | 备注 |
|---|---|---|---|
| 登录 | 用户名输入框 | `(By.ID, "user-name")`，data-test=`username` | 推荐直接用 ID |
| 登录 | 密码输入框 | `(By.ID, "password")`，data-test=`password` | |
| 登录 | 登录按钮 | `(By.ID, "login-button")`，data-test=`login-button` | |
| 登录 | 错误提示 | `h3[data-test='error']` | 登录/结算/未登录公用**
| 首页 | 商品列表容器 | `.inventory_list` | 无 data-test，用 class |
| 首页 | 商品块 | `.inventory_item` | |
| 首页 | 商品名称 | `[data-test='inventory-item-name']`（类 `.inventory_item_name`） | |
| 首页 | 商品价格 | `[data-test='inventory-item-price']` | |
| 首页 | 商品描述 | `.inventory_item_desc` | |
| 首页 | 商品图片 | `img.inventory_item_img` | 断言用 naturalWidth |
| 首页 | 排序下拉框 | `select[data-test='product-sort-container']` | 值：az/za/lohi/hilo |
| 首页 | 加购按钮 | `[data-test='add-to-cart-{slug}']` | slug 表见 1.3 |
| 首页 | 移除按钮 | `[data-test='remove-{slug}']` | 同 slug 规则 |
| 首页 | 购物车角标 | `[data-test='shopping-cart-badge']`（类 `.shopping_cart_badge`） | 归零后从 DOM 移除 |
| 首页 | 购物车图标 | `[data-test='shopping-cart-link']` | |
| 详情页 | 详情容器 | `.inventory_details_container` | |
| 详情页 | 名称/描述/价格 | `.inventory_details_name` / `_desc` / `_price` | |
| 详情页 | 标题链接 | `a[data-test='item-4-title-link']` | 旧版本回退 `#item_4_title_link` |
| 详情/完成页 | 返回列表 | `[data-test='back-to-products']` | 两个页面共用 |
| 购物车 | 购物车列表 | `.cart_list` / `.cart_item` | |
| 购物车 | 数量 | `.cart_quantity` | |
| 购物车 | 继续购物 | `[data-test='continue-shopping']` | |
| 购物车 | 去结算 | `[data-test='checkout']` | |
| 结算 | 三个输入框 | `[data-test='firstName']` / `'lastName'` / `'postalCode'` | 亦可用 `#first-name` 等 ID |
| 结算 | 继续/取消/完成 | `[data-test='continue']` / `'cancel'` / `'finish'` | |
| 结算 | 金额汇总 | `.summary_subtotal_label` / `.summary_tax_label` / `.summary_total_label` | |
| 结算 | 支付信息区 | `.summary_info` | |
| 完成页 | 成功标题 | `[data-test='complete-header']`（类 `.complete-header`） | |
| 完成页 | 说明文案 | `.complete-text` | |
| 菜单 | 汉堡按钮 | `(By.ID, "react-burger-menu-btn")` | |
| 菜单 | 4 个菜单项 | `[data-test='inventory-sidebar-link' / 'about-sidebar-link' / 'reset-sidebar-link' / 'logout-sidebar-link']` | |
| 菜单 | 关闭按钮 | `(By.ID, "react-burger-cross-btn")` | |
| 菜单 | 菜单容器/遮罩 | `.bm-menu-wrap` / `.bm-overlay` | 状态断言用 aria-hidden |

### 1.3 商品 slug 映射表（data-test 动态值）

```python
SLUG_BY_ID = {
    4: "sauce-labs-backpack",
    0: "sauce-labs-bike-light",
    1: "sauce-labs-bolt-t-shirt",
    5: "sauce-labs-fleece-jacket",
    2: "sauce-labs-onesie",
    3: "test.allthethings()-t-shirt-(red)",   # 注意：括号在属性值中原样保留
}
# 用法示例
add_btn = (By.CSS_SELECTOR, f"[data-test='add-to-cart-{slug}']")
```

---

## 二、等待策略建议

### 2.1 全局原则

- **显式等待（WebDriverWait）为唯一准入闸门**：所有交互后的状态断言前都必须等待目标状态出现，禁止裸 `time.sleep`。
- 隐式等待 `driver.implicitly_wait` 建议设为 0~2s 仅做兜底；**计时类用例（SPC-001）前必须关闭隐式等待**，否则耗时测量被轮询吞掉、结果失真。
- 显式等待默认 `timeout=10s`、`poll_frequency=0.5s`，通过 conftest fixture 参数化。

### 2.2 典型场景 → 等待条件对照表

| 场景 | 等待条件（ExpectedConditions） | 示例代码 |
|---|---|---|
| 页面跳转成功 | `url_contains` / `url_to_be` | `WebDriverWait(d,10).until(EC.url_contains("/inventory.html"))` |
| 商品列表加载完成 | `visibility_of_element_located` | `.inventory_list` |
| 错误提示出现 | `visibility_of_element_located` | `h3[data-test='error']` |
| 角标数字变化 | `text_to_be_present_in_element` | `EC.text_to_be_present_in_element((By.CSS_SELECTOR, "[data-test='shopping-cart-badge']"), "2")` |
| 按钮变为 Remove | `visibility_of_element_located` | `[data-test='remove-sauce-labs-backpack']` |
| 元素消失（按钮/角标/菜单） | `invisibility_of_element_located` | 元素不在 DOM 时同样满足 |
| 点击前 | `element_to_be_clickable`（点击前统一使用，替代直接 click） | |
| 下拉框选项生效 | 先 `visibility` 再 `Select.select_by_value`，随后断言 `get_attribute("value")` | |

### 2.3 performance_glitch_user 加载延迟处理

1. **超时上浮**：该账号每次导航有 3~5s+ 渲染延迟，配套显式等待 timeout 从 10s 上调至 **15~20s**（通过 fixture 注入，不全局上调）。
2. **计时与断言分离**：先关闭隐式等待 → `time.monotonic()` 计时 → 显式等待终态出现 → 计算耗时。不要把计时逻辑混进带隐等的方法里。
3. **阈值策略**：绝对阈值 `>= 3.0s` 在 CI 环境（headless/无 GPU/资源抢占）下可能波动，**优先使用相对基线**：同批次以 standard_user 执行相同流程记录 `t_base`，断言 `t_glitch >= 2 * t_base`；绝对阈值仅作本地开发参考。
4. **用例隔离**：glitch 账号只跑性能类用例（LOGIN-008 / SPC-001），不要编入功能回归冒烟集，避免拖慢套件并制造超时误报。

---

## 三、各特殊账号特性说明及自动化应对策略

| 账号 | 已知异常特性 | 自动化应对策略 |
|---|---|---|
| `standard_user` | 无异常，全功能正常 | 基线账号：正向功能用例、行为差异对照的参照系 |
| `locked_out_user` | 登录即被拒，报锁定文案 | 只断言错误文案 + URL 停留 + 按钮可重试；不要进入主流程 |
| `problem_user` | 全部商品图片指向同一异常资源（sl-404）；排序失效 | 断图片用 **src 集合唯一数==1**（勿用 naturalWidth>0 判错，sl-404 本身是张真图）；排序断言"未按期望顺序排列"并记录实际顺序 |
| `performance_glitch_user` | 每次导航 3~5s+ 延迟 | 见 2.3：超时上浮 + 关闭隐等计时 + 相对基线 + 性能用例隔离 |
| `error_user` | 部分商品 add-to-cart/remove 无响应、排序失效、部分表单行为异常 | 用 **行为差异计数断言**：全量点击 6 个加购按钮，断言 `成功添加数 < 6`（基线 6/6），并把每次点击后的按钮态/角标值写进报告；具体失效商品不写死（版本间有变动） |
| `visual_user` | 布局错位（购物车图标脱离 header 落到内容区）、图标遮挡 | 坐标采集对比：standard_user 基线 rect vs visual_user rect，断言偏移超可配置像素阈值（如 x>50 / y>70），数值记录进报告；**不做截图像素级对比**（太脆）；此类用例标记软断言/known-issue |

**数据隔离铁律**：特殊账号用例必须在独立 fixture 中登录，一个测试会话内禁止混用账号——排序状态、购物车状态、cookie 会相互污染。

---

## 四、Cookie / Session 管理建议

1. **会话模型**：Swag Labs 登录后写入 `session-username` cookie，退出登录即清除。登录态失效 = 该 cookie 消失，可作为所有权限类断言的权威依据。
2. **用例隔离策略**：
   - 每个测试用例 function 级 fixture 新建 driver 并真实走 UI 登录（保障用例独立性、可并行）；
   - 若为提速使用 module 级共享会话（仅限 standard_user 纯读用例），**断言购物车前必须先 reset app state**（`reset-sidebar-link`），防止前序用例购物车状态污染。
3. **未登录/会话失效用例**（LOGIN 各反向用例、MNU-006、COM-003）：必须用全新无 cookie 上下文——`driver.delete_all_cookies()` 后 `get()`，或直接 `ChromeOptions().add_argument("--incognito")`。
4. **禁止 cookie 注入式登录**：正式用例一律真实 UI 登录，`add_cookie` 注入会绕过登录流程，使登录类用例失去覆盖意义；`pickle` 保存/恢复 cookies 仅用于本地调试断点续跑。
5. **浏览器与驱动**：Selenium 4.6+ 的 Selenium Manager 自动管理 chromedriver；Chrome 建议固定版本（CI 镜像锁定）；本地开发用 headful（便于肉眼排查），CI 用 `--headless=new`；glitch 性能用例在 headless 下 GPU 关闭、耗时波动大，建议剔除 CI 门禁或标记 quarantine。

---

## 五、测试数据管理建议

1. **常量集中管理**：`data/constants.py` 统一存放 `USERS`、`PRODUCTS`（slug/name/price/id 四元组）、`EXPECTED_AZ/ZA/LOHI/HILO`、`ERROR_MSG` 文案字典、`CHECKOUT_VALID/INVALID` 参数集。禁止在用例中散落魔法字符串。
2. **数据驱动（pytest.mark.parametrize）**：
   - 登录反向组合（4 组错误输入）
   - 6 商品逐项断言（遍历 PRODUCTS）
   - 4 种排序（az/za/lohi/hilo → 期望列表）
   - 结算三字段空值/非法值组合
   - 内部页面未登录访问 URL 列表
3. **金额断言精度**：展示型断言用字符串精确匹配（`== "$29.99"`）；计算型断言用 `decimal.Decimal("29.99")` 运算后再与页面提取值 `Decimal()` 化比较。**全程避免 float**（0.1+0.2 类误差会让总价断言偶发失败）。
4. **期望数据双保险**：内置期望常量之外，suite 初始化时（session 级 fixture）抓取一次列表页 6 商品名称/价格与常量 diff，不一致立即告警——防止站点商品数据变更后所有用例"集体假失败"而无人知道根因。
5. **测试产物**：失败用例自动截图存 `artifacts/screenshots/{用例ID}_{timestamp}.png`；SPC 系列（耗时、坐标、行为差异计数）数值写入 report 附件，便于趋势观测与 known-issue 管理。
6. **执行顺序建议**：冒烟集（LOGIN-001/INV-001/CART-001/CO-002/CO-010/MNU-006）→ 正向全量 → 反向 → 特殊账号专项（最后跑，失败不阻塞主流程门禁）。

---

## 六、工程结构参考（Page Object 模式）

```
swaglabs_ui_tests/
├─ conftest.py              # driver/登录 fixture、失败截图、timeout 注入
├─ data/
│  └─ constants.py          # USERS / PRODUCTS / 期望列表 / 错误文案
├─ pages/
│  ├─ base_page.py          # find(dt)、wait_for、click_btn 等公共方法
│  ├─ login_page.py         # login(user, pwd)、error_text()
│  ├─ inventory_page.py     # add_to_cart(slug)、remove(slug)、badge_text()、sort_by(v)
│  ├─ item_page.py          # get_name/desc/price、back_to_products()
│  ├─ cart_page.py          # cart_items()、remove_from_cart(slug)、continue_shopping()
│  ├─ checkout_page.py      # fill_info()、fill_invalid()、summary_amounts()、finish()
│  └─ menu.py               # open/close、all_items/about/reset/logout
└─ tests/
   ├─ test_login.py         # SAUCE-LOGIN-xxx
   ├─ test_inventory.py     # SAUCE-INV-xxx
   ├─ test_item.py          # SAUCE-DTL-xxx
   ├─ test_cart.py          # SAUCE-CART-xxx
   ├─ test_checkout.py      # SAUCE-CO-xxx
   ├─ test_menu.py          # SAUCE-MNU-xxx
   ├─ test_common.py        # SAUCE-COM-xxx
   └─ test_special_users.py # SAUCE-SPC-xxx
```

> 完整用例设计（52 条）见《SAUCE_SwagLabs_UI自动化测试用例设计.md》。