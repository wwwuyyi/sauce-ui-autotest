# -*- coding: utf-8 -*-
"""
locators.py —— 跨页面公共元素定位器（唯一来源）

同一元素在多个 Page 中出现时集中定义于此，各 Page 通过同名常量引用，
对外常量名保持不变（如 InventoryPage.BADGE、CartPage.CART_LIST）。
仅收敛复用定位器；页面独有定位器仍留在各自 Page 类中。
"""
from selenium.webdriver.common.by import By

# ---------------- 商品列表 / 商品块 ----------------
INVENTORY_LIST = (By.CSS_SELECTOR, ".inventory_list")               # 商品列表容器
INVENTORY_ITEM = (By.CSS_SELECTOR, ".inventory_item")               # 商品块
INVENTORY_ITEM_NAME = (By.CSS_SELECTOR, ".inventory_item_name")     # 商品名称
INVENTORY_ITEM_IMG = (By.CSS_SELECTOR, "img.inventory_item_img")    # 商品图片
ADD_TO_CART_ANY = (By.CSS_SELECTOR, "[data-test^='add-to-cart-']")  # 所有加购按钮

# ---------------- 顶部导航 ----------------
BADGE = (By.CSS_SELECTOR, "[data-test='shopping-cart-badge']")      # 购物车角标
CART_LINK = (By.CSS_SELECTOR, "[data-test='shopping-cart-link']")   # 购物车图标
PRIMARY_HEADER = (By.CSS_SELECTOR, ".primary_header")               # 顶部 header
TITLE = (By.CSS_SELECTOR, ".title")                                 # 页面主标题

# ---------------- 购物车 / 结算共用 ----------------
CART_LIST = (By.CSS_SELECTOR, ".cart_list")                         # 购物车列表容器
CART_ITEM = (By.CSS_SELECTOR, ".cart_item")                         # 购物车商品行
BACK_TO_PRODUCTS = (By.CSS_SELECTOR, "[data-test='back-to-products']")  # 返回商品列表

# ---------------- 错误提示（登录/结算/未登录共用） ----------------
ERROR_MESSAGE = (By.CSS_SELECTOR, "h3[data-test='error']")          # 错误提示文案
ERROR_CONTAINER = (By.CSS_SELECTOR, ".error-message-container")     # 错误提示容器
