# -*- coding: utf-8 -*-
"""
test_inventory.py —— 商品首页模块测试用例（TestCase 用例层）

职责：只做【业务调用 + 结果断言】，数据全部来自 config/env.yaml。

覆盖原始用例（核心断言逻辑完整保留）：
  SAUCE-INV-001   商品列表加载（数量与非空校验）
  SAUCE-INV-002   商品名称/价格/图片逐项断言
  SAUCE-INV-003~006 商品排序（数据驱动合并，4 组参数化数据）
  SAUCE-INV-007   商品加入购物车（按钮切换+角标+1）
  SAUCE-INV-008   移除购物车（按钮恢复+角标消失）
  SAUCE-INV-009   购物车角标多商品累计计数
"""
import logging
import re
from decimal import Decimal

import allure
import pytest

from utils.allure_util import set_severity_from_str
from utils.data_util import get_product
from utils.yaml_util import YamlUtil

logger = logging.getLogger(__name__)

CONFIG = YamlUtil().read_yaml("config/env.yaml")

# 价格展示格式：$ 开头 + 数字 + 可选两位小数（SAUCE-INV-001 格式校验基准）
PRICE_PATTERN = re.compile(r"^\$\d+(\.\d{2})?$")


def _expected_names(case_data: dict) -> list:
    return CONFIG["sort_expected"][case_data["names_key"]]


def _expected_price_numbers(case_data: dict) -> list:
    """期望价格序列转换为 Decimal 列表（避免 float 精度误差）"""
    return [Decimal(price.replace("$", ""))
            for price in CONFIG["sort_expected"][case_data["prices_key"]]]


