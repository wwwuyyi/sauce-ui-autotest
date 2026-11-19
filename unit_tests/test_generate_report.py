# -*- coding: utf-8 -*-
"""generate_report.py 纯函数单元测试（不依赖真实 Allure 目录与浏览器）"""
import json

from generate_report import load_cases, seconds_between


def _write_json(directory, name: str, payload: dict) -> None:
    """在临时目录写入一份 *-result.json / *-container.json"""
    (directory / f"{name}.json").write_text(json.dumps(payload), encoding="utf-8")


def _case(uuid: str, history_id: str, start: int, status: str = "passed",
          name: str = "case", test_case_id: str = None) -> dict:
    payload = {"uuid": uuid, "historyId": history_id, "start": start,
               "stop": start + 1000, "status": status, "name": name}
    if test_case_id:
        payload["testCaseId"] = test_case_id
    return payload


def test_dedupe_keeps_latest_attempt(tmp_path):
    """重跑产生的多条结果按 historyId 去重，保留 start 最大的一次"""
    _write_json(tmp_path, "a-result", _case("u1", "h1", 1000, "failed"))
    _write_json(tmp_path, "b-result", _case("u2", "h1", 2000, "passed"))
    _write_json(tmp_path, "c-result", _case("u3", "h2", 1500, "passed", "case2"))

    cases = load_cases(tmp_path)

    assert len(cases) == 2
    by_history = {case["historyId"]: case for case in cases}
    assert by_history["h1"]["uuid"] == "u2"
    assert by_history["h1"]["status"] == "passed"
    # 结果按 start 升序输出
    assert [case["uuid"] for case in cases] == ["u3", "u2"]


def test_dedupe_uses_history_id_not_test_case_id(tmp_path):
    """参数化实例只有 historyId 不同：不能被 testCaseId 合并成一条"""
    _write_json(tmp_path, "p1-result",
                _case("u1", "h1", 1000, name="param[1]", test_case_id="tc1"))
    _write_json(tmp_path, "p2-result",
                _case("u2", "h2", 2000, name="param[2]", test_case_id="tc1"))

    cases = load_cases(tmp_path)

    assert len(cases) == 2
    assert {case["historyId"] for case in cases} == {"h1", "h2"}


def test_container_attachments_merged_into_case(tmp_path):
    """container 的 befores/afters 附件并入对应 result 的 _fixture_attachments"""
    _write_json(tmp_path, "case-result", _case("u1", "h1", 1000))
    _write_json(tmp_path, "case-container", {
        "uuid": "c1",
        "children": ["u1"],
        "befores": [{"name": "setup", "attachments": [
            {"name": "fixture 截图", "source": "s1.png", "type": "image/png"}]}],
        "afters": [{"name": "teardown", "attachments": [
            {"name": "控制台日志", "source": "s2.txt", "type": "text/plain"}]}],
    })
    # 指向不存在 result 的 container 不应报错
    _write_json(tmp_path, "orphan-container", {"uuid": "c2", "children": ["missing"]})

    cases = load_cases(tmp_path)

    assert len(cases) == 1
    attachments = cases[0]["_fixture_attachments"]
    assert [att["name"] for att in attachments] == ["fixture 截图", "控制台日志"]
    assert [att["stage"] for att in attachments] == ["setup", "teardown"]


def test_malformed_result_file_is_ignored(tmp_path):
    """损坏的 result JSON 被跳过，不影响其他用例"""
    (tmp_path / "broken-result.json").write_text("{not json", encoding="utf-8")
    _write_json(tmp_path, "good-result", _case("u1", "h1", 1000))

    cases = load_cases(tmp_path)

    assert len(cases) == 1
    assert cases[0]["uuid"] == "u1"


def test_seconds_between_handles_missing_and_invalid_values():
    """耗时换算：正常值四舍五入到 2 位，缺省/非法值容错为 0.0"""
    assert seconds_between(1000, 3500) == 2.5
    assert seconds_between("1000", "2250") == 1.25
    assert seconds_between(None, 1000) == 0.0
    assert seconds_between(1000, None) == 0.0
    assert seconds_between("bad", 1000) == 0.0
    assert seconds_between(None, None) == 0.0
