#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gate-check.py — PM Agent 流程产物机器强制门禁（v5.22 建立，架构级风险 B1 修复；v5.29 新增 G5）

用途：把「蓝图已产出」「UI 走查已执行」「无登录页」「PRD 必交付物」「浏览器断言已执行」
      从"文档强制（靠 Agent 自觉）"升级为"机器强制（不过就打回）"。lint/pm-review/browser
      已在 build 内自动跑，本脚本补上 build 覆盖不到的**流程产物**检查，交付前必须运行。

用法：
    python scripts/gate-check.py --outdir {交付目录} [--mobile] [--single]

参数：
    --outdir  交付目录（各端产物 + work/ + _snapshots/ 所在目录）
    --mobile  强制检查移动端 M79（登录页）——传产物文件名时用 --mobile-file

    python scripts/gate-check.py --outdir {目录} --mobile-file {移动端产物.html}

检查项（任一 fail → 退出码 1，禁止交付）：
    G1 蓝图已产出：work/pm-bluemap.md 存在且含 7 节必需标题（产品定位/信息架构/
       核心用户流程/关键状态机/边界态清单/不做清单/易错交互预判）
       + 契约先行：蓝图 mtime 不得早于 project-contract-*.md（茶叶商城教训：蓝图
       先于契约自由发挥，规划契约外功能导致与实际产物失配）
    G2 UI 走查已执行：_snapshots/index.html 图集存在 + _snapshots/ui/ 有截图
       + work/ui-review.md 走查报告存在且含通过标记（「✅」且含「通过」或「修复」）
    G3 无默认登录页（移动端）：产物不含 page-login / wechatLogin / 登录态函数
       （M79 铁律）
    G4 PRD 必交付物（M106）：契约第十一章含需求文档 → 对应产物必须存在；
       work/prd/ 注入文件（详细版四件套或简易版两件套）必须齐全非空。
       需求文档 100% 生成，防"三端原型做完但 PRD 漏交付"（闪修侠事故）
    G5 浏览器断言已执行（v5.29；v5.31 扩双端）：交付前对移动端与桌面端产物实跑
       browser-check.py（B1-B19），任一断言失败 = 禁止交付。堵 --no-verify/--skip-browser
       跳过浏览器断言漏洞（茶叶商城事故：B6 死按钮漏网交付，ui-review 却声称全部通过；
       D44 桌面端详情误用 openDrawer 抽屉——桌面端同样纳入强制复核）

退出码：
    0 = 全部通过，可以交付
    1 = 存在未完成流程产物，禁止交付