@allure.epic("Sauce Demo 商城")
@allure.feature("商品首页模块")
class TestInventory:
    """商品首页模块测试用例集合"""

    # ===================== SAUCE-INV-001 商品列表加载 =====================

    @allure.story("商品列表")
    @allure.severity(allure.severity_level.BLOCKER)
    @allure.title("SAUCE-INV-001 商品列表加载（数量与非空校验）")
    @allure.description("列表页展示 6 个商品，名称/价格/图片均非空且格式正确")
    @pytest.mark.smoke
    def test_inventory_items_loaded(self, inventory_page):
        with allure.step("校验页面 URL"):
            assert inventory_page.get_current_url() == CONFIG["urls"]["inventory"]

        with allure.step("校验商品列表容器可见"):
            assert inventory_page.is_element_visible(inventory_page.INVENTORY_LIST)

        with allure.step("断言1-商品总数为 6"):
            assert inventory_page.get_product_count() == CONFIG["expected"]["inventory_item_count"]

        with allure.step("断言2-全部商品名称非空"):
            names = inventory_page.get_product_names()
            assert all(name.strip() != "" for name in names)

        with allure.step("断言3-全部价格格式符合 $X.YY"):
            for price in inventory_page.get_product_prices():
                assert PRICE_PATTERN.fullmatch(price) is not None, f"价格格式异常: {price}"

        with allure.step("断言4-全部商品图片 src 非空"):
            srcs = inventory_page.get_product_image_srcs()
            assert all(src for src in srcs)

    # ===================== SAUCE-INV-002 逐项内容断言 =====================

    @allure.story("商品列表")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("SAUCE-INV-002 商品名称/价格/图片逐项断言")
    @allure.description("展示内容与官方商品数据完全一致：名称/价格精确匹配，图片真实渲染")
    def test_inventory_items_exact_content(self, inventory_page):
        az_names = CONFIG["sort_expected"]["az_names"]
        az_prices = CONFIG["sort_expected"]["az_prices"]

        with allure.step("断言1-商品名称与官方列表精确一致"):
            assert inventory_page.get_product_names() == az_names

        with allure.step("断言2-商品价格与官方列表精确一致"):
            assert inventory_page.get_product_prices() == az_prices

        with allure.step("等待全部商品图片完成解码"):
            inventory_page.wait_product_images_loaded()

        with allure.step("断言3-全部图片真实渲染（naturalWidth>0）"):
            for width in inventory_page.get_image_natural_widths():
                assert width > 0, "存在未真实解码的图片（naturalWidth=0）"

        with allure.step("断言4-图片 alt 属性校验（站点版本差异，配置可开关软硬校验）"):
            alts = inventory_page.get_image_alts()
            if CONFIG["expected"].get("require_image_alt_nonempty", False):
                assert all(alt.strip() != "" for alt in alts), f"存在空 alt 的图片: {alts}"
            else:
                allure.attach(" | ".join(alts), "图片 alt 实际值", allure.attachment_type.TEXT)
                logger.warning("站点当前版本部分图片 alt 为空，已记录实际值（记录型软校验）")

        with allure.step("断言5-首商品加购按钮可见"):
            backpack = get_product(4)
            assert inventory_page.is_element_visible(inventory_page.add_button(backpack["slug"]))

    # ===================== SAUCE-INV-003~006 排序（数据驱动） =====================

    @allure.story("商品排序")
    @pytest.mark.parametrize(
        "case_data",
        CONFIG["sort_cases"],
        ids=[case["case_id"] for case in CONFIG["sort_cases"]],
    )
    @allure.title("商品排序（数据驱动）")
    @allure.description("四种排序（az/za/lohi/hilo）排序后名称与价格序列完全符合期望，下拉框选中值正确")
    def test_product_sort(self, inventory_page, case_data):
        allure.dynamic.title(case_data["name"])
        set_severity_from_str("normal")

        expected_names = _expected_names(case_data)

        with allure.step(f"选择排序方式: {case_data['value']} 并等待生效"):
            inventory_page.sort_and_wait_names(case_data["value"], expected_names)

        with allure.step("断言1-下拉框选中值正确"):
            assert inventory_page.get_sort_value() == case_data["value"]

        with allure.step("断言2-名称顺序与期望序列完全一致"):
            actual_names = inventory_page.get_product_names()
            assert actual_names == expected_names
            assert actual_names[0] == expected_names[0]   # 首元素
            assert actual_names[-1] == expected_names[-1]  # 末元素

        with allure.step("断言3-价格顺序与期望序列完全一致"):
            assert inventory_page.get_price_numbers() == _expected_price_numbers(case_data)

        with allure.step("断言4-商品总数仍为 6"):
            assert inventory_page.get_product_count() == CONFIG["expected"]["inventory_item_count"]

    # ===================== SAUCE-INV-007 加购 =====================

    @allure.story("购物车联动")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("SAUCE-INV-007 商品加入购物车（按钮切换+角标+1）")
    @allure.description("点击加购后按钮切换为 Remove、加购按钮消失、购物车角标显示 1")
    def test_add_item_to_cart(self, inventory_page):
        backpack = get_product(4)
        slug = backpack["slug"]

        with allure.step("点击加购并等待按钮切换"):
            inventory_page.add_to_cart(slug)

        with allure.step("断言1-按钮切换为 Remove 且文案正确"):
            assert inventory_page.get_button_text(inventory_page.remove_button(slug)) == "Remove"

        with allure.step("断言2-加购按钮已从 DOM 消失"):
            assert inventory_page.is_add_button_absent(slug)

        with allure.step("断言3-购物车角标显示 1"):
            inventory_page.wait_badge_text("1")
            assert inventory_page.get_badge_text() == "1"

    # ===================== SAUCE-INV-008 移除 =====================

    @allure.story("购物车联动")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("SAUCE-INV-008 移除购物车（按钮恢复+角标消失）")
    @allure.description("点击 Remove 后按钮恢复为 Add to cart、角标从 DOM 移除")
    def test_remove_item_from_cart(self, inventory_page):
        backpack = get_product(4)
        slug = backpack["slug"]

        with allure.step("预置：先加购 1 件商品"):
            inventory_page.add_to_cart(slug)
            inventory_page.wait_badge_text("1")

        with allure.step("点击移除并等待按钮恢复"):
            inventory_page.remove_from_cart(slug)

        with allure.step("断言1-按钮恢复为 Add to cart 且文案正确"):
            assert inventory_page.get_button_text(inventory_page.add_button(slug)) == "Add to cart"

        with allure.step("断言2-移除按钮已从 DOM 消失"):
            assert inventory_page.is_remove_button_absent(slug)

        with allure.step("断言3-角标归零后从 DOM 移除"):
            assert inventory_page.is_badge_absent()

    # ===================== SAUCE-INV-009 角标累计 =====================

    @allure.story("购物车联动")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("SAUCE-INV-009 购物车角标多商品累计计数")
    @allure.description("依次加购 3 件商品，角标数字依次为 1、2、3，按钮状态集合正确")
    def test_badge_accumulate_count(self, inventory_page):
        slugs = [CONFIG["products"][i]["slug"] for i in (0, 1, 2)]  # Backpack/Bike Light/Onesie

        with allure.step("依次加购 3 件商品并逐步校验角标"):
            for index, slug in enumerate(slugs, start=1):
                inventory_page.add_to_cart(slug)
                inventory_page.wait_badge_text(str(index))
                assert inventory_page.get_badge_text() == str(index), (
                    f"第 {index} 次加购后角标应为 {index}")

        with allure.step("断言1-最终角标为 3"):
            assert inventory_page.get_badge_text() == "3"

        with allure.step("断言2-按钮状态集合正确（3 移除 + 3 加购，共 6 商品）"):
            assert inventory_page.get_remove_button_count() == 3
            assert inventory_page.get_add_button_count() == 3