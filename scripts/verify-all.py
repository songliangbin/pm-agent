#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
verify-all.py — PM Agent 一键交付门禁（2026-08-09 建立；2026-08-13 重构去掉 demo 依赖）

不再依赖 demo 文件（demo 已随历史清理删除，且与"真实项目实例"职能重叠）。
质量不降反升：用「副本一致性 + 模板双副本 lint + 模板浏览器断言 + build 冒烟构建」四道门禁
覆盖原 demo 的全部验证目标（模板可构建 + 模板可运行 + 副本不同步）。

用法:
    python scripts/verify-all.py          # 默认：副本一致 + 模板 lint + 浏览器断言 + 冒烟构建
    python scripts/verify-all.py --prd    # 额外验证 PRD 详细版+简易版
    python scripts/verify-all.py --legacy # 额外验证 V1/移动端历史遗留模板
"""
import os
import re
import sys
import json
import shutil
import tempfile
import subprocess

# 非 UTF-8 终端（Windows GBK/cp936）打印 ✅❌ 等 emoji 会抛 UnicodeEncodeError，强制 UTF-8 输出
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable
LINT = os.path.join(BASE, 'standards', 'agent-lint.py')
BROWSER = os.path.join(BASE, 'scripts', 'browser-check.py')
BUILD = os.path.join(BASE, 'scripts', 'build-prototype.py')
SPLIT = os.path.join(BASE, 'scripts', 'split-pitfalls.py')

# 技能副本根：默认等于自身 BASE（纯单副本安装，即分发给他人放在任意 skills 文件夹下的标准形态），
# 此时一致性门禁自动跳过，绝不因"检测到其它目录"而误报红灯。
# 仅在作者本地「双副本开发流」下，才用环境变量 PM_AGENT_SKILL_DIR 显式指向另一份副本以启用一致性门禁。
SKILL_ROOT = os.environ.get('PM_AGENT_SKILL_DIR', BASE)

def _core_templates():
    """核心模板清单（去重）。单副本下只列 BASE；双副本下追加另一副本的同名模板。"""
    paths = [
        os.path.join(BASE, 'templates', 'prototype-desktop-v3.html'),
        os.path.join(BASE, 'templates', 'prototype-desktop-v2.html'),
        os.path.join(BASE, 'templates', 'prototype-mobile.html'),
    ]
    if os.path.abspath(SKILL_ROOT) != os.path.abspath(BASE):
        for name in ('prototype-desktop-v3.html', 'prototype-desktop-v2.html', 'prototype-mobile.html'):
            p = os.path.join(SKILL_ROOT, 'templates', name)
            if p not in paths:
                paths.append(p)
    return paths

# 当前维护核心：V2/V3/Mobile 模板（单副本直接校验；双副本开发流额外校验另一副本）
CORE_TEMPLATE_FILES = _core_templates()
# 历史遗留模板（旧范式 V1 桌面端，存在已知 C1-8 骨架缺失，--legacy 纳入）
# 注：移动端已于 2026-08-13 修复 M63 div 噪音 + DATA 标记位置，升级为核心模板
LEGACY_FILES = [
    os.path.join(BASE, 'templates', 'prototype-desktop.html'),
]
# PRD 文件（--prd 时加入）
PRD_FILES = [
    (os.path.join(BASE, 'templates', 'prd-template.html'), 'detailed'),
    (os.path.join(BASE, 'templates', 'prd-template-simple.html'), 'simple'),
]


def run_lint(paths, prd_mode=None):
    """跑 lint，返回 (文件数, 失败数)。paths 可为纯路径列表或 (path, mode) 元组列表"""
    if not paths:
        return 0, 0
    files = [p if isinstance(p, str) else p[0] for p in paths]
    missing = [f for f in files if not os.path.exists(f)]
    if missing:
        for f in missing:
            print(f'❌ 文件不存在: {f}')
        return len(paths), len(missing)
    cmd = [PY, LINT] + files
    if prd_mode:
        cmd += ['--prd-mode', prd_mode]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    out = r.stdout + r.stderr
    failed = 0
    for l in out.splitlines():
        m = __import__('re').search(r'❌ (\d+) 项失败', l)
        if m:
            failed += int(m.group(1))
    print(out[-1200:])
    return len(paths), failed


def check_skill_sync():
    """校验技能副本与项目是否一致。返回失败数（0 或 1）。

    单副本安装（SKILL_ROOT == BASE，即分发给他人后放在任意 skills 文件夹下的标准形态）
    无需同步，直接跳过并返回 0；只有作者本地「双副本开发流」才真正执行 --check。
    """
    if os.path.abspath(SKILL_ROOT) == os.path.abspath(BASE):
        print('\n[0/3] 技能副本一致性检查：单副本安装（即分发形态），无需同步，跳过')
        return 0
    print('\n[0/3] 技能副本一致性检查（sync-templates.py --check）')
    sync = os.path.join(BASE, 'scripts', 'sync-templates.py')
    if not os.path.exists(sync):
        # 2026-08-17 修复：sync 脚本自身未随副本同步时，勿误导为"副本不一致"，
        # 应明确提示门禁依赖缺失，并从项目副本运行一次同步补齐。
        print('⚠️ 技能副本缺少 sync-templates.py（verify-all 的门禁依赖）。')
        print('   该脚本负责把项目副本同步到技能副本，请从项目副本运行一次同步补齐：')
        print('   cd <项目副本> && python scripts/sync-templates.py')
        return 1
    try:
        r = subprocess.run([PY, sync, '--check'], capture_output=True, text=True, encoding='utf-8', errors='replace')
    except Exception as e:
        print(f'⚠️ 运行 sync-templates.py 失败：{e}')
        return 1
    out = (r.stdout + r.stderr).strip()
    print(out[-800:] if out else '(无输出)')
    if r.returncode != 0:
        print('❌ 技能副本与项目不一致——副本不同步会让交付门禁/生成结果分叉，须先运行 scripts/sync-templates.py')
        return 1
    return 0


def check_doc_consistency():
    """[doc] 文档一致性核验：history-pitfalls.md 实际条数 vs SKILL.md 步骤①声明。
    防"踩坑计数漂移"（此前按编号尾号累加，D 系列编号不连续致总数错 3 项）。
    计数不一致即红灯，禁止交付；修改须以 history-pitfalls.md 实际行数为准。"""
    print('\n[doc] 文档一致性核验（踩坑库实际条数 vs SKILL.md 声明）')
    try:
        with open(os.path.join(BASE, 'history-pitfalls.md'), 'r', encoding='utf-8') as f:
            hp = f.read()
        with open(os.path.join(BASE, 'SKILL.md'), 'r', encoding='utf-8') as f:
            sk = f.read()
    except Exception as e:
        print(f'❌ 读取文档失败: {e}')
        return 1
    m = len(re.findall(r'^\| M\d+ \|', hp, re.M))
    p = len(re.findall(r'^\| P\d+ \|', hp, re.M))
    d = len(re.findall(r'^\| D\d+(-[0-9]+)? \|', hp, re.M))
    # 与 split-pitfalls 分节语义对齐：移动端分节内的 [移动端] 标签 D 行（如 D46）计入移动端，
    # 不计入桌面端。复用 split-pitfalls.build_subsets 的 detail 计数（唯一真相源，防双标）。
    try:
        import importlib.util
        _spec = importlib.util.spec_from_file_location(
            'split_pitfalls', os.path.join(BASE, 'scripts', 'split-pitfalls.py'))
        _sp = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_sp)
        _, _detail = _sp.build_subsets(hp)
        m, p, d = _detail['M'], _detail['P'], _detail['D_total']
    except Exception as _e:
        print(f'  (split-pitfalls 计数复用失败，回退前缀统计: {_e})')
    decl = re.search(r'踩坑库[^，\n]*?(\d+) 项：(\d+) 移动端 \+ (\d+) PRD \+ (\d+) 桌面端', sk)
    if not decl:
        print('❌ SKILL.md 未找到踩坑库声明（格式：踩坑库…N 项：A 移动端 + B PRD + C 桌面端）')
        return 1
    decl_total, decl_m, decl_p, decl_d = map(int, decl.groups())
    actual_total = m + p + d
    errors = []
    if m != decl_m:
        errors.append(f'移动端声明 {decl_m}≠实际 {m}')
    if p != decl_p:
        errors.append(f'PRD 声明 {decl_p}≠实际 {p}')
    if d != decl_d:
        errors.append(f'桌面端声明 {decl_d}≠实际 {d}')
    if actual_total != decl_total:
        errors.append(f'总数声明 {decl_total}≠实际 {actual_total}')
    if errors:
        print(f'❌ 踩坑库计数不一致: {"; ".join(errors)}')
        print('   → 修改 SKILL.md 步骤①声明与 history-pitfalls.md 实际条数对齐（禁止按编号尾号累加）')
        return 1
    print(f'✅ 踩坑库计数一致（{m} 移动端 + {p} PRD + {d} 桌面端 = {actual_total} 项）')
    return 0


def check_pitfall_split():
    """[doc] 踩坑库拆分一致性：4 个子集文件（mobile/prd/desktop/common）必须与
    history-pitfalls.md 源同步派生。防止"改源头漏子集"（D44 拆分后新增门禁）。
    调用 split-pitfalls.py --check 重生成比对。"""
    print('\n[doc] 踩坑库子集一致性核验（history-pitfalls 派生文件 vs 源）')
    if not os.path.exists(SPLIT):
        print('❌ scripts/split-pitfalls.py 不存在')
        return 1
    r = subprocess.run([PY, SPLIT, '--check'], capture_output=True, text=True, encoding='utf-8', errors='replace')
    out = (r.stdout + r.stderr).strip()
    print(out)
    return 0 if r.returncode == 0 else 1


def browser_check_templates():
    """对 V2/V3 项目模板跑真实浏览器断言（Playwright，B1-B3++++）。返回失败数。"""
    print('\n[2/3] 模板浏览器断言（browser-check.py，验证模板可运行）')
    files = [
        os.path.join(BASE, 'templates', 'prototype-desktop-v2.html'),
        os.path.join(BASE, 'templates', 'prototype-desktop-v3.html'),
    ]
    if not os.path.exists(BROWSER):
        print('❌ browser-check.py 不存在')
        return 1
    # -u 无缓冲：browser-check 结尾用 os._exit 立即终止（Windows chromium 关闭崩溃 D27），
    # 无缓冲可确保 print 内容在 os._exit 前已写入 pipe，subprocess 才能捕获输出。
    r = subprocess.run([PY, '-u', BROWSER] + files, capture_output=True, text=True, encoding='utf-8', errors='replace')
    out = r.stdout + r.stderr
    print(out[-1800:])
    return 0 if r.returncode == 0 else 1


def smoke_build():
    """冒烟构建：对 V2/V3/Mobile 模板各跑一次最小 build（--no-verify），
    验证构建链路（TEMPLATE_MAP/标记齐全/主色与占位符替换/标记清理）不崩；
    移动端额外对构建产物跑 browser-check（验证模板可构建 + 产物可运行 + 离线内嵌可用）。"""
    print('\n[3/3] build 冒烟构建（验证模板可正确构建 + 移动端产物可运行）')
    failed = 0
    for ttype, tname in [('desktop-v2', 'prototype-desktop-v2.html'), ('desktop-v3', 'prototype-desktop-v3.html'), ('mobile', 'prototype-mobile.html')]:
        print(f'\n--- 冒烟构建: {tname} ---')
        tmpdir = tempfile.mkdtemp(prefix='pm_smoke_')
        cfg = os.path.join(tmpdir, 'config.json')
        out = os.path.join(tmpdir, 'out.html')
        colors = {"--accent": "#00B96B", "--accent-hover": "#00A85F", "--accent-rgb": "0,185,107",
                  "--accent-bg": "#E6F7EF", "--accent-border": "#B7E4C7",
                  "--brand": "#00B96B", "--brand-light": "#34D399", "--brand-rgb": "0,185,107", "--brand-bg": "#E6F7EF"}
        config = {"project": "冒烟测试", "colors": colors}
        # V3 桌面端注入最小业务文件：不注入则模板默认示例页（page-list 等）残留、
        # 而示例 JS 被 build 清空（EXAMPLES_START 标记 v5.31 已修正到示例函数之前）→
        # 冒烟产物"有按钮无函数/有 tbody 无渲染"，与真实项目不符（D44 修复暴露）。
        # 注：V2 模板无 EXAMPLES 标记（示例 JS 保留且依赖模板示例页），不注入保持自洽。
        if ttype == 'desktop-v3':
            nav = os.path.join(tmpdir, 'nav.html')
            main = os.path.join(tmpdir, 'pages.html')
            data = os.path.join(tmpdir, 'data.js')
            with open(nav, 'w', encoding='utf-8') as f:
                f.write('<div class="nav-item active" data-page="dashboard" onclick="switchPage(\'dashboard\')"><i class="fa-solid fa-gauge-high"></i><span class="label">工作台</span></div>')
            with open(main, 'w', encoding='utf-8') as f:
                f.write('<div class="page active" id="page-dashboard"><div class="page-header"><div><h2>工作台</h2><p class="page-desc">冒烟测试</p></div></div><div class="grid-4 mb" id="dashStats"></div></div>')
            with open(data, 'w', encoding='utf-8') as f:
                f.write('const demoData = { stats: [], todos: [], orders: [], activities: [], members: [], roles: [], menus: [], dicts: [], logs: [], depts: [], groups: [] };')
            config['nav'] = nav
            config['pages'] = main
            config['data'] = data
        if ttype == 'mobile':
            # 移动端需最小注入文件，否则 {{导航项}}/{{页面内容}} 占位符残留
            nav = os.path.join(tmpdir, 'nav.html')
            main = os.path.join(tmpdir, 'main.html')
            sub = os.path.join(tmpdir, 'sub.html')
            data = os.path.join(tmpdir, 'data.js')
            with open(nav, 'w', encoding='utf-8') as f:
                f.write('<div class="nav-tab active" data-tab="home" onclick="switchTab(\'home\')"><div class="nav-tab-icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M3 12l9-9 9 9"/></svg></div><span class="nav-tab-label">首页</span></div>')
            with open(main, 'w', encoding='utf-8') as f:
                f.write('<div class="page active" id="page-home"><div class="page-content"><div class="home-section-title">冒烟测试</div></div></div>')
            with open(sub, 'w', encoding='utf-8') as f:
                f.write('<div class="sub-page" id="sub-smoke"><div class="sub-page-header"><div class="sub-page-nav"><div class="sub-page-back" onclick="closeSubPage(\'sub-smoke\')"><svg viewBox="0 0 24 24"><polyline points="15 18 9 12 15 6"/></svg></div><span class="sub-page-title">详情</span></div></div><div class="sub-page-body">冒烟测试子页</div></div>')
            with open(data, 'w', encoding='utf-8') as f:
                f.write('const smokeData = [];')
            config['nav'] = nav
            config['mainPage'] = main
            config['pages'] = sub
            config['data'] = data
        with open(cfg, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False)
        # v5.41：mobile 冒烟不再 --skip-embed —— 走真实交付路径（自动离线内嵌），
        # 与 B-OFFLINE 断言闭环（--skip-embed 产物会被 browser-check 如实打回）。
        # V2/V3 冒烟仅做构建级验证，保留 skip-embed 加速。
        build_cmd = [PY, BUILD, '--template', ttype, '--config', cfg, '--out', out, '--no-verify']
        if ttype != 'mobile':
            build_cmd.append('--skip-embed')
        r = subprocess.run(build_cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
        ok = r.returncode == 0 and os.path.exists(out)
        residue = ''
        if ok:
            content = open(out, encoding='utf-8').read()
            if 'Agent:XXX' in content or 'Agent:PAGE_START' in content or 'Agent:DATA_START' in content or 'Agent:NAV_START' in content:
                residue = '模板注入标记残留'
            if '{{' in content:
                residue = (residue + ' 占位符残留').strip()
        if ok and not residue:
            print('  ✅ 构建成功，标记/占位符已清理')
        else:
            failed += 1
            print(f'  ❌ 构建失败或{residue}')
            print((r.stdout + r.stderr)[-600:])
        # 移动端：对构建产物跑真实浏览器断言（验证模板可运行）
        if ok and not residue and ttype == 'mobile':
            br = subprocess.run([PY, '-u', BROWSER, out], capture_output=True, text=True, encoding='utf-8', errors='replace')
            if br.returncode != 0:
                failed += 1
                print('  ❌ 移动端构建产物 browser-check 失败:')
                print((br.stdout + br.stderr)[-600:])
            else:
                print('  ✅ 移动端构建产物 browser-check 通过')
        shutil.rmtree(tmpdir, ignore_errors=True)
    return failed


# ---- v5.41：系统管理内置模块齐备门禁 + PRD 双模式冒烟 ----

SYSADMIN_PAGES = ['page-org', 'page-roles', 'page-menus', 'page-dicts', 'page-logs']
SYSADMIN_FUNCS = ['renderOrgTree', 'saveMember', 'saveRole', 'renderMenus', 'openMenuAdd',
                  'saveMenu', 'filterDicts', 'saveDict', 'filterLogs', 'deleteMenu', 'toggleMenuExpand']


def check_sysadmin_builtin():
    """[component] 系统管理黄金模块齐备门禁（v5.41）：
    系统管理 5 页面 / JS 函数库同时维护于 V2/V3 模板永久区与 components/system-admin.html，
    历史发生过「修一份漏一份」的分叉（MEMORY §0 同步教训）。本门禁按 agent-lint M51
    白名单对 V2/V3 模板硬断言——任一缺失即内置副本漂移，fail。
    components/system-admin.html 为拼接片段（非独立交付物，agent-lint 已豁免其独立完整性），
    不纳入本硬校验。"""
    print('\n[1.8] 系统管理内置模块齐备（V2/V3 × M51 白名单）')
    failed = 0
    for rel in ('prototype-desktop-v2.html', 'prototype-desktop-v3.html'):
        path = os.path.join(BASE, 'templates', rel)
        try:
            t = open(path, encoding='utf-8').read()
        except Exception as e:
            print(f'  ❌ {rel} 读取失败: {e}')
            failed += 1
            continue
        miss_p = [p for p in SYSADMIN_PAGES if p not in t]
        miss_f = [f for f in SYSADMIN_FUNCS if f not in t]
        if miss_p or miss_f:
            failed += 1
            print(f'  ❌ {rel}: 缺页面={miss_p or "无"} 缺函数={miss_f or "无"}（内置副本漂移，M51 白名单）')
        else:
            print(f'  ✅ {rel}: 系统 5 页 + 11 核心函数齐全')
    return failed


_PRD_NAV = '<div class="nav-item active" data-section="home" onclick="showSection(\'home\')">系统首页</div>'
_PRD_INFO_TABLE = ('<table><tr><th>文档名称</th><td>冒烟PRD</td></tr>'
                   '<tr><th>文档版本</th><td>1.0</td></tr><tr><th>文档状态</th><td>评审中</td></tr>'
                   '<tr><th>编写人</th><td>PM Agent</td></tr><tr><th>创建日期</th><td>2026-08-27</td></tr></table>')


def _prd_sec(i, t, cls='prd-section'):
    return f'<section id="{i}" class="{cls}">{t}</section>'


def _prd_sections(mode):
    if mode == 'detailed':
        items = [('home', '决策层 · 系统首页' + _PRD_INFO_TABLE, 'tab-content active'),
                 ('overview', '决策层 · 项目概述', None), ('user-research', '决策层 · 用户研究', None),
                 ('business-goals', '决策层 · 业务目标', None), ('feature-plan', '决策层 · 功能规划', None),
                 ('architecture', '方案层 · 系统架构', None), ('solution-comparison', '方案层 · 解决方案对比', None),
                 ('cost-roi', '方案层 · 成本ROI测算', None), ('schedule', '方案层 · 排期', None),
                 ('risk-management', '方案层 · 风险管理', None), ('roles', '实现层 · 角色权限', None),
                 ('biz-modules', '实现层 · 核心业务模块', None), ('feature-design', '实现层 · 功能详细设计', None),
                 ('data-structure', '实现层 · 数据结构', None), ('interface', '实现层 · 接口设计', None),
                 ('test-acceptance', '实现层 · 测试验收', None), ('changelog', '附录 · 变更记录 changelog', None)]
    else:
        items = [('home', '系统首页', 'tab-content active'), ('overview', '项目概述', None),
                 ('feature-plan', '功能规划', None), ('architecture', '系统架构', None),
                 ('roles', '角色权限', None), ('biz-modules', '核心业务模块', None),
                 ('feature-detail', '功能详细设计', None), ('data-structure', '数据结构', None),
                 ('testing', '测试验收', None)]
    return ''.join(_prd_sec(i, t) if c is None else _prd_sec(i, t, c) for i, t, c in items)


def prd_smoke_build():
    """[prd-smoke] PRD 双模式冒烟构建（v5.41）：原先 --prd 仅跑模板 lint，
    不覆盖「注入→拼装→占位符替换→标记剥离」构建链路。现各模式最小合法注入
    build 一次（章节壳/索引/知识库满足 PRD 全量 lint——lint 在 build 内强制，
    这也顺带回归了 PRD 专项检查的判定链路）。"""
    print('\n[prd-smoke] PRD 双模式冒烟构建（验证注入链路可运行）')
    failed = 0
    for mode in ('simple', 'detailed'):
        tmpdir = tempfile.mkdtemp(prefix='pm_prd_smoke_')
        nav = os.path.join(tmpdir, 'nav.html')
        sec = os.path.join(tmpdir, 'sections.html')
        with open(nav, 'w', encoding='utf-8') as f:
            f.write(_PRD_NAV)
        with open(sec, 'w', encoding='utf-8') as f:
            f.write(_prd_sections(mode))
        config = {'project': '冒烟测试', 'template': 'prd',
                  'colors': {'--prd-primary': '#0F766E', '--prd-primary-light': '#14B8A6',
                             '--prd-primary-bg': '#F0FDFA'},
                  'nav': nav, 'sections': sec}
        if mode == 'detailed':
            ids = ['home', 'overview', 'user-research', 'business-goals', 'feature-plan',
                   'architecture', 'solution-comparison', 'cost-roi', 'schedule',
                   'risk-management', 'roles', 'biz-modules', 'feature-design',
                   'data-structure', 'interface', 'test-acceptance', 'changelog']
            si = os.path.join(tmpdir, 'section-index.js')
            with open(si, 'w', encoding='utf-8') as f:
                f.write('var sectionIndex=[' +
                        ','.join("{id:'%s',title:'章节%s',keywords:'k%d'}" % (i, i, n) for n, i in enumerate(ids)) +
                        '];')
            kb = os.path.join(tmpdir, 'knowledge-base.js')
            with open(kb, 'w', encoding='utf-8') as f:
                f.write('var knowledgeBase=[' +
                        ','.join("{q:'问题%d?',a:'答案%d'}" % (i, i) for i in range(1, 13)) + '];')
            config['sectionIndex'] = si
            config['kb'] = kb
        cfgp = os.path.join(tmpdir, 'config.json')
        with open(cfgp, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False)
        out = os.path.join(tmpdir, 'out.html')
        r = subprocess.run([PY, BUILD, '--template', 'prd', '--prd-mode', mode,
                            '--config', cfgp, '--out', out, '--no-verify', '--skip-embed'],
                           capture_output=True, text=True, encoding='utf-8', errors='replace')
        ok = r.returncode == 0 and os.path.exists(out)
        residue = ''
        if ok:
            content = open(out, encoding='utf-8').read()
            import re as _re
            if _re.search(r'Agent:[A-Z_]+_(START|END)', content):
                residue = '标记残留'
            if '{{' in content:
                residue = (residue + ' 占位符残留').strip()
        if ok and not residue:
            print(f'  ✅ [{mode}] 构建成功，标记/占位符已清理')
        else:
            failed += 1
            print(f'  ❌ [{mode}] 构建失败或{residue}')
            print((r.stdout + r.stderr)[-500:])
        shutil.rmtree(tmpdir, ignore_errors=True)
    return failed


def main():
    args = sys.argv[1:]
    do_prd = '--prd' in args
    do_legacy = '--legacy' in args

    print('=' * 60)
    print('PM Agent 交付门禁一键验证')
    print('=' * 60)

    total_failed = 0

    # 0) 技能副本一致性
    total_failed += check_skill_sync()

    # 0.5) 文档一致性核验（踩坑库计数 vs SKILL.md 声明 + 子集派生一致性）
    total_failed += check_doc_consistency()
    total_failed += check_pitfall_split()

    # 1) 模板双副本 lint（V2/V3/Mobile 项目 + 技能）
    print('\n[1/3] 模板双副本 lint（V2/V3/Mobile 项目模板 + 技能副本）')
    _, failed = run_lint(CORE_TEMPLATE_FILES)
    total_failed += failed

    # 1.8) 系统管理内置模块齐备（v5.41：V2/V3 内置副本漂移硬校验）
    total_failed += check_sysadmin_builtin()

    # 2) 模板浏览器断言（Playwright）
    total_failed += browser_check_templates()

    # 3) build 冒烟构建
    total_failed += smoke_build()

    # 1.5) 历史遗留模板（可选）
    if do_legacy:
        print('\n[legacy] 历史遗留模板（V1 桌面端）')
        print('  ℹ 已知容忍项：C1-8 系统管理骨架缺失为 V1 历史遗留既定状态'
              '（MEMORY §0/v5.28 审计结论：不修）；其余任何新增失败都视为真实回归')
        _, failed = run_lint(LEGACY_FILES)
        total_failed += failed

    # PRD（可选）
    if do_prd:
        print('\n[prd] PRD 模板（详细版 + 简易版）')
        for path, mode in PRD_FILES:
            print(f'\n--- {os.path.basename(path)} [{mode}] ---')
            _, failed = run_lint([(path, mode)], prd_mode=mode)
            total_failed += failed
        # v5.41：PRD 双模式冒烟构建（补注入链路验证）
        total_failed += prd_smoke_build()

    print('=' * 60)
    if total_failed == 0:
        print(f'🎉 交付门禁全部通过（副本一致 + 模板 lint + 浏览器断言 + 冒烟构建'
              + (' + PRD' if do_prd else '') + (' + legacy' if do_legacy else '') + '）')
        sys.exit(0)
    else:
        print(f'❌ 交付门禁未通过：{total_failed} 项失败，禁止交付！')
        sys.exit(1)


if __name__ == '__main__':
    main()
