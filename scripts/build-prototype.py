#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build-prototype.py — PM Agent 交付物确定性拼装脚本（支柱 A 核心）

用法：
    python scripts/build-prototype.py --template desktop --config config.json --out 输出.html
    python scripts/build-prototype.py --template mobile  --config config.json --out 输出.html
    python scripts/build-prototype.py --template prd     --config config.json --out 输出.html
    python scripts/build-prototype.py --template prd --prd-mode simple --config config.json --out 简易需求文档.html

config.json 格式（由主 Agent 汇总子 Agent 产出后生成）：
{
    "project": "项目名",
    "template": "desktop | mobile | prd",
    "colors": {                       // 主色变量（替换 COLOR_START/END 区域）
        "--accent": "#FF6B4A",
        "--accent-hover": "#FF5733",
        "--accent-bg": "#FFF4F1",
        "--accent-border": "#FFD4C7",
        "--sidebar-active": "rgba(255,107,74,0.12)"
    },
    "nav": "work/xxx/nav.html",       // 导航 HTML（替换 NAV_START/END）
    "pages": "work/xxx/pages.html",   // 页面 HTML（替换 PAGE_START/END）
    "data": "work/xxx/data.js",       // 数据 JS（替换 DATA_START/END）
    "biz": "work/xxx/biz.js",         // 业务函数 JS（追加到 script 末尾，可选）
    "sectionIndex": "work/xxx/section-index.js",  // PRD 专用：替换 SEARCH_DATA_START/END（可选）
    "kb": "work/xxx/knowledge-base.js"            // PRD 专用：替换 DATA_START/END 中的知识库（可选）
}

行为：
    1. 读取模板 → 替换主色变量 → 清空示例区 → 注入 4 个内容块 → 清理注入标记 → 输出
    2. 自动运行 agent-lint.py（第 1 层验证）
    3. 自动运行 browser-check.py（第 2 层验证，可选 --skip-browser 跳过）

退出码：
    0 = 构建 + 全部验证通过
    1 = 构建失败或验证失败
