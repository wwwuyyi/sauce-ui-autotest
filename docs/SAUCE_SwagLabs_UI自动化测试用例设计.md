# Swag Labs（saucedemo）UI 自动化测试用例设计

- **被测系统**：https://www.saucedemo.com/
- **技术栈**：Python 3.10+ / Selenium 4.x / pytest / Chrome（Selenium Manager 自动管理驱动）
- **统一密码**：`secret_sauce`
- **通用约定**：
  1. 所有 URL 断言使用完整地址（前缀 `https://www.saucedemo.com`）。
  2. "元素不可见"分两种实现，按元素特性选用：
     - 元素存在但隐藏 → `assert element.is_displayed() == False`
     - 元素从 DOM 移除（如购物车角标、登录表单）→ `assert driver.find_elements(...) == []`
  3. 购物车角标 `.shopping_cart_badge` 在数量归零后**从 DOM 移除**，故清零断言统一用 `find_elements(...) == []`。
  4. 除登录模块与"特殊账号专项""未登录访问"用例外，其余用例前置条件均由 fixture 以 `standard_user` 登录保证。
  5. 页面元素一律优先使用 `data-test` 属性定位（详见《自动化执行注意事项》）。

## 用例统计

| 模块 | 模块缩写 | 用例数 |
|---|---|---|
| 登录 | LOGIN | 10 |
| 商品首页 | INV | 9 |
| 商品详情页 | DTL | 5 |
| 购物车 | CART | 4 |
| 结算下单 | CO | 11 |
| 侧边栏菜单 | MNU | 6 |
| 页面通用场景 | COM | 3 |
| 边界与异常（特殊账号专项） | SPC | 4 |
| **合计** | | **52** |

---

## 1. 登录模块（模块名称：登录模块，缩写 LOGIN）

### SAUCE-LOGIN-001 正常登录（standard_user）
- **用例类型**：正向
- **前置条件**：Chrome 打开 `https://www.saucedemo.com/`，无残留 cookie/登录态
- **操作步骤**：
  1. 定位用户名输入框 `(By.ID, "user-name")`，输入 `standard_user`
  2. 定位密码输入框 `(By.ID, "password")`，输入 `secret_sauce`
  3. 点击登录按钮 `(By.ID, "login-button")`
- **预期结果**：登录成功，跳转商品列表页，展示 6 个商品
- **自动化重点校验点**：
  - 页面URL：`WebDriverWait(driver,10).until(EC.url_contains("/inventory.html"))`；`assert driver.current_url == "https://www.saucedemo.com/inventory.html"`
  - 元素可见性：`WebDriverWait(driver,10).until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".inventory_list")))`
  - 商品数量：`assert len(driver.find_elements(By.CSS_SELECTOR, ".inventory_item")) == 6`
  - 文本断言：页面标题 `(By.CSS_SELECTOR, ".title")` 文本 `== "Products"`
  - 元素不可见：登录表单已销毁，`assert driver.find_elements(By.ID, "login-button") == []`
  - Cookie 断言：`assert driver.get_cookie("session-username") is not None`，且 `value == "standard_user"`

### SAUCE-LOGIN-002 锁定用户登录（locked_out_user）
- **用例类型**：反向
- **前置条件**：登录页打开，无登录态
- **操作步骤**：
  1. 用户名输入 `locked_out_user`
  2. 密码输入 `secret_sauce`
  3. 点击 `(By.ID, "login-button")`
- **预期结果**：登录失败，停留在登录页，展示锁定错误提示
- **自动化重点校验点**：
  - 文本断言（报错文案）：`WebDriverWait(driver,10).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "h3[data-test='error']")))`，其文本 `== "Epic sadface: Sorry, this user has been locked out."`
  - 元素可见性：错误容器 `(By.CSS_SELECTOR, ".error-message-container")` `is_displayed() == True`
  - 页面URL：`assert driver.current_url == "https://www.saucedemo.com/"`（未被重定向至商品页）
  - 按钮状态：`login_btn.is_displayed() == True` 且 `login_btn.is_enabled() == True`（可再次提交）
  - 元素不可见：`assert driver.find_elements(By.CSS_SELECTOR, ".inventory_list") == []`（未进入商品页）

### SAUCE-LOGIN-003 错误用户名/错误密码
- **用例类型**：反向
- **前置条件**：登录页打开，无登录态
- **操作步骤**：
  1. 用户名输入 `wrong_user`，密码输入 `wrong_password`（两者均非系统账号）
  2. 点击 `#login-button`
- **预期结果**：登录失败，停留在登录页，提示"用户名密码不匹配"
- **自动化重点校验点**：
  - 文本断言：`h3[data-test='error']` 文本 `== "Epic sadface: Username and password do not match any user in this service"`
  - 元素可见性：`.error-message-container` 可见
  - 页面URL：`assert driver.current_url == "https://www.saucedemo.com/"`
  - 输入值回读：`driver.find_element(By.ID, "user-name").get_attribute("value") == "wrong_user"`（输入未被清空）
  - Cookie 断言：`assert driver.get_cookie("session-username") is None`（未建立会话）

### SAUCE-LOGIN-004 空用户名+空密码
- **用例类型**：反向
- **前置条件**：登录页打开，无登录态
- **操作步骤**：
  1. 用户名、密码均不输入，直接点击 `#login-button`
- **预期结果**：登录失败，提示用户名必填
- **自动化重点校验点**：
  - 文本断言：`h3[data-test='error']` 文本 `== "Epic sadface: Username is required"`
  - 元素可见性：`.error-message-container` 可见
  - 页面URL：`assert driver.current_url == "https://www.saucedemo.com/"`
  - 按钮状态：登录按钮仍 `is_enabled() == True`

### SAUCE-LOGIN-005 仅用户名（密码为空）
- **用例类型**：反向
- **前置条件**：登录页打开，无登录态
- **操作步骤**：
  1. 用户名输入 `standard_user`，密码留空
  2. 点击 `#login-button`
- **预期结果**：登录失败，提示密码必填
- **自动化重点校验点**：
  - 文本断言：`h3[data-test='error']` 文本 `== "Epic sadface: Password is required"`
  - 元素可见性：`.error-message-container` 可见
  - 页面URL：`assert driver.current_url == "https://www.saucedemo.com/"`

