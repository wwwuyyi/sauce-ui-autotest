# -*- coding: utf-8 -*-
"""
generate_report.py —— 单文件 HTML 测试报告生成器（零依赖，纯 Python 标准库）

用途：直接解析 Allure 原始数据（reports/allure_results/ 下的 *-result.json /
      *-container.json / environment.properties），渲染为一个自包含的 index.html，
      无需安装 Allure CLI / Java 之外的任何环境（本脚本连 Java 都不需要）。

特点：
1. 零依赖：只用标准库（json / base64 / html / pathlib），任何 Python 3.8+ 可直接运行；
2. 单文件交付：CSS/JS 全部内联，截图以 base64 内嵌（>1.5MB 的超大图自动降级为相对路径），
   一个 index.html 即可发给任何人/上传 GitHub Pages 直接浏览；
3. 数据源不动：不修改任何 allure 原始 JSON，以后想换官方 Allure CLI 随时可切换；
4. 功能对齐 Allure Web：汇总卡片/状态与严重级别筛选/关键词搜索/用例步骤树/
   失败信息+堆栈/失败截图/参数化数据/环境信息。

用法：
    python generate_report.py                # 解析默认目录并生成报告
    python generate_report.py --open         # 生成后自动用默认浏览器打开
    python generate_report.py --results reports/allure_results --output out.html
"""
import argparse
import base64
import html
import json
import shutil
import webbrowser
from datetime import datetime
from pathlib import Path

# 项目根目录（脚本位于项目根，直接基于本文件定位）
PROJECT_ROOT = Path(__file__).resolve().parent

# 状态映射：allure 状态 -> (中文名, CSS 类名)
STATUS_MAP = {
    "passed": ("通过", "pass"),
    "failed": ("失败", "fail"),
    "broken": ("异常", "broken"),
    "skipped": ("跳过", "skip"),
}
# 严重级别展示顺序（与 Allure 一致）
SEVERITY_ORDER = ["blocker", "critical", "normal", "minor", "trivial"]
SEVERITY_CN = {
    "blocker": "致命", "critical": "严重", "normal": "普通",
    "minor": "次要", "trivial": "轻微",
}

MAX_IMAGE_EMBED_BYTES = 1.5 * 1024 * 1024  # 超过 1.5MB 的图片不内嵌，改相对路径引用
OVER_BUDGET_DIR_NAME = "attachments"       # 超大图附件目录名（位于输出 HTML 旁，随报告一起交付）
TEXT_TRUNCATE = 4000                       # 文本附件最大展示字符数
TRACE_TRUNCATE = 6000                      # 失败堆栈最大展示字符数


# ======================================================================
# 一、数据解析
# ======================================================================

def load_environment(results_dir: Path) -> list:
    """解析 environment.properties，返回 [(key, value), ...]"""
    env_file = results_dir / "environment.properties"
    if not env_file.exists():
        return []
    items = []
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            key, value = line.split("=", 1)
            items.append((key.strip(), value.strip()))
    return items


def has_attachments(stage: dict) -> bool:
    return bool(stage.get("attachments"))