"""

import re
import os
import sys
import json
import shutil
import subprocess
import argparse

# 非 UTF-8 终端（Windows GBK/cp936）打印 ✅❌ 等 emoji 会抛 UnicodeEncodeError，强制 UTF-8 输出
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding='utf-8')
    except Exception:
        pass

# 技能根目录（脚本位于 scripts/ 下）
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(SKILL_DIR, 'templates')
STANDARDS_DIR = os.path.join(SKILL_DIR, 'standards')
SCRIPTS_DIR = os.path.join(SKILL_DIR, 'scripts')

TEMPLATE_MAP = {
    'desktop': 'prototype-desktop.html',
    'desktop-v2': 'prototype-desktop-v2.html',
    'desktop-v3': 'prototype-desktop-v3.html',
    'mobile': 'prototype-mobile.html',
    'prd': 'prd-template.html',
}

# ============================================================
# 标记工具
# ============================================================

def replace_between(content, start_marker, end_marker, new_content, label):
    """替换 start_marker 与 end_marker 之间的内容（含标记），返回替换结果"""
    s_idx = content.find(start_marker)
    if s_idx == -1:
        raise ValueError(f'[build] 模板缺少标记 {start_marker}（{label}）')
    e_idx = content.find(end_marker, s_idx)
    if e_idx == -1:
        raise ValueError(f'[build] 模板缺少标记 {end_marker}（{label}）')
    e_end = e_idx + len(end_marker)
    # 延伸 END 标记到该行末尾（清除标记行的说明文字，如 "// Agent:DATA_END — 助手数据结束"）
    line_end = content.find('\n', e_end)
    if line_end != -1:
        e_end = line_end
    else:
        e_end = len(content)
    return content[:s_idx] + new_content + content[e_end:]


def replace_color_zone(content, colors):
    """替换主色 CSS 变量值（v4.0 M18 修复：不再依赖 COLOR_START 标记定位，
    因为模板顶部使用指南注释块中的说明文字含 'Agent:COLOR_START' 字样，
    会干扰 find() 定位导致替换失效。改为全文件 '--var:' 定义替换，
    只匹配定义行（var(--xxx) 引用不含冒号，--xxx-hover 有后缀不误伤）。"""
    new_content = content
    for var_name, value in colors.items():
        pattern = re.compile(r'(--' + re.escape(var_name.lstrip('-')) + r'\s*:\s*)[^;]+(;)')
        new_content = pattern.sub(r'\g<1>' + value + r'\g<2>', new_content)
    return new_content




def auto_accent_rgb(content):
    """M42 修复：如果 --accent-rgb 未被替换（仍为默认值 92,108,240），
    从 --accent HEX 值自动计算正确的 RGB 三元组。"""
    import re as _re
    # 读取 --accent 值
    accent_match = _re.search(r'--accent\s*:\s*(#[0-9a-fA-F]{6})', content)
    rgb_match = _re.search(r'--accent-rgb\s*:\s*([0-9,\s]+)', content)
    if not accent_match or not rgb_match:
        return content
    accent_hex = accent_match.group(1)
    current_rgb = rgb_match.group(1).strip()
    # 如果 --accent-rgb 仍是默认值 92,108,240，自动修正
    if current_rgb.replace(' ', '') == '92,108,240':
        r = int(accent_hex[1:3], 16)
        g = int(accent_hex[3:5], 16)
        b = int(accent_hex[5:7], 16)
        correct_rgb = f"{r},{g},{b}"
        content = content.replace(rgb_match.group(0), f'--accent-rgb: {correct_rgb}', 1)
        print(f"  [M42 自动修复] --accent-rgb: 92,108,240 → {correct_rgb}（从 --accent {accent_hex} 计算）")
    return content


def replace_css_vars_direct(content, colors):
    """直接替换 :root 中的 CSS 变量值（移动端模板无 COLOR_START 标记时使用）"""
    new_content = content
    for var_name, value in colors.items():
        pattern = re.compile(r'(--' + re.escape(var_name.lstrip('-')) + r'\s*:\s*)[^;]+(;)')
        new_content = pattern.sub(r'\g<1>' + value + r'\g<2>', new_content)
    return new_content


def strip_injection_markers(content):
    """清理生成文件中的模板注入标记注释（C1-3 要求）"""
    # 清理模板顶部"Agent 使用指南"注释块（╔ 装饰框 或 文本描述两种格式）
    content = re.sub(r'<!--\s*\n╔[^\n]*\n[\s\S]*?╝\s*\n-->', '', content, count=1)
    content = re.sub(r'<!--\s*\n\s*(?:PRD 需求文档模板|.*Agent 使用指南)[\s\S]*?\n\s*-->', '', content, count=1)
    # 清理 Agent:XXX_START/END 注释行（整行或行内）
    content = re.sub(r'[ \t]*<!--\s*Agent:[A-Z_]+\s*START[^\n]*-->[ \t]*\n?', '', content)
    content = re.sub(r'[ \t]*<!--\s*Agent:[A-Z_]+\s*END[^\n]*-->[ \t]*\n?', '', content)
    content = re.sub(r'[ \t]*//\s*Agent:[A-Z_]+\s*START[^\n]*\n?', '', content)
    content = re.sub(r'[ \t]*//\s*Agent:[A-Z_]+\s*END[^\n]*\n?', '', content)
    # 清理行内注释形式
    content = content.replace('<!-- Agent:COLOR_START', '/* 主色变量 */')
    content = re.sub(r'/\*\s*=+\s*Agent:COLOR_START[^\*]*\*/', '/* 主色变量 */', content)
    content = re.sub(r'/\*\s*=+\s*Agent:COLOR_END[^\*]*\*/', '', content)
    # 清理行内 "(Agent: 替换)" 提示（放宽为可带任意尾注，如 "/* (Agent: 替换) 主色 HEX */"）
    content = re.sub(r'/\*\s*\(Agent: 替换\)[^\*]*\*/', '', content)
    # 清理 Agent 收尾提醒
    content = re.sub(r'<!--\s*🔔\s*Agent 收尾提醒[^\n]*-->[ \t]*\n?', '', content)
    content = re.sub(r'<!--\s*Agent 收尾提醒[^\n]*-->[ \t]*\n?', '', content)
    return content


def replace_placeholders(content, config):
    """替换模板文本占位符 {{项目名称}} / {{版本号}} 等（全部替换，不留空值）"""
    import datetime
    today = datetime.date.today().strftime('%Y-%m-%d')
    placeholders = {
        '{{项目名称}}': config.get('project', '项目名称') or '项目名称',
        '{{版本号}}': config.get('version', '1.0') or '1.0',
        '{{管理员姓名}}': config.get('admin', '管理员') or '管理员',
        '{{项目描述}}': config.get('description', '') or '',
        '{{今日日期}}': config.get('date', today) or today,
        '{{端名称}}': config.get('endName', '移动端') or '移动端',
        '{{首页标题}}': config.get('homeTitle', '首页') or '首页',
        '{{更新日期}}': config.get('date', today) or today,
        '{{阶段}}': config.get('stage', '评审中') or '评审中',
    }
    for key, value in placeholders.items():
        content = content.replace(key, value)
    return content


# ============================================================
# 构建流程
# ============================================================

def build(config, prd_mode='detailed'):
    template_name = TEMPLATE_MAP.get(config.get('template', ''))
    if not template_name:
        raise ValueError(f'未知模板类型: {config.get("template")}，可选 desktop/mobile/prd')

    # PRD 简易版：选用独立的简易模板（无智能助手 / 搜索栏）
    if config.get('template') == 'prd' and prd_mode == 'simple':
        template_name = 'prd-template-simple.html'

    template_path = os.path.join(TEMPLATES_DIR, template_name)
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()

    print(f"[build] 模板: {template_name} ({len(content)/1024:.0f}KB)")
    is_mobile = config.get('template') == 'mobile'

    # 1. 替换主色变量（M18 修复：全文件 --var: 定义替换，覆盖三种模板）
    if config.get('colors'):
        content = replace_color_zone(content, config['colors'])
        content = auto_accent_rgb(content)  # M42: 自动修正 --accent-rgb

    # 1a. 移动端专用：--accent 系自动映射为 --brand 系（5.21 根因修复）
    # 历史坑：移动端模板主色用 --brand/--brand-light/--brand-bg/--brand-rgb，
    # 但 config 契约只约定 --accent 系，导致构建后紫绿色分裂。
    # 这里读取 --accent 自动推导整套 --brand 系，并补全 --accent-rgb（移动端登录页/关于页引用）。
    if is_mobile and config.get('colors'):
        import re as _re
        colors = config['colors']
        accent = colors.get('--accent')
        if accent:
            mobile_colors = {}
            mobile_colors['--brand'] = accent
            mobile_colors['--brand-light'] = colors.get('--accent-hover', accent)
            mobile_colors['--brand-bg'] = colors.get('--accent-bg', '#E8F6EF')
            # --brand-rgb / --accent-rgb 从 --accent HEX 推导
            _m = _re.match(r'#([0-9a-fA-F]{6})', accent)
            if _m:
                _h = _m.group(1)
                _rgb = f"{int(_h[0:2],16)}, {int(_h[2:4],16)}, {int(_h[4:6],16)}"
                mobile_colors['--brand-rgb'] = _rgb
                mobile_colors['--accent-rgb'] = _rgb
            content = replace_color_zone(content, mobile_colors)
            print(f"[build] 移动端主题映射: --accent({accent}) → --brand 系（自动统一品牌色）")

    # 1b. 移动端专用：底部导航 {{导航项}} / 主页面 {{页面内容}} / 导航模式
    if is_mobile:
        if config.get('nav'):
            nav_content = _read_file(config['nav'], 'nav')
            content = content.replace('{{导航项}}', nav_content)
            print(f"[build] 注入底部导航: {os.path.basename(config['nav'])}")
        # 导航模式（class 变体，不改底座结构）：solid=传统固定底栏 / fab=中间凸起；默认毛玻璃悬浮胶囊
        nav_mode = config.get('navMode', '')
        if nav_mode in ('solid', 'fab'):
            content = content.replace('<div class="bottom-nav" id="bottomNav">',
                                      f'<div class="bottom-nav nav-{nav_mode}" id="bottomNav">', 1)
            print(f"[build] 底部导航模式: {nav_mode}")
        if config.get('mainPage'):
            mp_content = _read_file(config['mainPage'], 'mainPage')
            content = content.replace('{{页面内容}}', mp_content)
            print(f"[build] 注入主页面: {os.path.basename(config['mainPage'])}")

    # 2. 注入导航（NAV_START/END，桌面端）
    # V2 顶栏外壳（原 V4，无左导航）：导航由 JS 数据对象 TOP_SECTIONS 驱动（顶栏区段），
    # 运行时 renderTopNav 渲染，故 V2(cockpit) 跳过 HTML NAV 注入（仅有顶栏导航，无左栏）。
    # v5.41 起 V2 支持可选 navjs 注入文件：config 配 "navjs" 键，build 将其整块替换进
    # 模板 // Agent:NAVJS_START/END 标记之间（包裹 MAX_TOPNAV + TOP_SECTIONS），并剥离标记。
    if config.get('nav') and not is_mobile and config.get('template') != 'desktop-v2':
        nav_content = _read_file(config['nav'], 'nav')
        content = replace_between(content, '<!-- Agent:NAV_START', '<!-- Agent:NAV_END', nav_content, 'NAV')
        print(f"[build] 注入导航: {os.path.basename(config['nav'])}")
    elif config.get('nav') and config.get('template') == 'desktop-v2':
        print('[build] 跳过 V2(cockpit) HTML NAV 注入（仅有顶栏导航，导航定制请配 navjs 注入文件）')

    # 2b. V2 顶栏导航注入（NAVJS 标记，v5.41）：可选；未提供时保留模板内置默认导航，
    #     标记行由 strip_injection_markers 在产物中统一剥离
    if config.get('navjs') and config.get('template') == 'desktop-v2':
        navjs_content = _read_file(config['navjs'], 'navjs')
        content = replace_between(content, '// Agent:NAVJS_START', '// Agent:NAVJS_END', navjs_content, 'NAVJS')
        print(f"[build] 注入 V2 顶栏导航(navjs): {os.path.basename(config['navjs'])}")

    # 3. 注入页面（desktop/mobile: PAGE_START/END；prd: SECTION_START/END）
    # PRD 模板：config 可用 pages 或 sections 键（历史文档用 sections，build 兼容别名）
    is_prd = config.get('template') == 'prd'
    pages_key = 'pages' if config.get('pages') else ('sections' if config.get('sections') else None)
    if is_prd and not pages_key:
        raise ValueError('[build] PRD 模板必须注入章节内容：config.json 需提供 pages（或 sections）键指向 sections.html，缺失则模板示例残留（曾静默假成功）')
    if pages_key:
        pages_content = _read_file(config[pages_key], pages_key)
        if is_prd:
            content = replace_between(content, '<!-- Agent:SECTION_START', '<!-- Agent:SECTION_END', pages_content, 'SECTION')
        else:
            content = replace_between(content, '<!-- Agent:PAGE_START', '<!-- Agent:PAGE_END', pages_content, 'PAGE')
        print(f"[build] 注入页面: {os.path.basename(config[pages_key])}")

    # 4. 注入数据（DATA_START/END）— 清空示例区并替换
    if config.get('data'):
        data_content = _read_file(config['data'], 'data')
        # 模板 DATA 区可能同时是 JS 注释块（<!-- -->）或纯 JS 注释（//）
        # 先尝试 JS 注释形式（模板内实际用 // Agent:DATA_START）
        if '// Agent:DATA_START' in content:
            content = replace_between(content, '// Agent:DATA_START', '// Agent:DATA_END', data_content, 'DATA')
        elif '<!-- Agent:DATA_START' in content:
            content = replace_between(content, '<!-- Agent:DATA_START', '<!-- Agent:DATA_END', data_content, 'DATA')
        else:
            # 标记缺失必须报错（曾经静默“假成功”，导致示例数据残留未被替换）
            raise ValueError('[build] 模板缺少标记 // Agent:DATA_START（DATA），无法注入数据')
        print(f"[build] 注入数据: {os.path.basename(config['data'])}")

    # 5. 注入业务函数（biz.js 追加到最后一个 script 的 </script> 前）
    if config.get('biz'):
        biz_content = _read_file(config['biz'], 'biz')
        last_script_end = content.rfind('</script>')
        if last_script_end == -1:
            raise ValueError('[build] 模板无 script 块，无法注入 biz')
        biz_block = '\n// ===== 业务函数（Agent 注入）=====\n' + biz_content + '\n'
        content = content[:last_script_end] + biz_block + content[last_script_end:]
        print(f"[build] 注入业务函数: {os.path.basename(config['biz'])}")

    # 5b. 清空模板示例业务实现（EXAMPLES_START/END 区，防"僵尸示例代码"污染生成文件）
    if '// Agent:EXAMPLES_START' in content:
        content = replace_between(content, '// Agent:EXAMPLES_START', '// Agent:EXAMPLES_END',
                                  '// 示例业务实现已由 build-prototype.py 清空（真实业务通过 biz.js 注入）', 'EXAMPLES')
        print('[build] 清空模板示例业务实现')

    # 6. PRD 专用：sectionIndex / 知识库
    if config.get('sectionIndex'):
        si_content = _read_file(config['sectionIndex'], 'sectionIndex')
        content = replace_between(content, '// Agent:SEARCH_DATA_START', '// Agent:SEARCH_DATA_END', si_content, 'SEARCH_DATA')
        print('[build] 注入 sectionIndex')
    if config.get('kb'):
        kb_content = _read_file(config['kb'], 'kb')
        content = replace_between(content, '// Agent:DATA_START', '// Agent:DATA_END', kb_content, 'KB')
        print('[build] 注入知识库')

    # 7. 替换文本占位符 + 清理注入标记（生成文件不残留模板标记）
    content = replace_placeholders(content, config)
    content = strip_injection_markers(content)

    return content


def _read_file(path, label):
    if not os.path.exists(path):
        raise ValueError(f'[build] {label} 文件不存在: {path}')
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


# ============================================================
# 验证流程
# ============================================================

def run_lint(output_path, prd_mode='detailed'):
    """第 1 层：Lint 可执行级检查"""
    print(f"\n[验证] Lint 检查: {os.path.basename(output_path)}")
    lint_script = os.path.join(STANDARDS_DIR, 'agent-lint.py')
    cmd = [sys.executable, lint_script, output_path, '--prd-mode', prd_mode]
    result = subprocess.run(
        cmd,
        capture_output=True, text=True, encoding='utf-8'
    )
    # 输出 Lint 报告尾部
    lines = result.stdout.strip().split('\n')
    for line in lines[-12:]:
        print(f"  {line}")
    return result.returncode == 0


def run_pm_review(output_path):
    """第 1.5 层：产品逻辑评审（移动端，pm-review.py）"""
    print(f"\n[验证] 产品逻辑评审: {os.path.basename(output_path)}")
    review_script = os.path.join(STANDARDS_DIR, 'pm-review.py')
    if not os.path.exists(review_script):
        print('  ⚠️ pm-review.py 不存在，跳过产品逻辑评审')
        return True
    cmd = [sys.executable, review_script, output_path]
    result = subprocess.run(
        cmd,
        capture_output=True, text=True, encoding='utf-8'
    )
    lines = result.stdout.strip().split('\n')
    for line in lines[-20:]:
        print(f"  {line}")
    # fail 项 = 阻断；warning 项 = 提示不阻断
    return result.returncode == 0


def run_browser(output_path, prd_mode='detailed'):
    """第 2 层：浏览器机械断言"""
    print(f"\n[验证] 浏览器断言: {os.path.basename(output_path)}")
    browser_script = os.path.join(SCRIPTS_DIR, 'browser-check.py')
    cmd = [sys.executable, browser_script, output_path, '--prd-mode', prd_mode]
    result = subprocess.run(
        cmd,
        capture_output=True, text=True, encoding='utf-8'
    )
    lines = result.stdout.strip().split('\n')
    for line in lines[-14:]:
        print(f"  {line}")
    return result.returncode == 0


# ============================================================
# 主入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='PM Agent 交付物确定性拼装脚本')
    parser.add_argument('--template', required=True, choices=['desktop', 'desktop-v2', 'desktop-v3', 'mobile', 'prd'], help='模板类型')
    parser.add_argument('--prd-mode', choices=['detailed', 'simple'], default='detailed',
                        help='PRD 文档模式：detailed=详细版(默认) / simple=简易版(无智能助手/搜索栏)')
    parser.add_argument('--config', required=True, help='config.json 路径')
    parser.add_argument('--out', required=True, help='输出 HTML 路径')
    parser.add_argument('--skip-browser', action='store_true', help='跳过浏览器验证（仅 Lint，lint 仍会拦住对齐/列宽等模板回归）')
    parser.add_argument('--no-verify', action='store_true', help='【危险】跳过浏览器断言；Lint 仍强制运行以拦住对齐/列宽等模板回归，交付前请勿使用')
    parser.add_argument('--skip-embed', action='store_true', help='跳过离线内嵌（产物保留 CDN 引用，需联网查看；一般交付建议开启内嵌）')
    args = parser.parse_args()

    # 读取配置
    if not os.path.exists(args.config):
        print(f'❌ config 文件不存在: {args.config}')
        sys.exit(1)
    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)
    config['template'] = args.template

    # 构建
    try:
        content = build(config, prd_mode=args.prd_mode)
        # D43 防护：桌面端产物品牌名校验（模板占位符替换后必须 == config.project）
        if args.template in ('desktop', 'desktop-v2', 'desktop-v3'):
            import re as _re
            m = _re.search(r'id="brandName">([^<]*)<', content)
            if m:
                actual = m.group(1).strip()
                expected = config.get('project', '')
                if actual != expected:
                    raise ValueError(
                        f'品牌名校验失败：产物 brandName="{actual}" ≠ config.project="{expected}"'
                        f'（模板硬编码品牌名残留或占位符未替换，D43，请检查 templates/prototype-desktop-v3.html 等）'
                    )
    except Exception as e:
        print(f'❌ 构建失败: {e}')
        sys.exit(1)

    # 输出
    out_dir = os.path.dirname(os.path.abspath(args.out))
    os.makedirs(out_dir, exist_ok=True)
    with open(args.out, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ 输出: {args.out} ({len(content)/1024:.0f}KB)")

    # M109 离线内嵌：默认执行（把 CDN 引用替换为 base64 内嵌，产物 100% 离线可用）
    # v5.41 收紧：内嵌失败 = 构建失败。「离线可用」是交付承诺的一部分，
    # 部分资源仍依赖 CDN 却放行构建 = 验证链路误判（审计确认项）。
    # 显式 --skip-embed 为主动豁免（产物标记 skipped，browser-check 会如实报给门禁）。
    if not args.skip_embed:
        try:
            embed_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'embed-offline.py')
            import subprocess as _sp
            _r = _sp.run([sys.executable, embed_script, '--input', args.out], capture_output=True, text=True, timeout=300)
            if _r.returncode == 0:
                print('✅ 离线内嵌完成：产物 100% 离线可用（图标/图表/样式内嵌）')
            else:
                print(f'❌ 离线内嵌失败（exit {_r.returncode}），构建中止。')
                print(f'   失败详情: {(_r.stderr or _r.stdout or "")[-400:]}')
                print('   处理：① 检查网络后重试（vendor 缓存在 assets/vendor/ 可断点重试）；'
                      '② 确接受联网交付则显式传 --skip-embed（产物将保留 CDN 引用并被浏览器校验如实标注）。')
                sys.exit(1)
        except ValueError as ve:
            raise
        except Exception as e:
            print(f'❌ 离线内嵌执行异常: {e} —— 构建中止。处理：检查网络 / Python 环境；确接受联网交付可显式传 --skip-embed。')
            sys.exit(1)

    if args.no_verify:
        # 即便要求跳过浏览器断言，Lint（第 1 层）仍必须运行：
        # 它能在不启动浏览器的前提下拦住对齐改回 center、列宽不均、操作列换行等模板级回归。
        # 真正"跳过全部验证"不安全，故不再提供。
        print('\n⚠️  [--no-verify] 已跳过浏览器断言；Lint + 产品逻辑评审仍强制运行以拦住模板级回归')
        lint_ok = run_lint(args.out, prd_mode=args.prd_mode)
        review_ok = run_pm_review(args.out) if args.template == 'mobile' else True
        if lint_ok and review_ok:
            print('\n🎉 构建 + Lint + 产品逻辑评审通过（未跑浏览器断言，交付前请用默认构建跑完整 B9 断言）')
            sys.exit(0)
        print('\n🚫 Lint/产品逻辑评审未通过，禁止交付')
        sys.exit(1)

    # 验证（默认路径：Lint + 产品逻辑评审 + 浏览器三闸）
    lint_ok = run_lint(args.out, prd_mode=args.prd_mode)
    review_ok = run_pm_review(args.out) if args.template == 'mobile' else True
    browser_ok = True
    if not args.skip_browser:
        browser_ok = run_browser(args.out, prd_mode=args.prd_mode)

    if lint_ok and review_ok and browser_ok:
        print("\n🎉 构建 + 全部验证通过，可以交付")
        sys.exit(0)
    else:
        print(f"\n🚫 验证未通过（Lint: {'✅' if lint_ok else '❌'} / 浏览器: {'✅' if browser_ok else '❌'}），禁止交付")
        sys.exit(1)


if __name__ == '__main__':
    main()