### SAUCE-LOGIN-006 仅密码（用户名为空）
- **用例类型**：反向
- **前置条件**：登录页打开，无登录态
- **操作步骤**：
  1. 用户名为空，密码输入 `secret_sauce`
  2. 点击 `#login-button`
- **预期结果**：登录失败，提示用户名必填（与 LOGIN-004 文案一致）
- **自动化重点校验点**：
  - 文本断言：`h3[data-test='error']` 文本 `== "Epic sadface: Username is required"`
  - 元素可见性：`.error-message-container` 可见
  - 页面URL：`assert driver.current_url == "https://www.saucedemo.com/"`

### SAUCE-LOGIN-007 特殊账号登录：problem_user
- **用例类型**：特殊账号专项
- **前置条件**：登录页打开，无登录态
- **操作步骤**：
  1. 用户名输入 `problem_user`，密码输入 `secret_sauce`
  2. 点击 `#login-button`，等待商品列表加载
- **预期结果**：能进入商品列表页，但所有商品图片为同一张异常（加载失败）图片
- **自动化重点校验点**：
  - 页面URL：`assert driver.current_url == "https://www.saucedemo.com/inventory.html"`
  - 元素可见性：`.inventory_list` 可见；`assert len(driver.find_elements(By.CSS_SELECTOR, ".inventory_item")) == 6`
  - 文本断言：6 个 `.inventory_item_name` 文本仍为官方名称列表（名称文本本身不受影响）
  - 图片异常断言：`srcs = [img.get_attribute("src") for img in driver.find_elements(By.CSS_SELECTOR, ".inventory_item_img")]`，`assert len(set(srcs)) == 1`（基线：standard_user 下为 6 个不同 src；problem_user 下全部指向同一 broken 资源）
  - 元素不可见：`assert driver.find_elements(By.CSS_SELECTOR, "h3[data-test='error']") == []`（登录成功无报错）

### SAUCE-LOGIN-008 特殊账号登录：performance_glitch_user
- **用例类型**：特殊账号专项
- **前置条件**：登录页打开；关闭隐式等待以进行耗时测量（见注意事项）
- **操作步骤**：
  1. 用户名输入 `performance_glitch_user`，密码输入 `secret_sauce`
  2. `t0 = time.monotonic()`，点击 `#login-button`
  3. `WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".inventory_list")))`，记录 `t1 = time.monotonic()`
- **预期结果**：最终登录成功（延迟明显高于 normal 账号）
- **自动化重点校验点**：
  - 加载延迟断言：`elapsed = t1 - t0`，`assert elapsed >= 3.0`（绝对阈值宽松化；CI 环境建议改用相对基线：`elapsed_glitch >= 2 * elapsed_standard`，基线与 SPC-001 联动）
  - 元素可见性（最终态）：`.inventory_list` 可见；`len(.inventory_item) == 6`
  - 页面URL：`assert driver.current_url == "https://www.saucedemo.com/inventory.html"`

### SAUCE-LOGIN-009 特殊账号登录：error_user
- **用例类型**：特殊账号专项
- **前置条件**：登录页打开，无登录态
- **操作步骤**：
  1. 用户名输入 `error_user`，密码输入 `secret_sauce`
  2. 点击 `#login-button`，等待商品列表加载
- **预期结果**：登录成功进入商品列表页（交互异常细节见 SPC-003）
- **自动化重点校验点**：
  - 页面URL：`assert driver.current_url == "https://www.saucedemo.com/inventory.html"`
  - 元素可见性：`.inventory_list` 可见；`len(.inventory_item) == 6`
  - 文本断言：6 个商品名称文本与官方列表一致（登录壳层正常）
  - 按钮存在性：`assert len(driver.find_elements(By.CSS_SELECTOR, "[data-test^='add-to-cart-']")) >= 1`
  - 元素不可见：`assert driver.find_elements(By.CSS_SELECTOR, "h3[data-test='error']") == []`

### SAUCE-LOGIN-010 特殊账号登录：visual_user
- **用例类型**：特殊账号专项
- **前置条件**：登录页打开，无登录态
- **操作步骤**：
  1. 用户名输入 `visual_user`，密码输入 `secret_sauce`
  2. 点击 `#login-button`，等待商品列表加载
- **预期结果**：登录成功，但页面布局存在视觉错位（如购物车图标位置脱离 header）
- **自动化重点校验点**：
  - 页面URL：`assert driver.current_url == "https://www.saucedemo.com/inventory.html"`
  - 元素可见性：`.inventory_list` 可见；`len(.inventory_item) == 6`；`.shopping_cart_link` 元素在 DOM 中存在
  - 文本断言：6 个商品名称与官方列表一致
  - 位置偏移探针（容错断言）：`cart_rect = driver.find_element(By.CSS_SELECTOR, ".shopping_cart_link").rect`，`header_rect = driver.find_element(By.CSS_SELECTOR, ".primary_header").rect`，断言 `cart_rect["y"] + cart_rect["height"]/2 > header_rect["y"] + header_rect["height"]`（图标中心落到 header 下方，即错位特征；先以 standard_user 采集基线对比，见 SPC-002）
  - 此项标记为"采样记录型"软断言（记录数值，不作为硬门禁，防版本差异误报）

---

## 2. 商品首页模块（模块名称：商品首页，缩写 INV）

### SAUCE-INV-001 商品列表加载（数量与非空校验）
- **用例类型**：正向
- **前置条件**：standard_user 已登录，位于 `/inventory.html`
- **操作步骤**：
  1. 等待 `.inventory_list` 可见
  2. 分别抓取全部商品块、名称、价格、图片元素集合
- **预期结果**：列表加载成功，6 个商品，名称/价格/图片均非空
- **自动化重点校验点**：
  - 页面URL：`assert driver.current_url == "https://www.saucedemo.com/inventory.html"`
  - 元素可见性：`EC.visibility_of_element_located((By.CSS_SELECTOR, ".inventory_list"))`
  - 数量断言：`items = driver.find_elements(By.CSS_SELECTOR, ".inventory_item")`，`assert len(items) == 6`
  - 非空校验（文本断言）：`assert all(e.text.strip() != "" for e in driver.find_elements(By.CSS_SELECTOR, ".inventory_item_name"))`
  - 价格格式断言：对每个 `.inventory_item_price` 文本执行 `re.fullmatch(r"^\$\\d+(\\.\\d{2})?$", text)` 不为 None
  - 图片 src 非空：`assert all(img.get_attribute("src") for img in driver.find_elements(By.CSS_SELECTOR, ".inventory_item_img"))`