def load_cases(results_dir: Path) -> list:
    """解析全部 *-result.json，并合并 container 中的 fixture 级附件"""
    cases = []
    for f in sorted(results_dir.glob("*-result.json")):
        try:
            cases.append(json.loads(f.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            continue
    cases.sort(key=lambda d: d.get("start") or 0)

    # 合并 container 附件：container.children 里的 uuid 对应 result，
    # 其 befores/afters 阶段的附件（fixture 内截图/日志）并入用例
    by_uuid = {c["uuid"]: c for c in cases if c.get("uuid")}
    for f in sorted(results_dir.glob("*-container.json")):
        try:
            container = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        for child_uuid in container.get("children", []):
            case = by_uuid.get(child_uuid)
            if case is None:
                continue
            fixture_atts = []
            for stage in list(container.get("befores", [])) + list(container.get("afters", [])):
                for att in stage.get("attachments", []):
                    fixture_atts.append({**att, "stage": stage.get("name", "fixture")})
            if fixture_atts:
                case.setdefault("_fixture_attachments", []).extend(fixture_atts)
    return cases


def label_map(case: dict) -> dict:
    """将 labels 列表转成 dict（severity/epic/feature/story/suite 等）"""
    result = {}
    for item in case.get("labels", []):
        result[item.get("name")] = item.get("value")
    return result


# ======================================================================
# 二、HTML 片段渲染
# ======================================================================

def render_attachments(attachments: list, results_dir: Path, asset_dir: Path = None) -> str:
    """渲染附件列表：图片内嵌 base64，文本/HTML 附件截断展示"""
    if not attachments:
        return ""
    parts = ['<div class="attachments">']
    for att in attachments:
        name = html.escape(att.get("name", "附件"))
        source = att.get("source", "")
        mime = att.get("type", "") or "text/plain"
        file_path = results_dir / source
        if not source or not file_path.exists():
            parts.append(f'<div class="att-missing">⚠ 附件缺失: {name} ({html.escape(source)})</div>')
            continue

        if mime.startswith("image/") and file_path.stat().st_size <= MAX_IMAGE_EMBED_BYTES:
            data = base64.b64encode(file_path.read_bytes()).decode("ascii")
            parts.append(
                f'<div class="att"><div class="att-name">📷 {name}</div>'
                f'<img class="att-img" src="data:{mime};base64,{data}" alt="{name}"></div>')
        elif mime.startswith("image/"):
            # 超大图片：复制到输出目录旁的 attachments/，报告目录自包含
            # （可整体拷贝交付 / 直接整目录发布 GitHub Pages，无需再携带 allure_results）
            refer = f"../allure_results/{html.escape(source)}"  # 兜底：结果目录相对引用
            if asset_dir is not None:
                try:
                    asset_dir.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(file_path, asset_dir / Path(source).name)
                    refer = f"{OVER_BUDGET_DIR_NAME}/{html.escape(Path(source).name)}"
                except OSError:
                    pass  # 复制失败不阻断报告生成，回退为结果目录引用
            parts.append(
                f'<div class="att"><div class="att-name">📷 {name}（大图，采用文件引用）</div>'
                f'<img class="att-img" src="{refer}" alt="{name}"></div>')
        else:
            try:
                text = file_path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                text = ""
            truncated = len(text) > TEXT_TRUNCATE
            shown = text[:TEXT_TRUNCATE]
            note = f'<div class="att-truncated">（内容过长已截断，共 {len(text)} 字符）</div>' if truncated else ""
            parts.append(
                f'<div class="att"><div class="att-name">📄 {name}</div>'
                f'<pre class="att-text">{html.escape(shown)}</pre>{note}</div>')
    parts.append("</div>")
    return "".join(parts)


def render_steps(steps: list, results_dir: Path, asset_dir: Path = None) -> str:
    """递归渲染步骤树（含每步附件）"""
    if not steps:
        return ""
    items = []
    for step in steps:
        status_name, status_cls = STATUS_MAP.get(step.get("status"), ("未知", "unknown"))
        step_html = (
            f'<li class="step step-{status_cls}">'
            f'<span class="step-dot" title="{status_name}"></span>'
            f'<span class="step-name">{html.escape(step.get("name", "未命名步骤"))}</span>'
            f'{render_attachments(step.get("attachments", []), results_dir, asset_dir)}'
            f'{render_steps(step.get("steps", []), results_dir, asset_dir)}'
            f"</li>")
        items.append(step_html)
    return f'<ul class="steps">{"".join(items)}</ul>'


def render_failure(case: dict) -> str:
    """渲染失败信息（message + trace）"""
    details = case.get("statusDetails") or {}
    if not details.get("message") and not details.get("trace"):
        return ""
    message = html.escape(str(details.get("message", "")))
    trace = str(details.get("trace", ""))
    truncated = len(trace) > TRACE_TRUNCATE
    trace_html = html.escape(trace[:TRACE_TRUNCATE])
    note = f'\n...（堆栈过长已截断，共 {len(trace)} 字符）' if truncated else ""
    return (f'<div class="failure"><div class="failure-msg">❌ {message}</div>'
            f'<pre class="failure-trace">{trace_html}{note}</pre></div>')


def render_params(case: dict) -> str:
    """渲染参数化数据（ids 如 SAUCE-INV-003）"""
    params = case.get("parameters") or []
    if not params:
        return ""
    chips = []
    for p in params:
        value = str(p.get("value", ""))
        shown = value if len(value) <= 120 else value[:120] + "…"
        chips.append(f'<span class="param-chip" title="{html.escape(value)}">{html.escape(shown)}</span>')
    return f'<div class="params">{"".join(chips)}</div>'


def seconds_between(start: int, stop: int) -> float:
    """毫秒时间戳差 -> 秒（缺省字段容错为 0）"""
    try:
        return round((int(stop) - int(start)) / 1000, 2)
    except (TypeError, ValueError):
        return 0.0


# ======================================================================
# 三、整体页面组装
# ======================================================================

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Web 商城 UI 自动化测试报告</title>
<style>
:root {{ --pass:#28a745; --fail:#d73a49; --broken:#a371f7; --skip:#8b949e;
        --bg:#f6f8fa; --card:#ffffff; --border:#e1e4e8; --primary:#1b4a7a; }}
* {{ box-sizing: border-box; }}
body {{ margin:0; font-family:-apple-system,"Segoe UI","Microsoft YaHei",sans-serif;
        background:var(--bg); color:#24292e; }}
header {{ background:linear-gradient(120deg,#0d2b52,#1b4a7a); color:#fff; padding:22px 32px; }}
header h1 {{ margin:0 0 6px; font-size:22px; }}
header .sub {{ opacity:.85; font-size:13px; }}
.env-chips {{ margin-top:12px; }}
.env-chip {{ display:inline-block; background:rgba(255,255,255,.15); border-radius:12px;
        padding:2px 10px; margin:3px 6px 0 0; font-size:12px; }}
main {{ max-width:1280px; margin:0 auto; padding:20px 32px 60px; }}
.cards {{ display:flex; flex-wrap:wrap; gap:12px; }}
.card {{ background:var(--card); border:1px solid var(--border); border-radius:8px;
        padding:14px 22px; min-width:110px; text-align:center; }}
.card .num {{ font-size:26px; font-weight:700; }}
.card .lbl {{ font-size:12px; color:#57606a; margin-top:2px; }}
.card .num.c-pass {{ color:var(--pass); }} .card .num.c-fail {{ color:var(--fail); }}
.card .num.c-broken {{ color:var(--broken); }} .card .num.c-skip {{ color:var(--skip); }}
.bar {{ height:10px; border-radius:5px; overflow:hidden; display:flex; margin:16px 0 4px;
        background:#eaecef; }}
.bar span {{ display:block; height:100%; }}
.bar-legend {{ font-size:12px; color:#57606a; }}
.toolbar {{ display:flex; flex-wrap:wrap; gap:10px; align-items:center; margin:18px 0 10px; }}
.status-filters {{ display:flex; gap:6px; }}
.filter-status {{ border:1px solid var(--border); background:var(--card); border-radius:16px;
        padding:4px 14px; cursor:pointer; font-size:13px; }}
.filter-status.active {{ background:var(--primary); color:#fff; border-color:var(--primary); }}
.toolbar select, .toolbar input {{ border:1px solid var(--border); background:var(--card);
        border-radius:6px; padding:5px 10px; font-size:13px; }}
.toolbar input {{ flex:1; min-width:180px; }}
.hint {{ font-size:12px; color:#57606a; margin-bottom:8px; }}
table {{ width:100%; border-collapse:collapse; background:var(--card);
        border:1px solid var(--border); border-radius:8px; overflow:hidden; }}
thead th {{ background:#f1f3f5; text-align:left; padding:10px 14px; font-size:13px;
        color:#57606a; border-bottom:1px solid var(--border); }}
tr.case {{ cursor:pointer; border-left:4px solid var(--border); }}
tr.case:hover {{ background:#f6fbff; }}
tr.case.open {{ background:#eef6ff; }}
tr.case.st-pass {{ border-left-color:var(--pass); }}
tr.case.st-fail {{ border-left-color:var(--fail); }}
tr.case.st-broken {{ border-left-color:var(--broken); }}
tr.case.st-skip {{ border-left-color:var(--skip); }}
tr.case td {{ padding:10px 14px; border-top:1px solid var(--border); font-size:13px; }}
tr.detail td {{ background:#fafbfc; border-top:1px dashed var(--border); padding:16px 20px; }}
.status-badge {{ display:inline-block; padding:2px 10px; border-radius:12px; color:#fff;
        font-size:12px; white-space:nowrap; }}
.badge-pass {{ background:var(--pass); }} .badge-fail {{ background:var(--fail); }}
.badge-broken {{ background:var(--broken); }} .badge-skip {{ background:var(--skip); }}
.sev {{ display:inline-block; padding:2px 8px; border-radius:4px; font-size:12px;
        font-weight:600; white-space:nowrap; }}
.sev-blocker {{ background:#d73a49; color:#fff; }}
.sev-critical {{ background:#ff7b3c; color:#fff; }}
.sev-normal {{ background:#ffc107; color:#5c4700; }}
.sev-minor {{ background:#8bb4ff; color:#10305c; }}
.sev-trivial {{ background:#d0d7de; color:#57606a; }}
.case-name {{ font-weight:600; }}
.case-meta {{ font-size:12px; color:#57606a; margin-top:3px; }}
.chip {{ display:inline-block; background:#eef1f4; border-radius:10px; padding:1px 8px;
        font-size:12px; color:#57606a; margin-right:4px; }}
.duration {{ font-variant-numeric: tabular-nums; color:#57606a; font-size:12px; }}
.steps {{ list-style:none; margin:6px 0 2px; padding-left:0; }}
.steps .steps {{ padding-left:22px; }}
.step {{ padding:2px 0; font-size:13px; }}
.step-dot {{ display:inline-block; width:8px; height:8px; border-radius:50%;
        margin-right:7px; background:#cbd2d9; }}
.step-pass .step-dot {{ background:var(--pass); }}
.step-fail .step-dot {{ background:var(--fail); }}
.step-broken .step-dot {{ background:var(--broken); }}
.step-skip .step-dot {{ background:var(--skip); }}
.failure {{ margin-top:10px; background:#fff5f5; border:1px solid #ffc9c9;
        border-radius:6px; padding:10px 12px; }}
.failure-msg {{ color:var(--fail); font-weight:600; font-size:13px; margin-bottom:6px; }}
.failure-trace {{ margin:0; font-size:12px; color:#6a4b4b; white-space:pre-wrap;
        word-break:break-all; max-height:260px; overflow:auto; }}
.attachments {{ margin-top:6px; }}
.att {{ margin:6px 0; }}
.att-name {{ font-size:12px; color:#57606a; margin-bottom:3px; }}
.att-img {{ max-width:100%; border:1px solid var(--border); border-radius:6px; }}
.att-text {{ margin:0; font-size:12px; background:#f1f3f5; border-radius:6px;
        padding:8px; white-space:pre-wrap; word-break:break-all; max-height:220px; overflow:auto; }}
.att-truncated, .att-missing {{ font-size:12px; color:#b35900; }}
.params {{ margin-top:6px; }}
.param-chip {{ font-size:11px; background:#fff8e1; color:#7a5b00; border-radius:4px;
        padding:1px 7px; margin-right:5px; }}
.empty {{ background:var(--card); border:1px dashed var(--border); border-radius:8px;
        padding:60px 20px; text-align:center; color:#57606a; }}
footer {{ text-align:center; color:#8b949e; font-size:12px; margin-top:30px; }}
</style>
</head>
<body>
<header>
  <h1>🧪 Web 商城 UI 自动化测试报告</h1>
  <div class="sub">数据源：Allure Results（框架自动生成） · 生成时间：{generated_at}</div>
  <div class="env-chips">{env_chips}</div>
</header>
<main>
  <div class="cards">{cards}</div>
  <div class="bar">{bar_segments}</div>
  <div class="bar-legend">{bar_legend}</div>

  <div class="toolbar">
    <div class="status-filters" id="status-filters">{status_buttons}</div>
    <select id="f-severity" onchange="applyFilters()">{severity_options}</select>
    <select id="f-feature" onchange="applyFilters()">{feature_options}</select>
    <input id="f-search" type="text" placeholder="🔍 搜索用例名 / 模块 / 参数…" oninput="applyFilters()">
  </div>
  <div class="hint">共 <b id="total-count">{total}</b> 条用例，当前显示 <b id="visible-count">{total}</b> 条；点击用例行展开步骤与截图。</div>

  <table>
    <thead><tr>
      <th style="width:70px">状态</th><th>用例</th><th style="width:90px">严重级别</th>
      <th style="width:80px">耗时</th><th style="width:130px">结果数据</th>
    </tr></thead>
    <tbody>{rows}</tbody>
  </table>
  {empty_banner}
  <footer>Generated by generate_report.py · 数据文件未做任何修改，可随时改用官方 Allure CLI 渲染</footer>
</main>
<script>
const applyFilters = () => {{
  const active = document.querySelector('#status-filters .filter-status.active');
  const st = active ? active.dataset.status : 'all';
  const sev = document.getElementById('f-severity').value;
  const feat = document.getElementById('f-feature').value;
  const q = document.getElementById('f-search').value.trim().toLowerCase();
  let visible = 0;
  document.querySelectorAll('tr.case').forEach(tr => {{
    const okSt = st === 'all' || tr.dataset.status === st;
    const okSev = sev === 'all' || tr.dataset.severity === sev;
    const okFeat = feat === 'all' || tr.dataset.feature === feat;
    const okQ = !q || tr.dataset.search.includes(q);
    const show = okSt && okSev && okFeat && okQ;
    tr.style.display = show ? '' : 'none';
    const detail = tr.nextElementSibling;
    if (detail && detail.classList.contains('detail')) {{
      detail.style.display = show && tr.classList.contains('open') ? '' : 'none';
    }}
    if (show) visible++;
  }});
  document.getElementById('visible-count').textContent = visible;
}};
const toggleRow = (tr) => {{
  tr.classList.toggle('open');
  const detail = tr.nextElementSibling;
  if (detail && detail.classList.contains('detail')) {{
    detail.style.display = tr.classList.contains('open') ? '' : 'none';
  }}
}};
window.addEventListener('DOMContentLoaded', () => {{
  document.querySelectorAll('#status-filters .filter-status').forEach(btn =>
    btn.addEventListener('click', () => {{
      document.querySelectorAll('#status-filters .filter-status').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      applyFilters();
    }}));
}});
</script>
</body>
</html>"""


def build_report(results_dir: Path, cases: list, env_items: list, asset_dir: Path = None) -> str:
    """组装报告 HTML 字符串"""
    if not cases:
        banner = ('<div class="empty">暂未发现 Allure 结果文件（*-result.json）。<br>'
                  '请先执行测试：<b>python -m pytest</b>，再运行本脚本生成报告。</div>')
        rows, cards, bar_segments, bar_legend, total = "", "", "", "", 0
    else:
        banner = ""

    # ---- 汇总卡片 ----
    status_count = {"passed": 0, "failed": 0, "broken": 0, "skipped": 0}
    severity_count = {}
    feature_set = []
    for case in cases:
        status_count[case.get("status", "skipped")] = status_count.get(case.get("status", "skipped"), 0) + 1
        labels = label_map(case)
        severity_count[labels.get("severity", "normal")] = severity_count.get(labels.get("severity", "normal"), 0) + 1
    total = len(cases)
    passed = status_count.get("passed", 0)
    failed = status_count.get("failed", 0)
    broken = status_count.get("broken", 0)
    skipped = status_count.get("skipped", 0)
    pass_rate = f"{passed * 100.0 / total:.1f}%" if total else "—"
    total_duration = sum(seconds_between(c.get("start"), c.get("stop")) for c in cases)

    cards = (
        f'<div class="card"><div class="num">{total}</div><div class="lbl">用例总数</div></div>'
        f'<div class="card"><div class="num c-pass">{passed}</div><div class="lbl">通过</div></div>'
        f'<div class="card"><div class="num c-fail">{failed}</div><div class="lbl">失败</div></div>'
        f'<div class="card"><div class="num c-broken">{broken}</div><div class="lbl">异常</div></div>'
        f'<div class="card"><div class="num c-skip">{skipped}</div><div class="lbl">跳过</div></div>'
        f'<div class="card"><div class="num" style="color:#1b4a7a">{pass_rate}</div><div class="lbl">通过率</div></div>'
        f'<div class="card"><div class="num" style="color:#1b4a7a">{total_duration:.1f}s</div><div class="lbl">总耗时</div></div>')

    def bar(color, width_pct):
        return f'<span style="background:{color};width:{width_pct:.1f}%"></span>' if width_pct > 0 else ""

    if total:
        bar_segments = (
            bar("#28a745", passed * 100.0 / total) + bar("#d73a49", failed * 100.0 / total)
            + bar("#a371f7", broken * 100.0 / total) + bar("#8b949e", skipped * 100.0 / total))
        bar_legend = (f"通过 {passed} · 失败 {failed} · 异常 {broken} · 跳过 {skipped} · "
                      f"通过率 {pass_rate} · 总耗时 {total_duration:.1f}s")
    else:
        bar_segments = bar_legend = ""

    # ---- 筛选控件 ----
    status_buttons = ['<button class="filter-status active" data-status="all">全部 '
                      f'<b>{total}</b></button>']
    for key in ("passed", "failed", "broken", "skipped"):
        name, _ = STATUS_MAP[key]
        status_buttons.append(
            f'<button class="filter-status" data-status="{key}">{name} <b>{status_count.get(key, 0)}</b></button>')
    status_buttons = "".join(status_buttons)

    severity_options = ['<option value="all">全部级别</option>']
    for sev in SEVERITY_ORDER:
        if sev in severity_count:
            severity_options.append(
                f'<option value="{sev}">{SEVERITY_CN.get(sev, sev)}（{severity_count[sev]}）</option>')
    severity_options = "".join(severity_options)

    feature_set = sorted({label_map(c).get("feature", "未分类") for c in cases})
    feature_options = ['<option value="all">全部模块</option>']
    feature_options += [f'<option value="{html.escape(f, quote=True)}">{html.escape(f)}</option>' for f in feature_set]
    feature_options = "".join(feature_options)

    # ---- 用例行 ----
    rows = []
    for case in cases:
        status_name, status_cls = STATUS_MAP.get(case.get("status"), ("未知", "unknown"))
        labels = label_map(case)
        severity = labels.get("severity", "normal")
        feature = labels.get("feature", "未分类")
        story = labels.get("story", "")
        name = case.get("name", "未命名用例")
        full_name = case.get("fullName", "")
        duration = seconds_between(case.get("start"), case.get("stop"))

        search_text = " ".join([name, full_name, feature, story,
                                labels.get("suite", ""), *[str(p.get("value", "")) for p in case.get("parameters", [])]]).lower()
        open_cls = (' class="case st-%s open"' % status_cls
                    if case.get("status") in ("failed", "broken")
                    else f' class="case st-{status_cls}"')

        meta = []
        if labels.get("epic"):
            meta.append(f'<span class="chip">{html.escape(labels["epic"])}</span>')
        meta.append(f'<span class="chip">{html.escape(feature)}</span>')
        if story:
            meta.append(f'<span class="chip">{html.escape(story)}</span>')
        meta_html = "".join(meta)

        detail_html = (
            f'<div class="description">{html.escape(case.get("description", ""))}</div>'
            f'{render_params(case)}'
            f'{render_steps(case.get("steps", []), results_dir, asset_dir)}'
            f'{render_failure(case)}'
            f'<b style="font-size:13px">用例附件</b>'
            f'{render_attachments(case.get("attachments", []), results_dir, asset_dir)}'
            f'<b style="font-size:13px">执行环境 / Fixture 附件</b>'
            f'{render_attachments(case.get("_fixture_attachments", []), results_dir, asset_dir)}')

        rows.append(
            f'<tr{open_cls} data-status="{status_cls}" data-severity="{severity}" '
            f'data-feature="{html.escape(feature, quote=True)}" data-search="{html.escape(search_text, quote=True)}" '
            f'onclick="toggleRow(this)">'
            f'<td><span class="status-badge badge-{status_cls}">{status_name}</span></td>'
            f'<td><div class="case-name">{html.escape(name)}</div>'
            f'<div class="case-meta">{meta_html}<span class="chip">{html.escape(full_name)}</span></div></td>'
            f'<td><span class="sev sev-{severity}">{SEVERITY_CN.get(severity, severity)}</span></td>'
            f'<td><span class="duration">{duration}s</span></td>'
            f'<td><span class="chip">{html.escape(labels.get("suite", "-"))}</span></td></tr>'
            f'<tr class="detail" style="display:none"><td colspan="5">{detail_html}</td></tr>')
    rows = "".join(rows)

    env_chips = "".join(
        f'<span class="env-chip">{html.escape(k)} = {html.escape(v)}</span>' for k, v in env_items)

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return PAGE_TEMPLATE.format(
        generated_at=generated_at, env_chips=env_chips, cards=cards,
        bar_segments=bar_segments, bar_legend=bar_legend,
        status_buttons=status_buttons, severity_options=severity_options,
        feature_options=feature_options, rows=rows, total=total,
        visible_count=total, empty_banner=banner,
    )


# ======================================================================
# 四、入口
# ======================================================================

def main():
    parser = argparse.ArgumentParser(
        description="将 Allure 原始结果渲染为单文件 HTML 测试报告（零依赖）")
    parser.add_argument("--results", default=str(PROJECT_ROOT / "reports" / "allure_results"),
                        help="Allure 原始结果目录（默认 reports/allure_results）")
    parser.add_argument("--output", default=str(PROJECT_ROOT / "reports" / "html-report" / "index.html"),
                        help="输出 HTML 路径（默认 reports/html-report/index.html，与官方 Allure 输出目录隔离）")
    parser.add_argument("--open", action="store_true", help="生成后用默认浏览器自动打开")
    args = parser.parse_args()

    results_dir = Path(args.results)
    if not results_dir.is_absolute():
        results_dir = PROJECT_ROOT / results_dir
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path

    env_items = load_environment(results_dir)
    cases = load_cases(results_dir)

    # 超大图附件目录：位于输出 HTML 旁，报告目录整体自包含
    # （整目录交付/发布 GitHub Pages 时不依赖外部的 allure_results 原图）
    output_path.parent.mkdir(parents=True, exist_ok=True)
    asset_dir = output_path.parent / OVER_BUDGET_DIR_NAME
    report_html = build_report(results_dir, cases, env_items, asset_dir)

    output_path.write_text(report_html, encoding="utf-8")

    print(f"[OK] 报告已生成: {output_path}")
    print(f"   数据源: {results_dir}")
    if asset_dir.is_dir() and list(asset_dir.iterdir()):
        print(f"   大图附件目录: {asset_dir}（>1.5MB 截图未内嵌，随报告目录一起交付）")
    if cases:
        from collections import Counter
        counter = Counter(c.get("status") for c in cases)
        print(f"   用例合计: {len(cases)} · 通过 {counter.get('passed', 0)} / "
              f"失败 {counter.get('failed', 0)} / 异常 {counter.get('broken', 0)} / "
              f"跳过 {counter.get('skipped', 0)}")
        print("   提示: 失败的用例行默认展开，可直接查看步骤与截图")
    else:
        print("   警告: 未发现用例结果，请先执行 python -m pytest")
    if args.open:
        webbrowser.open(output_path.resolve().as_uri())


if __name__ == "__main__":
    main()