"""

import os
import re
import sys
import json
import argparse
import subprocess

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding='utf-8')
    except Exception:
        pass

OK = '✅'
FAIL = '❌'
WARN = '⚠️'


def _find_contract(outdir):
    """定位 project-contract-*.md（work/ 子目录或顶层）。
    目录不存在/不可读时安全返回 None——门禁自身的健壮性优先于检查结论：
    缺 work/ 是被检项目的流程问题（应由对应 G 项报告 fail），绝不允许让
    os.listdir 抛 FileNotFoundError 使整个脚本崩溃而拿不到完整失败清单。"""
    for base in (os.path.join(outdir, 'work'), outdir):
        if not os.path.isdir(base):
            continue
        try:
            names = os.listdir(base)
        except OSError:
            continue
        for f in names:
            if f.startswith('project-contract-') and f.endswith('.md'):
                return os.path.join(base, f)
    return None


def _guarded(run_fn):
    """单项检查异常护栏：任何检查内部抛错都降级为该 G 项 fail 并继续跑其余项，
    保证输出完整可恢复的失败清单（禁止半路崩溃）。"""
    try:
        return run_fn()
    except Exception as e:
        return False, f'检查自身异常: {type(e).__name__}: {str(e)[:120]}（门禁不应崩溃，按未通过处理并重跑）'

# 蓝图 7 节必需标题
BLUEMAP_SECTIONS = [
    '产品定位',
    '信息架构',
    '核心用户流程',
    '关键状态机',
    '边界态清单',
    '不做清单',
    '易错交互预判',
]

# M79 登录页特征（出现任一 = 有登录页/登录态函数）
LOGIN_PATTERNS = [
    r'id="page-login"',
    r'function\s+wechatLogin\s*\(',
    r'function\s+merchantLogin\s*\(',
    r'function\s+merchantLogout\s*\(',
    r'class="[^"]*\blogin-form\b',
]


def check_bluemap(outdir):
    """G1: 蓝图已产出 + 契约先行（蓝图须晚于契约，防自由发挥超前规划）"""
    path = os.path.join(outdir, 'work', 'pm-bluemap.md')
    if not os.path.exists(path):
        return False, f'缺少 work/pm-bluemap.md（步骤②b 蓝图未产出，禁止生成）'
    if os.path.getsize(path) == 0:
        return False, f'work/pm-bluemap.md 为空文件（蓝图未填写）'
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    missing = [s for s in BLUEMAP_SECTIONS if s not in content]
    if missing:
        return False, f'蓝图缺少必需章节: {", ".join(missing)}（模板 7 节须齐全）'
    # 不做清单非空 + 易错预判 ≥3（蓝图自检最低要求）
    if not re.search(r'\[ \]', content):
        return False, '蓝图「不做清单」为空（未登记排除项，防范围膨胀）'
    issues = len(re.findall(r'^\| \d+ \|', content, re.M))
    if issues < 3:
        return False, f'蓝图「易错交互预判」疑似不足（表格行 <3，模板要求 ≥3）'
    # 契约先行校验（茶叶商城教训）：多端项目蓝图产出时间不得早于契约
    # 蓝图早于契约 = 主 Agent 未以契约为范围约束就自由发挥（茶叶商城：蓝图规划秒杀/券
    # 而契约无此功能，导致蓝图与实际产物失配）
    contract = _find_contract(outdir)
    if contract:
        blue_mtime = os.path.getmtime(path)
        ct_mtime = os.path.getmtime(contract)
        if blue_mtime < ct_mtime:
            return False, f'蓝图产出早于契约（{os.path.basename(contract)}）——违反「契约先行」，蓝图必须基于已确认契约的功能范围产出，禁止超前自由发挥（茶叶商城教训）'
    return True, f'work/pm-bluemap.md（7 节齐全，蓝图已产出）'


def check_ui_review(outdir):
    """G2: UI 走查已执行

    v5.41 收紧：旧版只查"有 PNG + 报告含通过字样"，无法证明全部页面被真实走查
    （截图失败仍会产出同名 PNG 素材、子页失败仅警告）。现以 ui-snapshot.py 产出的
    _snapshots/manifest.json 为完整性依据：
      - manifest 缺失/无记录 → fail（走查流程根本没跑或跑的是旧版工具）
      - 任一文件 mode != 'browser' → fail（DOM 降级 ≠ 真实截图走查）
      - 任一 tab/sub/page 失败明细 → fail（附明细）
      - captured 数量少于 expected → fail
    """
    idx = os.path.join(outdir, '_snapshots', 'index.html')
    if not os.path.exists(idx):
        return False, f'缺少 _snapshots/index.html（未运行 ui-snapshot.py 截图，UI 走查未执行）'
    ui_dir = os.path.join(outdir, '_snapshots', 'ui')
    if not os.path.isdir(ui_dir):
        return False, f'缺少 _snapshots/ui/ 目录（截图未生成）'
    pngs = [f for f in os.listdir(ui_dir) if f.endswith('.png')]
    if not pngs:
        return False, f'_snapshots/ui/ 无截图（走查素材为空）'
    report = os.path.join(outdir, 'work', 'ui-review.md')
    if not os.path.exists(report):
        return False, f'缺少 work/ui-review.md（UI 走查报告未产出，禁止只截图不走查）'
    with open(report, 'r', encoding='utf-8') as f:
        rc = f.read()
    if '✅' not in rc or not re.search(r'通过|修复', rc):
        return False, f'work/ui-review.md 无通过/修复标记（走查报告未完成）'
    # v5.41：走查完整性以 manifest.json 为准
    mpath = os.path.join(outdir, '_snapshots', 'manifest.json')
    if not os.path.exists(mpath):
        return False, '缺少 _snapshots/manifest.json（v5.41 起走查完整性以此清单为准；请重新运行 scripts/ui-snapshot.py 生成）'
    try:
        with open(mpath, 'r', encoding='utf-8') as f:
            mf = json.load(f)
    except Exception as e:
        return False, f'manifest.json 解析失败: {str(e)[:80]}（请重新运行 ui-snapshot.py）'
    entries = mf.get('files') or {}
    if not entries:
        return False, 'manifest.json 无任何走查记录（未对产物采集截图），请重新运行 ui-snapshot.py'
    problems = []
    for abspath, entry in entries.items():
        name = entry.get('file') or os.path.basename(abspath)
        mode = entry.get('mode')
        if mode != 'browser':
            problems.append(f'{name}: 走查模式为 {mode}（非真实浏览器截图，需在装好 Playwright/Chromium 的环境重跑）')
            continue
        bads = list(entry.get('tab_failures') or []) + list(entry.get('sub_failures') or []) \
               + list(entry.get('page_failures') or [])
        exp_t, cap_t = len(entry.get('expected_tabs') or []), int(entry.get('captured_tabs') or 0)
        exp_s, cap_s = len(entry.get('expected_subs') or []), int(entry.get('captured_subs') or 0)
        if bads:
            problems.append(f'{name}: {len(bads)} 个页面未成功走查: {"; ".join(bads[:3])}')
        elif cap_t < exp_t or cap_s < exp_s:
            problems.append(f'{name}: 截图覆盖不足（Tab {cap_t}/{exp_t}，子页 {cap_s}/{exp_s}）')
    if problems:
        return False, 'UI 走查不完整: ' + ' | '.join(problems[:4]) + '（修复产物问题后重新运行 ui-snapshot.py，直至所有页面截图成功）'
    return True, f'UI 走查已执行且完整（图集 + {len(pngs)} 张截图 + manifest 各页全部成功 + 走查报告）'


def check_mobile_login(mobile_file):
    """G3: 无默认登录页（M79）"""
    if not mobile_file:
        return True, '未指定移动端产物，跳过 M79 检查'
    if not os.path.exists(mobile_file):
        return False, f'移动端产物不存在: {mobile_file}'
    with open(mobile_file, 'r', encoding='utf-8') as f:
        content = f.read()
    hits = []
    for pat in LOGIN_PATTERNS:
        for m in re.finditer(pat, content):
            hits.append(m.group(0)[:40])
    if hits:
        return False, f'检测到登录页/登录态函数（M79 铁律）: {"; ".join(hits[:3])}'
    return True, '无默认登录页（M79 合规）'


# 契约交付物类型 → PRD 产物识别
PRD_DELIVERABLE_TYPES = ('PRD', '需求文档', 'prd', '需求')


def check_prd_deliverable(outdir):
    """G4: PRD 必交付物（M106 防护）— 需求文档 100% 生成

    根因（实战：闪修侠项目 3 端原型都做了，PRD 子 Agent 后台任务会话切换丢失，
    work/prd/ 为空，需求文档未产出却照常交付）：
    deliverables-check 依赖主 Agent 手动运行，靠自觉 → 漏跑就漏交付。
    本检查把"PRD 是否生成"升级为机器强制：
    ① 契约（project-contract-*.md）第十一章交付物清单含 PRD/需求文档类型 → 对应产物必须存在
    ② work/prd/ 注入四件套：详细版必须 nav.html/sections.html/section-index.js/knowledge-base.js
       全部存在非空；简易版至少 nav.html/sections.html（详细版/简易版任一存在即通过注入检查）
    ③ 产物根目录存在 `*-需求文档.html` 或 `*-需求.html`（与契约交付物文件名匹配）
    """
    # ① 契约 PRD 交付物核对（契约在 work/ 子目录或顶层，_find_contract 对缺失目录安全返回 None）
    contract = _find_contract(outdir)
    if contract:
        with open(contract, 'r', encoding='utf-8') as f:
            cc = f.read()
        # 提取交付物清单中的需求文档项（只取"交付物清单"章节表格内的行）
        needs_prd = False
        prd_names = []
        in_deliverable_section = False
        for line in cc.split('\n'):
            if re.match(r'^#+.*交付物清单', line):
                in_deliverable_section = True
                continue
            if in_deliverable_section and re.match(r'^#+', line):
                break  # 离开交付物清单章节
            if not in_deliverable_section:
                continue
            if not line.startswith('|'):
                continue  # 只处理表格行，排除引用块/注释（避免把"注入文件铁律"当交付物）
            if 'PRD' in line or '需求文档' in line or '需求' in line:
                needs_prd = True
                # 匹配该行中的 HTML 文件名
                m = re.search(r'([\w\-]+\.html)', line)
                if m:
                    prd_names.append(m.group(1))
        if needs_prd:
            missing_names = [n for n in prd_names if not os.path.exists(os.path.join(outdir, n))]
            if missing_names:
                return False, f'契约交付物清单含需求文档，但产物缺失: {", ".join(missing_names)}（PRD 未生成，禁止交付）'
    else:
        return True, '未找到 project-contract-*.md（契约缺失，跳过 PRD 交付物核对）'

    # ② work/prd/ 注入四件套
    prd_dir = os.path.join(outdir, 'work', 'prd')
    if not os.path.isdir(prd_dir):
        return False, f'缺少 work/prd/ 目录（PRD 注入内容未产出）'
    detailed_files = ['nav.html', 'sections.html', 'section-index.js', 'knowledge-base.js']
    simple_files = ['nav.html', 'sections.html']
    prd_files = os.listdir(prd_dir)
    # 详细版四件套或简易版两件套，任一齐全即通过
    has_detailed = all(f in prd_files and os.path.getsize(os.path.join(prd_dir, f)) > 0 for f in detailed_files)
    has_simple = all(f in prd_files and os.path.getsize(os.path.join(prd_dir, f)) > 0 for f in simple_files)
    if not has_detailed and not has_simple:
        missing_d = [f for f in detailed_files if f not in prd_files or os.path.getsize(os.path.join(prd_dir, f)) == 0]
        return False, f'work/prd/ 注入文件不齐全（详细版需 {"/".join(detailed_files)}，简易版至少 {"/".join(simple_files)}）；当前缺: {", ".join(missing_d)}'
    return True, f'PRD 已生成（契约核对通过 + work/prd/ 注入齐全）'


def check_browser_verified(target_file, label='移动端'):
    """G5: 浏览器断言已执行（交付前强制复核，堵 --no-verify 漏洞）

    根因（茶叶商城事故）：生成时用 --no-verify 跳过浏览器断言，B6 死按钮
    （work-stat/todo-item/mine-menu-item 无 onclick）漏网交付，ui-review 却声称
    "全部通过"——deliverables-check/原 gate-check 只查"文件存在"不查"断言真跑过"。
    v5.31 扩展：支持 --mobile-file 与 --desktop-file 双端复核。茶叶商城教训——
    桌面端（平台管理端/商家端）详情误用 openDrawer 抽屉（D44）、死按钮漏网，
    G5 原来只查移动端，桌面端浏览器断言无人强制，故扩为两端都复核。
    本检查交付前对目标产物实跑 browser-check.py（B1-B19），任一失败 = 禁止交付。
    """
    if not target_file:
        return True, f'未指定{label}产物，跳过浏览器断言复核（多端项目建议传 --mobile-file / --desktop-file）'
    if not os.path.exists(target_file):
        return False, f'{label}产物不存在: {target_file}'
    browser_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'browser-check.py')
    if not os.path.exists(browser_script):
        return False, 'browser-check.py 不存在（浏览器断言复核无法执行，禁止交付）'
    try:
        # v5.41：--strict-runtime —— G5 复核必须真跑；Playwright/Chromium 缺失时
        # browser-check 退码 3（不再静默退 0 冒充通过），本检查据此判 fail 并给安装指引
        r = subprocess.run([sys.executable, '-u', browser_script, target_file, '--strict-runtime'],
                           capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=180)
    except Exception as e:
        return False, f'浏览器断言复核执行异常: {str(e)[:120]}'
    if r.returncode == 3:
        out = (r.stdout + r.stderr).strip()
        tail = out[-200:] if out else ''
        return False, (f'浏览器验证环境不可用（Playwright/Chromium 缺失），G5 无法确认断言已执行——'
                       f'禁止以"环境缺失"冒充通过。请先运行 python scripts/check-env.py 自动安装后重试。{tail}')
    if r.returncode != 0:
        out = (r.stdout + r.stderr).strip()
        failed_lines = [l.strip() for l in out.splitlines() if '✗' in l or '❌' in l or '失败' in l]
        summary = '; '.join(failed_lines[:3]) if failed_lines else out[-200:]
        return False, f'{label}浏览器断言复核失败（生成时可能用了 --no-verify 跳过断言，交付前必须修复）: {summary}'
    return True, f'{label}浏览器断言复核通过（B1-B19 全过，无死按钮/抽屉塞详情）'


def main():
    parser = argparse.ArgumentParser(description='PM Agent 流程产物机器强制门禁')
    parser.add_argument('--outdir', required=True, help='交付目录（含 work/ 与 _snapshots/）')
    parser.add_argument('--mobile-file', help='移动端产物 HTML 路径（M79 登录页检查）')
    parser.add_argument('--desktop-file', help='桌面端产物 HTML 路径（G5 桌面端浏览器断言复核，v5.31）')
    args = parser.parse_args()

    outdir = os.path.abspath(args.outdir)
    if not os.path.isdir(outdir):
        print(f'{FAIL} 交付目录不存在: {outdir}')
        sys.exit(1)

    print('🔒 流程产物机器强制门禁 (gate-check.py)')
    print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
    fails = []

    # G1 蓝图（_guarded：单项异常降级为该 G 项 fail，继续跑完整清单，禁止半路崩溃）
    ok, msg = _guarded(lambda: check_bluemap(outdir))
    print(f"  {OK if ok else FAIL} [G1] 蓝图已产出：{msg}")
    if not ok:
        fails.append(f'G1 {msg}')

    # G2 UI 走查
    ok, msg = _guarded(lambda: check_ui_review(outdir))
    print(f"  {OK if ok else FAIL} [G2] UI 走查已执行：{msg}")
    if not ok:
        fails.append(f'G2 {msg}')

    # G3 M79
    ok, msg = _guarded(lambda: check_mobile_login(args.mobile_file))
    print(f"  {OK if ok else FAIL} [G3] 无默认登录页：{msg}")
    if not ok:
        fails.append(f'G3 {msg}')

    # G4 PRD 必交付物（M106：需求文档 100% 生成）
    ok, msg = _guarded(lambda: check_prd_deliverable(outdir))
    print(f"  {OK if ok else FAIL} [G4] PRD 必交付物：{msg}")
    if not ok:
        fails.append(f'G4 {msg}')

    # G5 浏览器断言复核（v5.29：交付前强制跑 browser-check，堵 --no-verify 漏洞；
    # v5.31：扩展 --desktop-file，桌面端也强制复核，堵 D44 抽屉塞详情漏网）
    ok, msg = _guarded(lambda: check_browser_verified(args.mobile_file, '移动端'))
    print(f"  {OK if ok else FAIL} [G5] 浏览器断言复核(移动端)：{msg}")
    if not ok:
        fails.append(f'G5 {msg}')
    ok, msg = _guarded(lambda: check_browser_verified(args.desktop_file, '桌面端'))
    print(f"  {OK if ok else FAIL} [G5] 浏览器断言复核(桌面端)：{msg}")
    if not ok:
        fails.append(f'G5 {msg}')

    print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
    if fails:
        print(f'{FAIL} 流程产物未完成 {len(fails)} 项，禁止交付:')
        for f in fails:
            print(f'  - {f}')
        print('\n   处理：按提示补齐（产出蓝图 / 执行 UI 走查并写报告 / 移除登录页 / 生成 PRD 需求文档 / 修复浏览器断言失败项）后重新运行本脚本，全部通过才可交付。')
        sys.exit(1)
    print('🎉 流程产物全部就绪（蓝图/UI 走查/M79/PRD 必交付物/浏览器断言复核），可以交付')
    sys.exit(0)


if __name__ == '__main__':
    main()