### SAUCE-INV-002 商品名称/价格/图片逐项断言
- **用例类型**：正向
- **前置条件**：standard_user 已登录
- **操作步骤**：
  1. 按 DOM 顺序抓取 6 个商品名称、价格、图片
  2. 与内置期望常量逐项比对
- **预期结果**：展示内容与官方商品数据完全一致
- **自动化重点校验点**（默认顺序即 A→Z）：
  - 名称列表精确断言：`names = [e.text for e in driver.find_elements(By.CSS_SELECTOR, ".inventory_item_name")]`，`assert names == ["Sauce Labs Backpack","Sauce Labs Bike Light","Sauce Labs Bolt T-Shirt","Sauce Labs Fleece Jacket","Sauce Labs Onesie","Test.allTheThings() T-Shirt (Red)"]`
  - 价格列表精确断言：`assert prices == ["$29.99","$9.99","$15.99","$49.99","$7.99","$15.99"]`
  - 图片加载状态：`assert all(img.get_attribute("naturalWidth") > 0 for img in driver.find_elements(By.CSS_SELECTOR, ".inventory_item_img"))`（naturalWidth>0 表明图片真实解码渲染，区别于 404 图）
  - 图片 alt 属性非空：`assert all(img.get_attribute("alt").strip() != "" ...)`
  - 元素可见性：`(By.CSS_SELECTOR, "button[data-test='add-to-cart-sauce-labs-backpack']")` 可见作为首商品按钮基准

### SAUCE-INV-003 商品排序：名称升序（A→Z）
- **用例类型**：正向
- **前置条件**：standard_user 已登录
- **操作步骤**：
  1. 定位下拉框 `(By.CSS_SELECTOR, "select[data-test='product-sort-container']")`
  2. `Select(...).select_by_value("az")`
- **预期结果**：商品按名称字母升序排列
- **自动化重点校验点**：
  - 下拉框状态断言：`select.get_attribute("value") == "az"`
  - 排序断言（文本断言）：`WebDriverWait(...).until(...)` 后抓取名称列表，`assert names == sorted(names, key=str.lower)` 且与内置 `EXPECTED_AZ` 常量完全一致
  - 首末元素断言：首个名称 `== "Sauce Labs Backpack"`，末个 `== "Test.allTheThings() T-Shirt (Red)"`
  - 元素可见性：列表仍可见且仍为 6 个商品

### SAUCE-INV-004 商品排序：名称降序（Z→A）
- **用例类型**：正向
- **操作步骤**：`select_by_value("za")`
- **预期结果**：商品按名称字母降序排列
- **自动化重点校验点**：
  - `select.get_attribute("value") == "za"`
  - `assert names == sorted(names, key=str.lower, reverse=True)` 且 `names[0] == "Test.allTheThings() T-Shirt (Red)"`、`names[-1] == "Sauce Labs Backpack"`

### SAUCE-INV-005 商品排序：价格升序（Price low→high）
- **用例类型**：正向
- **操作步骤**：`select_by_value("lohi")`
- **预期结果**：价格从低到高排列
- **自动化重点校验点**：
  - `select.get_attribute("value") == "lohi"`
  - 价格顺序断言：`nums = [float(p.text.replace("$","")) for p in driver.find_elements(By.CSS_SELECTOR, ".inventory_item_price")]`，`assert nums == [7.99, 9.99, 15.99, 15.99, 29.99, 49.99]`（用 Decimal 或整数分转换比较，避免浮点精度问题，见注意事项）
  - 首元素断言：第一个价格文本 `== "$7.99"`（Onesie），末尾 `== "$49.99"`（Fleece Jacket）

### SAUCE-INV-006 商品排序：价格降序（Price high→low）
- **用例类型**：正向
- **操作步骤**：`select_by_value("hilo")`
- **预期结果**：价格从高到低排列
- **自动化重点校验点**：
  - `select.get_attribute("value") == "hilo"`
  - 价格顺序断言：`assert nums == [49.99, 29.99, 15.99, 15.99, 9.99, 7.99]`

### SAUCE-INV-007 商品加入购物车（按钮状态变化+角标+1）
- **用例类型**：正向
- **前置条件**：已完成登录，购物车为空
- **操作步骤**：
  1. 点击 `(By.CSS_SELECTOR, "button[data-test='add-to-cart-sauce-labs-backpack']")`
- **预期结果**：Backpack 加入购物车，按钮变为 Remove，角标显示 1
- **自动化重点校验点**：
  - 按钮切换断言：`WebDriverWait(driver,10).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "button[data-test='remove-sauce-labs-backpack']")))`
  - 文本断言（按钮文案）：remove 按钮文本 `== "Remove"`
  - 元素不可见：`assert driver.find_elements(By.CSS_SELECTOR, "button[data-test='add-to-cart-sauce-labs-backpack']") == []`
  - 角标数字断言：`WebDriverWait(driver,10).until(EC.text_to_be_present_in_element((By.CSS_SELECTOR, "[data-test='shopping-cart-badge']"), "1"))`，`assert badge.text == "1"`

### SAUCE-INV-008 移除购物车（按钮恢复+角标-1/消失）
- **用例类型**：正向
- **前置条件**：Backpack 已在购物车（badge=1）
- **操作步骤**：
  1. 点击 `button[data-test='remove-sauce-labs-backpack']`
- **预期结果**：按钮恢复为 Add to cart，角标消失
- **自动化重点校验点**：
  - 按钮恢复断言：`EC.visibility_of_element_located((By.CSS_SELECTOR, "button[data-test='add-to-cart-sauce-labs-backpack']"))`，其文本 `== "Add to cart"`
  - 元素不可见：`assert driver.find_elements(By.CSS_SELECTOR, "button[data-test='remove-sauce-labs-backpack']") == []`
  - 角标消失断言：`assert driver.find_elements(By.CSS_SELECTOR, "[data-test='shopping-cart-badge']") == []`（角标归零后从 DOM 移除）

### SAUCE-INV-009 购物车角标多商品累计计数
- **用例类型**：正向
- **前置条件**：已登录，购物车为空
- **操作步骤**：
  1. 依次点击 `add-to-cart-sauce-labs-backpack`、`add-to-cart-sauce-labs-bike-light`、`add-to-cart-sauce-labs-onesie`
  2. 每添加一个商品后立即检查角标
- **预期结果**：角标数字依次为 1、2、3
- **自动化重点校验点**（循环内逐步断言）：
  - 角标数字断言：第 i 次添加后 `assert badge.text == str(i+1)`，最终 `== "3"`
  - 按钮状态集合断言：`assert len(driver.find_elements(By.CSS_SELECTOR, "[data-test^='remove-']")) == 3`、`assert len(driver.find_elements(By.CSS_SELECTOR, "[data-test^='add-to-cart-']")) == 3`（3 加 3 未加，共 6 商品）
  - 元素可见性：每次角标均先 `EC.visibility_of_element_located` 再取文本

---

## 3. 商品详情页模块（模块名称：商品详情页，缩写 DTL）

### SAUCE-DTL-001 点击商品名进入详情页
- **用例类型**：正向
- **前置条件**：standard_user 已登录，位于商品列表页
- **操作步骤**：
  1. 点击 Backpack 名称链接 `(By.CSS_SELECTOR, "a[data-test='item-4-title-link']")`（旧版回退 `#item_4_title_link`）
- **预期结果**：跳转至 Backpack 详情页
- **自动化重点校验点**：
  - 页面URL：`WebDriverWait(driver,10).until(EC.url_contains("/inventory-item.html?id=4"))`；`assert driver.current_url == "https://www.saucedemo.com/inventory-item.html?id=4"`
  - 元素可见性：`.inventory_details_container` 可见；`.inventory_details_name` 可见；返回按钮 `[data-test='back-to-products']` 可见
  - 文本断言：`.inventory_details_name` 文本 `== "Sauce Labs Backpack"`
  - 元素不可见：`.inventory_list`（列表容器）不再存在，`assert driver.find_elements(By.CSS_SELECTOR, ".inventory_list") == []`

### SAUCE-DTL-002 详情信息与列表页核对一致
- **用例类型**：正向
- **前置条件**：列表页已提前抓取 Backpack 的 `name/desc/price` 文本存入变量
- **操作步骤**：
  1. 从列表页进入 Backpack 详情（同 DTL-001）
  2. 抓取详情页各信息元素文本
- **预期结果**：详情页名称、描述、价格与列表页完全一致
- **自动化重点校验点**：
  - 文本断言（名称）：`.inventory_details_name` 文本 `== 列表页 name 变量 == "Sauce Labs Backpack"`
  - 文本断言（描述）：`.inventory_details_desc` 文本 `== 列表页 .inventory_item_desc 对应文本`，且非空（如包含 "carry.allTheThings()"）
  - 文本断言（价格）：`.inventory_details_price` 文本 `== 列表页 price 变量 == "$29.99"`
  - 图片加载状态：详情图 `img` 的 `naturalWidth > 0`
  - 元素可见性：`.inventory_details_name/desc/price` 三元素均 `is_displayed() == True`

### SAUCE-DTL-003 详情页添加购物车
- **用例类型**：正向
- **前置条件**：位于 Backpack 详情页，购物车为空
- **操作步骤**：
  1. 点击 `button[data-test='add-to-cart-sauce-labs-backpack']`（详情页与列表页共用同一 data-test）
- **预期结果**：详情页按钮切换为 Remove，角标+1
- **自动化重点校验点**：
  - 按钮切换断言：`EC.visibility_of_element_located((By.CSS_SELECTOR, "button[data-test='remove-sauce-labs-backpack']"))`，文本 `== "Remove"`
  - 元素不可见：`add-to-cart-sauce-labs-backpack` 按钮 `find_elements(...) == []`
  - 角标数字断言：`badge = driver.find_element(By.CSS_SELECTOR, "[data-test='shopping-cart-badge']")`，`assert badge.text == "1"`
  - 页面URL：`assert driver.current_url == "https://www.saucedemo.com/inventory-item.html?id=4"`（加购不跳页）

### SAUCE-DTL-004 详情页移除购物车
- **用例类型**：正向
- **前置条件**：详情页已加购（badge=1）
- **操作步骤**：
  1. 点击 `button[data-test='remove-sauce-labs-backpack']`
- **预期结果**：按钮恢复 Add to cart，角标消失
- **自动化重点校验点**：
  - 按钮恢复断言：`add-to-cart-sauce-labs-backpack` 可见，文本 `== "Add to cart"`
  - 角标消失断言：`assert driver.find_elements(By.CSS_SELECTOR, "[data-test='shopping-cart-badge']") == []`
  - 页面URL 保持：`assert "...inventory-item.html?id=4" in driver.current_url`

### SAUCE-DTL-005 详情页返回商品列表
- **用例类型**：正向
- **前置条件**：位于任一商品详情页
- **操作步骤**：
  1. 点击 `[data-test='back-to-products']`
- **预期结果**：返回商品列表页
- **自动化重点校验点**：
  - 页面URL：`assert driver.current_url == "https://www.saucedemo.com/inventory.html"`
  - 元素可见性：`EC.visibility_of_element_located((By.CSS_SELECTOR, ".inventory_list"))`
  - 数量断言：`len(driver.find_elements(By.CSS_SELECTOR, ".inventory_item")) == 6`

---

## 4. 购物车模块（模块名称：购物车，缩写 CART）

### SAUCE-CART-001 购物车页面跳转
- **用例类型**：正向
- **前置条件**：已登录且购物车有 1 个商品（Backpack）
- **操作步骤**：
  1. 点击 `(By.CSS_SELECTOR, "[data-test='shopping-cart-link']")`
- **预期结果**：跳转至购物车页面
- **自动化重点校验点**：
  - 页面URL：`assert driver.current_url == "https://www.saucedemo.com/cart.html"`
  - 元素可见性：`.cart_list` 可见；`.shopping_cart_link` 仍在页面上方可见
  - 文本断言（页面标题）：`(By.CSS_SELECTOR, ".title")` 文本 `== "Your Cart"`

### SAUCE-CART-002 购物车内商品信息核对
- **用例类型**：正向
- **前置条件**：已加购 Backpack + Bike Light（badge=2）
- **操作步骤**：
  1. 进入购物车页
  2. 抓取所有 `.cart_item` 的名称、价格、数量
- **预期结果**：商品信息与添加时完全一致
- **自动化重点校验点**：
  - 数量断言：`assert len(driver.find_elements(By.CSS_SELECTOR, ".cart_item")) == 2`
  - 名称断言：`names == ["Sauce Labs Backpack", "Sauce Labs Bike Light"]`
  - 价格断言：对应商品价格文本 `== ["$29.99", "$9.99"]`
  - 数量文本断言：每个 `.cart_item` 内 `.cart_quantity` 文本 `== "1"`
  - 角标数字断言：`badge.text == "2"`
  - 元素可见性：每个 `.cart_item` 的 `.cart_item_label` 内商品链接可见

### SAUCE-CART-003 购物车删除商品（角标联动）
- **用例类型**：正向
- **前置条件**：购物车含 Backpack + Bike Light（badge=2）
- **操作步骤**：
  1. 点击 Backpack 行内的 `button[data-test='remove-sauce-labs-backpack']`
- **预期结果**：Backpack 从购物车消失，角标降为 1
- **自动化重点校验点**：
  - 元素不可见（该商品消失）：`WebDriverWait(...).until(EC.invisibility_of_element_located((By.CSS_SELECTOR, "button[data-test='remove-sauce-labs-backpack']")))` 且 `cart_item` 数 `== 1`
  - 剩余商品文本断言：剩余唯一商品名 `== "Sauce Labs Bike Light"`
  - 角标数字断言：`badge.text == "1"`
  - 连锁清空断言：再删除 Bike Light 后 `assert driver.find_elements(By.CSS_SELECTOR, "[data-test='shopping-cart-badge']") == []`

### SAUCE-CART-004 继续购物按钮
- **用例类型**：正向
- **前置条件**：位于购物车页
- **操作步骤**：
  1. 点击 `[data-test='continue-shopping']`
- **预期结果**：跳回商品列表页
- **自动化重点校验点**：
  - 页面URL：`assert driver.current_url == "https://www.saucedemo.com/inventory.html"`
  - 元素可见性：`.inventory_list` 可见；`len(.inventory_item) == 6`

---

## 5. 结算下单模块（模块名称：结算下单，缩写 CO）

### SAUCE-CO-001 进入 Checkout（表单页）
- **用例类型**：正向
- **前置条件**：购物车至少 1 个商品
- **操作步骤**：
  1. 进入购物车页，点击 `[data-test='checkout']`
- **预期结果**：跳转结算第一步（用户信息表单）
- **自动化重点校验点**：
  - 页面URL：`assert driver.current_url == "https://www.saucedemo.com/checkout-step-one.html"`
  - 文本断言：页面标题 `.title` `== "Checkout: Your Information"`
  - 元素可见性（表单三要素）：`[data-test='firstName']`、`[data-test='lastName']`、`[data-test='postalCode']` 三个输入框均 `is_displayed() == True`
  - 按钮状态：`[data-test='continue']` 可见且 `is_enabled() == True`；`[data-test='cancel']` 可见

### SAUCE-CO-002 正常填写用户信息并提交
- **用例类型**：正向
- **前置条件**：位于 checkout-step-one
- **操作步骤**：
  1. First Name 输入 `Zhang`，Last Name 输入 `San`，Postal Code 输入 `100000`
  2. 点击 `[data-test='continue']`
- **预期结果**：进入结算概览页
- **自动化重点校验点**：
  - 页面URL：`WebDriverWait(...).until(EC.url_contains("/checkout-step-two.html"))`
  - 文本断言：`.title` `== "Checkout: Overview"`
  - 元素可见性：`.cart_list`（概览商品清单）可见；`[data-test='finish']` 可见且 enabled
  - 元素不可见：`assert driver.find_elements(By.CSS_SELECTOR, "[data-test='firstName']") == []`（已离开表单页）

### SAUCE-CO-003 空 FirstName
- **用例类型**：反向
- **前置条件**：位于 checkout-step-one
- **操作步骤**：
  1. First Name 留空，Last Name 填 `San`，Postal Code 填 `100000`
  2. 点击 `[data-test='continue']`
- **预期结果**：停留在表单页，报错提示 First Name 必填
- **自动化重点校验点**：
  - 文本断言（逐字段错误提示）：`WebDriverWait(...).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "h3[data-test='error']")))`，文本 `== "Error: First Name is required"`
  - 页面URL：`assert driver.current_url == "https://www.saucedemo.com/checkout-step-one.html"`（未跳转）
  - 元素可见性：`.error-message-container` 可见

### SAUCE-CO-004 空 LastName
- **用例类型**：反向
- **操作步骤**：First Name=`San`，Last Name 留空，Postal=`100000`，提交
- **预期结果**：报错 Last Name 必填
- **自动化重点校验点**：
  - 文本断言：`h3[data-test='error']` 文本 `== "Error: Last Name is required"`
  - 页面URL：仍为 `checkout-step-one.html`
  - 元素可见性：`.error-message-container` 可见

### SAUCE-CO-005 空 ZipCode
- **用例类型**：反向
- **操作步骤**：First=`Zhang`，Last=`San`，Postal 留空，提交
- **预期结果**：报错 Postal Code 必填
- **自动化重点校验点**：
  - 文本断言：`h3[data-test='error']` 文本 `== "Error: Postal Code is required"`
  - 页面URL：仍为 `checkout-step-one.html`
  - 元素可见性：`.error-message-container` 可见

### SAUCE-CO-006 非法字符输入（特殊符号/XSS 载荷）
- **用例类型**：反向
- **前置条件**：位于 checkout-step-one
- **操作步骤**（参数化两组数据）：
  1. First Name=`<script>alert('xss')</script>`；另一组 First Name=`!@#$%^&*()_+`
  2. Last Name=`San`，Postal=`100000`，点击 `[data-test='continue']`
- **预期结果**：站点无前端输入格式校验，提交被接受进入概览页（**记录为站点实际行为**，作为安全关注点备注）
- **自动化重点校验点**：
  - 页面URL：`assert ".../checkout-step-two.html" in driver.current_url`（提交成功、无校验拦截）
  - 弹窗断言：`try: driver.switch_to.alert; alert_found=True; except NoAlertPresentException: alert_found=False`，`assert alert_found is False`（XSS 载荷未被执行为弹窗）
  - 输入回读断言：提交前 `driver.find_element(By.CSS_SELECTOR, "[data-test='firstName']").get_attribute("value")` 与输入串完全一致（未被清洗/截断）

### SAUCE-CO-007 超长字符串输入
- **用例类型**：反向
- **前置条件**：位于 checkout-step-one
- **操作步骤**：
  1. First Name 输入 `"A" * 300`（300 字符超长串）
  2. Last=`San`，Postal=`100000`，提交
- **预期结果**：无 maxlength 校验，提交进入概览页
- **自动化重点校验点**：
  - 页面URL：进入 `checkout-step-two.html`
  - 输入回读断言：提交前 `value` 长度 `== 300`（未被截断）
  - 元素可见性：概览页 `.cart_list` 可见

### SAUCE-CO-008 非数字 ZipCode
- **用例类型**：反向
- **前置条件**：位于 checkout-step-one
- **操作步骤**：
  1. First=`Zhang`，Last=`San`，Postal=`abc!@`（非数字）
  2. 提交
- **预期结果**：站点仅做非空校验，提交成功进入概览页（记录为实际行为）
- **自动化重点校验点**：
  - 页面URL：`assert ".../checkout-step-two.html" in driver.current_url`
  - 元素可见性：概览页 `[data-test='finish']` 可见

### SAUCE-CO-009 概览页商品信息与总价计算核对
- **用例类型**：正向
- **前置条件**：购物车为 Backpack($29.99) + Bike Light($9.99)，已完成表单提交进入概览页
- **操作步骤**：
  1. 抓取概览页商品行与汇总区三个金额标签
- **预期结果**：商品信息正确，Item total=39.98，Tax=3.20，Total=43.18
- **自动化重点校验点**：
  - 数量断言：`len(driver.find_elements(By.CSS_SELECTOR, ".cart_item")) == 2`
  - 名称/价格断言：两商品名称与价格精确匹配添加时数据
  - 汇总文本断言（Decimal 转换后比较，避免浮点误差）：
    - `.summary_subtotal_label` 文本 `== "Item total: $39.98"`
    - `.summary_tax_label` 文本 `== "Tax: $3.20"`
    - `.summary_total_label` 文本 `== "Total: $43.18"`
  - 计算正确性断言：`Decimal(页面Item total提取) == Decimal("29.99") + Decimal("9.99")`；`Tax == subtotal * Decimal("0.08")` 四舍五入到分；`Total == subtotal + tax`
  - 元素可见性：`.summary_info`（支付/物流信息区）可见；`[data-test='finish']` 可见且 `is_enabled()`

### SAUCE-CO-010 完成订单成功提示
- **用例类型**：正向
- **前置条件**：位于概览页
- **操作步骤**：
  1. 点击 `[data-test='finish']`
- **预期结果**：进入订单完成页，展示感谢文案
- **自动化重点校验点**：
  - 页面URL：`assert driver.current_url == "https://www.saucedemo.com/checkout-complete.html"`
  - 文本断言（成功文案）：`.complete-header`（`data-test='complete-header'`）文本 `== "Thank you for your order!"`
  - 文本断言（说明文案）：`.complete-text` 可见且文本 `== "Your order has been dispatched, and will arrive just as fast as the pony can get there!"`
  - 元素可见性：完成页插图 `(By.CSS_SELECTOR, "img.pony_express")` 可见；`[data-test='back-to-products']` 可见
  - 购物车清空断言：`assert driver.find_elements(By.CSS_SELECTOR, "[data-test='shopping-cart-badge']") == []`（下单后购物车已清空）

### SAUCE-CO-011 订单完成后返回首页
- **用例类型**：正向
- **前置条件**：位于 checkout-complete 页
- **操作步骤**：
  1. 点击 `[data-test='back-to-products']`
- **预期结果**：回到商品列表页，购物车为空
- **自动化重点校验点**：
  - 页面URL：`assert driver.current_url == "https://www.saucedemo.com/inventory.html"`
  - 元素可见性：`EC.visibility_of_element_located((By.CSS_SELECTOR, ".inventory_list"))`
  - 角标不可见：`assert driver.find_elements(By.CSS_SELECTOR, "[data-test='shopping-cart-badge']") == []`

---

## 6. 侧边栏菜单模块（模块名称：侧边栏菜单，缩写 MNU）

### SAUCE-MNU-001 打开侧边栏
- **用例类型**：正向
- **前置条件**：standard_user 已登录，位于商品列表页
- **操作步骤**：
  1. 点击汉堡按钮 `(By.ID, "react-burger-menu-btn")`（`data-test='react-burger-menu-btn'`）
- **预期结果**：侧边栏滑出，展示 4 个菜单项与关闭按钮，页面被遮罩压暗
- **自动化重点校验点**：
  - 元素可见性：菜单容器 `(By.CSS_SELECTOR, ".bm-menu-wrap")` 可见，且 `aria-hidden` 属性 `== "false"`
  - 菜单项可见性（4 项逐一断言）：`[data-test='inventory-sidebar-link']`、`[data-test='about-sidebar-link']`、`[data-test='reset-sidebar-link']`、`[data-test='logout-sidebar-link']` 均 `is_displayed() == True`
  - 关闭按钮可见：`(By.ID, "react-burger-cross-btn")` 可见
  - 遮罩层状态：覆盖层 `(By.CSS_SELECTOR, ".bm-overlay")` 存在且可见（页面内容被压暗）

### SAUCE-MNU-002 关闭侧边栏
- **用例类型**：正向
- **前置条件**：侧边栏已打开
- **操作步骤**：
  1. 点击 `#react-burger-cross-btn`
- **预期结果**：侧边栏收起，遮罩消失
- **自动化重点校验点**：
  - 元素不可见：`WebDriverWait(...).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-test='add-to-cart-sauce-labs-backpack']")))`（列表页可正常交互）；`.bm-menu-wrap` 的 `aria-hidden` 属性 `== "true"` 或不可见
  - 关闭按钮不可见：`react-burger-cross-btn` `is_displayed() == False` 或 `find_elements == []`
  - 元素可见性：`.inventory_list` 可见（主内容未受影响）

### SAUCE-MNU-003 All Items 跳转
- **用例类型**：正向
- **前置条件**：当前位于详情页或购物车页（以详情页为例）
- **操作步骤**：
  1. 打开侧边栏，点击 `[data-test='inventory-sidebar-link']`
- **预期结果**：回到商品列表页
- **自动化重点校验点**：
  - 页面URL：`assert driver.current_url == "https://www.saucedemo.com/inventory.html"`
  - 元素可见性：`.inventory_list` 可见；`len(.inventory_item) == 6`
  - 侧边栏状态：菜单已自动收起（`.bm-menu-wrap` `aria-hidden == "true"`）

### SAUCE-MNU-004 About 跳转外链
- **用例类型**：正向
- **前置条件**：已登录
- **操作步骤**：
  1. 打开侧边栏，点击 `[data-test='about-sidebar-link']`（target=_blank 新开标签页）
  2. `driver.switch_to.window(driver.window_handles[-1])`
- **预期结果**：新标签页打开 Sauce Labs 官网
- **自动化重点校验点**：
  - 页面URL（新窗口）：`WebDriverWait(...).until(...)` 后 `assert driver.current_url.startswith("https://saucelabs.com")`
  - 窗口数量断言：`assert len(driver.window_handles) == 2`
  - 回切断言：关闭新窗口 `driver.close(); driver.switch_to.window(driver.window_handles[0])`，原窗口 URL 仍 `== ".../inventory.html"`（主站会话未受影响）

### SAUCE-MNU-005 Reset App State 重置购物车与按钮状态
- **用例类型**：正向
- **前置条件**：购物车已有 2 个商品（badge=2，2 个 Remove 按钮）
- **操作步骤**：
  1. 打开侧边栏，点击 `[data-test='reset-sidebar-link']`
- **预期结果**：购物车清空、全部 Add to Cart 按钮恢复、角标消失
- **自动化重点校验点**：
  - 角标清零断言：`assert driver.find_elements(By.CSS_SELECTOR, "[data-test='shopping-cart-badge']") == []`
  - 按钮恢复断言：`assert len(driver.find_elements(By.CSS_SELECTOR, "[data-test^='add-to-cart-']")) == 6` 且 `assert len(driver.find_elements(By.CSS_SELECTOR, "[data-test^='remove-']")) == 0`
  - 侧边栏状态：菜单已自动收起（`.bm-menu-wrap` 不可见）
  - 报警交叉验证：进入购物车页 `len(.cart_item) == 0`

### SAUCE-MNU-006 Logout 退出登录
- **用例类型**：正向
- **前置条件**：已登录
- **操作步骤**：
  1. 打开侧边栏，点击 `[data-test='logout-sidebar-link']`
- **预期结果**：退出登录回到登录页，会话 cookie 清除
- **自动化重点校验点**：
  - 页面URL：`WebDriverWait(...).until(EC.url_to_be("https://www.saucedemo.com/"))`
  - 元素可见性：`(By.ID, "login-button")` 可见
  - Cookie 断言：`assert driver.get_cookie("session-username") is None`
  - 深度访问重定向断言：`driver.get("https://www.saucedemo.com/inventory.html")` 后被重定向回 `https://www.saucedemo.com/`，`h3[data-test='error']` 文本包含 `"You can only access"` 与 `"when you are logged in"`（与 COM-003 联动）

---

## 7. 页面通用场景模块（模块名称：页面通用场景，缩写 COM）

### SAUCE-COM-001 浏览器刷新后状态与登录态保持
- **用例类型**：正向
- **前置条件**：已登录且购物车有 2 个商品（badge=2）
- **操作步骤**：
  1. `driver.refresh()`
- **预期结果**：页面回到商品列表页，登录态与购物车状态保持
- **自动化重点校验点**：
  - 页面URL：刷新后 `assert driver.current_url == "https://www.saucedemo.com/inventory.html"`
  - 元素可见性：`.inventory_list` 重新可见（刷新后需重新定位等待）
  - 角标数字断言：重新定位后 `badge.text == "2"`
  - 按钮状态断言：2 个 `remove-*` 按钮仍在（`len([data-test^='remove-']) == 2`）
  - Cookie 断言：`session-username` cookie 仍存在（登录态保持的依据）

### SAUCE-COM-002 浏览器前进/后退导航
- **用例类型**：正向
- **前置条件**：已登录，从列表页进入 Backpack 详情页
- **操作步骤**：
  1. `driver.back()`；断言后 `driver.forward()`
- **预期结果**：后退回到列表页，前进回到详情页
- **自动化重点校验点**：
  - 后退 URL 断言：`back()` 后 `assert driver.current_url == "https://www.saucedemo.com/inventory.html"`；`.inventory_list` 可见
  - 前进 URL 断言：`forward()` 后 `assert driver.current_url == "https://www.saucedemo.com/inventory-item.html?id=4"`
  - 元素可见性：`.inventory_details_name` 重新可见；再 `back()` 后可见 `.inventory_list`
  - 元素不可见：后退后 `assert driver.find_elements(By.CSS_SELECTOR, ".inventory_details_container") == []`

### SAUCE-COM-003 会话失效/未登录直接访问内部页面（重定向校验）
- **用例类型**：反向
- **前置条件**：全新无 cookie 会话（`delete_all_cookies()` 或新开 driver）
- **操作步骤**（参数化三个内部 URL）：
  1. 分别直接访问 `/inventory.html`、`/cart.html`、`/checkout-step-one.html`、`/inventory-item.html?id=4`
- **预期结果**：全部被重定向回登录页并给出提示
- **自动化重点校验点**：
  - 页面URL：每次 `driver.get(内部URL)` 后 `WebDriverWait(...).until(EC.url_to_be("https://www.saucedemo.com/"))`
  - 文本断言（重定向提示）：`h3[data-test='error']` 可见且文本包含 `"You can only access"` 与 `"when you are logged in"`（不同内页路径文案中路径部分不同，用 contains 断言）
  - 元素可见性：`#login-button` 可见
  - Cookie 断言：`assert driver.get_cookie("session-username") is None`

---

## 8. 边界与异常场景模块（模块名称：边界与异常/特殊账号专项，缩写 SPC）

### SAUCE-SPC-001 performance_glitch_user 加载延迟阈值校验
- **用例类型**：特殊账号专项
- **前置条件**：以 `performance_glitch_user` 登录（关闭隐式等待以免吞掉计时，显式等待 timeout=20s）
- **操作步骤**：
  1. `t0 = time.monotonic()` 点击登录
  2. `WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".inventory_list")))`，`t1 = time.monotonic()`
  3. 同批次以 standard_user 执行相同流程记录基线耗时 `t_base`
- **预期结果**：页面最终加载成功，但耗时显著高于基线
- **自动化重点校验点**：
  - 延迟阈值断言：`assert (t1 - t0) >= 3.0`（绝对阈值；CI 不稳定时启用相对断言）
  - 相对基线断言（备选/并列）：`assert (t1 - t0) >= 2 * t_base`（基线 typically <1.5s）
  - 元素可见性（最终态）：`.inventory_list` 可见；`len(.inventory_item) == 6`
  - 页面URL：`== "https://www.saucedemo.com/inventory.html"`
  - 耗时值记录：将 `t1-t0` 记入测试 report/attachment，便于趋势观察

### SAUCE-SPC-002 visual_user 视觉异常校验（图片加载+位置偏移容忍）
- **用例类型**：特殊账号专项
- **前置条件**：分别以 standard_user（基线）与 visual_user 登录两次采集坐标
- **操作步骤**：
  1. visual_user 登录至列表页
  2. 采集 6 张商品图 `naturalWidth` 与购物车图标 rect
  3. 与 standard_user 基线坐标对比
- **预期结果**：图片本身正常加载，但购物车图标位置偏移（错位特征）
- **自动化重点校验点**：
  - 图片加载断言：`assert all(img.get_attribute("naturalWidth") > 0 for img in .inventory_item_img)`（visual_user 图片资源本身正常）
  - 位置偏移容忍断言：`cart_rect = driver.find_element(By.CSS_SELECTOR, ".shopping_cart_link").rect`；记录基线 `(x0,y0)` 与 visual_user `(x1,y1)`；断言 `abs(x1-x0) > 50 or abs(y1-y0) > 70`（像素阈值可配置化；**容错设计**：断言的是"与基线存在可测偏移"，不以截图 diff 为准）
  - 元素可见性：`.shopping_cart_link` 可见（即便错位仍可点击）；`.inventory_list` 可见；`len(.inventory_item) == 6`
  - 记录型软断言：坐标差值写入报告；若某版本偏移未复现，标记 skip/known-issue，不硬失败

### SAUCE-SPC-003 error_user 交互异常校验（行为不一致性断言）
- **用例类型**：特殊账号专项
- **前置条件**：error_user 已登录，购物车为空；同批次以 standard_user 采集基线（6/6 添加成功）
- **操作步骤**：
  1. 依次点击全部 6 个 `[data-test^='add-to-cart-']` 按钮，每次点击后统计：按钮是否变为 Remove、角标是否 +1
  2. 选择价格降序排序 `select_by_value("hilo")`，抓取价格顺序
- **预期结果**：部分（或全部）加购交互无响应、排序结果异常（与基线不一致）
- **自动化重点校验点**：
  - 行为差异断言（加购）：`added = 实际角标累计数`，`assert added < 6`（基线 standard_user 为 6/6）；记录每次点击后的 `badge 值/按钮态` 明细进报告
  - 元素状态不更新断言：遍历商品列表，`assert 存在至少1个商品：add-to-cart 按钮点击后仍然可见（未变成 remove）`（`find_elements("[data-test^='remove-']")` 数量 `< 6`）
  - 排序异常断言：hilo 排序后 `nums != [49.99, 29.99, 15.99, 15.99, 9.99, 7.99]`（error_user 排序失效，顺序保持默认），并记录实际顺序
  - 登录壳断言：页面 URL 与 6 商品列表正常（区分"登录能力"与"交互能力"）

### SAUCE-SPC-004 problem_user 图片资源与排序异常校验
- **用例类型**：特殊账号专项
- **前置条件**：problem_user 已登录
- **操作步骤**：
  1. 抓取 6 张商品图 src 集合
  2. 选择价格升序 `select_by_value("lohi")`，抓取价格顺序
- **预期结果**：图片全部为同一异常资源；排序失效
- **自动化重点校验点**：
  - 图片异常断言：`srcs = [img.get_attribute("src") for img in .inventory_item_img]`，`assert len(set(srcs)) == 1`（基线 standard_user 为 6 个唯一 src；且 src 指向 sl-404 类资源可附加断言 `any("sl-404" in s for s in srcs)`）
  - 排序失效断言：lohi 后 `nums != [7.99, 9.99, 15.99, 15.99, 29.99, 49.99]`，记录实际顺序
  - 文本健在断言：6 个商品名称与官方列表一致（图片异常不影响文本数据）
  - 元素可见性：`.inventory_list` 可见、6 商品数量正确

---

## 附：期望常量（供脚本内置比对，避免测试数据硬编码散落）

```python
USERS = {"standard_user": "secret_sauce", "locked_out_user": "secret_sauce",
         "problem_user": "secret_sauce", "performance_glitch_user": "secret_sauce",
         "error_user": "secret_sauce", "visual_user": "secret_sauce"}

PRODUCTS = [
  {"slug": "sauce-labs-backpack",           "id": 4, "name": "Sauce Labs Backpack",             "price": "29.99"},
  {"slug": "sauce-labs-bike-light",         "id": 0, "name": "Sauce Labs Bike Light",           "price": "9.99"},
  {"slug": "sauce-labs-bolt-t-shirt",       "id": 1, "name": "Sauce Labs Bolt T-Shirt",         "price": "15.99"},
  {"slug": "sauce-labs-fleece-jacket",      "id": 5, "name": "Sauce Labs Fleece Jacket",        "price": "49.99"},
  {"slug": "sauce-labs-onesie",             "id": 2, "name": "Sauce Labs Onesie",               "price": "7.99"},
  {"slug": "test.allthethings()-t-shirt-(red)", "id": 3, "name": "Test.allTheThings() T-Shirt (Red)", "price": "15.99"},
]

EXPECTED_AZ   = ["Sauce Labs Backpack", "Sauce Labs Bike Light", "Sauce Labs Bolt T-Shirt",
                 "Sauce Labs Fleece Jacket", "Sauce Labs Onesie", "Test.allTheThings() T-Shirt (Red)"]
EXPECTED_ZA   = list(reversed(EXPECTED_AZ))
EXPECTED_LOHI = [p for p in sorted(PRODUCTS, key=lambda x: Decimal(x["price"]))]
EXPECTED_HILO = list(reversed(EXPECTED_LOHI))

ERROR_MSG = {
    "locked":   "Epic sadface: Sorry, this user has been locked out.",
    "mismatch": "Epic sadface: Username and password do not match any user in this service",
    "no_user":  "Epic sadface: Username is required",
    "no_pass":  "Epic sadface: Password is required",
    "no_first": "Error: First Name is required",
    "no_last":  "Error: Last Name is required",
    "no_zip":   "Error: Postal Code is required",
    "not_login":"Epic sadface: You can only access '/inventory.html' when you are logged in.",
}
```