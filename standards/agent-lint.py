#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agent-lint.py — PM Agent 交付物自动化 Lint 检查脚本

用法：
    python standards/agent-lint.py 生成的文件1.html 生成的文件2.html ...

退出码：
    0 = 全部通过
    1 = 有失败项（详见输出报告）

检查项（30+ 项）：
    框架铁律 F1-F9、交互铁律 I1/I5/Q3+/Q9、质感铁律 T1/T6/Q5/Q6/Q10/Q11
    桌面端专项 D7/D9/D10、基础设施 R1-R5
    PRD 专项、枚举覆盖率、伪页面检测、文字对比度检测
"""

import re
import sys
import os
import argparse
from collections import defaultdict

# 非 UTF-8 终端（Windows GBK/cp936）打印 ✅❌ 等 emoji 会抛 UnicodeEncodeError，强制 UTF-8 输出
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding='utf-8')
    except Exception:
        pass

# ============================================================
# 工具函数
# ============================================================

def read_file(path):
    """读取文件内容（UTF-8）"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return None

def is_template_file(path):
    """判断是否为模板文件（基础骨架模板，跳过部分检查）"""
    basename = os.path.basename(path).lower()
    template_names = [
        'prototype-mobile.html',
        'prototype-desktop.html',
        'prototype-desktop-v2.html',
        'prototype-desktop-v3.html',
        'prd-template.html',
        'prd-template-simple.html',
    ]
    return basename in template_names

def is_component_file(path):
    """判断是否为组件库文件（路径含 components/）"""
    normalized = path.replace('\\', '/')
    return '/components/' in normalized or 'components/' in normalized

def is_prd_file(content):
    """判断是否为 PRD 文档"""
    return 'prd-section' in content or ('tab-content' in content and 'showSection' in content) \
           or 'PM-AGENT-PRD' in content  # 简易版 PRD 标记（无 findAnswer）

def is_prd_simple(content):
    """判断是否为简易版 PRD — 特征：PM-AGENT-PRD 标记 且 无 findAnswer（智能助手）"""
    return 'PM-AGENT-PRD' in content and 'findAnswer' not in content

def is_mobile_file(content):
    """判断是否为移动端原型"""
    return 'phone-frame' in content or 'phone-screen' in content

def is_desktop_file(content):
    """判断是否为桌面端原型"""
    return ('sidebar' in content.lower() and 'navigateTo' in content) or \
           ('loginPage' in content and 'switchPage' in content)

def is_v2_paradigm(content):
    """判断是否为桌面端 V2「轻量工作台(Portal)」范式（数据驱动：表格/分页/详情由 JS 运行时注入）。
    通过模板内置签名标记 pm-agent-paradigm:desktop-v2 识别，该标记 build 不会被清理。"""
    return 'pm-agent-paradigm:desktop-v2' in content

def is_v3_paradigm(content):
    """判断是否为桌面端 V3「现代侧栏仪表盘」范式（数据驱动：侧栏导航/表格/分页/图表由 JS 运行时注入）。
    通过模板内置签名标记 pm-agent-paradigm:desktop-v3 识别，该标记 build 不会被清理。
    V3 与 V2 同属「数据驱动」现代范式，共享 D9/M47/M49/C1-7 等静态降级（运行时由 browser-check 验证）。"""
    return 'pm-agent-paradigm:desktop-v3' in content

def is_v4_paradigm(content):
    """判断是否为桌面端 V4「企业驾驶舱（顶栏外壳 + 内容全宽 + 右栏系统通知）」范式。
    数据驱动：顶栏区段 TOP_SECTIONS / 系统管理子页 / 右栏系统通知均由 JS 运行时注入。
    通过模板内置签名标记 pm-agent-paradigm:desktop-v4 识别，该标记 build 不会被清理。
    V4 无左栏侧边栏（与 V3 的 .sidebar 不同），系统管理 5 子页由 browser-check M22/B3++++ 验证，
    与 V2/V3 同属「数据驱动」现代范式，共享 D9/M47/M49/C1-7 等静态降级。"""
    return 'pm-agent-paradigm:desktop-v4' in content

def is_modern_paradigm(content):
    """V2 + V3 + V4 现代数据驱动范式并集（共享静态降级策略）"""
    return is_v2_paradigm(content) or is_v3_paradigm(content) or is_v4_paradigm(content)

# ============================================================
# 检查结果类
# ============================================================

class CheckResult:
    def __init__(self):
        self.passed = []
        self.failed = []
        self.warnings = []

    def ok(self, rule_id, msg):
        self.passed.append((rule_id, msg))

    def fail(self, rule_id, msg):
        self.failed.append((rule_id, msg))

    def warn(self, rule_id, msg):
        self.warnings.append((rule_id, msg))

    @property
    def exit_code(self):
        return 0 if not self.failed else 1

# ============================================================
# 检查规则
# ============================================================

# --- 框架铁律 F1-F9 ---

def check_f1_phone_frame(content, result, is_template, is_component):
    """F1: 手机模拟器"""
    if is_template or is_component:
        result.ok('F1', '模板/组件文件跳过')
        return
    if not is_mobile_file(content):
        result.ok('F1', '非移动端文件跳过')
        return
    if 'phone-frame' in content and 'phone-screen' in content:
        result.ok('F1', 'phone-frame 框架存在')
    else:
        result.fail('F1', '移动端原型缺少 phone-frame 或 phone-screen 结构')

def check_f3_status_bar(content, result, is_template, is_component):
    """F3: 灵动岛+状态栏"""
    if is_template or is_component:
        result.ok('F3', '模板/组件文件跳过')
        return
    if not is_mobile_file(content):
        result.ok('F3', '非移动端文件跳过')
        return
    has_island = 'dynamic-island' in content
    has_status = 'status-bar' in content
    if has_island and has_status:
        result.ok('F3', '灵动岛+状态栏完整')
    else:
        missing = []
        if not has_island:
            missing.append('dynamic-island')
        if not has_status:
            missing.append('status-bar')
        result.fail('F3', f'缺少: {", ".join(missing)}')

def check_f5_adjust_scale(content, result, is_template, is_component):
    """F5: 响应式缩放"""
    if is_template or is_component:
        result.ok('F5', '模板/组件文件跳过')
        return
    if not is_mobile_file(content):
        result.ok('F5', '非移动端文件跳过')
        return
    if 'adjustScale' in content and 'Math.max' in content:
        result.ok('F5', 'adjustScale 函数存在且含 Math.max 保护')
    elif 'adjustScale' in content:
        result.warn('F5', 'adjustScale 存在但未检测到 Math.max 缩放下限保护')
    else:
        result.fail('F5', '缺少 adjustScale() 函数')

def check_f6_top_bar(content, result, is_template, is_component):
    """F6: 顶部导航栏"""
    if is_template or is_component:
        result.ok('F6', '模板/组件文件跳过')
        return
    if not is_mobile_file(content):
        result.ok('F6', '非移动端文件跳过')
        return
    if 'top-bar' in content:
        result.ok('F6', '.top-bar 导航栏存在')
    else:
        result.fail('F6', '缺少 .top-bar 顶部导航栏')

def check_f7_sub_page(content, result, is_template, is_component):
    """F7: 二级子页面"""
    if is_template or is_component:
        result.ok('F7', '模板/组件文件跳过')
        return
    if not is_mobile_file(content):
        result.ok('F7', '非移动端文件跳过')
        return
    if 'sub-page' in content:
        result.ok('F7', '.sub-page 结构存在')
    else:
        result.fail('F7', '缺少 .sub-page 二级页面结构')

def check_f8_css_vars(content, result, is_template, is_component):
    """F8: CSS变量完整性"""
    if is_template or is_component:
        result.ok('F8', '模板/组件文件跳过')
        return
    if not is_mobile_file(content):
        result.ok('F8', '非移动端文件跳过')
        return
    has_status_h = '--status-h' in content
    has_topbar_h = '--topbar-h' in content
    if has_status_h and has_topbar_h:
        result.ok('F8', '--status-h 和 --topbar-h 变量存在')
    else:
        missing = []
        if not has_status_h:
            missing.append('--status-h')
        if not has_topbar_h:
            missing.append('--topbar-h')
        result.fail('F8', f'缺少 CSS 变量: {", ".join(missing)}')

def check_f9_bottom_nav_standard(content, result, is_template, is_component):
    """F9: iOS 风格悬浮导航（M40最终版：nav-wrapper > nav-mask[mask-image渐隐] + bottom-nav）"""
    if is_template or is_component:
        result.ok('F9', '模板/组件文件跳过')
        return
    if not is_mobile_file(content):
        result.ok('F9', '非移动端文件跳过')
        return
    if 'bottom-nav' not in content:
        result.ok('F9', '无底部导航（可能该页面无底部Tab）')
        return
    issues = []
    # 检查1: 禁止使用 ::before 伪元素放蒙版
    has_pseudo_before = bool(re.search(r'\.bottom-nav\s*::\s*before', content))
    if has_pseudo_before:
        issues.append('使用了 ::before 伪元素放蒙版（应使用 nav-mask 独立元素）')
    # 检查2: 必须有 nav-wrapper 统一容器
    if 'nav-wrapper' not in content:
        issues.append('缺少 nav-wrapper 统一容器（底部导航必须包裹在 nav-wrapper 内）')
    # 检查3: 必须有 nav-mask 渐变蒙版元素
    if 'nav-mask' not in content:
        issues.append('缺少 nav-mask 渐变蒙版元素（蒙版应为独立元素在导航背后）')
    else:
        mask_css_match = re.search(r'\.nav-mask\s*\{([^}]+)\}', content)
        if mask_css_match:
            mask_css = mask_css_match.group(1)
            # 蒙版必须有 mask-image（M40：用 mask-image 让 backdrop-filter 一起渐隐，无硬边界）
            if 'mask-image' not in mask_css and '-webkit-mask-image' not in mask_css:
                issues.append('nav-mask 缺少 mask-image（M40：必须用 mask-image 渐隐，否则 backdrop-filter 顶部有硬边界）')
            else:
                # mask-image 方向必须 to top
                if 'to top' not in mask_css:
                    issues.append('nav-mask mask-image 方向错误（必须 to top：底部完整→顶部渐隐）')
            # 蒙版必须有 backdrop-filter 毛玻璃
            if 'backdrop-filter' not in mask_css:
                issues.append('nav-mask 缺少 backdrop-filter（蒙版毛玻璃效果）')
            # 蒙版必须有 pointer-events:none
            if 'pointer-events:none' not in mask_css and 'pointer-events: none' not in mask_css:
                issues.append('nav-mask 缺少 pointer-events:none')
            # 蒙版 z-index 必须低于导航
            if 'z-index:1' not in mask_css and 'z-index: 1' not in mask_css:
                issues.append('nav-mask z-index 应为 1（低于导航的 z-index:2）')
            # 蒙版背景必须是明显可见的白色渐变（M58：低透明纯色+mask-image 双重渐隐 → 视觉不可见）
            bg_m = re.search(r'background:\s*([^;]+)', mask_css)
            if bg_m:
                bg_val = bg_m.group(1).strip()
                if 'gradient' not in bg_val:
                    alpha_m = re.search(r'rgba?\(255,\s*255,\s*255,\s*([0-9.]+)\)', bg_val)
                    if alpha_m and float(alpha_m.group(1)) < 0.75:
                        issues.append('nav-mask 背景是低透明纯色（alpha ' + alpha_m.group(1) + '）+ mask-image 渐隐双重叠加导致蒙版视觉不可见，应改明显白色渐变 background:linear-gradient(to top, rgba(255,255,255,0.94) 0%, ...)（M58）')
                    elif not alpha_m and 'transparent' not in bg_val and 'rgba' not in bg_val and '#' not in bg_val:
                        issues.append('nav-mask 背景值异常（应为白色渐变）（M58）')
    # 检查4: bottom-nav 导航栏样式
    nav_css_match = re.search(r'\.bottom-nav\s*\{([^}]+)\}', content)
    if nav_css_match:
        nav_css = nav_css_match.group(1)
        # 必须有 backdrop-filter 毛玻璃
        if 'backdrop-filter' not in nav_css:
            issues.append('缺少 backdrop-filter 毛玻璃效果')
        # 必须有 border-radius 圆角
        if 'border-radius' not in nav_css:
            issues.append('缺少 border-radius 圆角（悬浮导航必须有圆角）')
        # 必须悬浮——bottom 不能为 0
        bottom_match = re.search(r'bottom:\s*(\d+)px', nav_css)
        if bottom_match:
            if int(bottom_match.group(1)) == 0:
                issues.append('bottom:0 贴底（悬浮导航应有 bottom 间距，如 12px）')
        else:
            issues.append('未设置 bottom 间距（应有 bottom:12px）')
        # 必须有左右间距
        left_match = re.search(r'left:\s*(\d+)px', nav_css)
        if left_match and int(left_match.group(1)) == 0:
            issues.append('left:0 全宽（悬浮导航应有 left 间距，如 12px）')
        # 必须有 box-shadow 阴影
        if 'box-shadow' not in nav_css:
            issues.append('缺少 box-shadow 阴影')
        # 导航 z-index 必须高于蒙版
        if 'z-index:2' not in nav_css and 'z-index: 2' not in nav_css:
            issues.append('bottom-nav z-index 应为 2（高于蒙版的 z-index:1）')
        # 必须 pointer-events:auto（容器 none，导航需单独开启）
        if 'pointer-events:auto' not in nav_css and 'pointer-events: auto' not in nav_css:
            issues.append('bottom-nav 缺少 pointer-events:auto（容器 none 时导航需单独开启）')
    if issues:
        result.fail('F9', '；'.join(issues))
    else:
        result.ok('F9', 'iOS 悬浮导航（统一容器+mask-image渐隐蒙版+毛玻璃+圆角+阴影）')

# --- 交互铁律 ---

# 真实功能函数关键词（非伪功能）
GENUINE_FUNC_PATTERN = re.compile(
    r'\b(?:openSub|openModal|closeModal|switchTab|switchPage|navigateTo|'
    r'openDrawer|closeDrawer|showSection|openSubPage|closeSubPage|'
    r'render[A-Z]\w*|edit[A-Z]\w*|delete[A-Z]\w*|save[A-Z]\w*|'
    r'confirmDelete\w*|update\w*|add\w*|toggle\w*|search\w*|filter\w*|'
    r'init\w*|load\w*|submit\w*|export\w*|import\w*|'
    r'goBack|goHome|doLogin|doSearch|findAnswer|showToast)'
)

def check_i1_all_buttons_respond(content, result, is_template, is_component):
    """I1: 全按钮响应"""
    if is_template:
        result.ok('I1', '模板文件跳过（骨架占位按钮）')
        return
    if is_component:
        result.ok('I1', '组件文件跳过（演示按钮）')
        return
    # 移除 HTML 注释块（注释内的参考示例按钮不计入）
    content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
    # 找所有 <button 标签
    buttons = re.findall(r'<button[^>]*>(.*?)</button>', content, re.DOTALL)
    buttons_no_onclick = 0
    for i, btn_html in enumerate(re.finditer(r'<button([^>]*)>', content)):
        attrs = btn_html.group(1)
        has_onclick = 'onclick' in attrs
        has_type_submit = 'type="submit"' in attrs or "type='submit'" in attrs
        if not has_onclick and not has_type_submit:
            buttons_no_onclick += 1
    # 也检查 .btn- 类元素（仅限可点击标签 button/a/span，排除 filter-btn-group 等容器）
    btn_class_no_onclick = 0
    for m in re.finditer(r'<(button|a|span)\s+class="[^"]*btn-[^"]*"[^>]*>', content, re.IGNORECASE):
        if 'onclick' not in m.group(0):
            btn_class_no_onclick += 1

    total_dead = buttons_no_onclick + btn_class_no_onclick
    if total_dead == 0:
        result.ok('I1', '所有按钮均有响应')
    elif total_dead <= 2:
        result.warn('I1', f'发现 {total_dead} 个无 onclick 的按钮/ btn 元素（可能是装饰性按钮）')
    else:
        result.fail('I1', f'发现 {total_dead} 个无 onclick 的按钮/ btn 元素')

def check_i5_pseudo_function_buttons(content, result, is_template, is_component):
    """I5: 功能真实实现 — 检测伪功能按钮（仅调用 showToast 而无真实功能）

    放行规则（实战校准）：禁用态/状态反馈按钮——若按钮带 disabled 属性、opacity 降低、
    或提示文案含状态词（审核中/待处理/敬请期待/稍后），点击提示状态是合理 UX，非伪功能。
    """
    if is_template or is_component:
        result.ok('I5', '模板/组件文件跳过')
        return
    # 找所有 onclick 事件（含其所在的标签上下文，用于判定禁用视觉）
    pseudo_buttons = []
    # 状态反馈词：禁用态/流程态提示是合理 UX（非伪功能）
    STATE_WORDS = ('审核中', '待处理', '待审核', '敬请期待', '稍后', '维护中', '暂停', '升级中',
                   '敬请留意', '已成交', '已售', '已下架', '已结束', '已失效', '已过期', '已取消',
                   '已退款', '已关闭', '已完成', '尚未', '暂不能', '无法', '未支付')
    for m in re.finditer(r'<[^>]*\bonclick="([^"]*)"[^>]*>', content):
        handler = m.group(1)
        tag = m.group(0)
        handler_stripped = handler.strip()
        # 检查是否仅调用 showToast / toast
        cleaned = re.sub(r'\s+', '', handler_stripped.rstrip(';'))
        is_pure_toast = re.match(r'^(showToast|toast)\s*\([^)]*\)$', cleaned) or \
                        re.match(r'^(showToast|toast)\s*\([^)]*\);\s*$', cleaned)
        if not is_pure_toast:
            continue
        # 放行禁用态/状态反馈按钮：opacity 降低 或 disabled 属性 或 文案含状态词
        is_disabled_visual = ('opacity' in tag and re.search(r'opacity\s*:\s*0?\.\d', tag)) or 'disabled' in tag
        if is_disabled_visual or any(w in handler for w in STATE_WORDS):
            continue
        pseudo_buttons.append(handler_stripped)
    if not pseudo_buttons:
        result.ok('I5', '未检测到伪功能按钮（仅 Toast 的按钮）')
    else:
        sample = pseudo_buttons[0][:60]
        result.fail('I5', f'检测到 {len(pseudo_buttons)} 个伪功能按钮（onclick 仅调用 showToast），示例: "{sample}"')

def check_q3_func_name_escape(content, result, is_template, is_component):
    """Q3+: 框架函数名不可逃逸 — 检测是否私自定义 toast() 替代 showToast()"""
    if is_template or is_component:
        result.ok('Q3+', '模板/组件文件跳过')
        return
    # 检查是否定义了 toast 函数（而非使用标准 showToast）
    has_custom_toast = bool(re.search(r'function\s+toast\s*\(', content))
    has_show_toast = bool(re.search(r'function\s+showToast\s*\(', content))
    if has_custom_toast and not has_show_toast:
        result.fail('Q3+', '检测到自定义 toast() 函数替代标准 showToast()，框架函数名不可逃逸')
    else:
        result.ok('Q3+', '未检测到框架函数名逃逸')

def check_q9_inline_showtoast_residue(content, result, is_template, is_component):
    """Q9: 内联 onclick 无残留 showToast 占位"""
    if is_template:
        result.ok('Q9', '模板文件跳过')
        return
    # 在骨架 HTML 中检查残留的 showToast() 占位伪按钮
    # 骨架中的占位通常形如 onclick="showToast('xxx')"
    # 但如果 showToast 在该文件中被正确定义且被真实功能调用，则不算残留
    # 这里检查的是模板骨架中标记区域的占位
    placeholder_pattern = re.findall(r'onclick="showToast\([\'"][^)]*[\'"]\)"', content)
    # 过滤掉真实的反馈型 Toast（如保存成功、删除成功等）
    real_feedback_keywords = ['成功', '已删除', '已添加', '已保存', '已更新', '已复制', '已通过', '已驳回', 'error', '失败', 'warning']
    genuine_placeholders = []
    for p in placeholder_pattern:
        is_real = any(kw in p for kw in real_feedback_keywords)
        if not is_real:
            genuine_placeholders.append(p)
    if not genuine_placeholders:
        result.ok('Q9', '无残留 showToast 占位伪按钮')
    else:
        result.fail('Q9', f'检测到 {len(genuine_placeholders)} 个残留 showToast 占位按钮，示例: "{genuine_placeholders[0][:60]}"')

def check_q5_scale_protection(content, result, is_template, is_component):
    """Q5: 缩放下限保护 — adjustScale() 必须用 Math.max(0.1, ...)"""
    if is_template or is_component:
        result.ok('Q5', '模板/组件文件跳过')
        return
    if not is_mobile_file(content):
        result.ok('Q5', '非移动端文件跳过')
        return
    if 'adjustScale' not in content:
        result.ok('Q5', '无 adjustScale 函数（可能不需要缩放）')
        return
    # 检查 Math.max 是否用于缩放保护
    if 'Math.max' in content and ('0.1' in content or '0.5' in content):
        result.ok('Q5', 'adjustScale 含 Math.max 缩放下限保护')
    else:
        result.fail('Q5', 'adjustScale 缺少 Math.max 缩放下限保护，可能导致缩放到 0 白屏')

def check_q6_filter_real_impl(content, result, is_template, is_component):
    """Q6: 筛选功能真实实现 — 搜索/筛选框必须在 render 中通过 .value 读取输入"""
    if is_template or is_component:
        result.ok('Q6', '模板/组件文件跳过')
        return
    # 检查是否有搜索/筛选输入框
    search_inputs = re.findall(r'<input[^>]*(?:type="search"|placeholder="[^"]*搜索|placeholder="[^"]*筛选|placeholder="[^"]*输入)', content)
    if not search_inputs:
        result.ok('Q6', '无搜索/筛选输入框')
        return
    # 检查是否有 .value 读取
    value_reads = re.findall(r'\.value\b', content)
    if value_reads:
        result.ok('Q6', f'检测到 {len(value_reads)} 处 .value 读取，筛选功能可能真实实现')
    else:
        result.fail('Q6', '存在搜索/筛选输入框但未检测到 .value 读取，筛选功能可能未真实实现')

def check_q10_nav_stack(content, result, is_template, is_component):
    """Q10: 导航栈一致 — subPageStack 必须通过 push/pop 管理"""
    if is_template or is_component:
        result.ok('Q10', '模板/组件文件跳过')
        return
    if 'subPageStack' not in content:
        result.ok('Q10', '无 subPageStack（可能使用其他导航管理方式）')
        return
    # 检查是否有 push 和 pop 操作
    has_push = '.push(' in content
    has_pop = '.pop(' in content
    if has_push and has_pop:
        result.ok('Q10', 'subPageStack 通过 push/pop 管理')
    else:
        missing = []
        if not has_push:
            missing.append('push')
        if not has_pop:
            missing.append('pop')
        result.fail('Q10', f'subPageStack 缺少 {"/".join(missing)} 操作，可能直接 display:none 绕过')

def check_q11_detail_parameterized(content, result, is_template, is_component):
    """Q11: 详情参数化 — open*Detail() 必须接受参数"""
    if is_template or is_component:
        result.ok('Q11', '模板/组件文件跳过')
        return
    # 找所有 openXxxDetail 函数定义
    detail_funcs = re.findall(r'function\s+(open\w*Detail)\s*\(([^)]*)\)', content)
    if not detail_funcs:
        result.ok('Q11', '无 open*Detail 函数')
        return
    hardcoded = []
    for func_name, params in detail_funcs:
        params = params.strip()
        if not params or params == '':
            hardcoded.append(func_name)
    if not hardcoded:
        result.ok('Q11', '所有 open*Detail 函数均接受参数')
    else:
        result.fail('Q11', f'以下 Detail 函数未接受参数（硬编码详情）: {", ".join(hardcoded)}')

# --- 质感铁律 ---

# 常见 Emoji 范围检测
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map symbols
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U00002700-\U000027BF"  # dingbats
    "\U0001F900-\U0001F9FF"  # supplemental symbols
    "\U0001FA00-\U0001FA6F"  # chess symbols
    "\U0001FA70-\U0001FAFF"  # symbols and pictographs extended-A
    "]+",
    flags=re.UNICODE
)

def check_t1_no_emoji(content, result, is_template, is_component):
    """T1: 零 Emoji"""
    if is_template:
        result.ok('T1', '模板文件跳过（占位内容可能含 Emoji）')
        return
    # 从 HTML 内容中移除 <svg> 标签内容（避免误判）
    content_no_svg = re.sub(r'<svg[^>]*>.*?</svg>', '', content, flags=re.DOTALL)
    # 移除注释
    content_clean = re.sub(r'<!--.*?-->', '', content_no_svg, flags=re.DOTALL)
    # 移除 <script> 标签内容（JS 代码中的符号不是 Emoji）
    content_clean = re.sub(r'<script[^>]*>.*?</script>', '', content_clean, flags=re.DOTALL)
    # 移除常见文本符号（✓ ✗ 等 dingbats 范围内的文本符号，非 Emoji）
    content_clean = content_clean.replace('\u2713', '').replace('\u2717', '').replace('\u2714', '').replace('\u2718', '')
    emojis = EMOJI_PATTERN.findall(content_clean)
    if not emojis:
        result.ok('T1', '未检测到 Emoji')
    else:
        result.fail('T1', f'检测到 {len(emojis)} 处 Emoji，示例: "{emojis[0]}"')

def check_t6_currency_symbol(content, result, is_template, is_component):
    """T6: 人民币符号 ¥"""
    # 检查是否有美元符号 $ 用于金额（排除代码中的变量如 $xxx）
    # 只检查可见文本中的 $ 金额模式，如 $100, $1,280
    dollar_amounts = re.findall(r'(?<![a-zA-Z_$])\$\s?\d', content)
    if not dollar_amounts:
        result.ok('T6', '未检测到美元符号金额')
    else:
        result.fail('T6', f'检测到 {len(dollar_amounts)} 处美元符号金额，应使用 ¥，示例: "{dollar_amounts[0]}"')

# --- 桌面端专项 ---

def check_d7_sidebar_collapse(content, result, is_template, is_component):
    """D7: 侧边栏折叠"""
    if is_template or is_component:
        result.ok('D7', '模板/组件文件跳过')
        return
    if not is_desktop_file(content):
        result.ok('D7', '非桌面端文件跳过')
        return
    # V3 现代侧栏仪表盘 / V4 三栏驾驶舱：均无「收起侧栏」功能 → D7 对 V3/V4 降级跳过
    if is_v3_paradigm(content) or is_v4_paradigm(content):
        result.ok('D7', 'V3/V4 无侧栏折叠功能（V4 三栏驾驶舱布局固定，2026-08-09）')
        return
    has_toggle = 'toggleSidebar' in content or 'toggleSidebar(' in content
    has_collapsed_class = 'collapsed' in content
    has_transition = 'transition' in content and ('width' in content or 'sidebar' in content.lower())
    if has_toggle and has_collapsed_class:
        result.ok('D7', '侧边栏折叠功能完整（函数+CSS类）')
    else:
        missing = []
        if not has_toggle:
            missing.append('toggleSidebar 函数')
        if not has_collapsed_class:
            missing.append('collapsed CSS 类')
        result.fail('D7', f'侧边栏折叠不完整，缺少: {", ".join(missing)}')

def check_d9_table_data_complete(content, result, is_template, is_component):
    """D9: 表格数据完整 — 每个表格至少 3 行数据（变更记录/日志类表格除外）"""
    if is_template:
        result.ok('D9', '模板文件跳过')
        return
    # PRD 为文档（规格表/字段表/权限矩阵等常仅 1-2 行），"每表≥3行"仅适用于桌面端原型运行态，故排除 PRD
    if not is_desktop_file(content):
        result.ok('D9', '非桌面端文件跳过（PRD 文档豁免）')
        return
    # V2/V3 数据驱动模板：表格数据由 JS 运行时注入，静态行数检查跳过（运行时由 browser-check B3+ 验证）
    if is_modern_paradigm(content):
        result.ok('D9', 'V2/V3 数据驱动模板：表格数据由 JS 运行时注入，静态行数检查跳过（运行时由 browser-check B3+ 验证）')
        return
    # 找所有 <tbody> 块
    tbodies = re.findall(r'<tbody>(.*?)</tbody>', content, re.DOTALL)
    empty_tables = []
    search_pos = 0
    for i, tbody in enumerate(tbodies):
        rows = re.findall(r'<tr', tbody)
        # 变更记录/操作日志表允许 1 行（初始记录）— 检查 tbody 及之前的表头区域
        if len(rows) < 3:
            tbody_start = content.find('<tbody>', search_pos)
            header_ctx = content[max(0, tbody_start - 400):tbody_start + 300]
            is_log_table = '变更' in header_ctx or '版本' in header_ctx or '日志' in header_ctx or '记录' in header_ctx
            if is_log_table and len(rows) >= 1:
                search_pos = tbody_start + 1
                continue
            if len(rows) == 0:
                empty_tables.append(f'表格#{i+1}（空tbody）')
            else:
                empty_tables.append(f'表格#{i+1}（仅{len(rows)}行）')
        search_pos = content.find('</tbody>', search_pos) + 1
    if not empty_tables:
        result.ok('D9', f'所有 {len(tbodies)} 个表格均有≥3行数据')
    else:
        result.fail('D9', f'{len(empty_tables)} 个表格数据不足: {"; ".join(empty_tables[:3])}')

def check_d10_system_management_interaction(content, result, is_template, is_component):
    """D10: 系统管理交互完整 — 新增/编辑/删除按钮必须有对应函数"""
    if is_template or is_component:
        result.ok('D10', '模板/组件文件跳过')
        return
    if not is_desktop_file(content):
        result.ok('D10', '非桌面端文件跳过')
        return
    # 检查系统管理相关按钮
    system_keywords = ['部门', '成员', '角色', '字典', '菜单配置', '组织']
    has_system_mgmt = any(kw in content for kw in system_keywords)
    if not has_system_mgmt:
        result.ok('D10', '无系统管理模块')
        return
    # 检查新增/编辑/删除按钮是否有真实函数
    add_buttons = re.findall(r'onclick="([^"]*(?:add|新增)[^"]*)"', content, re.IGNORECASE)
    edit_buttons = re.findall(r'onclick="([^"]*(?:edit|编辑)[^"]*)"', content, re.IGNORECASE)
    delete_buttons = re.findall(r'onclick="([^"]*(?:delete|删除)[^"]*)"', content, re.IGNORECASE)

    # 检查这些按钮是否仅调用 showToast
    all_system_buttons = add_buttons + edit_buttons + delete_buttons
    pseudo_count = 0
    for handler in all_system_buttons:
        cleaned = re.sub(r'\s+', '', handler.strip().rstrip(';'))
        if re.match(r'^(showToast|toast)\s*\([^)]*\)$', cleaned):
            pseudo_count += 1

    if pseudo_count == 0:
        result.ok('D10', '系统管理按钮均有真实函数')
    else:
        result.fail('D10', f'{pseudo_count} 个系统管理按钮仅调用 showToast（伪功能），需实现真实 CRUD')

# --- 基础设施 R1-R5 ---

def check_r1_startup_entry(content, result, is_template, is_component):
    """R1: 有启动入口 — DOMContentLoaded 或 window.onload"""
    if is_template:
        result.ok('R1', '模板文件跳过（模板内置启动逻辑）')
        return
    if is_prd_file(content):
        result.ok('R1', 'PRD 文档跳过（IIFE 自动执行，无启动入口概念）')
        return
    has_dom_loaded = 'DOMContentLoaded' in content
    has_window_load = 'window.onload' in content
    if has_dom_loaded or has_window_load:
        result.ok('R1', '检测到启动入口（DOMContentLoaded/window.onload）')
    else:
        result.fail('R1', '缺少 DOMContentLoaded 或 window.onload 启动入口')

def check_r2_init_function(content, result, is_template, is_component):
    """R2: 有 init 函数"""
    # PRD 文档 IIFE 自执行，无 init 概念（与 R1 一致跳过）
    if is_prd_file(content):
        result.ok('R2', 'PRD 文档跳过（IIFE 自执行，无 init 概念）')
        return
    has_init = bool(re.search(r'function\s+init\s*\(', content))
    if has_init:
        result.ok('R2', 'init 函数已定义')
    else:
        # 桌面端可能用 doLogin 作为入口
        if is_desktop_file(content) and 'doLogin' in content:
            result.ok('R2', '桌面端使用 doLogin 作为入口（可接受）')
        else:
            result.warn('R2', '未检测到 init 函数定义')

def check_r3_init_called(content, result, is_template, is_component):
    """R3: init 被调用"""
    # PRD 文档 IIFE 自执行，无 init 概念
    if is_prd_file(content):
        result.ok('R3', 'PRD 文档跳过（IIFE 自执行，无 init 概念）')
        return
    # 检查 init() 是否在代码中被调用（非仅定义）
    init_calls = re.findall(r'(?<!function\s)init\s*\(\s*\)', content)
    if init_calls:
        result.ok('R3', f'init 函数被调用（{len(init_calls)} 次）')
    else:
        if is_desktop_file(content) and 'doLogin' in content:
            result.ok('R3', '桌面端使用 doLogin 作为入口')
        else:
            result.warn('R3', 'init 函数可能未被调用')

def check_r4_prd_has_script(content, result, is_template, is_component):
    """R4: PRD 有 script — PRD 文档必须含 <script> 标签且长度 > 500 字符"""
    if not is_prd_file(content):
        result.ok('R4', '非 PRD 文件跳过')
        return
    script_tags = re.findall(r'<script[^>]*>(.*?)</script>', content, re.DOTALL)
    total_script_len = sum(len(s) for s in script_tags)
    if script_tags and total_script_len > 500:
        result.ok('R4', f'PRD 含 {len(script_tags)} 个 script 标签，总长度 {total_script_len} 字符')
    else:
        result.fail('R4', f'PRD script 内容不足（{total_script_len} 字符），需 > 500 字符')

def check_r5_default_page_visible(content, result, is_template, is_component):
    """R5: 默认页面可见 — 至少有一个 .page 或 .prd-section 带 active 类"""
    if is_template:
        result.ok('R5', '模板文件跳过')
        return
    has_active_page = bool(re.search(r'class="[^"]*page[^"]*active', content)) or \
                      bool(re.search(r'class="[^"]*active[^"]*page', content)) or \
                      bool(re.search(r'class="[^"]*tab-content[^"]*active', content))
    if has_active_page:
        result.ok('R5', '检测到默认显示的页面（含 active 类）')
    else:
        result.fail('R5', '未检测到带 active 类的默认页面')

# --- PRD 专项检查 ---

def check_prd_simple_sections(content, result, is_template, is_component):
    """简易版 PRD 核心章节校验 — 详细版专属铁律（附录/知识库/变更记录/文档信息表等）按设计省略"""
    if not is_prd_file(content):
        result.ok('PRD-简易章节', '非 PRD 文件跳过')
        return
    required = ['home', 'overview', 'feature-plan', 'architecture', 'roles', 'data-structure', 'testing']
    missing = [rid for rid in required
               if f'id="{rid}"' not in content and f"id='{rid}'" not in content]
    if missing:
        result.fail('PRD-简易章节', f'简易版 PRD 缺少核心章节: {", ".join(missing)}')
    else:
        result.ok('PRD-简易章节', '核心章节（首页/概述/功能规划/架构/角色/数据结构/测试）齐全')
    # 核心业务模块与功能详细设计为简易版主干（注入说明-PRD-simple.md 强制），但不强制单一固定 id，
    # 核心业务模块按实体分节（如 #order-module），功能详细设计固定 #feature-detail，二选一缺失即告警
    if "id=\"feature-detail\"" not in content and "id='feature-detail'" not in content:
        result.fail('PRD-简易章节', '简易版 PRD 缺少「功能详细设计」章节（#feature-detail）')
    else:
        result.ok('PRD-功能详细设计', '#feature-detail 存在')


def _extract_css_selectors(html):
    """提取 <style> 内 CSS 选择器集合（忽略 @keyframes 内部与注释，避免把 0%/50% 误当选择器）"""
    m = re.search(r'<style[^>]*>(.*?)</style>', html, re.S)
    if not m:
        return set()
    css = m.group(1)
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    css = re.sub(r'@keyframes[^{]*\{.*?\}', '', css, flags=re.S)
    sels = set()
    for part in css.split('}'):
        if '{' in part:
            sel = part.split('{', 1)[0].strip()
            if sel:
                sels.add(sel)
    return sels


def _is_allowed_css_removal(sel):
    """判断被删选择器是否属于『允许删』范畴（仅 chat / search / header-ai / 聊天动画）"""
    s = sel.lower()
    if '%' in s:
        return True
    allowed = ('chat', 'search', 'header-ai', 'robot', 'msg', 'typing')
    return any(k in s for k in allowed)


def check_simple_template_style_parity(content, result, is_template, is_component):
    """P34: 简易版 PRD 模板样式铁律 —— 其 CSS 必须是详细版 PRD 模板 CSS 的【子集】。
    仅允许删除 chat/search 相关（.chat-* / .header-search* / .search-* / .header-ai-* / 聊天动画 keyframes）。
    任何共用样式（侧栏/导航/内容区/表格/卡片/章节/主题色）被删即判失败，防止『砍样式』回归。"""
    if not is_template:
        return
    if 'PM-AGENT-PRD' not in content:
        return  # 仅对简易版 PRD 模板生效
    detailed_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'templates', 'prd-template.html')
    if not os.path.exists(detailed_path):
        result.ok('P34', '详细版模板不存在，跳过样式一致性校验')
        return
    try:
        det_content = open(detailed_path, encoding='utf-8').read()
    except Exception:
        result.ok('P34', '详细版模板读取失败，跳过')
        return
    det_sels = _extract_css_selectors(det_content)
    sim_sels = _extract_css_selectors(content)
    removed = det_sels - sim_sels  # 详细版有、简易版被删的
    forbidden = [s for s in removed if not _is_allowed_css_removal(s)]
    if forbidden:
        result.fail('P34', f'简易版砍掉了共用样式（应仅删 chat/search 模块）: {", ".join(sorted(forbidden)[:15])}')
    else:
        result.ok('P34', '简易版 CSS ⊆ 详细版 CSS（仅含 chat/search 删除，共用样式完整保留）')


def check_prd_three_layer(content, result, is_template, is_component):
    """PRD 三层结构完整性 — 检测决策层/方案层/实现层/附录"""
    if not is_prd_file(content):
        result.ok('PRD-三层', '非 PRD 文件跳过')
        return
    has_decision = '决策层' in content or 'decision' in content.lower()
    has_solution = '方案层' in content or 'solution' in content.lower()
    has_impl = '实现层' in content or 'implementation' in content.lower() or '实现' in content
    has_appendix = '附录' in content or 'changelog' in content.lower() or '变更记录' in content

    missing = []
    if not has_decision:
        missing.append('决策层')
    if not has_solution:
        missing.append('方案层')
    if not has_impl:
        missing.append('实现层')
    # 简易版 PRD 按设计排除附录（注入说明-PRD-simple.md），不强制要求
    if not is_prd_simple(content) and not has_appendix:
        missing.append('附录')

    if not missing:
        result.ok('PRD-三层', '三层结构完整' + ('' if is_prd_simple(content) else '+附录'))
    else:
        result.fail('PRD-三层', f'PRD 三层结构不完整，缺少: {", ".join(missing)}')

def check_prd_stat_cards(content, result, is_template, is_component):
    """PRD 统计卡片数据非空"""
    if not is_prd_file(content):
        result.ok('PRD-统计卡片', '非 PRD 文件跳过')
        return
    # 检查是否有统计卡片且数据非空（非"Agent 填充"占位）
    stat_sections = re.findall(r'(?:stat-card|统计|KPI|dashboard-card).*?(?=</div>|</section>)', content, re.DOTALL | re.IGNORECASE)
    if not stat_sections:
        result.ok('PRD-统计卡片', '无统计卡片区域')
        return
    # 检查是否有"Agent 填充"占位（说明数据未填充）
    placeholder_count = content.count('Agent 填充')
    if placeholder_count > 10:
        result.warn('PRD-统计卡片', f'检测到 {placeholder_count} 处 "Agent 填充" 占位，数据可能未完全填充')
    else:
        result.ok('PRD-统计卡片', '统计卡片区域存在')

def check_prd_biz_flow(content, result, is_template, is_component):
    """PRD biz-flow / biz-swimlane 存在性"""
    if not is_prd_file(content):
        result.ok('PRD-流程图', '非 PRD 文件跳过')
        return
    has_biz_flow = 'biz-flow' in content or 'biz-panorama' in content or 'biz-row' in content
    has_swimlane = 'biz-swimlane' in content or 'swimlane' in content.lower() or '泳道' in content
    has_mermaid = 'mermaid' in content.lower()
    if has_biz_flow or has_swimlane or has_mermaid:
        result.ok('PRD-流程图', '检测到业务流程图/泳道图组件')
    else:
        result.warn('PRD-流程图', '未检测到 biz-flow / biz-swimlane / mermaid 流程图组件')

def check_prd_knowledge_base(content, result, is_template, is_component):
    """PRD knowledgeBase ≥ 10 条"""
    if not is_prd_file(content):
        result.ok('PRD-知识库', '非 PRD 文件跳过')
        return
    if is_template:
        result.ok('PRD-知识库', '模板文件跳过（占位内容）')
        return
    # 简易版 PRD 按设计不产出 knowledgeBase（无搜索/智能助手），豁免
    if is_prd_simple(content):
        result.ok('PRD-知识库', '简易版 PRD 无知识库（无搜索/智能助手，按设计省略）')
        return
    # 统计 knowledgeBase 条目数
    kb_items = re.findall(r'(?:knowledgeBase|knowledge_base|kbItem|kb-item)\s*[:=]\s*\{', content)
    # 也检查知识库数组的项数（贪婪匹配到最后一个 ]）
    kb_array_match = re.search(r'(?:knowledgeBase|knowledgeItems)\s*[:=]\s*\[(.*)\]', content, re.DOTALL)
    if kb_array_match:
        kb_count = kb_array_match.group(1).count('{')
    else:
        kb_count = len(kb_items)
    # 也检查 findAnswer 函数中的知识条目
    qa_items = re.findall(r'(?:question|q)\s*:\s*["\']([^"\']+)["\']', content)

    total_kb = max(kb_count, len(qa_items))
    if total_kb >= 10:
        result.ok('PRD-知识库', f'知识库条目 ≥ 10（检测到 {total_kb} 条）')
    elif total_kb >= 8:
        result.warn('PRD-知识库', f'知识库条目不足（检测到 {total_kb} 条，需 ≥ 10）')
    else:
        result.fail('PRD-知识库', f'知识库条目严重不足（检测到 {total_kb} 条，需 ≥ 10）')

def check_prd_changelog(content, result, is_template, is_component):
    """PRD 变更记录完整性"""
    if not is_prd_file(content):
        result.ok('PRD-变更记录', '非 PRD 文件跳过')
        return
    # 简易版 PRD 按设计排除附录/变更记录，豁免
    if is_prd_simple(content):
        result.ok('PRD-变更记录', '简易版 PRD 无变更记录（附录整体省略，按设计豁免）')
        return
    has_changelog_section = 'changelog' in content.lower() or '变更记录' in content
    if has_changelog_section:
        result.ok('PRD-变更记录', '变更记录章节存在')
    else:
        result.fail('PRD-变更记录', '缺少变更记录章节')

def check_prd_template_residue(content, result, is_template, is_component):
    """PRD 模板示例残留检查 — 拦截"注入失败静默假成功"

    根因（实战，M93 之后）：config.json 用了 sections 键而 build 只认 pages 键，
    build 未报错 → 详细版模板默认示例（文档信息表/业务目标/P0/P1/P2 功能表等，
    占位文本为"Agent 填充"）原样输出 → 需求文档全是占位符。检测：产物含
    "Agent 填充"/"Agent:填充"等模板占位文本 = 注入未替换 = fail。
    """
    if is_template:
        result.ok('PRD-模板残留', '模板文件跳过')
        return
    if not is_prd_file(content):
        result.ok('PRD-模板残留', '非 PRD 文件跳过')
        return
    # 模板占位文本（详细版示例表格中的 "Agent 填充"）
    hits = re.findall(r'Agent\s*[：:]?\s*填充', content)
    if hits:
        result.fail('PRD-模板残留', f'检测到 {len(hits)} 处模板占位文本"Agent 填充"（sections.html 未注入，模板示例残留），禁止交付')
    else:
        result.ok('PRD-模板残留', '无模板示例残留（章节已注入）')

def check_prd_nav_class(content, result, is_template, is_component):
    """P13: PRD 导航类名一致性 — CSS/HTML/JS 三处导航类名必须一致"""
    if not is_prd_file(content):
        result.ok('PRD-导航类名', '非 PRD 文件跳过')
        return
    # 检测 CSS 中定义的导航项类名
    css_sidebar = '.sidebar-item' in content
    css_nav = '.nav-item' in content
    # 检测 HTML 中使用的导航项类名
    html_sidebar = 'class="sidebar-item' in content or "class='sidebar-item" in content
    html_nav = 'class="nav-item' in content or "class='nav-item" in content
    # 检测 JS 中引用的导航项类名
    js_sidebar = "querySelectorAll('.sidebar-item')" in content or "querySelector('.sidebar-item'" in content
    js_nav = "querySelectorAll('.nav-item')" in content or "querySelector('.nav-item'" in content

    issues = []
    # CSS 与 HTML 不一致
    if css_sidebar and html_nav and not html_sidebar:
        issues.append('CSS定义.sidebar-item但HTML用.nav-item')
    if css_nav and html_sidebar and not html_nav:
        issues.append('CSS定义.nav-item但HTML用.sidebar-item')
    # CSS 与 JS 不一致
    if css_sidebar and js_nav and not js_sidebar:
        issues.append('CSS定义.sidebar-item但JS用.nav-item')
    if css_nav and js_sidebar and not js_nav:
        issues.append('CSS定义.nav-item但JS用.sidebar-item')
    # HTML 与 JS 不一致
    if html_sidebar and js_nav and not js_sidebar:
        issues.append('HTML用.sidebar-item但JS用.nav-item')
    if html_nav and js_sidebar and not js_nav:
        issues.append('HTML用.nav-item但JS用.sidebar-item')
    # JS 用 a[href] 但 HTML 无 href
    if 'a[href' in content and js_nav:
        # 检查 nav-item 是否有 href
        nav_items = re.findall(r'class="nav-item[^"]*"[^>]*', content)
        missing_href = [ni for ni in nav_items if 'href=' not in ni]
        if missing_href and 'a[href' in content:
            issues.append(f'JS用a[href]选择器但{len(missing_href)}个nav-item缺href属性')

    if issues:
        result.fail('PRD-导航类名', '导航类名不一致: ' + '; '.join(issues))
    else:
        result.ok('PRD-导航类名', 'CSS/HTML/JS 导航类名一致')

def check_prd_currency_symbol(content, result, is_template, is_component):
    """P14: PRD 货币符号检查 — 禁止美元符号 $ 作为货币使用，必须用 ¥"""
    if not is_prd_file(content):
        result.ok('PRD-货币符号', '非 PRD 文件跳过')
        return
    if is_template:
        result.ok('PRD-货币符号', '模板文件跳过')
        return
    # 排除 JS 模板字符串 ${...} 和 CSS 变量 var(--...)
    # 匹配 $ 后跟数字（可能有空格），或数字后跟 $，且不在 ${ 模式内
    # 策略：先移除所有 ${...} 模板字符串，再搜索剩余 $ 符号
    cleaned = re.sub(r'\$\{[^}]*\}', '', content)  # 移除 ${variable}
    # 搜索剩余内容中的 $ 符号（排除 $$ 这种数学公式场景）
    # 货币用途：$ 数字、数字 $、$数字
    currency_matches = re.findall(r'\$\s*[\d,]+\.?\d*|[\d,]+\.?\d*\s*\$(?!\$)', cleaned)
    # 也检测单独的 $ 后跟"元"或"价格"等关键词
    if not currency_matches:
        currency_matches = re.findall(r'\$(?:\s*(?:元|价格|金额|费用|成本|收入|支出|佣金))', cleaned)
    if currency_matches:
        result.fail('PRD-货币符号', f'检测到 {len(currency_matches)} 处美元符号 $ 作为货币使用（应改为 ¥）: {currency_matches[:5]}')
    else:
        # P14扩展：检测美元符号形状的SVG图标（特征path：中间竖线+S形弯曲）
        dollar_svg_patterns = [
            r'M12\s+1v22M17\s+5H9',  # 成本与ROI的$图标
            r'M12\s+1v22M5\s+8h11',   # 提现模块的$图标
        ]
        svg_matches = []
        for pattern in dollar_svg_patterns:
            found = re.findall(pattern, content)
            if found:
                svg_matches.extend(found)
        if svg_matches:
            result.fail('PRD-货币符号', f'检测到 {len(svg_matches)} 处美元符号形状的SVG图标（应用计算器/钱包等替代图标）')
        else:
            result.ok('PRD-货币符号', '未检测到货币用途的美元符号 $ 或 $ 形状图标')

def check_prd_prototype_link(content, result, is_template, is_component):
    """P15: PRD 原型链接检查 — 打开原型按钮必须使用相对路径，禁止 javascript:void(0)"""
    if not is_prd_file(content):
        result.ok('PRD-原型链接', '非 PRD 文件跳过')
        return
    if is_template:
        result.ok('PRD-原型链接', '模板文件跳过')
        return
    # 检测是否包含"原型与UI"或"打开原型"相关内容
    if '打开原型' not in content and 'prototypes' not in content.lower():
        result.ok('PRD-原型链接', '无原型入口区域，跳过')
        return
    # 提取原型区域的链接
    # 查找包含"打开原型"文本的 <a> 标签
    import re as _re
    proto_links = _re.findall(r'<a[^>]*href="([^"]*)"[^>]*>[^<]*<i[^>]*fa-external-link[^>]*>[^<]*打开原型</a>', content)
    if not proto_links:
        # 更宽松的匹配
        proto_links = _re.findall(r'<a[^>]*href="([^"]*?)"[^>]*>.*?打开原型.*?</a>', content, _re.DOTALL)
    if not proto_links:
        result.ok('PRD-原型链接', '未检测到原型入口链接')
        return
    bad_links = []
    for link in proto_links:
        if link in ('javascript:void(0)', '#', '') or link.startswith('javascript:'):
            bad_links.append(link)
    if bad_links:
        result.fail('PRD-原型链接', f'检测到 {len(bad_links)} 个无效原型链接（javascript:void(0)/#），必须改为相对路径如 "用户端原型.html"')
    else:
        result.ok('PRD-原型链接', f'原型链接均为有效相对路径（{len(proto_links)} 个）')


def check_prd_api_param_residue(content, result, is_template, is_component):
    """P16: PRD API 参数复制残留检查 — 接口参数必须与接口功能匹配"""
    if not is_prd_file(content):
        result.ok('PRD-API参数', '非 PRD 文件跳过')
        return
    if is_template:
        result.ok('PRD-API参数', '模板文件跳过')
        return
    if 'api-design' not in content and '接口设计' not in content:
        result.ok('PRD-API参数', '无接口设计章节，跳过')
        return
    import re as _re
    # 检测接口区块中是否有明显的参数不匹配
    # 启发式：搜索类接口不应包含 keyword（搜索关键词），详情类接口不应包含 categoryId
    issues = []
    # 查找"获取详情"类接口但包含搜索参数
    detail_sections = _re.findall(r'(?:获取|查看|查询).*?详情.*?</div>\s*</div>', content, _re.DOTALL)
    for sec in detail_sections:
        if 'keyword' in sec.lower() and '搜索' not in sec:
            issues.append('详情接口包含搜索参数 keyword')
    # 查找接口参数表中重复出现的完全相同参数块（可能复制粘贴）
    param_blocks = _re.findall(r'<td>(\w+)</td><td>(\w+)</td><td>(是|否)</td>', content)
    if len(param_blocks) > 0:
        # 统计相同参数出现次数（排除公共参数）
        from collections import Counter
        common_params = {'page', 'pageSize', 'token', 'timestamp', 'id', 'pageNum'}
        param_names = [b[0] for b in param_blocks if b[0] not in common_params]
        dup_counts = Counter(param_names)
        # 单个参数出现超过4次可能为复制残留
        for p, c in dup_counts.items():
            if c > 4:
                issues.append(f'参数 {p} 出现 {c} 次，可能为复制残留')
    if issues:
        result.warn('PRD-API参数', f'检测到可能的参数复制残留：{"; ".join(issues[:3])}')
    else:
        result.ok('PRD-API参数', '接口参数未发现明显复制残留')

def check_prd_func_param_relevance(content, result, is_template, is_component):
    """P17: PRD 功能设计参数表字段相关性检查"""
    if not is_prd_file(content):
        result.ok('PRD-功能参数', '非 PRD 文件跳过')
        return
    if is_template:
        result.ok('PRD-功能参数', '模板文件跳过')
        return
    if '功能设计' not in content and 'function-design' not in content:
        result.ok('PRD-功能参数', '无功能设计章节，跳过')
        return
    # 启发式检查：功能参数表中是否有明显不相关的字段
    # 如"发布"功能包含"审核状态"、"拒绝原因"等审核流程字段
    import re as _re
    publish_sections = _re.findall(r'(?:发布|新增|创建).*?(?:功能|参数).*?</table>', content, _re.DOTALL | _re.IGNORECASE)
    issues = []
    for sec in publish_sections:
        if '审核状态' in sec or '拒绝原因' in sec:
            issues.append('发布/新增功能参数表包含审核流程字段（审核状态/拒绝原因）')
    if issues:
        result.warn('PRD-功能参数', f'参数表可能混入无关字段：{"; ".join(issues[:2])}')
    else:
        result.ok('PRD-功能参数', '功能参数表字段相关性正常')

def check_prd_review_consistency(content, result, is_template, is_component):
    """P18: PRD 评审意见与实际内容一致性检查"""
    if not is_prd_file(content):
        result.ok('PRD-评审一致', '非 PRD 文件跳过')
        return
    if is_template:
        result.ok('PRD-评审一致', '模板文件跳过')
        return
    import re as _re
    # 查找评审意见中的"改为X"模式
    review_changes = _re.findall(r'改为\s*(\d+)\s*(小时|天|分钟|%)', content)
    if not review_changes:
        result.ok('PRD-评审一致', '无评审修改标注，跳过')
        return
    issues = []
    for val, unit in review_changes:
        target = f'{val}{unit}'
        # 检查文档中是否还有其他数值与"改为"的目标不一致
        # 查找相同上下文中的其他数值
        pattern = rf'(\d+)\s*{unit}'
        all_vals = _re.findall(pattern, content)
        unique_vals = set(all_vals)
        if len(unique_vals) > 2:  # 允许一些波动
            issues.append(f'{unit} 在文档中有多个不同取值: {sorted(unique_vals)}')
    if issues:
        result.warn('PRD-评审一致', f'关键数值可能不一致：{"; ".join(issues[:2])}')
    else:
        result.ok('PRD-评审一致', '评审意见与实际内容一致')

def check_prd_color_scheme(content, result, is_template, is_component):
    """P19: PRD 配色方案与契约一致性检查"""
    if not is_prd_file(content):
        result.ok('PRD-配色方案', '非 PRD 文件跳过')
        return
    if is_template:
        result.ok('PRD-配色方案', '模板文件跳过')
        return
    import re as _re
    # 检查 --prd-primary 是否仍为模板默认色 #2563eb
    primary_match = _re.search(r'--prd-primary:\s*(#[0-9a-fA-F]{6})', content)
    if primary_match:
        color = primary_match.group(1).lower()
        if color == '#2563eb':
            result.fail('PRD-配色方案', f'--prd-primary 仍为模板默认色 #2563eb，必须替换为项目契约约定的主色')
        else:
            result.ok('PRD-配色方案', f'--prd-primary = {color}（已替换为项目主色）')
    else:
        result.ok('PRD-配色方案', '未找到 --prd-primary 定义，跳过')

def check_prd_page_count_consistency(content, result, is_template, is_component):
    """P20: PRD 页面数量一致性检查"""
    if not is_prd_file(content):
        result.ok('PRD-页面数量', '非 PRD 文件跳过')
        return
    if is_template:
        result.ok('PRD-页面数量', '模板文件跳过')
        return
    import re as _re
    # 查找所有"X页"的数字
    page_counts = _re.findall(r'(\d+)\s*页', content)
    if len(page_counts) < 2:
        result.ok('PRD-页面数量', '页面数量引用不足2处，跳过一致性检查')
        return
    # 分端统计
    user_counts = []
    admin_counts = []
    for i, match in enumerate(_re.finditer(r'(用户端|管理端|平台端|客户端).{0,20}?(\d+)\s*页', content)):
        if '用户' in match.group(1) or '客户' in match.group(1):
            user_counts.append(int(match.group(2)))
        else:
            admin_counts.append(int(match.group(2)))
    issues = []
    if len(user_counts) >= 2 and len(set(user_counts)) > 1:
        issues.append(f'用户端页面数量不一致: {user_counts}')
    if len(admin_counts) >= 2 and len(set(admin_counts)) > 1:
        issues.append(f'管理端页面数量不一致: {admin_counts}')
    if issues:
        result.warn('PRD-页面数量', f'页面数量可能不一致：{"; ".join(issues)}')
    else:
        result.ok('PRD-页面数量', f'页面数量一致（引用{len(page_counts)}处）')

def check_prd_workload_explanation(content, result, is_template, is_component):
    """P21: PRD 工作量统计说明检查"""
    if not is_prd_file(content):
        result.ok('PRD-工作量', '非 PRD 文件跳过')
        return
    if is_template:
        result.ok('PRD-工作量', '模板文件跳过')
        return
    if '工作量' not in content and '人天' not in content and '工时' not in content:
        result.ok('PRD-工作量', '无工作量统计，跳过')
        return
    # 检查是否有"计算说明"或"备注"列
    has_explanation = any(kw in content for kw in ['计算说明', '估算依据', '备注', '说明列', '计算依据'])
    if has_explanation:
        result.ok('PRD-工作量', '工作量统计包含计算说明')
    else:
        result.warn('PRD-工作量', '工作量统计缺少计算说明列，建议添加"计算说明"或"备注"列')

def check_prd_data_structure_coverage(content, result, is_template, is_component):
    """P22: PRD 数据结构完整性检查"""
    if not is_prd_file(content):
        result.ok('PRD-数据结构', '非 PRD 文件跳过')
        return
    if is_template:
        result.ok('PRD-数据结构', '模板文件跳过')
        return
    if '数据结构' not in content and 'data-structure' not in content and '数据库设计' not in content:
        result.ok('PRD-数据结构', '无数据结构章节，跳过')
        return
    import re as _re
    # 统计数据表数量
    table_count = len(_re.findall(r'<h3[^>]*>.*?(?:表|Table).*?</h3>', content))
    # 检查是否有基础字段
    has_base_fields = all(field in content for field in ['created_at', 'updated_at']) or \
                      all(field in content for field in ['create_time', 'update_time']) or \
                      all(field in content for field in ['创建时间', '更新时间'])
    if table_count < 5:
        result.warn('PRD-数据结构', f'数据表数量较少（{table_count}张），建议检查是否覆盖所有功能模块')
    elif not has_base_fields:
        result.warn('PRD-数据结构', '数据表可能缺少基础字段（创建时间/更新时间）')
    else:
        result.ok('PRD-数据结构', f'数据结构覆盖{table_count}张表，基础字段完整')

def check_prd_doc_info_table(content, result, is_template, is_component):
    """P23: PRD 文档信息表检查"""
    if not is_prd_file(content):
        result.ok('PRD-文档信息', '非 PRD 文件跳过')
        return
    if is_template:
        result.ok('PRD-文档信息', '模板文件跳过')
        return
    # 简易版 PRD 按设计排除文档信息表（注入说明-PRD-simple.md「被排除的章节」），豁免
    if is_prd_simple(content):
        result.ok('PRD-文档信息', '简易版 PRD 无文档信息表（按设计省略）')
        return
    # 检查是否包含标准文档信息表的关键字段
    required_fields = ['文档名称', '文档版本', '文档状态', '编写人', '创建日期']
    found = [f for f in required_fields if f in content]
    missing = [f for f in required_fields if f not in content]
    if len(found) >= 4:
        result.ok('PRD-文档信息', f'文档信息表完整（{len(found)}/{len(required_fields)} 字段）')
    elif len(found) >= 2:
        result.warn('PRD-文档信息', f'文档信息表不完整，缺少: {missing}')
    else:
        result.fail('PRD-文档信息', '缺少标准文档信息表（文档名称/版本/状态/编写人/创建日期）')

def check_prd_interaction_coverage(content, result, is_template, is_component):
    """P24: PRD 页面交互设计完整性检查"""
    if not is_prd_file(content):
        result.ok('PRD-交互设计', '非 PRD 文件跳过')
        return
    if is_template:
        result.ok('PRD-交互设计', '模板文件跳过')
        return
    if '交互' not in content and 'interaction' not in content.lower():
        result.ok('PRD-交互设计', '无交互设计章节，跳过')
        return
    # 检查是否覆盖管理端
    has_admin = '管理端' in content or '后台' in content
    has_user = '用户端' in content or '前端' in content
    if has_user and not has_admin:
        result.warn('PRD-交互设计', '交互设计可能只覆盖用户端，缺少管理端交互说明')
    elif has_user and has_admin:
        result.ok('PRD-交互设计', '交互设计覆盖用户端和管理端')
    else:
        result.ok('PRD-交互设计', '交互设计章节存在')

def check_prd_module_list(content, result, is_template, is_component):
    """P25: PRD 功能模块清单检查"""
    if not is_prd_file(content):
        result.ok('PRD-模块清单', '非 PRD 文件跳过')
        return
    if is_template:
        result.ok('PRD-模块清单', '模板文件跳过')
        return
    # 简易版用 feature-plan（功能规划表）替代独立模块清单，豁免
    if is_prd_simple(content):
        result.ok('PRD-模块清单', '简易版 PRD 用功能规划表替代（按设计省略独立模块清单）')
        return
    if '功能模块清单' in content or '功能模块列表' in content:
        result.ok('PRD-模块清单', '功能模块清单章节存在')
    else:
        result.warn('PRD-模块清单', '缺少"功能模块清单"章节，建议在决策层或方案层中添加')

def check_prd_prototype_page_list(content, result, is_template, is_component):
    """P26: PRD 原型页面清单检查"""
    if not is_prd_file(content):
        result.ok('PRD-原型清单', '非 PRD 文件跳过')
        return
    if is_template:
        result.ok('PRD-原型清单', '模板文件跳过')
        return
    if '打开原型' not in content and 'prototypes' not in content.lower():
        result.ok('PRD-原型清单', '无原型入口区域，跳过')
        return
    if '原型页面清单' in content or '页面清单' in content or '原型预览' in content:
        result.ok('PRD-原型清单', '原型页面清单存在')
    else:
        result.warn('PRD-原型清单', '原型与UI章节缺少原型页面清单，建议添加分端页面列表')



def check_prd_biz_panorama_misuse(content, result, is_template, is_component):
    """P27: PRD 架构图 biz-panorama 滥用检查 — biz-panorama 不得与内部 grid 混用"""
    if not is_prd_file(content):
        result.ok('PRD-架构布局', '非 PRD 文件跳过')
        return
    if is_template:
        result.ok('PRD-架构布局', '模板文件跳过')
        return
    import re as _re
    # 检测同时包含 biz-panorama 和 grid-cols-2 的容器
    # 查找 class 中同时包含 biz-panorama 的元素，检查其内部是否有 grid-cols-2
    panorama_matches = list(_re.finditer(r'class="[^"]*biz-panorama[^"]*"', content))
    if not panorama_matches:
        result.ok('PRD-架构布局', '未使用 biz-panorama 类，跳过')
        return
    issues = []
    for m in panorama_matches:
        # 查找该元素之后500字符内是否有 grid-cols-2
        after = content[m.end():m.end()+500]
        if 'grid-cols-2' in after or 'grid-cols-3' in after:
            issues.append(f'位置 {m.start()}: biz-panorama 内部使用了 Tailwind grid，会导致布局压缩')
    if issues:
        result.fail('PRD-架构布局', f'检测到 {len(issues)} 处 biz-panorama 与内部 grid 混用，必须移除 biz-panorama 类（仅保留 biz-flow）')
    else:
        result.ok('PRD-架构布局', f'biz-panorama 使用正常（{len(panorama_matches)} 处）')


def check_prd_hardcoded_blue(content, result, is_template, is_component):
    """P28: PRD CSS 硬编码蓝色检查 — 交互元素禁止硬编码 #2563eb"""
    if not is_prd_file(content):
        result.ok('PRD-硬编码颜色', '非 PRD 文件跳过')
        return
    import re as _re
    # 查找 :root 变量定义区域，豁免变量定义行
    root_match = _re.search(r':root\s*\{[^}]*\}', content)
    root_end = root_match.end() if root_match else 0

    # 查找 .biz-node.blue 等多色变体中的蓝色（豁免）
    # 豁免模式：.xxx.blue / .xxx.light-blue / .xxx.dark-blue / .xxx.sky 中的蓝色
    variant_pattern = r'\.(?:biz-node|sw-node|biz-ladder-card|biz-panorama-card|biz-tl-dot)\.(?:blue|light-blue|dark-blue|sky)\s*\{[^}]*\}'
    variant_matches = list(_re.finditer(variant_pattern, content))
    exempt_ranges = [(m.start(), m.end()) for m in variant_matches]
    # 也豁免 .biz-tl-item.current（蓝色表示"当前"状态）
    current_pattern = r'\.biz-tl-item\.current::after\s*\{[^}]*\}'
    for m in _re.finditer(current_pattern, content):
        exempt_ranges.append((m.start(), m.end()))

    def is_exempt(pos):
        if pos < root_end:
            return True
        for start, end in exempt_ranges:
            if start <= pos < end:
                return True
        return False

    # 检测硬编码 #2563eb
    issues = []
    for m in _re.finditer(r'#2563eb', content):
        if not is_exempt(m.start()):
            # 获取上下文
            line_start = content.rfind('\n', 0, m.start()) + 1
            line_end = content.find('\n', m.end())
            if line_end == -1:
                line_end = len(content)
            context = content[line_start:line_end].strip()[:80]
            issues.append(f'硬编码 #2563eb: {context}')

    # 检测硬编码 rgba(37,99,235 或 rgba(37, 99, 235
    for m in _re.finditer(r'rgba\(\s*37\s*,\s*99\s*,\s*235', content):
        if not is_exempt(m.start()):
            line_start = content.rfind('\n', 0, m.start()) + 1
            line_end = content.find('\n', m.end())
            if line_end == -1:
                line_end = len(content)
            context = content[line_start:line_end].strip()[:80]
            issues.append(f'硬编码 rgba(37,99,235): {context}')

    if issues:
        detail_str = '; '.join(issues[:5])
        result.fail('PRD-硬编码颜色', f'检测到 {len(issues)} 处硬编码蓝色（应使用 var(--prd-primary)）: {detail_str}')
    else:
        result.ok('PRD-硬编码颜色', '无硬编码蓝色，CSS 变量使用正常')




def check_accent_rgb_consistency(content, result, is_template, is_component):
    """M42: --accent-rgb 与 --accent 一致性检查"""
    import re as _re
    # 只检查桌面端/移动端原型（含 --accent 变量的文件）
    accent_match = _re.search(r'--accent\s*:\s*(#[0-9a-fA-F]{6})', content)
    rgb_match = _re.search(r'--accent-rgb\s*:\s*([0-9,\s]+)', content)
    if not accent_match or not rgb_match:
        return  # 无 accent 变量，跳过

    accent_hex = accent_match.group(1)
    current_rgb = rgb_match.group(1).strip().replace(' ', '')

    # 如果是模板文件，跳过（模板使用默认值，由 build 脚本替换）
    if is_template:
        result.ok('M42-accent-rgb', '模板文件跳过（由 build 脚本替换）')
        return

    # 计算正确的 RGB
    r = int(accent_hex[1:3], 16)
    g = int(accent_hex[3:5], 16)
    b = int(accent_hex[5:7], 16)
    correct_rgb = f"{r},{g},{b}"

    if current_rgb == '92,108,240':
        result.fail('M42-accent-rgb', f'--accent-rgb 仍为默认蓝紫色 92,108,240，应替换为 {correct_rgb}（匹配 --accent {accent_hex}）')
    elif current_rgb != correct_rgb:
        result.fail('M42-accent-rgb', f'--accent-rgb ({current_rgb}) 与 --accent ({accent_hex} → RGB {correct_rgb}) 不匹配')
    else:
        result.ok('M42-accent-rgb', f'--accent-rgb ({correct_rgb}) 与 --accent ({accent_hex}) 一致')

    # 检查硬编码蓝紫色
    hardcoded_issues = []
    for color in ['#8b5cf6', '#c7d2fe', '#a5b4fc']:
        if color in content and not is_template:
            count = content.count(color)
            hardcoded_issues.append(f'{color}({count}处)')

    if hardcoded_issues:
        result.fail('M42-硬编码紫色', f'检测到硬编码蓝紫色: {"; ".join(hardcoded_issues)}，应使用 CSS 变量')
    else:
        result.ok('M42-硬编码紫色', '无硬编码蓝紫色')
# --- 枚举覆盖率检测 ---


def check_chart_bar_visibility(content, result, is_template, is_component):
    """M43: 柱状图 .bar 必须有背景色；禁止 rank-bar 类名复用为整行容器"""
    import re as _re
    if is_template:
        return
    # 1. .bar 缺少 background（柱体透明不可见）
    bar_match = _re.search(r'\.bar\s*\{[^}]*\}', content)
    if bar_match and 'background' not in bar_match.group(0):
        result.fail('M43-柱状图', '.bar 缺少 background 背景色，柱子透明不可见（应加 linear-gradient(180deg,var(--accent),var(--accent-hover))）')
    elif bar_match:
        result.ok('M43-柱状图', '.bar 已定义背景色')
    # 2. rank-bar 类名复用冲突（inline-flex 覆盖 display:inline-block 但 width:90px 残留）
    if 'class="rank-bar" style="display:flex' in content:
        result.fail('M43-类名复用', 'rank-bar 被用作整行 flex 容器（display:flex 覆盖了 90px 宽条定义），应改用专用类 rank-row')
    else:
        result.ok('M43-类名复用', '无 rank-bar 类名复用冲突')


def check_chart_height_pixel(content, result, is_template, is_component):
    """M44: 柱状图 .bar 高度禁止用百分比（flex-auto 父容器无法解析 %，柱子塌缩为等高）"""
    if is_template:
        return
    # 检测柱状图渲染代码中用百分比高度（如 style="height:' + pct + '%"）
    if "height:' + pct + '%" in content or 'height:" + pct + "%' in content:
        result.fail('M44-柱高', '柱状图用百分比高度，父容器 .bar-col 高度 auto 无法解析 %，柱子会等高塌缩。应改用像素高度：var chartH = 140; Math.round(d.value / maxV * chartH) + "px"')
    elif "Math.round(d.value / maxV * chartH)" in content:
        result.ok('M44-柱高', '柱状图使用像素高度计算，正常')
    else:
        result.ok('M44-柱高', '未检测到柱状图渲染代码或已使用像素高度')


def check_product_manage_rules(content, result, is_template, is_component):
    """M45: 商品管理规范 — 商品列表禁审核按钮；驳回必填理由；商品审核在商品列表前"""
    if is_template:
        return
    issues = []
    # 1. 商品列表禁止出现审核按钮（审核功能只在商品审核页）
    if "onclick=\"reviewProduct(" in content:
        issues.append('商品列表存在审核按钮（reviewProduct），审核功能应只在商品审核页')
    # 2. 驳回必须填理由：rejectProduct 必须弹窗且 confirmReject 校验空值
    if "function rejectProduct" in content:
        if "rejectReasonInput" not in content or "confirmReject" not in content:
            issues.append('rejectProduct 未弹窗填写驳回理由（必须必填理由再驳回）')
    # 3. 菜单顺序：商品审核(data-page=productReview)在商品列表(data-page=products)之前
    nav_i = content.find('data-page="productReview"')
    nav_p = content.find('data-page="products"')
    if nav_i > 0 and nav_p > 0 and nav_i > nav_p:
        issues.append('侧边栏菜单顺序错误：商品审核应在商品列表前面')
    if issues:
        result.fail('M45-商品管理', '; '.join(issues))
    else:
        result.ok('M45-商品管理', '商品管理规范符合（审核页在前/列表无审核按钮/驳回必填理由）')


def check_detail_form_choice(content, result, is_template, is_component):
    """M46: 弹窗 vs 二级页面 — 详情字段多必须用二级页面，禁止 openModal/openDrawer 塞全字段
    v5.31 强化（D44 茶叶商城教训）：详情入口的形态机器强制三连——
    ① openModal('xx详情') 塞全字段 → 拦截（原有）
    ② openDrawer('xx详情') 右侧抽屉塞详情 → 拦截（新增，原来漏检）
    ③ openDetailPage('xxxDetail') 调用 → 必须存在对应 page-xxxDetail 容器
       （.detail-header + .detail-cards + goBackFromDetail），禁止调用空壳页面（新增）
    """
    if is_template:
        return
    import re as _re
    issues = []
    # 1. 详情仍用弹窗展示（openModal('xx详情') 且 body 字段 >8 → 应二级页面）
    detail_modal_idx = content.find("openModal('商品详情'")
    if detail_modal_idx < 0:
        detail_modal_idx = content.find("openModal('订单详情'")
    if detail_modal_idx >= 0:
        window = content[max(0, detail_modal_idx - 8000):detail_modal_idx]
        field_count = window.count("info-item")
        if field_count > 8:
            issues.append('详情仍用弹窗展示（约 ' + str(field_count) + ' 个字段），应改为二级页面（M46）')
    # 2. 详情误用右侧抽屉（openDrawer('xx详情' → 必须 openDetailPage 内容区二级页）
    #    （D44：茶叶商城平台管理端 4 个详情全部误用 openDrawer，用户要求内容区二级页+面包屑）
    drawer_details = _re.findall(r"openDrawer\(\s*['\"]([^'\"]*详情[^'\"]*)['\"]", content)
    for dtitle in drawer_details:
        issues.append('详情入口误用右侧抽屉 openDrawer("' + dtitle[:30] + '...")，必须改为 openDetailPage 内容区二级页（带面包屑 + goBackFromDetail 返回，M46/D44）')
    # 3. openDetailPage 调用的详情页容器必须存在且结构完整（防调用空壳页面）
    #    过滤模板注释示例名（xxxDetail/yyyDetail 等泛化占位，模板注释说明文档不算真实调用）
    detail_calls = _re.findall(r"openDetailPage\(\s*['\"]([a-zA-Z]+Detail)['\"]", content)
    detail_calls = [pg for pg in detail_calls if not _re.match(r'^(xxx|yyy|zzz|aaa|bbb|ccc)\w*', pg)]
    for pg in detail_calls:
        pg_marker = 'id="page-' + pg + '"'
        if pg_marker not in content:
            issues.append('openDetailPage("' + pg + '") 缺少对应详情页容器 ' + pg_marker + '（M46/D44：详情必须真实存在于内容区，而非抽屉）')
        else:
            pg_idx = content.find(pg_marker)
            block = content[pg_idx:pg_idx + 2000]
            if 'detail-header' not in block:
                issues.append('详情页容器 ' + pg + ' 缺少 .detail-header（二级页头，M46/D44）')
            # v5.32 D45：V1/V2/V3 统一范式——标题区必须含 detail-title + detail-sub 副标题结构
            # （茶叶商城教训：V3 模板示例曾是"裸 detail-title + 静态写死字段"的简化版，与舒享到家等
            #  正确实现不一致，导致详情页形态三端不统一；统一范式：detail-title(可内嵌tag) + detail-sub + detail-actions）
            if 'detail-title' not in block:
                issues.append('详情页容器 ' + pg + ' 缺少 .detail-title（二级页标题，M46/D45）')
            if 'detail-sub' not in block:
                issues.append('详情页容器 ' + pg + ' 缺少 .detail-sub 副标题（V1/V2/V3 统一详情页范式，M46/D45：标题区 = detail-title + detail-sub + detail-actions）')
            if 'detail-cards' not in block:
                issues.append('详情页容器 ' + pg + ' 缺少 .detail-cards（详情卡片区，M46/D44）')
            if 'detail-grid' not in block and 'detail-desc' not in block and 'detail-timeline' not in block:
                issues.append('详情页容器 ' + pg + ' 内容区必须含 .detail-grid（kv 注入）/ .detail-desc / .detail-timeline 至少其一（M46/D45）')
            if 'goBackFromDetail' not in block:
                issues.append('详情页容器 ' + pg + ' 返回按钮未绑定 goBackFromDetail()（M46/D44）')
    # 4. 既有二级页面必须含返回按钮
    for pg in ['productDetail', 'orderDetail', 'verifyDetail', 'userDetail', 'merchantDetail']:
        pg_marker = 'id="page-' + pg + '"'
        if pg_marker in content:
            pg_idx = content.find(pg_marker)
            block = content[pg_idx:pg_idx + 1500]
            if 'detail-back' not in block:
                issues.append('二级页面 ' + pg + ' 缺少返回按钮（detail-back）')
            if 'goBackFromDetail' not in block:
                issues.append('二级页面 ' + pg + ' 返回按钮未绑定 goBackFromDetail()')
    if issues:
        result.fail('M46-详情形态', '; '.join(issues))
    else:
        result.ok('M46-详情形态', '详情形态合规（无 drawer/弹窗塞详情，详情页容器完整）')


def check_list_detail_coverage(content, result, is_template, is_component):
    """M47: 列表→详情覆盖 — 需详情列表必须有详情按钮；详情操作后须返回"""
    if is_template:
        return
    # PRD 为文档，无 JS 交互，不适用"列表-详情"原型模式
    if is_prd_file(content):
        result.ok('M47-列表详情', 'PRD 文档豁免（文档无 JS 交互，非列表-详情原型）')
        return
    # V2/V3/V4 现代数据驱动：详情入口/返回的形态与容器由 M46（v5.31 强化）静态强制拦截
    # （openDrawer('xx详情') 塞抽屉 → fail；openDetailPage 调用缺 page-xxxDetail 容器 → fail）；
    # 点击「查看」后必须呈现内容区二级页（.detail-header 可见且 drawer 未开）由 browser-check B19 运行时断言验证
    if is_modern_paradigm(content):
        result.ok('M47-列表详情', 'V2/V3/V4 数据驱动：详情形态静态拦截见 M46（drawer/弹窗塞详情→fail），运行时呈现由 browser-check B19 断言（点查看→.detail-header 出现）')
        return
    # 移动端豁免：手机端用 sub-page 二级页体系，非桌面列表-详情模式
    if 'phone-frame' in content and 'sub-page' in content:
        result.ok('M47-列表详情', '移动端豁免（sub-page 二级页体系，非桌面列表-详情模式）')
        return
    issues = []
    # 1. 需详情的列表必须有详情入口（详情按钮）
    required_details = [
        ('viewUserDetail', '用户列表'),
        ('viewTxnDetail', '交易流水'),
        ('viewSplitDetail', '分账记录'),
        ('viewWithdrawDetail', '提现审核'),
        ('viewReportDetail', '举报列表'),
    ]
    for fn, label in required_details:
        if fn not in content:
            issues.append(label + ' 缺少详情入口（应加详情按钮 + ' + fn + ' 函数）')
    # 2. 详情页操作函数操作后必须返回（goBackFromDetail）
    if 'banUser(id)' in content:
        idx = content.find('function banUser(id)')
        block = content[idx:idx + 200]
        # 列表快捷操作保留，详情操作区用 goBackFromDetail 返回
    # 3. 关联跳转函数存在性（订单号可点击跳转）
    if 'goToOrderDetail' not in content:
        issues.append('缺少 goToOrderDetail 关联跳转函数（交易/分账详情订单号跳转）')
    if issues:
        result.fail('M47-列表详情', '; '.join(issues))
    else:
        result.ok('M47-列表详情', '详情覆盖合规（用户/流水/分账/提现/举报均有详情+关联跳转）')


def check_modal_dual_mode(content, result, is_template, is_component):
    """M48: 弹窗双模式 — 单参 openModal 必须有对应静态弹窗且 body 非空"""
    if is_template:
        return
    issues = []
    import re as _re
    # 1. 单参 openModal('xxx') 调用必须有 xxx-overlay 静态弹窗
    single_calls = _re.findall(r"openModal\([ ]*['\"]([^'\"]+)['\"][ ]*\)", content)
    for name in single_calls:
        if name.endswith('-overlay'):
            continue
        if name in ('modalOverlay',):
            continue
        if 'overlay' in name:
            continue
        if name + '-overlay' not in content:
            issues.append('单参 openModal(' + name + ') 缺少对应静态弹窗 ' + name + '-overlay（M48）')
    # 2. 静态弹窗 modal-body 必须有表单字段（禁空 body）
    overlays = _re.findall(r'id="([\w]+-overlay)"', content)
    for ov in overlays:
        ov_idx = content.find('id="' + ov + '"')
        block = content[ov_idx:ov_idx + 2500]
        if 'modal-body' in block:
            body_idx = block.find('modal-body')
            body_block = block[body_idx:body_idx + 1200]
            # 空 body 判定：无 input/select/textarea/字段内容
            if not _re.search(r'<input|<select|<textarea|class="form-row"', body_block):
                issues.append('静态弹窗 ' + ov + ' 的 modal-body 为空（M48）')
    if issues:
        result.fail('M48-弹窗双模式', '; '.join(issues))
    else:
        result.ok('M48-弹窗双模式', '弹窗双模式合规（单参调用均有静态弹窗且 body 非空）')


def check_modal_form_style(content, result, is_template, is_component):
    """M49: 弹窗表单排版 — form-row 垂直布局、label 样式、行间距"""
    if is_template:
        return
    # PRD 为文档，无 .form-row/.modal-input 弹窗体系，不适用
    if is_prd_file(content):
        result.ok('M49-弹窗表单', 'PRD 文档豁免（文档无弹窗表单样式要求）')
        return
    # 移动端豁免：手机端用 form-group 表单体系，非桌面 modal-input 弹窗
    if 'phone-frame' in content and 'sub-page' in content:
        result.ok('M49-弹窗表单', '移动端豁免（form-group 表单体系，非桌面弹窗表单）')
        return
    # V2/V3 现代数据驱动：表单体系为 .fr-label + .fld（垂直节奏/输入框统一样式），与 V1 的 .form-row>label / .modal-input 命名不同
    if is_modern_paradigm(content):
        v2_issues = []
        if '.form-row{display:grid' in content:
            v2_issues.append('.form-row 使用了 grid 水平布局，应改为 flex（M49）')
        if '.fr-label' not in content:
            v2_issues.append('.fr-label 缺少 label 样式（V2 表单标签类）（M49）')
        if 'input.fld' not in content and 'input.fld,select.fld' not in content:
            v2_issues.append('V2 输入框缺少 .fld 统一样式（M49）')
        elif 'height:38px' not in content:
            v2_issues.append('.fld 缺少统一高度 38px（M49）')
        if v2_issues:
            result.fail('M49-弹窗表单', '; '.join(v2_issues))
        else:
            result.ok('M49-弹窗表单', 'V2/V3 弹窗表单排版合规（.fr-label/.fld 垂直节奏齐全）')
        return
    issues = []
    # 1. form-row 必须是垂直布局（flex-direction:column），禁止 grid 水平挤行
    if '.form-row{display:grid' in content or '.form-row{display: grid' in content:
        issues.append('.form-row 使用了 grid 水平布局，应改为 flex column 垂直排布（M49）')
    if '.form-row{' not in content or 'flex-direction:column' not in content:
        issues.append('.form-row 缺少垂直排布（flex-direction:column）（M49）')
    # 2. 行间距：form-row 必须有 margin-bottom
    if '.form-row{display:flex' in content and 'margin-bottom' not in content:
        # 宽松判断：至少存在 margin-bottom 定义（任意行距规则）
        issues.append('.form-row 缺少行间距 margin-bottom（相邻字段应间隔 20px）（M49）')
    # 3. label 样式必须存在（13px 600 text2）
    if '.form-row > label' not in content and '.form-row .info-label' not in content:
        issues.append('.form-row 缺少 label 样式（13px/600/--text2）（M49）')
    # 4. 输入框尺寸统一（modal-input 38px）
    if '.modal-input' in content and 'height:38px' not in content:
        issues.append('.modal-input 缺少统一高度 38px（M49）')
    if 'input.modal-input,select.modal-input,textarea.modal-input' not in content:
        issues.append('.modal-input 未提升特异性（会被通用 input 样式覆盖 padding/height）（M49）')
    if issues:
        result.fail('M49-弹窗表单', '; '.join(issues))
    else:
        result.ok('M49-弹窗表单', '弹窗表单排版合规（垂直布局/间距节奏/label/输入框样式齐全）')


def check_menu_tree_design(content, result, is_template, is_component):
    """M50: 菜单配置三级树 — 新增入口/树形渲染/类型联动/删除保护"""
    if is_template or is_component:
        return
    issues = []
    has_menu_page = 'id="page-menus"' in content or '菜单配置' in content and 'menusTableBody' in content
    if not has_menu_page:
        return
    # 1. 必须有新增菜单入口
    if 'openMenuAdd' not in content:
        issues.append('菜单配置缺少「新增菜单」入口函数 openMenuAdd（M50）')
    # 2. 树形渲染（level0/level1/level2）
    if 'menu-level0' not in content or 'menu-level1' not in content or 'menu-level2' not in content:
        issues.append('菜单树缺少三级层级样式（menu-level0/1/2）（M50）')
    if 'parentId' not in content:
        issues.append('菜单数据缺少 parentId 字段（无法建立父子关系）（M50）')
    if 'perms' not in content:
        issues.append('菜单数据缺少 perms 权限标识字段（M50）')
    # 3. 类型联动
    if 'menuTypeChange' not in content:
        issues.append('缺少菜单类型联动函数 menuTypeChange（按钮隐藏路由/图标）（M50）')
    # 4. 删除保护
    if '请先删除子菜单' not in content:
        issues.append('缺少删除保护（有子级菜单禁止删除）（M50）')
    # 5. 校验
    if '按钮必须挂在菜单下' not in content:
        issues.append('缺少校验（按钮必须挂在菜单下）（M50）')
    if issues:
        result.fail('M50-菜单树', '; '.join(issues))
    else:
        result.ok('M50-菜单树', '菜单配置合规（新增入口/三级树/类型联动/删除保护/校验齐全）')


def check_system_admin_integrity(content, result, is_template, is_component):
    """M51: 系统管理标准模块完整性 — 5 页面 ID + 核心函数白名单强校验"""
    if is_template or is_component:
        return
    if is_prd_file(content) or ('phone-frame' in content and 'sub-page' in content):
        return
    # 仅当文件中存在系统管理侧边栏/入口时才校验（避免纯业务原型误报）
    has_sysadmin_hint = ('系统管理' in content) or ('page-menus' in content) or ('menusTableBody' in content)
    if not has_sysadmin_hint:
        return
    pages = ['page-org', 'page-roles', 'page-menus', 'page-dicts', 'page-logs']
    funcs = ['renderOrgTree', 'saveMember', 'saveRole', 'renderMenus', 'openMenuAdd',
             'saveMenu', 'filterDicts', 'saveDict', 'filterLogs', 'deleteMenu', 'toggleMenuExpand']
    missing_pages = [p for p in pages if p not in content]
    missing_funcs = [fn for fn in funcs if fn not in content]
    issues = []
    if missing_pages:
        issues.append('系统管理页面缺失: ' + ', '.join(missing_pages) + '（M51 禁止重写/删减）')
    if missing_funcs:
        issues.append('系统管理函数缺失: ' + ', '.join(missing_funcs) + '（M51）')
    if issues:
        result.fail('M51-系统管理', '; '.join(issues))
    else:
        result.ok('M51-系统管理', '系统管理模块完整性合规（5 页面 + 11 核心函数齐全）')


def check_dept_tree_menu(content, result, is_template, is_component):
    """M52: 部门树操作下拉菜单 + 三级结构"""
    if is_template or is_component:
        return
    if is_prd_file(content) or ('phone-frame' in content and 'sub-page' in content):
        return
    if 'deptTree' not in content:
        return
    issues = []
    if 'dept-more-btn' not in content or 'dept-more-menu' not in content:
        issues.append('部门树缺少操作下拉菜单（dept-more-btn/menu）（M52）')
    if 'deptPin' not in content:
        issues.append('缺少置顶函数 deptPin（M52）')
    if 'openDeptAddChild' not in content:
        issues.append('缺少添加子部门函数 openDeptAddChild（M52）')
    if 'renderDeptNode' not in content:
        issues.append('部门树未递归渲染 renderDeptNode（最多支持三级）（M52）')
    if '修改' not in content or '重命名' not in content or '置顶' not in content:
        issues.append('下拉菜单缺少修改/重命名/置顶项（M52）')
    if issues:
        result.fail('M52-部门树', '; '.join(issues))
    else:
        result.ok('M52-部门树', '部门树合规（操作下拉菜单+三级结构+置顶+添加子部门）')

def check_html_structure_balance(content, result, is_template, is_component):
    """C1-9: HTML 结构平衡 — div 开闭必须成对（防 D8：非贪婪正则误删嵌套块导致 page 容器过早闭合、内容溢出到所有页面底部）"""
    # 剥离注释 / style / script（JS 字符串里可能含 <div>、</div>，会干扰计数）
    s = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
    s = re.sub(r'<style\b[^>]*>.*?</style>', '', s, flags=re.DOTALL)
    s = re.sub(r'<script\b[^>]*>.*?</script>', '', s, flags=re.DOTALL)
    open_n = len(re.findall(r'<div\b', s))
    close_n = len(re.findall(r'</div>', s))
    if open_n == close_n:
        result.ok('C1-11', f'HTML 结构平衡：<div> 开闭 {open_n}/{close_n}')
    else:
        result.fail('C1-11', f'HTML 结构失衡：<div> 开 {open_n} vs </div> 闭 {close_n}（差 {open_n-close_n}）——疑似容器闭合被破坏，内容会溢出到其他页面（D8 教训：删除嵌套块勿用非贪婪正则，改后务必跑本检查）')

# --- V2/v4 桌面端专项拦截（列表页三件套 + 导航一致性） ---

def check_c1_page_desc_ban(content, result, is_template, is_component):
    """C1-12: 仅 V2/驾驶舱范式(desktop-v4) 列表页禁止 page-desc；V1/V3 范式 page-desc 属设计语言，允许"""
    if not is_v4_paradigm(content):
        result.ok('C1-12', '非 V2/驾驶舱范式（page-desc 为设计语言，跳过）')
        return
    if re.search(r'class="page-desc"', content) or re.search(r'<p class="page-desc"', content):
        result.fail('C1-12', '存在 class="page-desc" 标题描述头（V2 列表页禁止 page-header/h2/page-desc，应直接进 .card 内容）')
    else:
        result.ok('C1-12', '无 page-desc 标题描述头（V2 列表页标题头已清理）')

def check_c1_table_column_align(content, result, is_template, is_component):
    """C1-13: 表格 thead 列数 == 对应 row 函数 <td> 开放数（防 tagBy/tagFrom 裸 span 导致整行列错位）"""
    import re as _re
    if is_template or is_component:
        result.ok('C1-13', '模板/组件内置表格由模板保障，跳过 row 对齐检查')
        return
    tables = _re.findall(r'<table class="data-table">.*?</table>', content, _re.S)
    if not tables:
        result.ok('C1-13', '无业务表格，跳过')
        return
    tbody_th = {}
    for t in tables:
        m_id = _re.search(r'<tbody id="([^"]+)"', t)
        ths = _re.findall(r'<th[ >]', t)  # 仅匹配 <th> / <th class=...>，排除 <thead> 误算
        if m_id:
            tbody_th[m_id.group(1)] = len(ths)
    issues = []
    for tbody_id, thc in tbody_th.items():
        rowfn = _re.sub(r'TableBody$', 'Row', tbody_id)
        m = _re.search(r'function ' + _re.escape(rowfn) + r'\s*\([^)]*\)\s*\{(.*?)\n\}', content, _re.S)
        body = None
        if m:
            body = m.group(1)
        else:
            # 回退：V1 风格在 filterXxx 函数内联渲染行（如 filterTransactions 内 return '<tr>...'），
            # 独立 Row 函数不存在（D26：thead 漏"操作"列、row 多一个 td 导致表格溢出、表头背景缺一节）
            base = _re.sub(r'TableBody$', '', tbody_id)
            filter_name = 'filter' + base[:1].upper() + base[1:]
            fm = _re.search(r'function ' + _re.escape(filter_name) + r'\s*\([^)]*\)\s*\{', content)
            if fm:
                start = fm.end()
                nxt = content.find('\nfunction ', start)
                end = nxt if nxt > 0 else len(content)
                fbody = content[start:end]
                rm = _re.search(r"return\s*'<tr>(.*?)</tr>'", fbody, _re.S) or \
                     _re.search(r'return\s*"<tr>(.*?)</tr>"', fbody, _re.S)
                if rm:
                    body = rm.group(1)
        if body is None:
            continue  # 找不到渲染函数（模板内置渲染或异常），跳过
        td_open = len(_re.findall(r'<td[ >]', body))
        if td_open != thc:
            issues.append(f'{tbody_id}: thead 列数 {thc} vs row <td> 数 {td_open}（错位，常见根因 tagBy/tagFrom 未用 <td> 包裹，或 thead 漏"操作"列）')
        for mm in _re.finditer(r'(\+|\s)(tagBy|tagFrom|tagSpan|statusTag)\s*\(', body):
            ctx = body[max(0, mm.start()-25):mm.start()]
            if '</td>' in ctx and '<td>' not in ctx[-15:]:
                issues.append(f'{tbody_id}: {mm.group(2)}() 未用 <td> 包裹（裸 span 导致列错位）')
                break
    if issues:
        result.fail('C1-13', '; '.join(issues))
    else:
        result.ok('C1-13', f'表格列对齐校验通过（{len(tbody_th)} 个表格 thead 与 row <td> 数一致）')

def check_c1_filter_bar_width(content, result, is_template, is_component):
    """C1-14: 仅 V2/V3 现代范式校验筛选下拉自适应并排（防全局 .fld{width:100%} 让下拉独占整行）。
    V1 用 .filter-bar select{width:auto} 且无全局 select.fld{width:100%}，属正确实现，跳过。"""
    import re as _re
    if not (is_v4_paradigm(content) or is_v3_paradigm(content)):
        result.ok('C1-14', '非 V2/V3 现代范式（筛选由各自范式保障），跳过')
        return
    if 'filter-bar' not in content:
        result.ok('C1-14', '无筛选栏，跳过')
        return
    # 仅当存在全局 select.fld{width:100%} 冲突时才要求 .filter-bar 内覆盖
    has_global_fld_width = _re.search(r'(?:input\.fld,select\.fld|select\.fld)\{[^}]*width:100%', content)
    if not has_global_fld_width:
        result.ok('C1-14', '无全局 select.fld{width:100%} 冲突，筛选自适应由范式保障')
        return
    if _re.search(r'\.filter-bar\s+select(?:\.fld)?\{[^}]*width:auto', content) or _re.search(r'\.filter-bar\s+select(?:\.fld)?\{[^}]*flex:0\s+0\s+auto', content):
        result.ok('C1-14', '.filter-bar select 已覆盖 width:auto（筛选下拉自适应并排）')
    else:
        result.fail('C1-14', '模板缺少 .filter-bar select{width:auto} 覆盖，全局 .fld{width:100%} 会让筛选下拉独占整行（M19 自适应并排铁律）')

def check_c1_nav_consistency(content, result, is_template, is_component):
    """C1-15: 业务板块多子页禁止 GROUPS 页内页签（必须 TOP_SECTIONS.children 顶栏下拉，导航一致性）"""
    import re as _re
    if is_template or is_component:
        result.ok('C1-15', '模板/组件跳过')
        return
    issues = []
    if _re.search(r'var\s+GROUPS\s*=', content):
        issues.append('存在 GROUPS 变量（业务板块自创页内页签，应改为 TOP_SECTIONS.children 下拉）')
    if _re.search(r'renderGroupTabs\s*\(', content):
        issues.append('调用 renderGroupTabs（页内页签切换，破坏导航一致性，应删除并改用 children 下拉）')
    if issues:
        result.fail('C1-15', '; '.join(issues))
    else:
        result.ok('C1-15', '导航一致：业务板块多子页统一走 TOP_SECTIONS.children 下拉（无 GROUPS/renderGroupTabs）')

def check_c1_action_col_layout(content, result, is_template, is_component):
    """C1-16: 操作列按钮必须横向排列且不换行（td.action-col 为 flex; gap; flex-wrap:nowrap; th.action-col 禁用 width:1% 强制窄列导致按钮竖排）"""
    import re as _re
    if 'action-col' not in content and 'data-table' not in content:
        result.ok('C1-16', '无操作列/数据表，跳过')
        return
    issues = []
    # 反模式：th.action-col 用 width:1% 把列压到最窄，按钮被挤成竖排
    if _re.search(r'th\.action-col\{[^}]*width:1%', content):
        issues.append('th.action-col 使用 width:1% 会把操作列压到最窄，导致按钮竖排（应改为 white-space:nowrap;text-align:right;padding-right:20px）')
    # 必须有 td.action-col flex 规则（V1 inline-flex 也兼容，V2/V3 用 flex）
    if not (_re.search(r'td\.action-col\{[^}]*display:\s*(?:inline-)?flex', content) or _re.search(r'td:last-child:has\(\.btn\)\{[^}]*display:\s*(?:inline-)?flex', content)):
        issues.append('缺少 td.action-col{display:flex;gap:8px} 规则，操作列按钮无法横向等距排列（§9.2）')
    # 禁止换行（校园集市 D30：不管2/3/4个按钮都不能换行）
    td_flex = _re.search(r'td\.action-col\{([^}]+)\}', content)
    if td_flex and ('flex-wrap:wrap' in td_flex.group(1) or ('flex-wrap' not in td_flex.group(1) and 'nowrap' not in td_flex.group(1))):
        # 若未声明 flex-wrap 则浏览器默认 nowrap，但若显式 wrap 则报错
        if 'flex-wrap:wrap' in td_flex.group(1):
            issues.append('td.action-col 显式 flex-wrap:wrap，操作列按钮会换行（应改为 flex-wrap:nowrap；所有按钮必须平铺放出）')
    if issues:
        result.fail('C1-16', '; '.join(issues))
    else:
        result.ok('C1-16', '操作列按钮横向排列且不换行：td.action-col 为 flex/nowrap，th.action-col 无 width:1% 强制窄列（D30）')

def check_c1_table_fixed_layout(content, result, is_template, is_component):
    """C1-17: 桌面端 data-table 必须 table-layout:fixed（各列均分整表宽度，无操作列后留白）。
    V1/V2/V3 现代范式统一要求。"""
    import re as _re
    if 'data-table' not in content:
        result.ok('C1-17', '无 data-table，跳过')
        return
    # V1 用 .data-table，V2/V3 用 table.data-table
    has_v1 = _re.search(r'\.data-table\{[^}]*table-layout:fixed', content)
    has_v2 = _re.search(r'table\.data-table\{[^}]*table-layout:fixed', content)
    if has_v1 or has_v2:
        result.ok('C1-17', 'data-table 为 table-layout:fixed，各列均分整表宽度（无操作列后留白）')
    else:
        result.fail('C1-17', '.data-table 缺少 table-layout:fixed，列按内容宽度分配会导致操作列后大量留白（应改为 table-layout:fixed，其余列均分剩余宽度）')

def check_c1_page_header_component(content, result, is_template, is_component):
    """C1-18: 仅 V2/desktop-v4（顶栏下拉范式）必须含 Page Header 组件（id="pageHeader" + .ph-crumbs + #pageActions）。
    V2 顶栏下拉会折叠，二级页无持续定位，故需面包屑(H2)/描述/右侧操作由 switchPage 从 TOP_SECTIONS+PAGE_META 自动推导；
    首页(dashboard)与详情页由 JS 隐藏。V3 现代侧栏范式靠左侧栏常驻提供二级定位，无需此组件，跳过。"""
    if not is_v4_paradigm(content):
        result.ok('C1-18', '非 V2/desktop-v4 顶栏范式（V3 侧栏已提供二级定位），跳过')
        return
    import re as _re
    if _re.search(r'id="pageHeader"', content) and _re.search(r'class="ph-crumbs"', content) and _re.search(r'id="pageActions"', content):
        result.ok('C1-18', '含 Page Header 组件（面包屑H2+描述+右侧操作，switchPage 自动推导）')
    else:
        result.fail('C1-18', 'V2/V3 缺少 Page Header 组件（需含 id="pageHeader" + class="ph-crumbs" + id="pageActions"，由 switchPage 自动填充面包屑/描述/操作）')

def check_c1_pagination_count(content, result, is_template, is_component):
    """C1-19: 分页器容器（.table-footer / .pagination-bar，含 id="XxxPager"）必须含 .pg-count（左"共X条"右翻页）。
    renderPager 依赖 .closest('.pagination-bar, .table-footer') 内的 .pg-count 更新计数；容器缺 .pg-count 时 flex(space-between)
    只剩翻页按钮、计数缺失、布局错位（D22）。模板/组件分页器由模板保障，跳过。"""
    if is_template or is_component:
        result.ok('C1-19', '模板/组件分页器由模板保障，跳过')
        return
    import re as _re
    problems = []
    for m in _re.finditer(r'id="(\w+Pager)"', content):
        pager_id = m.group(1)
        before = content[:m.start()]
        opens = [(before.rfind('<div class="table-footer"'), 'table-footer'),
                 (before.rfind('<div class="pagination-bar"'), 'pagination-bar')]
        opens = [(i, c) for i, c in opens if i >= 0]
        if not opens:
            continue  # 找不到已知分页容器（可能是 JS 引用或自定义结构），跳过不误伤
        start, cls = max(opens)
        seg = content[start:m.end()]
        if 'class="pg-count"' not in seg:
            problems.append(f'{pager_id}（{cls} 容器缺 .pg-count）')
    if problems:
        result.fail('C1-19', '; '.join(problems) + ' —— 分页器必须为 左"共X条(.pg-count)" 右翻页(.pages)，renderPager 依赖 .pg-count 更新计数，缺失会导致计数不显示且按钮位置错乱（D22）')
    else:
        result.ok('C1-19', '分页器容器均含 .pg-count（左"共X条"右翻页，布局正常）')

def check_c1_export_btn_ban(content, result, is_template, is_component):
    """C1-20: 仅 V2/desktop-v4（Page Header 范式）——导出/新增按钮必须上移到页头（PAGE_META actions），
    禁止列表页 HTML 残留 class="btn-export" 筛选区按钮（与页头重复，D23）。
    V1/V3 无页头 actions，筛选区导出按钮属各自设计语言，跳过。模板/组件由模板保障，跳过。"""
    if not is_v4_paradigm(content) or is_template or is_component:
        result.ok('C1-20', '非 V2/desktop-v4 生成文件（V1/V3 无页头 actions 或模板/组件），跳过')
        return
    import re as _re
    n = len(_re.findall(r'class="btn-export"', content))
    if n:
        result.fail('C1-20', f'列表页 HTML 残留 {n} 个 class="btn-export" 导出按钮——V2 页头 actions 已提供导出，须移除筛选区重复按钮（D23）')
    else:
        result.ok('C1-20', '无筛选区导出按钮残留（导出统一在页头 actions）')

def check_c1_table_no_overflow_x(content, result, is_template, is_component):
    """C1-21: .table-wrap 禁止使用 overflow-x:auto（防横向滚动条遮挡内容，D29 教训）。
    模板检测：扫描 .table-wrap{...} 不得含 overflow-x:auto
    生成 HTML 检测：禁止在 table-wrap 容器上用内联 style="overflow-x:auto" 覆盖"""
    if is_template:
        for m in re.finditer(r'\.table-wrap\s*\{([^}]*)\}', content):
            if 'overflow-x:auto' in m.group(1):
                result.fail('C1-21', '模板 .table-wrap 样式含 overflow-x:auto（D29 禁横滚，靠字段 ellipsis+进详情解决溢出）')
                return
        result.ok('C1-21', '模板 .table-wrap 未使用 overflow-x:auto（响应式兜底）')
        return
    if is_component:
        result.ok('C1-21', '组件文件跳过')
        return
    # 生成 HTML：扫描内联样式覆盖
    pat = re.compile(r'(class="[^"]*table-wrap[^"]*"[^>]*style="[^"]*overflow-x\s*:\s*auto)|(style="[^"]*overflow-x\s*:\s*auto[^"]*"[^>]*class="[^"]*table-wrap)', re.DOTALL)
    if pat.search(content):
        result.fail('C1-21', '生成 HTML 在 .table-wrap 上用内联样式覆盖回 overflow-x:auto（D29 禁横滚，详见注入说明 D29）')
    else:
        result.ok('C1-21', '无 .table-wrap 横滚内联样式（D29 兜底）')

def check_c1_list_column_count(content, result, is_template, is_component):
    """C1-22: 列表页 thead 列数 ≤ 7（D29 铁律：超过 7 字段需进详情）。
    仅告警不阻断（避免误伤 V2 模板自带的 8 列表菜单管理）"""
    if is_template or is_component:
        result.ok('C1-22', '模板/组件由 lint 保障，跳过列数检查')
        return
    issues = []
    for m in re.finditer(r'<thead[^>]*>\s*<tr[^>]*>(.*?)</tr>', content, re.DOTALL):
        ths = re.findall(r'<th\b', m.group(1))
        if len(ths) > 7:
            issues.append(f'<thead> 含 {len(ths)} 列')
    if issues:
        result.warn('C1-22', f"{'; '.join(issues)} —— D29 铁律：列表字段 ≤ 7 列，超出的次要字段移到详情页（见于校园集市项目：退款 8→7、订单 8→7、用户 8→7、举报 8→7）")
    else:
        result.ok('C1-22', '列表列数 ≤ 7 列（D29 兜底）')

def check_c1_action_button_count(content, result, is_template, is_component):
    """C1-23: 操作列禁止「更多」下拉折叠，所有按钮必须平铺放出（D30 铁律）。
    之前在 D29 允许超过 3 个按钮折叠成 .dropdown，校园集市项目暴露该方案导致：
    (1) 按钮被隐藏，用户找不到操作；(2) 下拉触发区域狭窄、点击体验差；(3) 菜单展开后容易被 td 裁剪。
    现改为：操作列全部按钮直接平铺，靠 table-layout:fixed + action-col 宽度自适应承载。
    模板文件也检查（模板不能提供操作列下拉机制）。"""
    issues = []
    # 1) 生成 HTML：直接在操作列 td 内出现 .dropdown
    for m in re.finditer(r'<td[^>]*class="[^"]*action-col[^"]*"[^>]*>(.*?)</td>', content, re.DOTALL):
        inner = m.group(1)
        if 'class="dropdown"' in inner or 'dropdown' in inner:
            issues.append('操作列 td.action-col 内出现 .dropdown（含「更多」下拉）——所有操作按钮必须直接平铺')
            break
    # 2) 业务/模板 HTML：在表格行（<tbody> 上下文）内出现 .dropdown，即视为操作列下拉折叠
    for m in re.finditer(r'<tbody[^>]*>(.*?)</tbody>', content, re.DOTALL):
        if 'class="dropdown"' in m.group(1) or 'class=\'dropdown\'' in m.group(1):
            issues.append('tbody 内出现 .dropdown（操作列使用了下拉折叠）——所有操作按钮必须直接平铺')
            break
    # 3) 模板 CSS：td.action-col 规则块不得引用 .dropdown（模板不应为操作列提供下拉折叠能力）
    if is_template or is_component:
        if re.search(r'td\.action-col[^}]*\.dropdown', content, re.DOTALL):
            issues.append('模板 td.action-col 样式与 .dropdown 关联（操作列不应提供下拉折叠能力）')
    if issues:
        result.fail('C1-23', '; '.join(issues))
    else:
        result.ok('C1-23', '操作列无「更多」下拉，所有按钮平铺放出（D30）')

def check_c1_dropdown_position_fixed(content, result, is_template, is_component):
    """C1-24: .dropdown-menu 直接定义必须是 position:fixed（D29 防护）。

    根因：td 为 ellipsis 设置了 overflow:hidden，absolute 定位的子元素会被裁剪成窄条，
    导致按钮文字水平重叠（用户截图问题：封禁账号/查看学校挤在一行）。
    必须用 fixed + JS 计算 left/top 才能脱离 td 的裁剪。

    "直接定义"判断：`.dropdown-menu` 前后都不是修饰符选择器部分。
    模板文件 skip（已确认用 fixed）。"""
    if is_template or is_component:
        result.ok('C1-24', '模板/组件由 lint 保障，跳过 dropdown 定位检查')
        return
    issues = []
    seen_direct = False
    for m in re.finditer(r'\.dropdown-menu', content):
        start = m.start()
        end = m.end()
        # 前面最近一个非空白字符
        prev_idx = start - 1
        while prev_idx >= 0 and content[prev_idx] in ' \t':
            prev_idx -= 1
        prev_char = content[prev_idx] if prev_idx >= 0 else ''
        # 后面紧跟的非空白字符（决定是否有修饰符后缀）
        next_idx = end
        while next_idx < len(content) and content[next_idx] in ' \t':
            next_idx += 1
        next_char = content[next_idx] if next_idx < len(content) else ''
        # 修饰符/后代选择器判定：
        # - 前面是字母/数字/点/下划线 → 选择器链有其他部分
        # - 后面是字母/数字/点/下划线/冒号 → 修饰符后缀（:hover、.button 等）
        has_modifier = False
        if prev_char and (prev_char.isalnum() or prev_char in '._'):
            has_modifier = True
        if next_char and (next_char.isalnum() or next_char in '._:'):
            has_modifier = True
        if has_modifier:
            continue  # 跳过修饰符/后代选择器
        # 找对应的 { 内容
        brace_idx = content.find('{', end)
        if brace_idx < 0:
            continue
        # 取 body 直到下一个匹配的 }
        depth = 0
        body_end = brace_idx
        for i in range(brace_idx, min(brace_idx + 500, len(content))):
            if content[i] == '{':
                depth += 1
            elif content[i] == '}':
                depth -= 1
                if depth == 0:
                    body_end = i
                    break
        body = content[brace_idx+1:body_end]
        # 跳过 JS 字符串中的误匹配
        if 'getComputedStyle' in body or 'toggleDropdown' in body or body.strip().startswith('//'):
            continue
        seen_direct = True
        if 'position:fixed' not in body and 'position: fixed' not in body:
            issues.append(f'.dropdown-menu 直接定义未使用 position:fixed（body 片段: {body[:60]}...）')
            break
    if not seen_direct:
        result.ok('C1-24', '无 .dropdown-menu 直接定义（可能不涉及下拉菜单）')
    elif issues:
        result.fail('C1-24', '【致命】.dropdown-menu 不是 position:fixed——会被 td overflow:hidden 裁剪成窄条，按钮文字重叠。修复：改 position:fixed + JS 计算 left/top')
    else:
        result.ok('C1-24', '.dropdown-menu 定位为 fixed（D29 兜底，避免被 td 裁剪）')

def check_c1_duplicate_action_buttons(content, result, is_template, is_component):
    """C1-25: 同一操作按钮不得在「页头 actions + filter-actions」两处重复定义（D31 防护）。

    根因：V2 模板（及继承它的生成产物）曾把「新增角色/新增菜单/新增字典」同时写在
    ① 静态 HTML 的 `.filter-actions`（表格工具栏右侧）和 ② `PAGE_META.xxx.actions`
    （页头右侧，switchPage 动态渲染），导致页面出现两个「新增角色」按钮。

    检查：提取 PAGE_META 各页面 actions 的 onclick 函数名集合 A，再提取静态 HTML 里
    `.filter-actions` 内所有按钮的 onclick 函数名集合 B，A ∩ B 非空即重复（fail 级）。

    注意：列表行内操作按钮（每行「编辑/删除」）在 tbody 里，不在 filter-actions，不会被误伤。
    模板文件也检查（模板自带重复必须拦截）。"""
    # 提取 PAGE_META.actions 里的 onclick 函数名
    meta_onclicks = set()
    for m in re.finditer(r'onclick\s*:\s*["\']([^"\']+)["\']', content):
        fn = re.match(r'(\w+)\s*\(', m.group(1))
        if fn:
            meta_onclicks.add(fn.group(1))
    # 提取 .filter-actions 内的按钮 onclick 函数名
    filter_onclicks = set()
    for m in re.finditer(r'<div[^>]*class="[^"]*filter-actions[^"]*"[^>]*>(.*?)</div>', content, re.DOTALL):
        inner = m.group(1)
        for bm in re.finditer(r'onclick="([^"]+)"', inner):
            fn = re.match(r'(\w+)\s*\(', bm.group(1))
            if fn:
                filter_onclicks.add(fn.group(1))
    dup = meta_onclicks & filter_onclicks
    if dup:
        result.fail('C1-25', f'【致命】操作按钮在「页头 actions + filter-actions」两处重复定义：{", ".join(sorted(dup))}——同一按钮只能放一处（统一放 PAGE_META.actions 页头），删除 filter-actions 里的重复按钮')
    else:
        result.ok('C1-25', '无页头/filter-actions 重复按钮（D31 兜底）')

def check_c1_list_layout_iron(content, result, is_template, is_component):
    """C1-26: 列表布局铁律静态检查（D32 防护，校园集市项目固化）。

    桌面端 data-table 列表必须同时满足：
      1. .table-wrap 左右内边距 20px（与 toolbar 对齐，首/末列 20px 间距基础）
      2. table.data-table / .data-table 使用 table-layout:fixed（列等分）
      3. th:first-child 左对齐 + padding-left:20px；th.action-col（或末列）右对齐 + padding-right:20px
      4. td.action-col 使用 flex-wrap:nowrap（操作按钮禁止换行）
      5. 文本列默认左对齐（text-align:left，表头与内容均左对齐）

    检查对象：模板文件必须全部满足；生成 HTML 继承模板样式，但也会扫内联覆盖。
    """
    if 'data-table' not in content:
        result.ok('C1-26', '无 data-table，跳过列表布局铁律检查')
        return
    import re as _re
    issues = []
    # 1) .table-wrap 左右 20px
    tw_match = _re.search(r'\.table-wrap\s*\{([^}]+)\}', content, _re.DOTALL)
    tw_body = tw_match.group(1) if tw_match else ''
    has_zero_twenty = bool(_re.search(r'padding\s*:\s*0\s+20px', tw_body))
    has_left_right = ('padding-left:20px' in tw_body.replace(' ', '') or 'padding-left: 20px' in tw_body) and \
                     ('padding-right:20px' in tw_body.replace(' ', '') or 'padding-right: 20px' in tw_body)
    if not (has_zero_twenty or has_left_right):
        issues.append('.table-wrap 未设置 padding:0 20px（首/末列无法对齐卡片 20px 边距）')
    # 2) table-layout:fixed
    v1_fixed = _re.search(r'\.data-table\s*\{[^}]*table-layout\s*:\s*fixed', content, _re.DOTALL)
    v2_fixed = _re.search(r'table\.data-table\s*\{[^}]*table-layout\s*:\s*fixed', content, _re.DOTALL)
    if not v1_fixed and not v2_fixed:
        issues.append('data-table 未使用 table-layout:fixed（无法实现列等分）')
    # 3) th 首/末对齐
    if not _re.search(r'thead\s+th:first-child\s*\{[^}]*text-align\s*:\s*left', content, _re.DOTALL):
        if not _re.search(r'th:first-child\s*\{[^}]*text-align\s*:\s*left', content, _re.DOTALL):
            issues.append('首列 th 未左对齐（第一字段应紧靠左侧 20px 边界）')
    if not _re.search(r'th\.action-col\s*\{[^}]*text-align\s*:\s*right', content, _re.DOTALL):
        # 兜底：检查末列 th 是否有 padding-right:20px 且 text-align:right
        if not _re.search(r'th\s*:\s*last-child\s*\{[^}]*text-align\s*:\s*right[^}]*padding-right\s*:\s*20px', content, _re.DOTALL):
            issues.append('操作列 th 未右对齐 + padding-right:20px（末字段按钮无法贴右 20px）')
    # 4) td.action-col nowrap
    action_col_match = _re.search(r'td\.action-col\s*\{([^}]*)\}', content, _re.DOTALL)
    if action_col_match:
        ac_body = action_col_match.group(1)
        if 'display:flex' not in ac_body and 'display:inline-flex' not in ac_body:
            issues.append('td.action-col 未使用 flex 布局')
        if 'flex-wrap:wrap' in ac_body:
            issues.append('td.action-col 显式 flex-wrap:wrap（操作按钮会换行）')
        if 'flex-wrap:nowrap' not in ac_body:
            issues.append('td.action-col 未显式声明 flex-wrap:nowrap（操作按钮可能换行）')
    else:
        issues.append('缺少 td.action-col 规则（操作列布局无保障）')
    # 5) 文本列默认左对齐（表头与内容均左对齐）
    if not _re.search(r'thead\s+th\s*\{[^}]*text-align\s*:\s*left', content, _re.DOTALL):
        if not _re.search(r'th\s*\{[^}]*text-align\s*:\s*left', content, _re.DOTALL):
            issues.append('thead th 未默认左对齐（文本列无法左对齐）')
    # 5b) body 与 header 对齐：tbody td 默认左对齐 + 首列左 + 操作列右（D32 防表头/内容错位）
    if not _re.search(r'tbody\s+td\s*\{[^}]*text-align\s*:\s*left', content, _re.DOTALL):
        if not _re.search(r'td\s*\{[^}]*text-align\s*:\s*left', content, _re.DOTALL):
            issues.append('tbody td 未默认左对齐（内容列与 thead th 不对齐）')
    if not _re.search(r'tbody\s+td:first-child\s*\{[^}]*text-align\s*:\s*left', content, _re.DOTALL):
        if not _re.search(r'td:first-child\s*\{[^}]*text-align\s*:\s*left', content, _re.DOTALL):
            issues.append('首列 tbody td 未左对齐（内容首列无法与 header 对齐）')
    if not _re.search(r'td\.action-col\s*\{[^}]*text-align\s*:\s*right', content, _re.DOTALL):
        if not _re.search(r'td\s*:\s*last-child:has\(\.btn\)\s*\{[^}]*text-align\s*:\s*right', content, _re.DOTALL):
            issues.append('操作列 td 未右对齐（内容末列按钮无法与 header 对齐）')
    if issues:
        result.fail('C1-26', '; '.join(issues))
    else:
        result.ok('C1-26', '列表布局铁律满足：列等分 + 首尾 20px + 文本列左对齐 + 操作不换行（D32）')

def check_c1_avatar_no_clip(content, result, is_template, is_component):
    """C1-27: 含头像的表格列禁止被裁剪（D33 防护）。

    旧模板在 tbody td 上设置 max-width:0，会导致头像列塌缩，只显示一半。
    新规则：若内容中存在 .avatar-circle / .user-avatar（且用于表格行），则：
      1. 全局 tbody td 不得使用 max-width:0；
      2. 必须为头像列提供 overflow:visible 的覆盖（.user-cell / td:has(.avatar-circle) / td:has(.user-avatar)）。
    """
    has_table_avatar = bool(re.search(r'<td[^>]*class="[^"]*(user-cell|avatar)[^"]*"', content, re.DOTALL)) or \
                       'avatar-circle' in content or 'user-avatar' in content
    if not has_table_avatar:
        result.ok('C1-27', '无表格头像列，跳过')
        return
    issues = []
    # 全局 max-width:0 会裁剪头像
    bad_td = re.search(r'tbody\s+td\s*\{([^}]*)\}', content, re.DOTALL)
    if bad_td and 'max-width:0' in bad_td.group(1):
        issues.append('tbody td 全局 max-width:0 会塌缩头像列（应移除，改用 overflow:hidden 在文本列兜底）')
    # 必须有头像列 overflow:visible 规则
    # 桌面端：表格头像列用 td:has(.avatar-circle/.user-avatar) 或 .user-cell 覆盖；
    # 移动端：头像在卡片/评论中，用通用 .avatar-circle/.user-avatar 规则兜底。
    has_avatar_overflow = bool(re.search(r'\.user-cell\s*\{[^}]*overflow\s*:\s*visible', content, re.DOTALL)) or \
                          bool(re.search(r'td\s*:\s*has\(\s*\.avatar-circle\s*\)\s*\{[^}]*overflow\s*:\s*visible', content, re.DOTALL)) or \
                          bool(re.search(r'td\s*:\s*has\(\s*\.user-avatar\s*\)\s*\{[^}]*overflow\s*:\s*visible', content, re.DOTALL)) or \
                          bool(re.search(r'\.avatar-circle\s*\{[^}]*overflow\s*:\s*visible', content, re.DOTALL)) or \
                          bool(re.search(r'\.user-avatar\s*\{[^}]*overflow\s*:\s*visible', content, re.DOTALL))
    if not has_avatar_overflow:
        issues.append('未检测到头像列 overflow:visible 规则（.user-cell 或 td:has(.avatar-circle/.user-avatar)）——头像可能被裁剪')
    if issues:
        result.fail('C1-27', '; '.join(issues))
    else:
        result.ok('C1-27', '表格头像列未被裁剪：全局无 max-width:0，且有 overflow:visible 覆盖（D33）')

def check_c1_phone_mask(content, result, is_template, is_component, filepath=None):
    """C1-28: 手机号/电话脱敏（D36 铁律）。生成文件不得含裸 11 位中国大陆手机号字面量
    1[3-9]\\d{9}，除非它位于 maskPhone(...) 调用参数内（即待脱敏原文，运行时会掩码）。
    注意：传入的 content 已被 read_file 剥离 <script>，而裸号常藏在 JS 数据层，因此优先扫描原始文件全文。"""
    # 扫描原始文件全文（含 <script> 数据层），裸号常躲在这里
    scan = content
    if filepath and os.path.exists(filepath):
        try:
            scan = open(filepath, encoding='utf-8', errors='replace').read()
        except Exception:
            scan = content
    # 去掉 maskPhone(...) 调用体，避免把"传入待脱敏原文"误判为违规
    stripped = re.sub(r'maskPhone\s*\([^)]*\)', ' ', scan, flags=re.DOTALL)
    raw = re.findall(r'1[3-9]\d{9}', stripped)
    if raw:
        uniq = sorted(set(raw))
        result.fail('C1-28', f'含 {len(uniq)} 处未脱敏的 11 位手机号（须用 maskPhone() 脱敏，或存储为 138****8001 形式）: {", ".join(uniq[:8])}（D36）')
    else:
        result.ok('C1-28', '无未脱敏手机号字面量（手机/电话已脱敏，D36）')

def check_c1_duplicate_id(content, result, is_template, is_component, filepath=None):
    """C1-29: 重复 ID 检测。生成文件任何 id="" 值不得出现 >1 次（含模板 id 与注入 id 冲突）。
    典型事故：Agent 在注入区又写了一个 <section id="loginPage">，与模板 <div id="loginPage"> 冲突，
    doLogin 只隐藏第一个，第二个 fixed+z-index:9999 永远遮住 app —— 登录假失败。
    模板/组件自身的 id 是唯一性的，此检查对模板也生效（模板重复 id 同样是 bug）。"""
    scan = content
    if filepath and os.path.exists(filepath):
        try:
            scan = open(filepath, encoding='utf-8', errors='replace').read()
        except Exception:
            scan = content
    # 只匹配 HTML 标签内的 id 属性（<tag ... id="...">），排除 JS 代码里的 `data.id = 'M'` 赋值与拼接
    ids = re.findall(r'<\w[^>]*?\bid\s*=\s*["\']([^"\']{1,120})["\']', scan)
    if not ids:
        result.ok('C1-29', '无 id 属性，跳过')
        return
    from collections import Counter
    dups = {k: v for k, v in Counter(ids).items() if v > 1}
    if dups:
        desc = '; '.join(f'"{k}"×{v}' for k, v in list(dups.items())[:8])
        result.fail('C1-29', f'检测到重复 id（同 id 在页面出现 >1 次会导致 getElementById 只取第一个、后写的永远无法定位）: {desc}（D37）')
    else:
        result.ok('C1-29', '无重复 id（模板与注入 id 无冲突）')

def check_c1_no_proj_switcher(content, result, is_template, is_component, filepath=None):
    """C1-30: V3 无项目切换器（D41 防护）。生成文件禁止含 proj-switcher / projMenu / 项目切换器残留。
    V3 模板已删除 .proj-switcher 组件（平台管理端=总后台，无门店/项目视角切换），
    若 Agent 参考 V1/V2 或历史项目在注入区自建该组件，说明层无法察觉，此检查强制拦截。
    仅对 V3 生效：V1 无该组件、V2 顶栏导航仍保留（该范式有自己的切换器形态），不误伤。"""
    if not is_v3_paradigm(content):
        result.ok('C1-30', '非 V3 范式，跳过')
        return
    scan = content
    if filepath and os.path.exists(filepath):
        try:
            scan = open(filepath, encoding='utf-8', errors='replace').read()
        except Exception:
            scan = content
    # 项目切换器特征：proj-switcher / proj-menu / projName / projMenu / toggleProjSwitcher / switchProject
    hits = []
    for pat, label in [
        (r'class=["\'][^"\']*proj-switcher', 'proj-switcher 容器'),
        (r'class=["\'][^"\']*proj-menu', 'proj-menu 下拉'),
        (r'id=["\']projMenu', 'projMenu 容器'),
        (r'id=["\']projName', 'projName 元素'),
        (r'toggleProjSwitcher\s*\(', 'toggleProjSwitcher 函数'),
        (r'switchProject\s*\(', 'switchProject 函数'),
    ]:
        if re.search(pat, scan):
            hits.append(label)
    if hits:
        result.fail('C1-30', f'检测到项目切换器残留（V3 已移除该组件，平台管理端无门店/项目切换）: {", ".join(hits)}（D41）')
    else:
        result.ok('C1-30', '无项目切换器残留（V3 平台管理端无门店/项目切换，D41）')


def _read_scan(content, filepath):
    """读取待扫描内容（优先磁盘文件，保证正则能跨长行）"""
    scan = content
    if filepath and os.path.exists(filepath):
        try:
            scan = open(filepath, encoding='utf-8', errors='replace').read()
        except Exception:
            scan = content
    return scan


def _entry_subpage_target(scan, onclick_expr):
    """解析入口 onclick 的目标 sub-page id。
    直接 openSubPage('sub-x') → 返回 sub-x；自定义函数 fn(...) → 找函数定义体中的首个 openSubPage('sub-y')。"""
    m = re.search(r"openSubPage\(\s*['\"]([^'\"]+)['\"]\s*\)", onclick_expr)
    if m:
        return m.group(1)
    fn = re.search(r"^\s*([A-Za-z_][\w]*)\s*\(", onclick_expr.strip())
    if fn:
        fname = fn.group(1)
        fm = re.search(r"function\s+" + re.escape(fname) + r"\s*\([^)]*\)\s*\{", scan)
        if fm:
            body = scan[fm.end():]
            bm = re.search(r"openSubPage\(\s*['\"]([^'\"]+)['\"]\s*\)", body[:3000])
            if bm:
                return bm.group(1)
    return None


def _subpage_block(scan, sub_id):
    """截取指定 sub-page 的 HTML 块"""
    m = re.search(r'<div\s+class="sub-page"[^>]*id="' + re.escape(sub_id) + r'"[^>]*>', scan)
    if not m:
        return None
    start = m.start()
    # 简单 div 平衡截取
    depth = 0
    for mm in re.finditer(r'<div\b[^>]*>|</div>', scan[m.start():]):
        tok = mm.group(0)
        if tok.startswith('</'):
            depth -= 1
        else:
            depth += 1
        if depth == 0:
            return scan[start: m.start() + mm.end()]
    return scan[start: start + 6000]


def _extract_onclick(tag):
    """提取标签 onclick 属性值。优先双引号包裹（值可含单引号，如 openActivity('newuser')）。"""
    m = re.search(r'onclick\s*=\s*"([^"]*)"', tag)
    if m:
        return m.group(1)
    m = re.search(r"onclick\s*=\s*'([^']*)'", tag)
    if m:
        return m.group(1)
    return None


def check_c1_no_back_to_top(content, result, is_template, is_component, filepath=None):
    """C1-31: 移动端禁止回到顶部按钮（D47 防护）。用户明确不要，模板已移除，注入自建即 fail。"""
    if not is_mobile_file(content):
        result.ok('C1-31', '非移动端，跳过')
        return
    scan = _read_scan(content, filepath)
    hits = []
    for pat, label in [
        (r'back-to-top', 'back-to-top 元素'),
        (r'id=["\']backToTop', 'backToTop 容器'),
        (r'initBackToTop\s*\(', 'initBackToTop 函数'),
        (r'function\s+scrollToTop', 'scrollToTop 函数'),
    ]:
        if re.search(pat, scan):
            hits.append(label)
    if hits:
        result.fail('C1-31', f'检测到回到顶部按钮残留（用户明确不要该组件，模板已移除，禁止自建）: {", ".join(hits)}（D47）')
    else:
        result.ok('C1-31', '无回到顶部按钮（模板已移除，D47）')


def check_c1_no_inline_overflow_y(content, result, is_template, is_component, filepath=None):
    """C1-32: 移动端禁止内联 overflow-y 滚动条（D46 防护）。内联样式里的纵向滚动 = 可见滚动条 = 违反零滚动条铁律。"""
    if not is_mobile_file(content):
        result.ok('C1-32', '非移动端，跳过')
        return
    scan = _read_scan(content, filepath)
    # 匹配内联 style 属性里的 overflow-y 或 max-height+overflow 组合
    inline_hits = []
    for m in re.finditer(r'style\s*=\s*["\']([^"\']*)["\']', scan):
        style = m.group(1)
        if re.search(r'overflow-y\s*:\s*(auto|scroll)', style):
            inline_hits.append('overflow-y:' + re.search(r'overflow-y\s*:\s*(auto|scroll)', style).group(1))
    if inline_hits:
        result.fail('C1-32', f'检测到内联 overflow-y 滚动条（移动端零滚动条铁律，内容由模板滚动容器处理）: {", ".join(dict.fromkeys(inline_hits))}（D46）')
    else:
        result.ok('C1-32', '无内联 overflow-y 滚动条（D46）')


def check_c1_sheet_inside_mask(content, result, is_template, is_component, filepath=None):
    """C1-33: 移动端 sheet 必须在 sheet-mask 内（D44 防护）。平铺独立 .sheet（mask 外）会脱离弹层容器层级。"""
    if not is_mobile_file(content):
        result.ok('C1-33', '非移动端，跳过')
        return
    scan = _read_scan(content, filepath)
    # 扫描 .sheet 元素，检查其是否位于 sheet-mask 容器内
    # 用标签栈跟踪 sheet-mask 开放状态
    import html.parser as _hp
    stack = []
    problems = []
    sheet_ids = []

    class _P(_hp.HTMLParser):
        def handle_starttag(self, tag, attrs):
            if tag == 'div':
                cls = dict(attrs).get('class', '')
                sid = dict(attrs).get('id', '')
                stack.append(cls)
                if 'sheet' in cls.split() and 'sheet-mask' not in cls.split():
                    if 'sheet-mask' not in stack:
                        problems.append(sid or cls or '(sheet)')
                if 'sheet-mask' in cls.split():
                    sheet_ids.append(sid or cls)
        def handle_endtag(self, tag):
            if tag == 'div' and stack:
                stack.pop()

    p = _P()
    try:
        p.feed(scan)
    except Exception:
        pass
    if problems:
        result.fail('C1-33', f'检测到平铺独立 .sheet（不在 sheet-mask 容器内，弹层会脱离遮罩层级）: {", ".join(problems[:6])}（D44）')
    else:
        result.ok('C1-33', 'sheet 均在 sheet-mask 容器内（D44）')


def check_c1_entry_mapping(content, result, is_template, is_component, filepath=None):
    """C1-34: 移动端首页入口目标页必须存在且含必备特征（D43 防护）。
    语义入口（.home-search/.home-banner/.store-card/.promo-card）的 onclick 目标 sub-page 必须真实存在，
    且含对应类型必备特征。全部入口指同一列表 / 目标页不存在 / 无特征 = fail。"""
    if not is_mobile_file(content):
        result.ok('C1-34', '非移动端，跳过')
        return
    scan = _read_scan(content, filepath)
    # 定位首页 page-home 段
    hm = re.search(r'<div\s+class="page[^"]*active[^"]*"[^>]*id="page-home"[^>]*>', scan)
    home = scan[hm.start(): hm.start() + 20000] if hm else scan
    # 特征对照：入口 class → (必备特征正则, 特征说明)
    ENTRY_FEATURES = [
        ('home-search', r'<input[^>]*>|search-box|search-input|hot-words|hot-tags', '搜索页(含输入框/热词)'),
        ('home-banner', r'promo-timer|data-countdown|activity|countdown', '活动专题页(含倒计时/活动特征)'),
        ('store-card', r'store-logo|store-name|rating|评分|评价', '门店详情页(含门店头/评分/评价)'),
        ('promo-card', r'promo-timer|data-countdown|countdown|活动', '活动专题页(含倒计时/活动特征)'),
    ]
    issues = []
    for cls, feat_re, feat_desc in ENTRY_FEATURES:
        # 找到该 class 的元素及其 onclick
        for em in re.finditer(r'<[^>]*class="[^"]*' + cls + r'[^"]*"[^>]*>', home):
            tag = em.group(0)
            onclick = _extract_onclick(tag)
            if onclick is None:
                continue  # 无 onclick 的容器元素（如 .home-search 里的子元素）跳过
            sub = _entry_subpage_target(scan, onclick)
            if sub is None:
                # onclick 未指向任何 sub-page（如 openServiceList）→ 直接判问题
                issues.append(f'{cls}: onclick="{onclick[:40]}" 未指向 {feat_desc}')
                continue
            blk = _subpage_block(scan, sub)
            if blk is None:
                issues.append(f'{cls}: 目标 {sub} 不存在（L5）')
            elif not re.search(feat_re, blk):
                issues.append(f'{cls}: 目标 {sub} 缺{feat_desc}特征')
    if issues:
        result.fail('C1-34', '首页入口目标页逻辑错误: ' + '；'.join(issues[:6]) + '（D43，依据移动端产品逻辑规范）')
    else:
        result.ok('C1-34', '首页入口目标页存在且特征完整（D43）')


def check_c1_entry_diversity(content, result, is_template, is_component, filepath=None):
    """C1-35: 同组入口目标必须多样（L6 铁律，D43 防护）。
    同组入口（banner 组/金刚区/营销卡组）onclick 目标去重后数量 < 组内入口数 = fail。
    类目金刚区各指各的类目列表（参数不同）天然通过；全部入口指同一列表即被拦截。"""
    if not is_mobile_file(content):
        result.ok('C1-35', '非移动端，跳过')
        return
    scan = _read_scan(content, filepath)
    hm = re.search(r'<div\s+class="page[^"]*active[^"]*"[^>]*id="page-home"[^>]*>', scan)
    home = scan[hm.start(): hm.start() + 20000] if hm else scan
    groups = [
        ('Banner 组', 'home-banner'),
        ('金刚区', 'home-cat'),
        ('营销卡组', 'promo-card'),
    ]
    issues = []
    for gname, cls in groups:
        targets = []
        for em in re.finditer(r'<[^>]*class="[^"]*' + cls + r'[^"]*"[^>]*>', home):
            ot = _extract_onclick(em.group(0))
            if ot:
                targets.append(ot.strip())
        if len(targets) >= 2 and len(set(targets)) < len(targets):
            issues.append(f'{gname}: {len(targets)} 个入口只有 {len(set(targets))} 个不同目标（L6 多样性）')
    if issues:
        result.fail('C1-35', '同组入口目标重复（L6 多样性铁律，每个入口必须指向不同目标页）: ' + '；'.join(issues) + '（D43）')
    else:
        result.ok('C1-35', '同组入口目标多样（L6）')


def check_c1_info_entry_no_sheet(content, result, is_template, is_component, filepath=None):
    """C1-36: 信息展示类入口禁止用弹窗（L7/M71 防护）。
    我的中心「关于/协议/帮助/版本」等信息类入口 onclick 指向 openSheet 即 fail（应 openSubPage 二级页）。
    信息展示量大需滚动返回上下文，弹窗只适合轻量选择。"""
    if not is_mobile_file(content):
        result.ok('C1-36', '非移动端，跳过')
        return
    scan = _read_scan(content, filepath)
    issues = []
    # mine-menu-item 信息展示类入口（文本含 关于/协议/帮助/版本/隐私/条款/说明）
    for m in re.finditer(r'<div\s+class="[^"]*mine-menu-item[^"]*"[^>]*>([\s\S]*?)</div>', scan):
        block = m.group(1)
        text = re.sub(r'<[^>]+>', '', block).strip()[:24]
        onclick = _extract_onclick(m.group(0))
        if text and onclick and 'openSheet' in onclick and re.search(r'关于|协议|帮助|版本|隐私|条款|说明', text):
            issues.append(f'{text} → {onclick[:36]}')
    if issues:
        result.fail('C1-36', '信息展示类入口用弹窗（应 openSubPage 二级页，L7）: ' + '；'.join(issues[:6]) + '（M71）')
    else:
        result.ok('C1-36', '信息展示类入口均为二级页（L7，M71）')


def check_c1_no_inline_form(content, result, is_template, is_component, filepath=None):
    """C1-37: 表单创建禁止内联展开（L7/M72 防护）。
    新增/编辑地址等表单必须独立 sub-page，禁止 toggleXxxForm 在列表下内联展开（挤压列表、打断浏览）。"""
    if not is_mobile_file(content):
        result.ok('C1-37', '非移动端，跳过')
        return
    scan = _read_scan(content, filepath)
    hits = []
    for mm in re.finditer(r'toggle[A-Z]\w*Form\s*\(', scan):
        hits.append(mm.group(0))
    if hits:
        result.fail('C1-37', f'检测到内联展开表单模式（应独立表单页 sub-xxx-form，L7）: {", ".join(dict.fromkeys(hits[:5]))}（M72）')
    else:
        result.ok('C1-37', '表单均为独立页面，无内联展开（L7，M72）')


def check_enum_coverage(content, result, is_template, is_component):
    """枚举覆盖率检测 — 从内容中提取状态枚举并检查覆盖率"""
    if is_template:
        result.ok('枚举覆盖', '模板文件跳过')
        return
    # 提取常见状态枚举
    status_patterns = re.findall(r'(待支付|待审核|待发货|待接单|已完成|已取消|已发货|已通过|已驳回|已禁用|营业中|休息中|正常|草稿)', content)
    unique_statuses = set(status_patterns)
    if len(unique_statuses) >= 3:
        result.ok('枚举覆盖', f'检测到 {len(unique_statuses)} 种状态枚举: {", ".join(sorted(unique_statuses)[:5])}')
    elif len(unique_statuses) > 0:
        result.warn('枚举覆盖', f'仅检测到 {len(unique_statuses)} 种状态枚举，覆盖率可能不足')
    else:
        result.ok('枚举覆盖', '无状态枚举（可能该文件不涉及状态管理）')

# --- 伪页面检测 ---

def check_pseudo_page(content, result, is_template, is_component):
    """伪页面检测 — 子页面内 70% 以上按钮仅调用 showToast 判定为伪页面"""
    if is_template or is_component:
        result.ok('伪页面', '模板/组件文件跳过')
        return
    # 找所有 sub-page 或 page 区域
    sub_pages = re.findall(r'class="[^"]*sub-page[^"]*"[^>]*>(.*?)</div>\s*(?=<div class="[^"]*sub-page|<div class="[^"]*bottom-nav|$)', content, re.DOTALL)
    if not sub_pages:
        result.ok('伪页面', '无子页面或无法提取')
        return
    pseudo_pages = []
    for i, page_content in enumerate(sub_pages):
        onclick_handlers = re.findall(r'onclick="([^"]*)"', page_content)
        if not onclick_handlers:
            continue
        pseudo_count = 0
        for handler in onclick_handlers:
            cleaned = re.sub(r'\s+', '', handler.strip().rstrip(';'))
            if re.match(r'^(showToast|toast)\s*\([^)]*\)$', cleaned):
                pseudo_count += 1
        ratio = pseudo_count / len(onclick_handlers) if onclick_handlers else 0
        if ratio >= 0.7:
            pseudo_pages.append(f'子页面#{i+1}（{pseudo_count}/{len(onclick_handlers)} 按钮仅 Toast）')
    if not pseudo_pages:
        result.ok('伪页面', '未检测到伪页面')
    else:
        result.fail('伪页面', f'检测到 {len(pseudo_pages)} 个伪页面: {"; ".join(pseudo_pages[:3])}')

# --- 文字对比度检测 ---

def check_text_contrast(content, result, is_template, is_component):
    """文字对比度基础检测 — 深色主题下文字透明度 < 0.45 报警"""
    if is_template:
        result.ok('对比度', '模板文件跳过')
        return
    # 检测深色背景配低透明度文字
    # 检查 rgba 文字色透明度
    low_opacity_texts = re.findall(r'color\s*:\s*rgba\s*\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*(0?\.[0-3]\d*)', content)
    # 检查深色背景 + 深色文字组合
    dark_bg_light_text_issues = []
    # 简化检测：深色背景（#000-#333）配 rgba 透明度 < 0.45
    if low_opacity_texts:
        low_values = [float(v) for v in low_opacity_texts if float(v) < 0.45]
        if low_values:
            result.warn('对比度', f'检测到 {len(low_values)} 处低透明度文字（< 0.45），可能对比度不足')
        else:
            result.ok('对比度', '文字透明度正常')
    else:
        result.ok('对比度', '未检测到低对比度文字')

    # 检查 $ 美元符号（已在 T6 检查）
    # 检查已知陷阱色组合（黄/绿/红配白字）
    # 排除纯白底 #fff（正常），仅匹配 #FFE*/#FFD* 等浅黄橙红绿底 + 白字
    trap_colors = re.findall(r'background[^;]*?(?:#FF[EF]|#ff[ef]|#FF[Dd][0-9A-Fa-f]{3}|yellow|lime|#00FF|#ff00)[^;]*?;[^}]*?color\s*:\s*(?:#fff|#FFF|white)', content, re.IGNORECASE)
    # 白底白字是误报（background:#fff 恰被 #ff[ef] 匹配），二次过滤：要求背景不是纯白
    trap_colors = [t for t in trap_colors if not re.match(r'background\s*:\s*#f{3}', t, re.IGNORECASE)]
    if trap_colors:
        result.warn('对比度', f'检测到 {len(trap_colors)} 处已知陷阱色组合（黄/绿/红配白字）')

# --- M10 页面容器检测 ---





# ============================================================
# M63 检查：二级子页面必须在 .content 容器之外
# ============================================================
def _safe_scan_text(content):
    """M119/M120/M121 等特性触发型检查共用的净化扫描源（v5.41）：
    只剥离 HTML 注释与 CSS/JS 块注释——防模板「教学注释中的示例代码」
    （如 M120 教学段里的 #categorySidebar / .cart-bar / page-cart 示例字样）
    被当成真实 DOM 触发误报（v5.40 实测：任意合法产物因模板注释残留被 M119 打回）。
    与 M63 强净化不同：这里故意保留 <script>/<style> 内容——JS 渲染函数名、
    模板内置组件 CSS 是 sticky/flex/gap 属性断言的合法证据载体。
    """
    t = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)   # HTML 注释
    return re.sub(r'/\*.*?\*/', '', t, flags=re.DOTALL)        # CSS / JS 块注释


def check_m63_subpage_position(content, result, is_template, is_component):
    """M63 完整检查（v7 升级）：
    1. 主页面（.page）必须都在 .content 容器内
    2. 二级子页面（.sub-page）必须都在 .content 容器外
    3. div 标签完全平衡（防止移动代码时残留/缺失闭合标签导致页面逃逸）
    
    注意：本检查面向移动端 DOM 结构；桌面端若含 .content/.page 结构同样适用，但 div 计数前必须剥离
    <script>/<style>/注释，避免 JS/CSS 字符串中的 <div 误报。"""
    import re
    # 基础计数：div 平衡（仅统计 HTML 标签，剥离 JS/CSS/注释中的字符串误报）
    html_only = re.sub(r'<script\b[^>]*>.*?</script>', '', content, flags=re.DOTALL)
    html_only = re.sub(r'<style\b[^>]*>.*?</style>', '', html_only, flags=re.DOTALL)
    html_only = re.sub(r'<!--.*?-->', '', html_only, flags=re.DOTALL)
    opens = len(re.findall(r'<div\b', html_only))
    closes = len(re.findall(r'</div>', html_only))
    if opens != closes:
        result.fail('M63', f'div 标签不平衡（<div>={opens} </div>={closes}，差异 {opens-closes}）——页面可能逃逸容器或残留闭合标签')
        return
    # 以下结构分析全部基于净化后的 html_only（与上方 div 计数同一坐标系）：
    # script/style/HTML 注释已剥离——防 CSS 教学注释内的示例代码（如 M120 的
    # page-cart 示例）被误判为逃逸 .content 的真实 DOM；JS 字符串中的模板片段同样豁免。
    c_start = html_only.find('<div class="content"')
    if c_start == -1:
        return
    # 用计数法找 .content 的真实闭合位置（html_only 中 script 内容已被剥离，
    # in_script 守卫保留仅为健壮性）
    depth = 0
    in_script = False
    i = c_start
    c_end = -1
    while i < len(html_only):
        if html_only.startswith('<script', i): in_script = True
        if html_only.startswith('</script>', i): in_script = False
        if not in_script:
            if html_only.startswith('<div', i):
                depth += 1
            elif html_only.startswith('</div>', i):
                depth -= 1
                if depth == 0:
                    c_end = i
                    break
        i += 1
    if c_end == -1:
        result.fail('M63', '未找到 .content 的闭合位置（.content 结构不完整）')
        return
    # 主页面必须在 .content 内
    bad_pages = []
    for m in re.finditer(r'<div class="page[^"]*" id="(page-[a-z]+)"', html_only):
        pos = m.start()
        if not (c_start < pos < c_end):
            bad_pages.append(m.group(1))
    if bad_pages:
        result.fail('M63', f'主页面逃逸 .content 容器：{", ".join(bad_pages)}（会被定位到屏幕顶部/被导航遮挡）')
        return
    # 二级子页面必须在 .content 外
    bad_subs = []
    for m in re.finditer(r'<div class="sub-page" id="(sub-[a-z]+)"', html_only):
        pos = m.start()
        if c_start < pos < c_end:
            bad_subs.append(m.group(1))
    if bad_subs:
        result.fail('M63', f'二级子页面在 .content 内部：{", ".join(bad_subs)}（顶部间距过大+残留元素）')
        return
    result.ok('M63', 'DOM 结构完整（div 平衡 + 主页面在 .content 内 + 子页面在 .content 外）')


# ============================================================
# M65 检查：.content 空白文本节点防偏移（font-size:0 + .page 重置）
# ============================================================
def check_m65_content_whitespace(content, result, is_template, is_component):
    """.content 必须 font-size:0（消除空白文本节点行框），.page 必须重置 font-size"""
    import re
    # 找 .content 规则块
    m = re.search(r'\.content\{[^}]*\}', content)
    if not m:
        return  # 无 .content 跳过
    block = m.group(0)
    if 'font-size:0' not in block:
        result.fail('M65', '.content 必须 font-size:0（否则空白文本节点行框会把 .page 下推约21px，搜索框距导航栏过大）')
        return
    # 找 .page 规则块
    pm = re.search(r'\.page\{[^}]*\}', content)
    if not pm or 'font-size' not in pm.group(0):
        result.fail('M65', '.page 必须显式 font-size（父级 font-size:0 后需恢复页内文字）')
        return
    result.ok('M65', '.content font-size:0 + .page font-size 重置（无空白文本偏移）')

def check_m82_list_container(content, result, is_template, is_component):
    """M82: 移动端卡片列表父容器必须是列表类，禁止裸 <div> 包卡片数组（否则卡片零间距）

    根因（M81 教训）：orderCardHTML 等由 list.map(xxxCardHTML).join('') 注入容器，
    但 list 间距由 .order-list{gap} 等列表类提供。子 Agent 写裸 <div id="ordersList"> 会丢间距。
    检测（两条互补路径，M82 增强）：
    A. 扫描产物中所有 id 含 List 的 div 容器，按语义核查是否用了对应列表类。
    B. 扫描 JS 中 `$('id')` / getElementById('id') 后接 innerHTML = ...map(...).join('') 的
       渲染目标容器（容器 id 可能不含 List，如 pickupBody/seckillBody——M82 增强版覆盖），
       检查该容器 HTML 标签是否有列表类（order-list/card-list/store-list 等）。
       带空态守卫的（list.length ? … : emptyState(…)）视为"数据可能为空但容器是列表"，
       仍需列表类。
    """
    if is_template or is_component:
        result.ok('M82', '模板/组件文件跳过')
        return
    if not is_mobile_file(content):
        result.ok('M82', '非移动端文件跳过')
        return
    # 已知列表类白名单（父容器用了其中之一即视为有间距容器）
    LIST_CLASSES = ('order-list', 'card-list', 'goods-list', 'product-list', 'msg-list',
                    'list', 'waterfall', 'todo-list', 'staff-list', 'addr-list', 'pets-list',
                    'ship-list', 'home-products', 'home-stores', 'home-cats', 'shop-cats',
                    'work-quick', 'mine-menu', 'order-tabs', 'store-list', 'coupon-list')
    fails = []
    warnings = []

    def _container_class(cid):
        """找容器 id 的 HTML 标签并提取 class"""
        for tag_m in (re.search(r'<div\b[^>]*\bid="' + re.escape(cid) + r'"[^>]*>', content),
                      re.search(r'<[a-z]+\b[^>]*\bid="' + re.escape(cid) + r'"[^>]*>', content)):
            if tag_m:
                cm = re.search(r'class="([^"]*)"', tag_m.group(0))
                if cm:
                    return cm.group(1), tag_m.group(0)
        return '', ''

    # ---- A 路径：id 含 List 的 div 容器 ----
    div_tags = re.findall(r'<div\b[^>]*\bid="([^"]*[Ll]ist[^"]*)"[^>]*>', content)
    div_tags = [t for t in div_tags if not t.lower().startswith('sub-')]
    for cid in div_tags:
        cls, _tag = _container_class(cid)
        cls_set = set(cls.split())
        has_list_cls = any(lc in cls_set for lc in LIST_CLASSES)
        cid_l = cid.lower()
        if 'order' in cid_l:
            if 'order-list' not in cls_set:
                fails.append(f'#{cid} 订单列表容器缺少 class="order-list"（卡片零间距，M81）')
            continue
        card_hints = ('goods', 'product', 'card', 'pickup', 'ship',
                      'todo', 'staff', 'merchant', 'coupon')
        if any(h in cid_l for h in card_hints) and not has_list_cls:
            warnings.append(f'#{cid} 疑似卡片列表容器但无列表类（{"、".join(LIST_CLASSES[:6])} 等之一），可能零间距')

    # ---- B 路径：JS 渲染目标容器（容器 id 可不含 List）----
    # 精确判定：容器必须是 innerHTML 赋值目标（textContent/其他不是），且赋值含 map().join()
    render_targets = set()

    def _is_render_target(cid):
        """cid 是否为卡片数组渲染目标：链式 .innerHTML 或变量声明后 .innerHTML = ...map().join()"""
        # map(...).join 的宽松匹配：容忍嵌套括号/箭头函数/模板字符串（用 .join( 出现即算，re.S 跨行）
        def _map_join():
            return r'\.map\s*\(.*?\.join\s*\('
        # 链式：$('cid').innerHTML = ... .map(...).join('') 或 getElementById('cid').innerHTML = ...
        pat_chain = (r'''(?:document\.getElementById\(\s*['"]%s['"]\s*\)|[$]\s*\(\s*['"]%s['"]\s*\))'''
                     r'''\s*\.innerHTML\s*=\s*[^;]*''' + _map_join())
        if re.search(pat_chain % (re.escape(cid), re.escape(cid)), content, re.S):
            return True
        # 变量式：const el = $('cid'); ...; el.innerHTML = ... .map().join('')
        for m in re.finditer(
                r'''(?:const|let|var)\s+(\w+)\s*=\s*(?:document\.getElementById\(\s*['"]''' + re.escape(cid) +
                r'''['"]\s*\)|[$]\s*\(\s*['"]''' + re.escape(cid) + r'''['"]\s*\))\s*;?''', content):
            varname = m.group(1)
            tail = content[m.end(): m.end() + 1200]
            if re.search(r'\b' + varname + r'\s*\.innerHTML\s*=\s*[^;]*' + _map_join(), tail, re.S):
                return True
        return False

    for m in re.finditer(r"""[$]\s*\(\s*['"]([^'"]+)['"]\s*\)""", content):
        cid = m.group(1)
        if _is_render_target(cid):
            render_targets.add(cid)
    for m in re.finditer(r"""getElementById\(\s*['"]([^'"]+)['"]\s*\)""", content):
        cid = m.group(1)
        if _is_render_target(cid):
            render_targets.add(cid)

    for cid in render_targets:
        if cid.lower().startswith('sub-'):
            continue  # sub-page 容器本身不是卡片列表父容器
        cls, tag = _container_class(cid)
        cls_set = set(cls.split())
        has_list_cls = any(lc in cls_set for lc in LIST_CLASSES)
        # 容器是滚动类/网格类也放行（shop-cats 横向、home-cats 宫格本身就是列表）
        grid_ok = bool(re.search(r'(?:shop-cats|sub-cats|home-cats|home-tiles|work-quick|waterfall|seg-tabs|orders-tabs|drag-scroll)', cls))
        if not has_list_cls and not grid_ok:
            # 判定渲染的是否是"卡片"（需要父容器 gap）还是"自带间距的行"：
            # ① list-item/tab/cat/tag 类（自带 margin）② 渲染内容内联 margin-bottom ③ 渲染内容 flex:1 均分（统计行）
            m0 = None
            for mm in re.finditer(r"""[$]\s*\(\s*['"]""" + re.escape(cid) + r"""['"]\s*\)""", content):
                m0 = mm
                break
            rendered_self_spaced = False
            if m0:
                tail = content[m0.end(): m0.end() + 2000]
                # 只分析该 map 调用到 .join('') 之间的回调体（避免跨函数误匹配）
                jm = re.search(r'\.map\s*\(.*?\.join\s*\(', tail, re.S)
                if jm:
                    tail = tail[:jm.end()]
                # 渲染回调第一行 HTML 的类 + 内联样式
                rm = re.search(r'\.map\s*\(.*?`?<[^>]*class="([^"]*)"[^>]*>', tail, re.S)
                if rm:
                    rcls = rm.group(1)
                    if any(k in rcls for k in ('list-item', 'tab', 'cat', 'tag', 'msg-item', 'order-tab')):
                        rendered_self_spaced = True
                # 渲染回调内第一段含内联 margin-bottom（自带间距）
                if re.search(r'\.map\s*\(.*?(?:margin-bottom|marginBottom)\s*:\s*\d+px', tail, re.S):
                    rendered_self_spaced = True
                # 渲染回调内含 flex:1（行内均分布局，非垂直卡片列表）
                if re.search(r'\.map\s*\(.*?(?:flex\s*:\s*1|flex:1)', tail, re.S):
                    rendered_self_spaced = True
            if not rendered_self_spaced:
                warnings.append(f'#{cid} 是卡片数组渲染目标（.map().join()）但容器无列表类（{"、".join(LIST_CLASSES[:6])} 等），卡片零间距')

    if fails:
        result.fail('M82', '；'.join(fails))
    elif warnings:
        result.warn('M82', '；'.join(warnings))
    else:
        result.ok('M82', f'列表容器间距校验通过（{len(div_tags)} 个 *List + {len(render_targets)} 个渲染目标容器均含列表类）')


def check_m83_menu_row_structure(content, result, is_template, is_component):
    """M83: 移动端菜单/列表行「两段式」结构契约 — 右箭头必须右对齐

    根因（用户实测）：.mine-menu-item 模板仅对 <i>last-child 推右，子 Agent 用
    <span>文字</span><svg>箭头</svg> 结构时箭头未推到行尾（贴文字）。模板已兼容
    i/svg 两种箭头，但结构必须满足「内容段 + 右侧元素为最后一个子元素」。
    检测规则（对每个 .mine-menu-item / .mine-order-entry / .list-item）：
    1. 行内含 ≥2 个子元素（文字 + svg/i/tag 箭头）时，文字必须包在 <span> 内，
       否则 flex 布局下文字不被 span:first-child{flex:1} 撑开，右侧元素贴文字；
    2. 行内禁止内联 style 里手写 display:flex;justify-content:space-between 排版
       （排版必须走组件类）。
    单段纯文字行（无右侧元素）是合法用法，不拦。
    """
    if is_template or is_component:
        result.ok('M83', '模板/组件文件跳过')
        return
    if not is_mobile_file(content):
        result.ok('M83', '非移动端文件跳过')
        return
    issues = []
    row_cls = r'(?:mine-menu-item|mine-order-entry|list-item)'
    # 1) 两段式但文字未包 span：行开始标签 → 裸文字 → <svg（右箭头）或 <i（箭头）或 <span class="tag
    for tail in (r'<svg\b', r'<i\b', r'<span[^>]*class="[^"]*\btag\b'):
        pat = re.compile(
            r'<[^>]+class="[^"]*\b' + row_cls + r'\b[^"]*"[^>]*>\s*([^<\s][^<]*?)\s*' + tail,
            re.S)
        for m in pat.finditer(content):
            txt = m.group(1).strip()
            if txt:
                issues.append(f'「{m.group(0)[:60].split(">")[0]}>…」行文字未包 <span> 即接右侧元素："{txt[:20]}"（M83：两段式必须 <span>文字</span> + 右侧元素）')
    # 2) 菜单/列表行内联 style 手写 flex/space-between 排版（排版应走组件类）
    inline_layout = re.findall(
        r'<[^>]+class="[^"]*(?:mine-menu-item|mine-order-entry|list-item)[^"]*"[^>]*style="[^"]*(?:justify-content:\s*space-between|display:\s*flex)',
        content)
    if inline_layout:
        issues.append(f'菜单/列表行内联 style 手写 flex/space-between 排版（{len(inline_layout)} 处，应走组件类）（M83）')
    if issues:
        result.fail('M83', '；'.join(issues))
    else:
        result.ok('M83', '菜单/列表行结构契约合规（两段式 + 箭头右对齐）')


def check_m85_mobile_ui_common(content, result, is_template, is_component):
    """M85/M86/M87: 移动端 UI 设计常识 — 返回按钮纯箭头 / 内容 16px 边距 / Tab 横向滚动不换行

    根因（用户实测）：① 二级页返回按钮被内联覆盖成白底阴影方块（真实 App 是透明左箭头）；
    ② page-content 内联 padding:0 让卡片贴边；③ .order-tab flex:1 等分导致 8 个 Tab 挤压换行。
    检测规则（针对子 Agent 产物的内联覆盖与错误结构）：
    1. sub-page-back 内联样式含 background/box-shadow（覆盖成卡片按钮）→ 拦截；
    2. page-content 内联 style 含 padding:0 且页面内有 order-list/card-list（卡片贴边）→ 拦截；
    3. order-tab 容器为 flex:1 或容器无横向滚动（overflow-x）→ 拦截（Tab 会挤压换行）。
    """
    if is_template or is_component:
        result.ok('M85', '模板/组件文件跳过')
        return
    if not is_mobile_file(content):
        result.ok('M85', '非移动端文件跳过')
        return
    issues = []
    # M85 返回按钮：sub-page-back 内联覆盖成卡片按钮/圆形胶囊
    for m in re.finditer(r'<[^>]+class="[^"]*\bsub-page-back\b[^"]*"[^>]*style="([^"]*)"', content):
        s = m.group(1)
        if re.search(r'background|box-shadow|border-radius', s):
            issues.append(f'返回按钮 .sub-page-back 内联 style 含背景/阴影/圆角（"{s[:40]}"），真实 App 返回是方角透明纯箭头（M85）')
    # M86 内容贴边：page-content 内联 padding:0 且含卡片列表（排除分栏布局 display:flex）
    for m in re.finditer(r'<[^>]+class="[^"]*page-content[^"]*"[^>]*style="([^"]*)"', content):
        s = m.group(1)
        is_split_layout = 'display:flex' in s or 'display: grid' in s
        if 'padding:0' in s and not is_split_layout and ('order-list' in content or 'card-list' in content):
            issues.append(f'page-content 内联 padding:0（"{s[:50]}"）覆盖了 16px 左右边距，卡片列表贴手机边框（M86）')
    # M87 Tab 换行：order-tab flex:1 等分 或 容器无横向滚动（overflow-x / drag-scroll）
    tab_bad = False
    # 容器标签缺横向滚动特征（drag-scroll 类也算）
    for m in re.finditer(r'<div\b[^>]*class="([^"]*orders-tabs[^"]*)"', content):
        cls = m.group(1)
        if 'drag-scroll' not in cls and 'overflow-x' not in content[m.start():m.start()+200]:
            tab_bad = True
    # 子 Agent 内联 flex:1 覆盖 order-tab
    if re.search(r'<[^>]+class="[^"]*\border-tab\b[^"]*"[^>]*style="[^"]*flex\s*:\s*1', content):
        tab_bad = True
    # 子 Agent 在 <style> 里重定义 .order-tab 为 flex:1（覆盖模板）
    if re.search(r'\.order-tab\s*\{[^}]*flex\s*:\s*1', content):
        tab_bad = True
    if tab_bad:
        issues.append('订单状态 Tab 存在 flex:1 等分或无横向滚动（drag-scroll），多个 Tab 会挤压换行；应 flex-shrink:0 + 容器横向滚动（M87）')
    if issues:
        result.fail('M85', '；'.join(issues))
    else:
        result.ok('M85', '移动端 UI 设计常识合规（返回纯箭头/16px 边距/Tab 横向滚动）')


def check_m88_control_form(content, result, is_template, is_component):
    """M88: 基础控件「形态完整性」— 内联 style 禁覆盖形态核心属性

    根因（M85 两轮修复教训）：设计常识问题靠"单属性拦截"总有漏——返回按钮先查了
    背景/阴影，漏了圆角（9999px = 圆圈）。本检查聚焦"形态最敏感属性"，一次到位。
    注意：内联 style 用于**布局/数据**（图区高度、价格颜色、数字等宽）是合法用法，
    不得误伤；只拦"与控件标准形态直接冲突"的少数核心属性。

    高置信规则（fail 级）：
      .sub-page-back  返回按钮 = 方角透明纯箭头（禁 background/box-shadow/border-radius）
      .btn-primary    主按钮 = 品牌色实心（禁 background 内联改色）
      .card/.order-card/.product-card/.list-item/.store-card/.tag
                      卡片/列表/标签 = 圆角由类控制（禁 border-radius 内联覆盖）
    """
    if is_template or is_component:
        result.ok('M88', '模板/组件文件跳过')
        return
    if not is_mobile_file(content):
        result.ok('M88', '非移动端文件跳过')
        return
    issues = []
    # 1) 返回按钮：形态核心属性（背景/阴影/圆角）内联覆盖 = 圆圈/卡片按钮
    for m in re.finditer(r'<[^>]+class="[^"]*\bsub-page-back\b[^"]*"[^>]*style="([^"]*)"', content):
        s = m.group(1)
        if re.search(r'background|box-shadow|border-radius', s):
            issues.append(f'返回按钮 .sub-page-back 内联 style 含背景/阴影/圆角（"{s[:45]}"），必须方角透明纯箭头（M88）')
    # 2) 主按钮：内联改背景色（破坏品牌色实心）
    for m in re.finditer(r'<[^>]+class="[^"]*\bbtn-primary\b[^"]*"[^>]*style="([^"]*)"', content):
        s = m.group(1)
        if re.search(r'background', s):
            issues.append(f'主按钮 .btn-primary 内联 style 改背景（"{s[:45]}"），必须品牌色实心（M88）')
    # 3) 卡片/列表/标签：内联覆盖圆角（形态最敏感属性）
    # 注：只用复合类名且排除 -子类（product-card-img 等图区容器是合法渐变+顶部圆角）
    for m in re.finditer(
            r'<[^>]+class="[^"]*\b(?:order-card|store-card|list-item)(?!-)[^"]*"[^>]*style="([^"]*)"'
            r'|<[^>]+class="[^"]*\bproduct-card(?!-)[^"]*"[^>]*style="([^"]*)"',
            content):
        s = m.group(1) or m.group(2) or ''
        if re.search(r'border-radius', s):
            issues.append(f'卡片/列表/标签内联 style 覆盖 border-radius（"{s[:45]}"），圆角由类控制（M88）')
    if issues:
        result.fail('M88', '；'.join(issues))
    else:
        result.ok('M88', '基础控件形态完整性合规（内联未覆盖形态核心属性）')


def check_m101_quantity_nowrap(content, result, is_template, is_component):
    """M101: 量值不换行 — 数字+单位拼接必须用 &nbsp;（防"万/公里"单独折行）

    根因（用户实测）：移动端 JS 用 `+c.price+'万'` 直接拼接数字与单位，
    窄容器/长数字时浏览器把量值断开（如"¥15.8"换行"万"），真实 App 绝无此现象。
    检测：JS 字符串拼接中，数字变量 + 中文单位（万/公里/元/年）未用 &nbsp; 分隔。
    放行：已用 &nbsp; / 非数字变量 / 静态文本（无法机械判断的）。
    """
    if is_template or is_component:
        result.ok('M101', '模板/组件文件跳过')
        return
    if not is_mobile_file(content):
        result.ok('M101', '非移动端文件跳过')
        return
    issues = []
    # 数字变量 + 中文单位拼接，未用 &nbsp;（允许 &nbsp; 已在单位前）
    pat = re.compile(
        r"\+?\s*[\w.]+\s*\+\s*'([^']*(?:万|公里|元|年)[^']*)'"
    )
    for m in pat.finditer(content):
        unit_part = m.group(1)
        # 排除已用 &nbsp; 的
        if '&nbsp;' in unit_part:
            continue
        # 仅当单位紧贴数字（无空格）时才可能是量值断行源
        # 形如 '万' 或 '万公里' 或 '万元'
        if re.match(r'^(万|公里|万元|万公里|元|年)(?:\s|&|$|<|>|"|\')', unit_part):
            issues.append(f'JS 数字+单位拼接未用 &nbsp;（"{unit_part[:15]}"），窄容器会折行（M101：数字与单位必须用 &nbsp; 连接）')
    if issues:
        result.fail('M101', '；'.join(sorted(set(issues))[:5]))
    else:
        result.ok('M101', '量值拼接合规（数字+单位用 &nbsp; 或非量值）')


def check_m111_clickable_divs(content, result, is_template, is_component):
    """M111: 可点语义 div 必须有 onclick — 禁止"可点样式 + 无交互"死按钮

    根因（茶叶商城事故）：工作台统计卡（work-stat）/待办（todo-item）/菜单项
    （mine-menu-item）使用 cursor:pointer 可点样式但未绑定 onclick，用户点击无反应；
    生成时若用 --no-verify 跳过浏览器断言，B6 运行时检查无法兜底，死按钮漏网交付。
    本检查在静态层兜底：剔除 <script> 与 HTML 注释后，扫描这些可点语义类的
    静态元素，无 onclick 即 fail。
    分层：静态 HTML 死按钮由本检查拦截；JS 动态渲染的死按钮由 browser-check B6
    （交付前 G5 强制复核）拦截，双层保险。
    """
    if is_template or is_component:
        result.ok('M111', '模板/组件文件跳过')
        return
    if not is_mobile_file(content):
        result.ok('M111', '非移动端文件跳过')
        return
    # 剔除 <script> 块与 HTML 注释（JS 动态渲染/隐藏示例不参与静态检查）
    stripped = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.S)
    stripped = re.sub(r'<!--.*?-->', '', stripped, flags=re.S)
    # 可点语义类 → 静态元素必须含 onclick（每类报一条，避免刷屏）
    # 注意类名必须完整匹配（(?<![\w-])/(?![\w-]) 防止 work-stat-num/lbl 子元素被误匹配，
    # \b 词边界无法区分 work-stat 与 work-stat-num，实测误报）
    clickable_classes = ['work-stat', 'todo-item', 'mine-menu-item']
    issues = []
    for cls in clickable_classes:
        for m in re.finditer(
            r'<(?:div|li|a)[^>]*class="[^"]*(?<![\w-])' + re.escape(cls) + r'(?![\w-])[^"]*"[^>]*>',
            stripped
        ):
            if 'onclick' not in m.group(0):
                issues.append(
                    f'<{cls}> 无 onclick（死按钮：可点样式但无交互——统计卡应跳转列表、'
                    f'待办应进详情/处理、菜单项应绑交互；纯展示请改用非可点类）'
                )
                break
    if issues:
        result.fail('M111', '；'.join(issues[:5]))
    else:
        result.ok('M111', '可点语义元素均有 onclick（无死按钮）')


def check_m112_subpage_title(content, result, is_template, is_component):
    """M112: 子页面标题必须带 class="sub-page-title" — 禁止裸 <span> 标题靠左

    根因（茶叶商城事故）：.sub-page-nav 内标题写成裸 <span>新增商品</span> 未带
    class="sub-page-title"。.sub-page-title{position:absolute;left:50%;transform:
    translateX(-50%)} 是标题居中的唯一机制——漏掉 class 标题就退回文档流靠左。
    模板 CSS 正确、示例正确，但产物注入时 class 被省略，两端移动端 24 个子页面
    全部中招；旧 lint 只有 M85/M88 查返回按钮、browser-check 无标题断言，双层盲区
    导致漏网交付。
    检测规则：剔除 <script>/注释后，对每个 .sub-page-nav 块，若内部存在无 class 的
    裸 <span>标题</span>（非返回按钮、非箭头），即 fail。
    """
    if is_template or is_component:
        result.ok('M112', '模板/组件文件跳过')
        return
    if not is_mobile_file(content):
        result.ok('M112', '非移动端文件跳过')
        return
    stripped = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.S)
    stripped = re.sub(r'<!--.*?-->', '', stripped, flags=re.S)
    issues = []
    for m in re.finditer(
        r'<div\s+class="[^"]*\bsub-page-nav\b[^"]*"[^>]*>([\s\S]*?)</div>\s*</div>',
        stripped
    ):
        block = m.group(1)
        for t in re.finditer(r'<span\s*>([^<]*)</span>', block):
            txt = t.group(1).strip()
            if txt:
                issues.append(
                    f'.sub-page-nav 内标题「{txt[:12]}」为裸 <span>，必须写成 '
                    f'<span class="sub-page-title">（否则标题靠左不居中）'
                )
                break
    if issues:
        result.fail('M112', '；'.join(sorted(set(issues))[:5]))
    else:
        result.ok('M112', '所有子页面标题均带 class="sub-page-title"（居中合规）')


def check_m113_grid_layout(content, result, is_template, is_component):
    """M113: 卡片/功能区网格布局完整性 — 禁止孤卡（卡片数与列数不整除）

    根因（茶叶商城事故）：.work-stats 是 3 列网格，工作台塞 4 个统计卡 → 3+1，
    第四行只剩「总收入」一个孤卡、右侧大片留白，视觉不协调。
    规则（静态层，覆盖已知网格容器）：
      1. .work-stats：子卡片数 % 列数（默认 3，内联 style 可覆盖）!= 0 → fail；
         存在跨行大卡 .work-stat-main（grid-column:1/-1 占满整行）时，只校验小卡数
         % 列数 == 0（「大卡 + 3 小卡」是标准组合，不产生孤卡）
      2. .work-quick：子项数 % 4 != 0 → fail
      3. .home-cats：子项数 % 5 != 0 → fail
    其他网格容器 / JS 动态渲染的网格由 browser-check B21 运行时兜底（通用扫描）。
    """
    if is_template or is_component:
        result.ok('M113', '模板/组件文件跳过')
        return
    if not is_mobile_file(content):
        result.ok('M113', '非移动端文件跳过')
        return
    stripped = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.S)
    stripped = re.sub(r'<!--.*?-->', '', stripped, flags=re.S)

    def grid_block(html, start):
        """从容器开标签结束位置起，返回容器闭合前的内容（div 深度归零）。"""
        depth = 1
        i = start
        while i < len(html):
            o = html.find('<div', i)
            c = html.find('</div>', i)
            if c == -1:
                return None
            if o != -1 and o < c:
                gt = html.find('>', o)
                depth += 1
                i = gt + 1
            else:
                depth -= 1
                if depth == 0:
                    return html[start:c]
                i = c + 6
        return None

    issues = []
    # (容器类, 子卡片类, 默认列数, 是否支持跨行大卡)
    specs = [
        ('work-stats', 'work-stat', 3, True),
        ('work-quick', 'work-quick-item', 4, False),
        ('home-cats', 'home-cat', 5, False),
    ]
    for cls, child, default_cols, has_main in specs:
        for m in re.finditer(
            r'<div[^>]*class="[^"]*(?<![\w-])' + re.escape(cls) + r'(?![\w-])[^"]*"[^>]*>',
            stripped
        ):
            tag = m.group(0)
            cols = default_cols
            sm = re.search(r'grid-template-columns:\s*repeat\((\d+),', tag)
            if sm:
                cols = int(sm.group(1))
            block = grid_block(stripped, m.end())
            if block is None:
                continue
            child_re = r'<div[^>]*class="[^"]*(?<![\w-])' + re.escape(child) + r'(?![\w-])[^"]*"[^>]*>'
            n = len(re.findall(child_re, block))
            main_re = r'<div[^>]*class="[^"]*(?<![\w-])' + re.escape(cls) + r'-main(?![\w-])[^"]*"[^>]*>'
            main_n = len(re.findall(main_re, block)) if has_main else 0
            if n == 0 and main_n == 0:
                issues.append(f'<{cls}> 网格容器内无卡片（空容器）')
                continue
            if main_n:
                if n % cols != 0:
                    issues.append(
                        f'<{cls}> 大卡(.{cls}-main)+{n} 个小卡：小卡数非列数({cols})整数倍，'
                        f'仍会产生孤卡留白（标准组合=大卡+{cols}小卡）'
                    )
            else:
                if n % cols != 0:
                    issues.append(
                        f'<{cls}> {n} 个卡片在 {cols} 列网格 = 孤卡留白（如 3+1），'
                        f'卡片数必须为列数整数倍，或改用跨行大卡(.<cls>-main)+{cols}小卡'
                    )
    if issues:
        result.fail('M113', '；'.join(sorted(set(issues))[:5]))
    else:
        result.ok('M113', '网格卡片数量与列数匹配（无孤卡留白）')


def check_m114_css_var_ref(content, result, is_template, is_component):
    """M114: CSS 变量引用必须已定义 — 禁止引用未定义变量导致样式整条失效

    根因（茶叶商城事故）：.work-stat-main 渐变背景写成
    `linear-gradient(135deg,var(--brand),var(--brand-hover))`，但 :root 只定义了
    --brand/--brand-light/--brand-bg/--brand-rgb，**没有 --brand-hover**——变量未定义
    时整个 background 声明被浏览器判为无效而丢弃，卡片回退默认白底，而文字 color:#fff
    → 白字白底看不清。
    规则：收集文件中所有 `--xxx:` 变量定义，扫描全部 `var(--xxx)` 引用，
    引用了未定义变量且无 fallback（`var(--xxx, 兜底值)`）即 fail。
    覆盖全部端型（移动端/桌面端/PRD），白字白底另有 browser-check B22 运行时兜底。
    """
    if is_template or is_component:
        result.ok('M114', '模板/组件文件跳过')
        return
    defined = {'--' + m.group(1) for m in re.finditer(r'--([a-zA-Z0-9_-]+)\s*:', content)}
    issues = set()
    for m in re.finditer(r'var\(\s*(--[a-zA-Z0-9_-]+)\s*(?:,\s*[^)]+)?\)', content):
        var = m.group(1)
        # --fa-* 为 Font Awesome 库内部变量（自带 fallback 机制），豁免
        if var.startswith('--fa-'):
            continue
        # 带 fallback（var(--x, 兜底值)）的引用是安全写法，不报
        tail = m.group(0).split(var, 1)[1]
        if ',' in tail:
            continue
        if var not in defined:
            issues.add(var)
    if issues:
        result.fail('M114', 'CSS 变量未定义却被引用（样式声明会整条失效，如白字白底）: ' + ', '.join(sorted(issues)))
    else:
        result.ok('M114', '所有 CSS 变量引用均有定义（无样式静默失效）')


def check_m115_startup_render(content, result, is_template, is_component):
    """M115: 启动渲染铁律（D49 防护）— 多页面移动端必须由 init() 统一执行初始渲染

    根因（茶叶商城事故）：注入端定义了 init() 与 10+ 个 render 函数
    （renderCart/renderOrders/renderNewArrival/renderCategorySidebar…），但模板启动
    只调用 renderHomeProducts，init() 从未执行 → 分类/购物车/订单/新品页全部空白，
    而「我的订单」入口因直接调用 goOrderTab→renderOrders 反而有数据（同一页面两种
    表现，数据存在却渲染不出）。
    规则：
      1) 存在 ≥2 个主页面容器（.page）时，脚本必须定义 init()（模板启动统一调用），
         或注入端自建 DOMContentLoaded 监听器统一调用全部 render 函数（商家端模式）；
      2) 定义了 init() 时，其函数体必须实际调用 ≥2 个 render* 函数（防空壳 init）；
      3) 未定义 init() 且无自建 DOMContentLoaded 渲染监听器，存在 ≥2 个 render* 函数
         定义即 fail（模板只兜底首页渲染，其余页面渲染函数成为永不执行的死代码 → 空白）。
    运行时兜底见 browser-check B23（所有主 Tab 页渲染目标非空）。
    """
    if is_template or is_component:
        result.ok('M115', '模板/组件文件跳过')
        return
    if 'phone-frame' not in content and 'sub-page' not in content:
        result.ok('M115', '非移动端文件跳过')
        return
    # 1. 主页面容器数（class="page …" 但排除 class="sub-page"）
    page_cnt = len(re.findall(r'<div class="page(?:\s|")', content))
    if page_cnt < 2:
        result.ok('M115', f'单页面/无多 Tab 结构（主页面容器 {page_cnt} 个），跳过')
        return
    render_funcs = set(re.findall(r'function\s+(render[A-Z]\w*)\s*\(', content))
    has_init = bool(re.search(r'function\s+init\s*\(', content))
    issues = []
    if not has_init:
        if len(render_funcs) >= 2:
            # 豁免：注入端自建 DOMContentLoaded 监听器统一调用渲染（商家端模式，合规）
            dcl_calls = 0
            for m in re.finditer(r'(?:document|window)\.addEventListener\(\s*[\'"]DOMContentLoaded[\'"]\s*,\s*function\s*\([^)]*\)\s*\{', content):
                seg = content[m.end():m.end() + 3000]
                dcl_calls = max(dcl_calls, len(set(re.findall(r'(render[A-Z]\w*)\s*\(', seg))))
            if dcl_calls < 2:
                issues.append(f'多页面({page_cnt}个)但未定义 init() 且无 DOMContentLoaded 统一渲染'
                              f'（模板只兜底首页，{len(render_funcs)} 个 render 函数将永不执行 → Tab 页/子页面空白）：'
                              + ', '.join(sorted(render_funcs)))
    else:
        im = re.search(r'function\s+init\s*\(', content)
        seg = content[im.end():im.end() + 4000]
        called = set(re.findall(r'(render[A-Z]\w*)\s*\(', seg))
        if len(called) < 2:
            issues.append(f'init() 函数体只调用了 {len(called)} 个 render 函数（应为空壳 init，'
                          f'页面渲染不完整）：' + ', '.join(sorted(called)))
    if issues:
        result.fail('M115', '；'.join(issues))
    else:
        result.ok('M115', f'启动渲染合规（{page_cnt} 个主页面，渲染入口已覆盖 {len(render_funcs)} 个渲染函数）')


def check_m116_cart_component(content, result, is_template, is_component):
    """M116: 购物车标准组件铁律（D50 防护）— 所有移动端购物车必须复用标准组件

    标准结构（市面通用，模板 prototype-mobile.html 已内置 CSS）：
      cart-list > cart-item(勾选 cart-check + 缩略图 cart-thumb + 信息区 cart-info
      [名称 cart-name/规格 cart-spec/单价 cart-price] + 数量步进 cart-qty-btn
      + 删除 cart-del) + cart-bar(全选 + 合计 + 结算 三要素缺一不可) + cart-empty 空态。
    根因（茶叶商城事故）：购物车 Tab 渲染函数未执行 → 只剩底部按钮（全选/结算），
    用户要求购物车做成标准组件，以后所有移动端直接复用（不得另起炉灶）。
    """
    if is_template or is_component:
        result.ok('M116', '模板/组件文件跳过')
        return
    if 'phone-frame' not in content and 'sub-page' not in content:
        result.ok('M116', '非移动端文件跳过')
        return
    if 'cart' not in content.lower():
        result.ok('M116', '无购物车页面，跳过')
        return
    issues = []
    # 1. 底部结算栏三要素（全选/合计/结算）
    bar_idx = content.find('<div class="cart-bar"')
    if bar_idx == -1:
        issues.append('缺少 .cart-bar 底部结算栏（M116 标准组件：全选+合计+结算三要素）')
    else:
        seg = content[bar_idx:bar_idx + 1200]
        for kw in ('全选', '合计', '结算'):
            if kw not in seg:
                issues.append(f'.cart-bar 缺少「{kw}」要素（M116 标准组件三要素缺一不可）')
    # 2. 数量步进器
    if 'cart-qty-btn' not in content:
        issues.append('购物车条目缺少数量步进器 .cart-qty-btn（M116 标准组件：- 数量 +）')
    # 3. 空态兜底
    if 'cartEmpty' not in content and 'cart-empty' not in content:
        issues.append('购物车缺少空态兜底（cartEmpty 图标+文案+去逛逛，M116 标准组件）')
    if issues:
        result.fail('M116', '；'.join(issues))
    else:
        result.ok('M116', '购物车为标准组件结构（列表+数量步进+底栏三要素+空态）')


def check_m117_filter_tabs_sticky(content, result, is_template, is_component):
    """M117: 筛选标签栏 sticky 铁律（D51 防护）— 订单/状态/筛选 tabs 必须固定在页面顶部

    根因（茶叶商城事故）：订单页「全部/待支付/待发货」筛选栏未 sticky，随列表内容
    一起滚动出视口（用户原话：这是基本常识）。模板 .orders-tabs 已内置
    position:sticky;top:8px（top 必须等于 .page-content padding-top，否则初始即被
    sticky 下推与首条内容重叠）。
    规则：产物中若出现自定义筛选容器类（类名以 tabs 结尾），其 CSS 定义必须
    position:sticky；复用模板 .orders-tabs 的视为合规（模板已 sticky）。
    """
    if is_template or is_component:
        result.ok('M117', '模板/组件文件跳过')
        return
    if 'phone-frame' not in content and 'sub-page' not in content:
        result.ok('M117', '非移动端文件跳过')
        return
    custom_tabs = set()
    for m in re.finditer(r'class="([^"]*\btabs\b[^"]*)"', content):
        for cls in m.group(1).split():
            if cls.endswith('tabs') and cls != 'orders-tabs':
                custom_tabs.add(cls)
    issues = []
    for cls in sorted(custom_tabs):
        if not re.search(r'\.' + re.escape(cls) + r'\{[^}]*position:\s*sticky', content):
            issues.append(f'筛选容器 .{cls} 未 position:sticky（M117：筛选栏必须固定在顶部不随内容滚动）')
    if issues:
        result.fail('M117', '；'.join(issues))
    else:
        result.ok('M117', '筛选标签栏均 sticky 固定（复用模板 .orders-tabs 或自定义含 sticky）')


def check_m119_category_sidebar_sticky(content, result, is_template, is_component):
    """M119: 分类页左侧类别栏 sticky+间距 铁律（茶叶商城事故防护）

    根因（茶叶商城事故）：分类页左侧「绿茶/红茶/乌龙…」类别栏未固定，随右侧商品卡
    片一起滚动出视口；且类别栏与商品卡片之间无间距（用户原话：这是低级错误、基本
    常识）。
    正确写法（模板/产物通用）：
        <div style="display:flex;min-height:100%;gap:14px;align-items:flex-start">
          <div style="width:86px;flex-shrink:0;position:sticky;top:8px" id="categorySidebar">…
        </div>
    铁律：① 左侧栏容器必须 position:sticky（top 需等于 .page-content padding-top 8px，
    否则初始即被下推与内容重叠）；② 侧栏必须给 flex 子项 align-self:flex-start，否则
    侧栏被 stretch 撑满全高、sticky 失去滚动空间而失效；③ 双栏 flex 父容器必须设置
    gap 以在类别栏与卡片之间留出间距。
    """
    if is_template or is_component:
        result.ok('M119', '模板/组件文件跳过')
        return
    if 'phone-frame' not in content and 'sub-page' not in content:
        result.ok('M119', '非移动端文件跳过')
        return
    # v5.41 净化扫描源：剥 HTML/CSS 注释，防模板「教学注释示例」（#categorySidebar 字样）误触发
    content = _safe_scan_text(content)
    # 仅当存在分类双栏骨架（侧栏容器或渲染函数）才检查
    if 'categorySidebar' not in content:
        result.ok('M119', '无分类页侧栏骨架，跳过')
        return
    issues = []
    # 1. 侧栏容器必须 sticky + top
    if not re.search(r'id=["\']categorySidebar["\'][^>]*position:\s*sticky', content) and \
       not re.search(r'position:\s*sticky[^>]*id=["\']categorySidebar["\']', content):
        issues.append('categorySidebar 未 position:sticky（分类栏必须固定不随内容滚动）')
    if 'categorySidebar' in content and re.search(r'id=["\']categorySidebar["\'][^>]*top:\s*8px', content) is None and \
       re.search(r'top:\s*8px[^>]*id=["\']categorySidebar["\']', content) is None:
        issues.append('categorySidebar sticky 的 top 应为 8px（等于 .page-content padding-top，防下推重叠）')
    # 2. 侧栏所在 flex 父容器必须 align-items:flex-start，否则 stretch 撑满使 sticky 失效
    if not re.search(r'align-items\s*:\s*flex-start', content):
        issues.append('分类双栏父容器缺 align-items:flex-start（侧栏被 stretch 撑满全高，sticky 会失效）')
    # 3. 双栏父容器必须 gap（类别栏与卡片之间留出间距）
    if not re.search(r'display\s*:\s*flex[^>]*\)?;?[^"]*?\bgap\s*:', content) and \
       not re.search(r'\bgap\s*:\s*\d+px', content):
        issues.append('分类双栏父容器缺 gap（类别栏与商品卡片之间应有间距）')
    if issues:
        result.fail('M119', '；'.join(issues))
    else:
        result.ok('M119', '分类侧栏 sticky+flex-start+gap 均已满足')


def check_m118_detail_bar_buttons(content, result, is_template, is_component):
    """M118: 底部操作栏按钮响应式铁律（D52 防护）— 禁止右侧留白、必须伸缩填满

    根因（茶叶商城事故）：商品详情页底部「加入购物车/立即购买」两按钮后大片留白——
    模板 `.detail-bar .btn{flex:0 0 auto}` 按钮按内容宽度排布不伸缩填满。
    行业常规（微信小程序详情页/CommerceActionBar）：底部栏主行为按钮宽度加倍
    （flex 2:1）、辅按钮等分（flex 1）、多按钮必须填满整行；单按钮自适应居中。
    模板已内置规范：`.detail-bar > .btn{flex:1 3 0}`（辅）+ `.btn-primary{flex:2 1 0}`
    （主）+ `.btn:only-child` 居中。本检查防注入端覆盖为"不伸缩"。
    """
    if is_template or is_component:
        result.ok('M118', '模板/组件文件跳过')
        return
    if 'phone-frame' not in content and 'sub-page' not in content:
        result.ok('M118', '非移动端文件跳过')
        return
    if 'detail-bar' not in content:
        result.ok('M118', '无底部操作栏（detail-bar），跳过')
        return
    issues = []
    # 1. 禁止把 detail-bar 按钮设为不伸缩（flex:0 0 auto / flex:none → 右侧留白）
    for pat in (r'\.detail-bar\s+\.btn\{[^}]*flex:\s*(?:0\s+0\s+auto|none)',
                r'\.detail-bar\s*>\s*\.btn\{[^}]*flex:\s*(?:0\s+0\s+auto|none)'):
        if re.search(pat, content):
            issues.append('底部操作栏按钮被设为 flex:0 0 auto / flex:none（不伸缩 → 右侧留白，M118）')
            break
    # 2. 自定义 .detail-bar > .btn 规则若存在但无 flex 伸缩 → fail（自建样式必须伸缩填满）
    m = re.search(r'\.detail-bar\s*>\s*\.btn\{([^}]*)\}', content)
    if m:
        seg = m.group(1)
        if 'flex:1' not in seg and 'flex:2' not in seg and 'flex-grow' not in seg:
            issues.append('自定义 .detail-bar > .btn 规则无 flex 伸缩（按钮不填满整行，M118）')
    if issues:
        result.fail('M118', '；'.join(issues))
    else:
        result.ok('M118', '底部操作栏按钮为响应式伸缩布局（主按钮 flex:2 更宽 / 辅按钮填满）')


def check_m120_cartbar_bottom_pin(content, result, is_template, is_component):
    """M120: 底部结算栏固定铁律（D54 防护）— 结算/全选栏必须压到底部导航上方，禁止悬在中间

    根因（茶叶商城事故）：购物车「全选+合计+结算」栏 position:sticky;bottom:0，但购物车
    页面容器(.page)是默认 block 且非 flex 列 → 空购物车/内容少时，.page-content 的
    min-height:100% 因父级(.page)auto 高度不解析而无法撑满滚动区，结算栏紧跟在内容后
    方，悬浮在界面中间，距离底部悬浮导航过远。
    铁律（模板 M120/D54 已内置，本检查防注入端覆盖）：
      ① #page-cart（或含 .cart-bar 的页面）必须是 flex 列：display:flex + flex-direction:column
         + min-height:100%，且用 data-display="flex" 声明（否则 switchTab 内联 display:block
         覆盖 flex、破坏底栏固定）；
      ② .cart-bar 必须 margin-top:auto（短内容/空态时仍被压到页面底部）；
      ③ .cart-bar 必须 position:sticky 且底部偏移 ≥ 浮动导航外露高度（通常 bottom 与页面
         padding-bottom 一致，保证长列表滚动时吸附在导航上方）。
    """
    if is_template or is_component:
        result.ok('M120', '模板/组件文件跳过')
        return
    if 'phone-frame' not in content and 'sub-page' not in content:
        result.ok('M120', '非移动端文件跳过')
        return
    # v5.41 净化扫描源：剥 HTML/CSS 注释，防模板「教学注释示例」（.cart-bar 字样）误触发
    content = _safe_scan_text(content)
    # 触发判定必须基于「DOM 实际使用」（class 属性出现 cart-bar）：模板内置的
    # .cart-bar{...} 组件 CSS 定义会让任何无购物车页面的产物命中 'cart-bar' 字样，
    # 继而被下面三条 DOM/CSS 断言打回（v5.41 实测最小产物误报根因）。
    # 断言阶段仍用含 <style> 的全文：真实使用场景允许由组件 CSS 或内联 style 满足。
    dom_scan = re.sub(r'<style\b[^>]*>.*?</style>', '', content, flags=re.DOTALL)
    if not re.search(r'class="[^"]*\bcart-bar\b[^"]*"', dom_scan):
        result.ok('M120', '产物未使用结算栏组件（仅模板内置 CSS 定义），跳过')
        return
    if 'cart-bar' not in content:
        result.ok('M120', '无底部结算栏（cart-bar），跳过')
        return
    issues = []
    # 1. 结算栏必须 margin-top:auto（短内容兜底，防悬中间）
    if not re.search(r'cart-bar[^>]*margin-top\s*:\s*auto', content) and \
       not re.search(r'\.cart-bar\{[^}]*margin-top\s*:\s*auto', content):
        issues.append('cart-bar 缺 margin-top:auto（内容少时会悬停在界面中间，M120）')
    # 2. 结算栏必须 position:sticky
    if not re.search(r'cart-bar[^>]*position\s*:\s*sticky', content) and \
       not re.search(r'\.cart-bar\{[^}]*position\s*:\s*sticky', content):
        issues.append('cart-bar 缺 position:sticky（长列表滚动时结算栏应吸附底部，M120）')
    # 3. 页面容器必须 flex 列（用 data-display="flex" 防 switchTab 覆盖）
    if 'data-display="flex"' not in content:
        issues.append('含 cart-bar 的页面容器未用 data-display="flex"（switchTab 内联 display:block 会覆盖 flex，结算栏无法固定底部，M120）')
    # 4. 页面容器必须 flex 列 + min-height:100%
    cart_page_ok = re.search(r'display\s*:\s*flex[^"]*flex-direction\s*:\s*column[^"}}]*min-height\s*:\s*100%', content) or \
                   re.search(r'display\s*:\s*flex[^"]*min-height\s*:\s*100%[^"}}]*flex-direction\s*:\s*column', content)
    if not cart_page_ok:
        issues.append('含 cart-bar 的页面容器不是「flex 列 + min-height:100%」，无法把结算栏压到底部（M120）')
    if issues:
        result.fail('M120', '；'.join(issues))
    else:
        result.ok('M120', '结算栏已 flex 列固定 + margin-top:auto + sticky（底部导航上方）')


def check_m121_category_sidebar_item_gap(content, result, is_template, is_component):
    """M121: 分类侧栏「分类项之间」垂直间距铁律（D55 防护）— 绿茶/红茶/乌龙…分类卡片不得紧贴

    根因（茶叶商城事故）：分类页左侧 #categorySidebar 是普通块级容器，由
    renderCategorySidebar() 填入的 .shop-cat 分类项（绿茶/红茶/乌龙/普洱/白茶）直接
    上下堆叠，无 gap 也无 margin → 各分类卡片彼此紧贴、无任何垂直间距（用户原话：
    红茶背后的卡片跟红茶的卡片没有任何间距）。
    注：M119 只查「侧栏与商品卡之间的横向 gap」，本规则补查「侧栏内部项与项之间」。
    正确写法（模板/产物通用）：
        <div style="width:86px;...;display:flex;flex-direction:column;gap:8px"
             id="categorySidebar">
    铁律：含 id="categorySidebar" 的容器必须 display:flex + flex-direction:column +
    显式 gap（在容器上用 gap 留垂直间距，禁止依赖每项内联 padding 凑间距）。
    """
    if is_template or is_component:
        result.ok('M121', '模板/组件文件跳过')
        return
    if 'phone-frame' not in content and 'sub-page' not in content:
        result.ok('M121', '非移动端文件跳过')
        return
    # v5.41 净化扫描源：同 M119（教学注释示例字样防误触发）
    content = _safe_scan_text(content)
    # 仅当存在分类侧栏骨架（侧栏容器或渲染函数）才检查
    if 'categorySidebar' not in content:
        result.ok('M121', '无分类页侧栏骨架，跳过')
        return
    # 找到 categorySidebar 所在的起始标签（含其内联 style），再进行三条子断言
    tag = None
    for tp in (r'<[^>]*id=["\']categorySidebar["\'][^>]*>',
               r'<[^>]*\bid=["\']categorySidebar["\'][^>]*>',
               r'<[^>]*id=["\']categorySidebar["\'][^>]*?>\s*</'):
        m = re.search(tp, content)
        if m:
            tag = m.group(0)
            break
    if not tag:
        result.ok('M121', '未定位到 categorySidebar 起始标签，跳过')
        return
    issues = []
    if 'flex-direction:column' not in tag:
        issues.append('categorySidebar 缺 flex-direction:column（分类项应纵向排列，M121）')
    if 'display:flex' not in tag:
        issues.append('categorySidebar 缺 display:flex（无法用 gap 在分类项之间留垂直间距，M121）')
    if not re.search(r'gap:\s*\d+', tag):
        issues.append('categorySidebar 缺显式 gap（分类项彼此紧贴无垂直间距，M121）')
    # 禁止把每项内联 padding 当间距（副作用是分类项被撑胖，且视觉上仍无独立间隔）
    if re.search(r'categorySidebar["\'][^>]*', content) and re.search(
            r'style="[^"]*13px[^"]*padding:\s*14px\s*8px', content):
        issues.append('发现分类项内联 padding:14px 8px（应以容器 gap 留间距，而非用 padding 凑，M121）')
    if issues:
        result.fail('M121', '；'.join(issues))
    else:
        result.ok('M121', '分类侧栏已是 flex 列 + gap，分类项之间间距正确')


def check_template_brand_placeholder(content, result, is_template, is_component):
    """T-BRAND: 模板品牌名占位符检查（D43 防护）— 模板品牌名位置必须用 {{项目名称}}
    根因（茶叶商城/舒享到家事故）：V3 模板从旧项目派生时 brandName/欢迎卡/设置页
    平台名/openGuide 4 处硬编码旧品牌名"舒享到家"，未用 {{项目名称}} 占位符，
    导致所有用该模板的项目品牌名错误（config 正确无用）。
    检查：模板文件中品牌名特征位置（brandName 元素/欢迎卡/settingsBody 平台名/
    openGuide 新手引导）必须包含 {{项目名称}} 占位符，硬编码具体品牌名即 fail。
    仅检查含品牌名特征的模板，无特征模板自动通过（不误伤 mobile/prd 等）。
    """
    if not is_template:
        result.ok('T-BRAND', '非模板文件跳过（产物品牌名由 build 校验 config.project）')
        return
    issues = []
    # 1. 顶栏 brandName 元素必须用占位符
    if 'id="brandName"' in content:
        m = re.search(r'id="brandName">([^<]*)<', content)
        if m and m.group(1).strip() != '{{项目名称}}':
            issues.append(f'brandName 内容 "{m.group(1).strip()}" 应为 {{项目名称}} 占位符（D43）')
    # 2. 欢迎卡品牌名
    if '欢迎回到' in content:
        m = re.search(r'欢迎回到[^<]*?管理后台', content)
        if m and '{{项目名称}}' not in m.group(0):
            issues.append('欢迎卡品牌名未用 {{项目名称}} 占位符（D43）')
    # 3. settingsBody 平台名称输入框 value
    if 'settingsBody' in content:
        for line in content.split('\n'):
            if 'settingsBody' in line and 'innerHTML' in line and '平台名称' in line:
                if '{{项目名称}}' not in line:
                    issues.append('settingsBody 平台名称未用 {{项目名称}} 占位符（D43）')
                break
    # 4. openGuide 新手引导品牌名
    if 'openGuide' in content and '欢迎使用' in content:
        m = re.search(r'欢迎使用「[^」]*」', content)
        if m and '{{项目名称}}' not in m.group(0):
            issues.append(f'新手引导品牌名 "{m.group(0)}" 未用 {{项目名称}} 占位符（D43）')
    if issues:
        result.fail('T-BRAND', '；'.join(issues[:4]))
    else:
        result.ok('T-BRAND', '模板品牌名均已占位符化（{{项目名称}}）')


def check_mobile_ui_standards(content, result, is_template, is_component):
    """M54: 移动端 UI 规范 — 零滚动条/宫格不被覆盖/底部固定栏/蒙版隐藏/导航自适应"""
    if is_template or is_component:
        return
    if 'phone-frame' not in content and 'sub-page' not in content:
        return
    issues = []
    # 1. 分类宫格禁止被内联 flex 覆盖（滚动条+换行根因）
    if 'class="home-cats"' in content and re.search(r'class="home-cats[^"]*"[^>]*style="[^"]*display:flex', content):
        issues.append('home-cats 被内联 display:flex 覆盖（应保持模板 5 列宫格，禁止横向滚动）（M54）')
    # 2. detail-bar 必须固定底部（absolute）
    if 'detail-bar' in content and re.search(r'\.detail-bar\{[^}]*position:sticky', content):
        issues.append('.detail-bar 使用了 sticky（应 absolute 固定二级页底部）（M54）')
    # 3. nav-mask 必须有隐藏逻辑（二级页蒙版残留）
    if 'nav-mask' in content and 'nav-mask.hide' not in content:
        issues.append('nav-mask 缺少 .hide 隐藏规则（二级页面会残留渐变蒙版）（M54）')
    if 'nav-mask' in content and "classList.add('hide')" not in content and 'classList.add("hide")' not in content:
        issues.append('openSubPage 未隐藏 nav-mask（二级页面残留首页蒙版）（M54）')
    # 4. 悬浮导航胶囊形 + 52px 高 + 双模式（M56）
    if '.bottom-nav' in content:
        if re.search(r'\.bottom-nav\{[^}]*border-radius:24px', content):
            issues.append('.bottom-nav 圆角应为 999px 胶囊形（24px 圆角会导致卡片不是 100% 圆角）（M56）')
        if re.search(r'\.bottom-nav\{[^}]*min-height:56px', content):
            issues.append('.bottom-nav 高度应为固定 52px（min-height:56px 会撑高卡片）（M56）')
        if re.search(r'\.bottom-nav\{[^}]*height:auto[^}]*min-height', content):
            issues.append('.bottom-nav 应为固定 52px 高（height:auto 导致高度异常）（M56）')
        # 发布 tab 禁止撑高（min-height 50-99px 均违规）
        if re.search(r'\.nav-tab\[data-tab="publish"\]\{[^}]*min-height:[5-9][0-9]px', content):
            issues.append('发布 tab min-height 过高（应 ≤44px，避免撑高悬浮卡片）（M56）')
        # nav-fab 模式必须有 fab-icon；有 fab-icon 必须标记 nav-fab（只检测 HTML 用法，CSS 定义不算）
        html_nav_fab = re.search(r'<div class="bottom-nav[^"]*nav-fab', content)
        html_fab_icon = re.search(r'<div class="[^"]*\bfab-icon\b', content)
        if html_fab_icon and not html_nav_fab:
            issues.append('使用 fab-icon 凸起按钮必须给 bottom-nav 加 nav-fab 模式类（M56）')
        if html_nav_fab and not html_fab_icon:
            issues.append('bottom-nav 标记 nav-fab 但缺少 fab-icon（凸起按钮类缺失）（M56）')
        # nav-tab 禁止固定 height（会 flex 压缩压扁圆形按钮）——仅匹配独立 .nav-tab 规则（行首）
        if re.search(r'(?:^|\n)\.nav-tab\{[^}]*height:5[0-9]px', content):
            issues.append('.nav-tab 固定高度会压缩凸起圆形按钮（应 height:auto 内容自适应）（M56）')
    # 5. 商品卡片占位图：必须手绘内联 SVG + 图区固定高度（M57，修复图区塌陷+字体依赖）
    if 'product-card' in content:
        # 5.1 禁止 fa-solid 占位图标（字体依赖 + 图区无高度会塌陷）
        if re.search(r'product-card[^>]*><div[^>]*position:relative"><i class="fa-solid', content):
            issues.append('商品卡片使用 fa-solid 占位图标（应改手绘内联 SVG，图区加固定高度）（M57）')
        # 5.2 图区必须有固定高度（110px 左右），防止 absolute 图标塌陷错位（按块检查静态图区）
        area_blocks = re.findall(r'<div style="border-radius:10px 10px 0 0;background:[^"]*?;position:relative[^"]*">', content)
        no_h = [b for b in area_blocks if 'height:' not in b]
        if no_h:
            issues.append('商品卡片图区缺少固定高度（高度塌陷会导致占位图错位压住标题）: ' + str(len(no_h)) + ' 处（M57）')
    # 6.5 横向滚动容器必须隐藏滚动条（M59：.drag-scroll 已内置，但内联 overflow-x:auto 也要隐藏）
    if 'overflow-x:auto' in content:
        inline_scrolls = re.findall(r'style="([^"]*overflow-x:auto[^"]*)"', content)
        bad_scrolls = [s for s in inline_scrolls if 'scrollbar-width' not in s]
        if bad_scrolls:
            issues.append(str(len(bad_scrolls)) + ' 处内联横向滚动容器未隐藏滚动条（应加 scrollbar-width:none 或用 .drag-scroll）（M59）')
    if 'sub-page' in content:
        blocks = re.split(r'(?=<div class="sub-page")', content)
        no_bar_pages = []
        for blk in blocks:
            if '<div class="sub-page"' not in blk or 'sub-template' in blk:
                continue
            if 'form-group' in blk and 'detail-bar' not in blk:
                sid_m = re.search(r'id="(sub-[a-z-]+)"', blk)
                no_bar_pages.append(sid_m.group(1) if sid_m else '?')
        if no_bar_pages:
            issues.append('二级页缺少 .detail-bar 固定底部操作区: ' + ','.join(no_bar_pages) + '（M55）')
    # 6.6 Tab 激活态禁止内联样式覆盖（M55）
    if re.search(r'class="[^"]*order-tab[^"]*active[^"]*"[^>]*style="[^"]*color:', content):
        issues.append('order-tab active 带内联 color 样式覆盖激活态（背景与文字颜色不匹配）（M55）')
    # 7. 标题栏联动
    if 'topBarTitle' in content and 'tabTitles' not in content:
        issues.append('switchTab 缺少 tabTitles 标题映射（顶部标题不随 Tab 更新）（M54）')
    if issues:
        result.fail('M54-移动端UI', '; '.join(issues))
    else:
        result.ok('M54-移动端UI', '移动端 UI 规范合规（零滚动条/宫格/固定栏/蒙版/导航/图标）')

def check_mobile_design_sense(content, result, is_template, is_component):
    """设计常识铁律（2026-08-13 固化）：
    1. 金刚区对称满格（5 列宫格入口数 = 5 或 10；4 列 = 4 或 8，禁 5+3 空位）
    2. 详情页完整性（电商商品详情页需参数表+评价；金融产品详情页需风险等级）
    3. 底部操作栏固定（.detail-bar 禁被 position:relative/static 覆盖）"""
    if is_template or is_component:
        return
    if 'phone-frame' not in content and 'sub-page' not in content:
        return
    issues = []
    # 1. 金刚区满格
    cats = re.findall(r'class="home-cat"', content)
    n = len(cats)
    if n > 0 and n not in (4, 5, 8, 10):
        issues.append(f'金刚区入口 {n} 个，5 列宫格必须 5 或 10（4 列必须 4 或 8），禁止 {n} 个造成空位（设计常识铁律①）')
    # 2. 详情页完整性（电商商品详情 / 金融产品详情）
    # 触发条件用结构特征（子页面标题=商品详情 或 HTML 中 class="detail-name"+class="detail-price"
    # 商品区），不用全文 contains / 裸类名——避免 CSS 定义（.detail-name{}）、注释、JS 字符串
    # 提及而误报（M118 注释事故：模板 CSS 注释含"商品详情"字样触发误报）
    has_ec_detail = bool(re.search(r'class="[^"]*sub-page-title[^"]*"[^>]*>\s*商品详情', content)) or \
                    ('class="detail-name"' in content and 'class="detail-price"' in content)
    if has_ec_detail:
        if '参数' not in content or '评价' not in content:
            issues.append('电商商品详情页缺 参数表 或 用户评价（设计常识铁律⑨，必须含 参数+图文+评价）')
    if '收益走势' in content or '历史业绩' in content:
        if '风险' not in content:
            issues.append('金融产品详情页缺 风险等级提示（金融铁律，必须含风险等级标签）')
    # 3. 底部操作栏禁止覆盖固定定位（.detail-bar 被 position:relative/static 覆盖）
    if re.search(r'class="[^"]*detail-bar[^"]*"[^>]*style="[^"]*position\s*:\s*(?:relative|static)', content):
        issues.append('详情页底部操作栏 .detail-bar 被 position:relative/static 覆盖，必须保持 absolute 固定底部（设计常识铁律⑪）')
    if issues:
        result.fail('设计常识', '; '.join(issues))
    else:
        result.ok('设计常识', '移动端设计常识合规（金刚区满格 + 详情页完整）')

def check_mobile_business_actions(content, result, is_template, is_component):
    """M53: 移动端业务交互真实化 — 关键业务按钮禁止绑 doAction 假提示，必须真实函数化"""
    if is_template or is_component:
        return
    if 'phone-frame' not in content and 'sub-page' not in content:
        return
    import re as _re
    issues = []
    # 业务动作关键词：若 doAction('关键词') 绑在按钮上则判为假按钮
    fake_kw = ['支付', '取消', '发货', '收货', '退款', '提现', '发布', '发送', '删除', '评价', '收藏',
               '下架', '上架', '面交', '再次购买', '物流', '确认收货', '提醒发货']
    # 1. 抓取所有 doAction('xxx') 调用，检查业务关键词（单引号/双引号分开匹配）
    for _m in list(_re.finditer(r"doAction\('([^']+)'\)", content)) + list(_re.finditer(r'doAction\("([^"]+)"\)', content)):
        kw = _m.group(1)
        for k in fake_kw:
            if k in kw:
                issues.append('假按钮: doAction(' + kw + ')（业务动作必须真实函数化）（M53）')
                break
    # 2. 关键业务函数存在性（按页面特征触发）
    has_chat = 'chatInput' in content or '输入消息' in content
    if has_chat and 'function sendChatMsg' not in content:
        issues.append('聊天页缺 sendChatMsg 真实收发函数（M53）')
    has_publish = '发布商品' in content or 'pubTitle' in content
    if has_publish and 'function submitPublish' not in content:
        issues.append('发布页缺 submitPublish 校验保存函数（M53）')
    has_order = 'order-card' in content and ('立即付款' in content or '确认收货' in content or '去发货' in content)
    if has_order:
        for fn in ['payOrder', 'cancelOrder', 'confirmReceive', 'shipOrder', 'refundOrder']:
            if ('function ' + fn) not in content:
                issues.append('订单页缺 ' + fn + ' 状态流转函数（M53）')
    has_wallet = '提现到微信零钱' in content or '可用余额' in content
    if has_wallet and 'function withdraw' not in content:
        issues.append('钱包页缺 withdraw 提现函数（M53）')
    has_addr = 'addr-card' in content and '收货地址' in content
    if has_addr:
        for fn in ['addAddress', 'deleteAddress', 'setDefaultAddress']:
            if ('function ' + fn) not in content:
                issues.append('地址页缺 ' + fn + ' 函数（M53）')
    has_review = '评价订单' in content or 'ratingStars' in content
    if has_review and 'function submitReview' not in content:
        issues.append('评价页缺 submitReview 函数（M53）')
    if issues:
        result.fail('M53-移动端业务', '; '.join(issues[:6]))
    else:
        result.ok('M53-移动端业务', '移动端业务真实化合规（无假按钮，关键业务函数齐全）')

def check_m10_page_container(content, result, is_template, is_component):
    """M10: 页面容器 — 使用多个 .page 元素时，必须有对应的 .page CSS 样式定义（仅移动端适用）"""
    if is_template or is_component:
        result.ok('M10', '模板/组件文件跳过')
        return
    if not is_mobile_file(content):
        result.ok('M10', '非移动端文件跳过（桌面端用 display 切换是正确实现）')
        return
    page_elements = re.findall(r'class="[^"]*\bpage\b[^"]*"', content)
    if len(page_elements) < 2:
        result.ok('M10', '页面数量少，无需检查容器样式')
        return
    # 检查是否有 .page 的 CSS 定义（含 position 或 inset 或 overflow）
    page_css = re.findall(r'\.page\s*\{[^}]*\}', content)
    has_position = any('position' in css for css in page_css) if page_css else False
    if page_css and has_position:
        result.ok('M10', '.page CSS 样式定义完整')
    else:
        result.fail('M10', '使用多个 .page 元素但缺少对应的 CSS 样式定义（需 position/inset/overflow）')

# --- M11 登录页规范 ---

def check_m11_login_default(content, result, is_template, is_component):
    """M11: 登录页规范 — 移动端原型默认不允许将 page-login 设为默认显示页面"""
    if is_template or is_component:
        result.ok('M11', '模板/组件文件跳过')
        return
    if not is_mobile_file(content):
        result.ok('M11', '非移动端文件跳过')
        return
    # 检查 page-login 是否带 active 类
    login_active = re.search(r'class="[^"]*page-login[^"]*active', content) or \
                   re.search(r'id="page-login"[^>]*class="[^"]*active', content)
    if login_active:
        result.fail('M11', 'page-login 被设为默认显示页面，移动端原型不允许默认显示登录页')
    else:
        result.ok('M11', '登录页未设为默认显示')

# ============================================================
# C1 系列：可执行级检查（v4.0 新增，拦截结构类事故）
# ============================================================

# C1-1 script 闭合完整性：检测 </script> 之后是否存在裸露的 JS 文本
def check_c1_script_closure(content, result, is_template, is_component):
    """C1-1: script 闭合完整性 — </script> 之后不得有裸 JS 代码"""
    # 找到最后一个 </script> 的位置
    last_script_end = content.rfind('</script>')
    if last_script_end == -1:
        result.ok('C1-1', '无 script 标签（可能是纯 HTML）')
        return
    # 检查 </script> 之后到 </body> 之间的内容
    tail = content[last_script_end + len('</script>'):]
    # 截取到 </body> 或文件末尾
    body_end = tail.find('</body>')
    if body_end != -1:
        tail = tail[:body_end]
    # 移除注释和空白
    tail_clean = re.sub(r'<!--.*?-->', '', tail, flags=re.DOTALL)
    tail_clean = tail_clean.strip()
    # 检测 JS 代码特征（函数定义、变量声明、DOM 操作）
    js_patterns = [
        r'function\s+\w+\s*\(',
        r'^\s*(var|let|const)\s+\w+\s*=',
        r'document\.getElementById',
        r'\.addEventListener',
        r'window\.',
        r'\.classList\.',
        r'\.style\.',
        r'\.innerHTML\s*=',
        r'forEach\s*\(',
    ]
    suspicious = []
    for pat in js_patterns:
        m = re.search(pat, tail_clean, re.MULTILINE)
        if m:
            suspicious.append(pat)
    if not tail_clean:
        result.ok('C1-1', '</script> 之后无裸文本')
    elif suspicious:
        # 找出具体行号
        line_no = content[:last_script_end].count('\n') + 2
        result.fail('C1-1', f'</script> 之后发现 {len(suspicious)} 处 JS 代码特征（第 {line_no} 行起），浏览器会将其渲染为纯文本！特征: {", ".join(suspicious[:3])}')
    else:
        result.ok('C1-1', '</script> 之后无裸 JS 代码（仅有普通文本/注释）')


# --- M34 布局偏移检测 ---

def check_m34_layout_offset(content, result, is_template, is_component):
    """M34: 检测移动端布局偏移问题 — 双重绝对定位、双重padding、导航栏过高"""
    if is_template or is_component:
        result.ok('M34', '模板/组件文件跳过')
        return
    if not is_mobile_file(content):
        result.ok('M34', '非移动端文件跳过')
        return

    issues = []

    # 检查1: .page 使用 position:absolute + top:calc（双重绝对定位）
    page_css_match = re.search(r'\.page\s*\{([^}]+)\}', content)
    if page_css_match:
        page_css = page_css_match.group(1)
        if 'position:absolute' in page_css and 'top:calc' in page_css:
            content_css_match = re.search(r'\.content\s*\{([^}]+)\}', content)
            if content_css_match and 'position:absolute' in content_css_match.group(1):
                issues.append('page+content 双重绝对定位（.page应改为position:relative）')

    # 检查2: .content 有 padding 且 .page-content 也有 padding（双重padding）
    content_css_match = re.search(r'\.content\s*\{([^}]+)\}', content)
    page_content_match = re.search(r'\.page-content\s*\{([^}]+)\}', content)
    if content_css_match and page_content_match:
        content_padding = re.search(r'padding:\s*([^;]+)', content_css_match.group(1))
        page_content_padding = re.search(r'padding:\s*([^;]+)', page_content_match.group(1))
        if content_padding and page_content_padding:
            content_pad_val = content_padding.group(1).strip()
            if content_pad_val != '0' and '0' not in content_pad_val.split()[0]:
                issues.append('content+page-content 双重padding（.content padding应为0）')

    # 检查3: .bottom-nav 高度超过 160px（异常过高，M38后正常高度约 104px）
    nav_height_match = re.search(r'\.bottom-nav\s*\{[^}]*height:\s*(\d+)px', content)
    if nav_height_match:
        nav_height = int(nav_height_match.group(1))
        if nav_height > 160:
            issues.append(f'bottom-nav 高度{nav_height}px异常过高（M38标准约104px：52px过渡区+52px按钮区）')

    if issues:
        result.fail('M34', '；'.join(issues))
    else:
        result.ok('M34', '布局偏移检测通过（无双重定位/双重padding/导航过高）')

def check_m41_horizontal_scrollbar(content, result, is_template, is_component):
    """M41: 移动端横向滚动条可见性检测 — overflow-x:auto/scroll 的容器必须隐藏滚动条"""
    if is_template or is_component:
        result.ok('M41', '模板/组件文件跳过')
        return
    if not is_mobile_file(content):
        result.ok('M41', '非移动端文件跳过')
        return
    issues = []
    # 检查1: 检测 overflow-x:auto 或 overflow-x:scroll 的 CSS 规则
    # 找到所有包含 overflow-x 的 CSS 规则块
    overflow_x_rules = re.findall(r'(\.[a-zA-Z_-][a-zA-Z0-9_-]*)\s*\{([^}]*overflow-x:\s*(?:auto|scroll)[^}]*)\}', content)
    for selector, css_block in overflow_x_rules:
        selector_name = selector.strip('.')
        # 跳过已知的纵向滚动容器（content/page/sub-page-body 等，这些已有隐藏规则）
        if selector_name in ('content', 'page', 'sub-page-body'):
            continue
        # 检查该选择器是否有对应的 ::-webkit-scrollbar 隐藏规则
        scrollbar_hidden = bool(re.search(
            r'\.' + re.escape(selector_name) + r'::-webkit-scrollbar\s*\{[^}]*display:\s*none',
            content
        ))
        # 检查是否有 scrollbar-width:none
        scrollbar_width_hidden = 'scrollbar-width:none' in css_block or 'scrollbar-width: none' in css_block
        if not scrollbar_hidden and not scrollbar_width_hidden:
            issues.append(f'.{selector_name} 有 overflow-x:auto/scroll 但未隐藏滚动条（需加 ::-webkit-scrollbar{{display:none}} 或 scrollbar-width:none）')
    # 检查2: 禁止 overflow:scroll / overflow-x:scroll（强制显示滚动条）
    if re.search(r'overflow\s*:\s*scroll', content) or re.search(r'overflow-x\s*:\s*scroll', content):
        issues.append('使用了 overflow:scroll/overflow-x:scroll（会强制显示滚动条，应改用 overflow-x:auto）')
    if issues:
        result.fail('M41', '；'.join(issues))
    else:
        result.ok('M41', '横向滚动条已隐藏（overflow-x:auto 容器均有 scrollbar 隐藏规则）')

# C1-2 函数定义-调用匹配：onclick 引用的每个函数必须有 function 定义且在 script 内
def check_c1_func_definition(content, result, is_template, is_component):
    """C1-2: 函数定义-调用匹配 — onclick 引用的函数必须真实存在"""
    if is_template:
        result.ok('C1-2', '模板文件跳过（骨架函数由模板保证）')
        return
    # 提取所有 script 块内容（函数定义搜索范围）
    script_blocks = re.findall(r'<script[^>]*>(.*?)</script>', content, re.DOTALL)
    # 但有些文件是单 script，有些可能 script 未闭合（商家端事故）——此时裸 JS 也算定义范围
    all_js = '\n'.join(script_blocks)
    # 收集所有已定义函数名（function 声明 + var xxx = function + window.xxx = function）
    defined_funcs = set()
    for m in re.finditer(r'function\s+([A-Za-z_$][\w$]*)\s*\(', all_js):
        defined_funcs.add(m.group(1))
    for m in re.finditer(r'(?:var|let|const)\s+([A-Za-z_$][\w$]*)\s*=\s*function', all_js):
        defined_funcs.add(m.group(1))
    for m in re.finditer(r'window\.([A-Za-z_$][\w$]*)\s*=\s*function', all_js):
        defined_funcs.add(m.group(1))
    for m in re.finditer(r'window\.([A-Za-z_$][\w$]*)\s*=\s*\(?function', all_js):
        defined_funcs.add(m.group(1))
    # 同时收集 HTML onclick 属性里引用的函数
    onclick_refs = set()
    for m in re.finditer(r'onclick="\s*([A-Za-z_$][\w$]*)\s*\(', content):
        onclick_refs.add(m.group(1))
    # 排除原生/内置函数
    builtin = {'return', 'if', 'for', 'while', 'function', 'var', 'let', 'const',
               'alert', 'confirm', 'prompt'}  # alert/confirm/prompt 为浏览器原生，onclick 直接调用合法
    onclick_refs -= builtin
    missing = sorted(onclick_refs - defined_funcs)
    if not missing:
        result.ok('C1-2', f'全部 {len(onclick_refs)} 个 onclick 引用函数均有定义')
    else:
        result.fail('C1-2', f'{len(missing)} 个 onclick 引用函数未定义: {", ".join(missing[:8])}（点击将抛 ReferenceError）')

# C1-3 模板残留检测：注入标记不得残留在生成文件中
def check_c1_template_residue(content, result, is_template, is_component):
    """C1-3: 模板残留检测 — 生成文件不得残留模板注入标记"""
    if is_template:
        result.ok('C1-3', '模板文件跳过（模板自身含标记）')
        return
    markers = [
        r'Agent:\s*[A-Z_]+\s*START',
        r'Agent:\s*[A-Z_]+\s*END',
        r'Agent 收尾提醒',
        r'{{[^}]+}}',  # 模板占位符
    ]
    found = []
    for pat in markers:
        for m in re.finditer(pat, content):
            # 提取上下文
            start = max(0, m.start() - 20)
            ctx = content[start:m.end() + 20].replace('\n', ' ')
            found.append(ctx.strip()[:60])
    if not found:
        result.ok('C1-3', '无模板注入标记残留')
    else:
        result.fail('C1-3', f'检测到 {len(found)} 处模板残留标记: {"; ".join(found[:4])}')

# C1-4 空表格检测：每个 tbody 必须有对应的渲染逻辑
def check_c1_empty_table(content, result, is_template, is_component):
    """C1-4: 空表格检测 — tbody 必须对应有 innerHTML 渲染逻辑"""
    if is_template:
        result.ok('C1-4', '模板文件跳过（示例表格由注入填充）')
        return
    # 找所有带 id 的 tbody
    tbody_ids = []
    for m in re.finditer(r'<tbody[^>]*id="([^"]+)"', content):
        tbody_ids.append(m.group(1))
    if not tbody_ids:
        result.ok('C1-4', '无 id 化 tbody（可能无表格或表格用 class）')
        return
    # 检查每个 id 是否在 JS 中被 getElementById 引用（渲染逻辑）
    missing_render = []
    for tid in tbody_ids:
        if tid not in content or f"getElementById('{tid}')" not in content:
            # 允许变量拼接形式 getElementById(tid)
            if not re.search(r"getElementById\(\s*['\"]?" + re.escape(tid) + r"['\"]?\s*\)", content):
                missing_render.append(tid)
    if not missing_render:
        result.ok('C1-4', f'全部 {len(tbody_ids)} 个 tbody 均有渲染逻辑')
    else:
        result.fail('C1-4', f'{len(missing_render)} 个 tbody 无渲染逻辑（打开将空白）: {", ".join(missing_render[:5])}')

# C1-5 JS 语法检测：提取 script 内容做括号/引号平衡检测
def check_c1_js_syntax(content, result, is_template, is_component):
    """C1-5: JS 语法基础检测 — script 块括号/引号/模板字符串平衡"""
    script_blocks = re.findall(r'<script[^>]*>(.*?)</script>', content, re.DOTALL)
    if not script_blocks:
        result.ok('C1-5', '无 script 块')
        return
    issues = []
    for idx, block in enumerate(script_blocks):
        # 移除字符串字面量后再做括号平衡（简化：跳过引号内容）
        # 括号平衡
        stack = []
        pairs = {')': '(', ']': '[', '}': '{'}
        in_str = None
        str_char = ''
        i = 0
        prev_ch = ''
        while i < len(block):
            ch = block[i]
            if in_str:
                if ch == '\\':
                    i += 2
                    continue
                if ch == str_char:
                    in_str = None
            else:
                # 正则字面量支持：/.../ 中的引号不视为字符串（M19 修复）
                # 启发式：/ 前一个非空白字符为运算符(非右括号)/括号开头/行首时视为正则开始
                # 右括号 ) ] } 后的 / 与 空格后的 / 通常是除法（如 x / 100、x) / 100）
                if ch == '/' and i + 1 < len(block) and block[i+1] not in ('/', '*'):
                    # 回溯到最近的非空白字符
                    prev_nb = ''
                    k = i - 1
                    while k >= 0 and block[k].isspace():
                        k -= 1
                    if k >= 0:
                        prev_nb = block[k]
                    prev_is_operand = prev_nb in ')]}'
                    is_regex = (prev_nb == '' or prev_nb in '(,=:?![{;&|+-*%<>') and not prev_is_operand
                    if is_regex:
                        # 跳到正则结束（下一个未转义的 /）
                        j = i + 1
                        while j < len(block):
                            if block[j] == '\\':
                                j += 2
                                continue
                            if block[j] == '/' or block[j] == '\n':
                                break
                            j += 1
                        i = j + 1
                        continue
                if ch in ('"', "'", '`'):
                    in_str = True
                    str_char = ch
                elif ch in '([{':
                    stack.append(ch)
                elif ch in ')]}':
                    if not stack or stack[-1] != pairs[ch]:
                        issues.append(f'script#{idx+1} 第 {block[:i].count(chr(10))+1} 行括号不匹配: {ch}')
                        break
                    stack.pop()
            prev_ch = ch
            i += 1
        else:
            if stack:
                issues.append(f'script#{idx+1} 有 {len(stack)} 个未闭合括号: {stack[-1]}')
            # 检查明显的字符串未闭合（行内单引号/双引号不配对）
            if in_str:
                issues.append(f'script#{idx+1} 字符串未闭合（{str_char}）')
    if not issues:
        result.ok('C1-5', f'全部 {len(script_blocks)} 个 script 块语法结构平衡')
    else:
        result.fail('C1-5', '; '.join(issues[:4]))

# C1-7 分页覆盖检查：桌面端每个含 data-table 的页面必须有分页容器（M20 防护）
def check_c1_pagination_coverage(content, result, is_template, is_component):
    """C1-7: 分页覆盖 — 每个含 data-table 的页面必须有 .pages 分页容器，防止"列表无分页"事故"""
    if is_template:
        result.ok('C1-7', '模板文件跳过')
        return
    if is_prd_file(content) or ('phone-frame' in content and 'sub-page' in content):
        result.ok('C1-7', 'PRD/移动端跳过（移动端使用滚动列表）')
        return
    # V2/V3 数据驱动：分页由 renderPager 运行时注入，静态容器检查跳过（运行时由 browser-check B3+ 验证）
    if is_modern_paradigm(content):
        result.ok('C1-7', 'V2/V3 数据驱动：分页由 renderPager 运行时注入，静态容器检查跳过')
        return
    # 找出所有 page 块及其内部是否含 data-table 和 .pages 分页容器
    pages = re.findall(r'<div class="page"[^>]*id="page-([^"]+)"[^>]*>(.*?)(?=<div class="page"|</body>)', content, re.DOTALL)
    # 统计展示类页面（TopN 排行/汇总表，固定行数无需分页）跳过
    STAT_PAGES = ('stats', 'finance', 'dashboard', 'report', 'analytics', 'analysis', 'commission')
    missing = []
    for pid, body in pages:
        if pid in STAT_PAGES:
            continue
        has_table = '<table' in body and ('data-table' in body)
        has_pager = 'class="pages"' in body or 'class="table-footer"' in body
        if has_table and not has_pager:
            missing.append(pid)
    if not missing:
        result.ok('C1-7', f'全部 {len(pages)} 个页面：有表格的页面均含分页容器')
    else:
        result.fail('C1-7', f'{len(missing)} 个页面有表格但缺分页容器: {", ".join(missing[:8])}')


# C1-8 侧边栏树形架构检查：平台管理端全部菜单统一为「一级菜单+二级菜单」树形 + 系统管理 5 个标准二级菜单（M22 防护）
def check_c1_system_arch(content, result, is_template, is_component):
    """C1-8: 侧边栏树形架构 — 全部菜单必须为 nav-parent+nav-children 树形（禁止分组标题平铺混合），系统管理含 5 个标准二级菜单"""
    # V4 顶栏外壳范式（无左栏侧边栏）：系统管理 5 子页由 browser-check M22/B3++++ 验证，
    # 不适用 C1-8 侧栏树形检查 → 降级跳过（与 D7 对 V3/V4 的跳过策略一致）。
    if is_v4_paradigm(content):
        result.ok('C1-8', 'V4 顶栏外壳无左栏侧边栏，系统管理子页由 browser-check 验证，跳过侧栏树形检查')
        return
    # 模板/组件：仅当采用 V2「顶栏一级+下拉二级」混合导航（topnav-group 且 无 nav-parent 树形）
    # 或 V3「现代侧栏仪表盘」（sidebar-nav 侧栏导航）时，才强制检查系统管理内置；
    # 其余模板（如 V1 侧栏树形）保持跳过，维持原行为。
    allow_check = ('topnav-group' in content and 'nav-parent' not in content) or ('sidebar-nav' in content)
    if (is_template or is_component) and not allow_check:
        result.ok('C1-8', '模板/组件文件跳过')
        return
    if is_prd_file(content) or ('phone-frame' in content and 'sub-page' in content):
        result.ok('C1-8', 'PRD/移动端跳过')
        return
    # 平台管理端特征：有 nav 侧边栏
    has_nav = 'nav-group' in content or 'nav-item' in content
    if not has_nav:
        result.ok('C1-8', '无侧边栏导航，跳过')
        return
    has_system_menu = '系统管理' in content
    if not has_system_menu:
        result.ok('C1-8', '无系统管理菜单，跳过')
        return
    issues = []
    # V3 现代侧栏仪表盘分支：检测 .sidebar 中的系统管理 5 个标准二级项（位于「系统设置」分组下）
    if 'sidebar-nav' in content:
        required = {'org': '我的组织', 'roles': '角色权限', 'menus': '菜单配置', 'dicts': '字典配置', 'logs': '操作日志'}
        sm = re.search(r'<aside class="sidebar"[^>]*>(.*?)(</aside>|<!-- ============ DRAWER)', content, re.DOTALL)
        sidebar_block = sm.group(1) if sm else content
        missing = []
        for pid, label in sorted(required.items()):
            if ('data-page="' + pid + '"') not in sidebar_block:
                missing.append('侧栏缺少系统管理项: ' + label)
            if ('id="page-' + pid + '"') not in content:
                missing.append('缺页面: ' + label)
        # V3 无侧栏折叠功能（用户 2026-08-09 要求移除收起侧栏），不检查 toggleSidebar
        if 'toggleNavGroup' not in content:
            missing.append('缺少分组折叠函数 toggleNavGroup')
        if not missing:
            result.ok('C1-8', '侧栏导航 + 系统管理 5 个标准二级菜单完整（V3 现代侧栏）')
        else:
            result.fail('C1-8', '; '.join(missing))
        return
    # V2 顶栏「一级 + 下拉二级」混合导航分支：检测 topnav-group 包裹的 系统管理 + 5 个标准二级项
    if 'topnav-group' in content and 'nav-parent' not in content:
        required = {'org': '我的组织', 'roles': '角色权限', 'menus': '菜单配置', 'dicts': '字典配置', 'logs': '操作日志'}
        # 取「系统管理」所在 topnav-group 区块（从 topnav-group 起 2500 字符窗口）
        sys_block = ''
        for m in re.finditer(r'<div class="topnav-group"', content):
            blk = content[m.start():m.start() + 2500]
            if '系统管理' in blk:
                sys_block = blk
                break
        if not sys_block:
            issues.append('顶栏混合导航缺少「系统管理」一级 + 下拉二级（topnav-group）')
        else:
            if 'has-sub' not in sys_block or 'topnav-sub' not in sys_block:
                issues.append('「系统管理」一级项缺 .has-sub 触发器或 .topnav-sub 下拉面板')
            for pid, label in sorted(required.items()):
                if ('data-page="' + pid + '"') not in sys_block or ('id="page-' + pid + '"') not in content:
                    issues.append('系统管理二级菜单缺失: ' + label)
        if 'toggleTopnavGroup' not in content:
            issues.append('缺少下拉展开函数 toggleTopnavGroup')
        if not issues:
            result.ok('C1-8', '顶栏全树形 + 系统管理 5 个标准二级菜单完整（V2 混合导航）')
        else:
            result.fail('C1-8', '; '.join(issues))
        return
    # 1. 全树形检查：只检查正文 HTML（排除 <style> 块内的 CSS 类名定义）
    html_body = content
    style_m = re.search(r'<style[^>]*>(.*?)</style>', content, re.DOTALL)
    if style_m:
        html_body = content[:style_m.start()] + content[style_m.end():]
    # 正文中真正的 nav-group-title 平铺（HTML 元素），排除 CSS 定义
    has_flat_title = bool(re.search(r'class="nav-group-title"', html_body))
    has_tree = 'nav-parent' in html_body and 'nav-children' in html_body
    if has_flat_title and has_tree:
        issues.append('侧边栏混合结构：nav-group-title 平铺与 nav-parent 树形并存，必须全树形')
    # 2. 五个标准二级菜单页面
    required = {'org': '我的组织', 'roles': '角色权限', 'menus': '菜单配置', 'dicts': '字典配置', 'logs': '操作日志'}
    missing_pages = []
    for pid, label in required.items():
        menu_ok = ('data-page="' + pid + '"' in content)
        page_ok = ('id="page-' + pid + '"' in content)
        if not menu_ok or not page_ok:
            missing_pages.append(label + '(menu:' + str(menu_ok) + ',page:' + str(page_ok) + ')')
    if missing_pages:
        issues.append('缺少标准二级菜单: ' + ', '.join(missing_pages))
    if not issues:
        result.ok('C1-8', '侧边栏全树形 + 系统管理 5 个标准二级菜单完整')
    else:
        result.fail('C1-8', '; '.join(issues))


# C1-9 组织架构检查：我的组织必须为企业微信式「部门树+成员列表」+ 完整 CRUD（M27 防护）
def check_c1_org_arch(content, result, is_template, is_component):
    """C1-9: 组织架构 — 我的组织页必须含 .org-layout 左右布局（部门树+成员列表）+ 部门/成员增删改查函数"""
    if is_template or is_component:
        result.ok('C1-9', '模板/组件文件跳过')
        return
    if is_prd_file(content) or ('phone-frame' in content and 'sub-page' in content):
        result.ok('C1-9', 'PRD/移动端跳过')
        return
    has_org = 'id="page-org"' in content
    if not has_org:
        result.ok('C1-9', '无我的组织页，跳过')
        return
    issues = []
    # 1. 布局：左部门树 + 右成员列表（org-layout）
    if '.org-layout' not in content:
        issues.append('缺少 org-layout 布局（应为企业微信式左右布局）')
    if 'deptTree' not in content:
        issues.append('缺少部门树容器(deptTree)')
    if 'membersTableBody' not in content:
        issues.append('缺少成员列表容器(membersTableBody)')
    # 2. 成员字段：姓名/手机号/部门/角色/状态
    for col in ['姓名', '手机号', '部门', '角色', '状态']:
        if col not in content:
            issues.append('成员列表缺字段: ' + col)
    # 3. 部门 CRUD 函数
    for fn in ['openDeptAdd', 'saveDeptAdd', 'openDeptRename', 'saveDeptRename', 'openDeptDelete', 'saveDeptDelete']:
        if ('function ' + fn) not in content:
            issues.append('部门 CRUD 缺函数: ' + fn)
    # 4. 成员 CRUD 函数
    for fn in ['openMemberAdd', 'saveMemberAdd', 'openMemberEdit', 'saveMemberEdit', 'toggleMemberStatus', 'openMemberDelete', 'saveMemberDelete']:
        if ('function ' + fn) not in content:
            issues.append('成员 CRUD 缺函数: ' + fn)
    # 5. 角色权限：角色 CRUD + 菜单权限勾选树 + 两步向导（M29/M31）
    for fn in ['openRoleAdd', 'openRoleEdit', 'roleWizardNext', 'roleWizardPrev', 'roleWizardSave', 'openRoleDelete', 'saveRoleDelete', 'togglePermGroup', 'togglePermMenu']:
        if ('function ' + fn) not in content:
            issues.append('角色权限缺函数: ' + fn)
    # 6. 系统管理页禁止导出按钮（M30）
    sys_export_pages = []
    for pid in ['org', 'roles', 'menus', 'dicts', 'logs']:
        # 该页面区块内的导出按钮
        page_block_m = re.search(r'id="page-' + pid + '"(.*?)(?=<!-- |id="page-|<script)', content, re.DOTALL)
        if page_block_m and 'btn-export' in page_block_m.group(1):
            sys_export_pages.append(pid)
    if sys_export_pages:
        issues.append('系统管理页禁止导出: ' + ', '.join(sys_export_pages) + '（M30）')
    # 7. 字典配置增删改查（M33）
    for fn in ['openDictAdd', 'saveDictAdd', 'openDictDelete', 'saveDictDelete']:
        if ('function ' + fn) not in content:
            issues.append('字典配置缺函数: ' + fn)
    if not issues:
        result.ok('C1-9', '组织架构完整（部门树+成员列表+部门/成员 CRUD+角色权限+字典 CRUD+系统管理页无导出）')
    else:
        result.fail('C1-9', '; '.join(issues))


# C1-10 配色冲突检查：内容区组件禁止引用深色侧边栏变量（M28 防护）
def check_c1_color_conflict(content, result, is_template, is_component):
    """C1-10: 配色冲突 — 内容区组件（非 .sidebar 区域）引用 --sidebar-hover/--sidebar-active/--sidebar-text 即视为配色冲突（白底黑字+深黑 hover 色块）"""
    if is_template or is_component:
        result.ok('C1-10', '模板/组件文件跳过')
        return
    if is_prd_file(content):
        result.ok('C1-10', 'PRD 使用 Tailwind CDN，跳过')
        return
    if 'phone-frame' in content and 'sub-page' in content:
        result.ok('C1-10', '移动端跳过')
        return
    # 找出 <style> 块
    style_m = re.search(r'<style[^>]*>(.*?)</style>', content, re.DOTALL)
    if not style_m:
        result.ok('C1-10', '无 style 块，跳过')
        return
    css = style_m.group(1)
    # 找出引用深色侧边栏变量的选择器块（排除 .sidebar 自身及其子级 nav-* 元素）
    DARK_VARS = ['--sidebar-hover', '--sidebar-active', '--sidebar-text', '--sidebar-bg']
    SIDEBAR_SELS = ('sidebar', 'nav-item', 'nav-parent', 'nav-chevron', 'nav-children', 'brand', 'user-chip', 'user-avatar')
    # 按规则块拆分（选择器 { 声明 }）
    blocks = re.findall(r'([^{}]+)\{([^{}]*)\}', css)
    offending = []
    for sel, dec in blocks:
        # 去掉注释后判断（选择器和声明值都去除 CSS 注释）
        sel_clean = re.sub(r'/\*.*?\*/', '', sel).strip()
        dec_clean = re.sub(r'/\*.*?\*/', '', dec)
        # 豁免：:root CSS 变量定义区、侧边栏相关元素、媒体查询外层
        if not sel_clean or ':root' in sel_clean or any(s in sel_clean for s in SIDEBAR_SELS):
            continue
        used_dark = [v for v in DARK_VARS if v in dec_clean]
        if used_dark:
            offending.append((sel_clean[:60], ','.join(used_dark)))
    if not offending:
        result.ok('C1-10', '内容区组件无深色侧边栏变量引用（配色规范）')
    else:
        detail = '; '.join([f'{s}({v})' for s, v in offending[:5]])
        result.fail('C1-10', f'内容区组件引用深色侧边栏变量导致配色冲突: {detail}（内容区应为浅色主题，hover 用 #f9fafb/var(--accent-bg)）')


# ============================================================
# 主检查流程
# ============================================================

# C1-6 类名覆盖率检查：HTML 中使用的 class 必须在 CSS 中有定义（M18 样式脱节防护）
def check_c1_class_coverage(content, result, is_template, is_component):
    """C1-6: 类名覆盖率 — 正文 HTML 使用的类必须有 CSS 定义，防止"有数据无样式"事故"""
    if is_template:
        result.ok('C1-6', '模板文件跳过')
        return
    if is_prd_file(content):
        result.ok('C1-6', 'PRD 使用 Tailwind CDN，跳过')
        return
    if 'offline-embedded' in content:
        # M109：离线内嵌产物（Tailwind/Mermaid 运行时动态生成 CSS，静态类名无法验证）
        result.ok('C1-6', '离线内嵌产物（Tailwind 运行时生成 CSS），跳过类名覆盖检查')
        return
    # 提取 CSS 中定义的类
    style_m = re.search(r'<style[^>]*>(.*?)</style>', content, re.DOTALL)
    if not style_m:
        result.ok('C1-6', '无 style 块，跳过')
        return
    defined = set(re.findall(r'\.([a-zA-Z][\w-]*)', style_m.group(1)))
    # 提取正文（body）HTML 中使用的类（先移除 script 块，避免 JS 拼接串干扰）
    body_m = re.search(r'<body[^>]*>(.*)</body>', content, re.DOTALL)
    if not body_m:
        result.ok('C1-6', '无 body 内容')
        return
    body_html = re.sub(r'<script[^>]*>.*?</script>', '', body_m.group(1), flags=re.DOTALL)
    used = set()
    for m in re.finditer(r'class="([^"]+)"', body_html):
        for cls in m.group(1).split():
            used.add(cls)
    # 排除动态/库类（Font Awesome 图标类由 CDN 提供）
    excluded_prefixes = ('fa-', 'fab-', 'fas-', 'far-', 'bi-', 'icon-')
    missing = sorted(u for u in used if not u.startswith(excluded_prefixes) and u not in defined)
    if not missing:
        result.ok('C1-6', f'全部 {len(used)} 个正文类名均有 CSS 定义（排除 fa-* 图标类）')
    else:
        result.fail('C1-6', f'{len(missing)} 个正文类名无 CSS 定义（有数据无样式）: {", ".join(missing[:10])}')


def run_all_checks(filepath, content, prd_mode='detailed'):
    """对单个文件运行所有检查"""
    result = CheckResult()
    is_template = is_template_file(filepath)
    is_component = is_component_file(filepath)

    # 框架铁律 F1-F9
    check_f1_phone_frame(content, result, is_template, is_component)
    check_f3_status_bar(content, result, is_template, is_component)
    check_f5_adjust_scale(content, result, is_template, is_component)
    check_f6_top_bar(content, result, is_template, is_component)
    check_f7_sub_page(content, result, is_template, is_component)
    check_f8_css_vars(content, result, is_template, is_component)
    check_f9_bottom_nav_standard(content, result, is_template, is_component)

    # 交互铁律
    check_i1_all_buttons_respond(content, result, is_template, is_component)
    check_i5_pseudo_function_buttons(content, result, is_template, is_component)
    check_q3_func_name_escape(content, result, is_template, is_component)
    check_q9_inline_showtoast_residue(content, result, is_template, is_component)
    check_q5_scale_protection(content, result, is_template, is_component)
    check_q6_filter_real_impl(content, result, is_template, is_component)
    check_q10_nav_stack(content, result, is_template, is_component)
    check_q11_detail_parameterized(content, result, is_template, is_component)

    # 质感铁律
    check_t1_no_emoji(content, result, is_template, is_component)
    check_t6_currency_symbol(content, result, is_template, is_component)

    # 桌面端专项
    check_d7_sidebar_collapse(content, result, is_template, is_component)
    check_d9_table_data_complete(content, result, is_template, is_component)
    check_d10_system_management_interaction(content, result, is_template, is_component)

    # 基础设施 R1-R5
    check_r1_startup_entry(content, result, is_template, is_component)
    check_r2_init_function(content, result, is_template, is_component)
    check_r3_init_called(content, result, is_template, is_component)
    check_r4_prd_has_script(content, result, is_template, is_component)
    check_r5_default_page_visible(content, result, is_template, is_component)

    # PRD 专项
    if prd_mode == 'simple':
        # 简易版 PRD：仅校验开发向核心章节，跳过详细版专属铁律（附录/知识库/变更记录/文档信息表/页面数量/工作量/评审一致/模块清单等）
        check_prd_simple_sections(content, result, is_template, is_component)
        check_simple_template_style_parity(content, result, is_template, is_component)  # P34 样式铁律：仅删 chat/search
        check_prd_stat_cards(content, result, is_template, is_component)
        check_prd_biz_flow(content, result, is_template, is_component)
        check_prd_nav_class(content, result, is_template, is_component)
        check_prd_currency_symbol(content, result, is_template, is_component)
        check_prd_prototype_link(content, result, is_template, is_component)
        check_prd_api_param_residue(content, result, is_template, is_component)
        check_prd_func_param_relevance(content, result, is_template, is_component)
        check_prd_color_scheme(content, result, is_template, is_component)
        check_prd_data_structure_coverage(content, result, is_template, is_component)
        check_prd_interaction_coverage(content, result, is_template, is_component)
        check_prd_prototype_page_list(content, result, is_template, is_component)
        check_prd_biz_panorama_misuse(content, result, is_template, is_component)
        check_prd_hardcoded_blue(content, result, is_template, is_component)
    else:
        check_prd_three_layer(content, result, is_template, is_component)
        check_prd_template_residue(content, result, is_template, is_component)
        check_prd_stat_cards(content, result, is_template, is_component)
        check_prd_biz_flow(content, result, is_template, is_component)
        check_prd_knowledge_base(content, result, is_template, is_component)
        check_prd_changelog(content, result, is_template, is_component)
        check_prd_nav_class(content, result, is_template, is_component)
        check_prd_currency_symbol(content, result, is_template, is_component)
        check_prd_prototype_link(content, result, is_template, is_component)
        check_prd_api_param_residue(content, result, is_template, is_component)
        check_prd_func_param_relevance(content, result, is_template, is_component)
        check_prd_review_consistency(content, result, is_template, is_component)
        check_prd_color_scheme(content, result, is_template, is_component)
        check_prd_page_count_consistency(content, result, is_template, is_component)
        check_prd_workload_explanation(content, result, is_template, is_component)
        check_prd_data_structure_coverage(content, result, is_template, is_component)
        check_prd_doc_info_table(content, result, is_template, is_component)
        check_prd_interaction_coverage(content, result, is_template, is_component)
        check_prd_module_list(content, result, is_template, is_component)
        check_prd_prototype_page_list(content, result, is_template, is_component)
        check_prd_biz_panorama_misuse(content, result, is_template, is_component)
        check_prd_hardcoded_blue(content, result, is_template, is_component)

    # 通用检测
    check_enum_coverage(content, result, is_template, is_component)
    check_pseudo_page(content, result, is_template, is_component)
    check_text_contrast(content, result, is_template, is_component)

    # 移动端专项
    check_m10_page_container(content, result, is_template, is_component)
    check_m11_login_default(content, result, is_template, is_component)
    check_m34_layout_offset(content, result, is_template, is_component)
    check_m41_horizontal_scrollbar(content, result, is_template, is_component)
    check_mobile_business_actions(content, result, is_template, is_component)
    check_mobile_ui_standards(content, result, is_template, is_component)
    check_mobile_design_sense(content, result, is_template, is_component)
    check_m63_subpage_position(content, result, is_template, is_component)
    check_m65_content_whitespace(content, result, is_template, is_component)
    check_m82_list_container(content, result, is_template, is_component)
    check_m83_menu_row_structure(content, result, is_template, is_component)
    check_m85_mobile_ui_common(content, result, is_template, is_component)
    check_m88_control_form(content, result, is_template, is_component)
    check_m101_quantity_nowrap(content, result, is_template, is_component)
    check_m111_clickable_divs(content, result, is_template, is_component)
    check_m112_subpage_title(content, result, is_template, is_component)
    check_m113_grid_layout(content, result, is_template, is_component)
    check_m114_css_var_ref(content, result, is_template, is_component)
    check_m115_startup_render(content, result, is_template, is_component)
    check_m116_cart_component(content, result, is_template, is_component)
    check_m117_filter_tabs_sticky(content, result, is_template, is_component)
    check_m118_detail_bar_buttons(content, result, is_template, is_component)
    check_m119_category_sidebar_sticky(content, result, is_template, is_component)
    check_m120_cartbar_bottom_pin(content, result, is_template, is_component)
    check_m121_category_sidebar_item_gap(content, result, is_template, is_component)
    check_template_brand_placeholder(content, result, is_template, is_component)

    # C1 系列：可执行级检查（v4.0）
    check_c1_script_closure(content, result, is_template, is_component)
    check_c1_func_definition(content, result, is_template, is_component)
    check_c1_template_residue(content, result, is_template, is_component)
    check_c1_empty_table(content, result, is_template, is_component)
    check_c1_js_syntax(content, result, is_template, is_component)
    check_c1_class_coverage(content, result, is_template, is_component)
    check_c1_pagination_coverage(content, result, is_template, is_component)
    check_c1_system_arch(content, result, is_template, is_component)
    check_c1_org_arch(content, result, is_template, is_component)
    check_c1_color_conflict(content, result, is_template, is_component)
    check_accent_rgb_consistency(content, result, is_template, is_component)
    check_chart_bar_visibility(content, result, is_template, is_component)
    check_chart_height_pixel(content, result, is_template, is_component)
    check_product_manage_rules(content, result, is_template, is_component)
    check_detail_form_choice(content, result, is_template, is_component)
    check_list_detail_coverage(content, result, is_template, is_component)
    check_modal_dual_mode(content, result, is_template, is_component)
    check_modal_form_style(content, result, is_template, is_component)
    check_menu_tree_design(content, result, is_template, is_component)
    check_system_admin_integrity(content, result, is_template, is_component)
    check_dept_tree_menu(content, result, is_template, is_component)
    check_html_structure_balance(content, result, is_template, is_component)

    # V2/v4 桌面端专项拦截（列表页三件套 + 导航一致性）
    check_c1_page_desc_ban(content, result, is_template, is_component)
    check_c1_table_column_align(content, result, is_template, is_component)
    check_c1_filter_bar_width(content, result, is_template, is_component)
    check_c1_nav_consistency(content, result, is_template, is_component)
    check_c1_action_col_layout(content, result, is_template, is_component)
    check_c1_table_fixed_layout(content, result, is_template, is_component)
    check_c1_page_header_component(content, result, is_template, is_component)
    check_c1_pagination_count(content, result, is_template, is_component)
    check_c1_export_btn_ban(content, result, is_template, is_component)
    check_c1_table_no_overflow_x(content, result, is_template, is_component)
    check_c1_list_column_count(content, result, is_template, is_component)
    check_c1_action_button_count(content, result, is_template, is_component)
    check_c1_dropdown_position_fixed(content, result, is_template, is_component)
    check_c1_duplicate_action_buttons(content, result, is_template, is_component)
    check_c1_list_layout_iron(content, result, is_template, is_component)
    check_c1_avatar_no_clip(content, result, is_template, is_component)
    check_c1_phone_mask(content, result, is_template, is_component, filepath)
    check_c1_duplicate_id(content, result, is_template, is_component, filepath)
    check_c1_no_proj_switcher(content, result, is_template, is_component, filepath)
    check_c1_no_back_to_top(content, result, is_template, is_component, filepath)
    check_c1_no_inline_overflow_y(content, result, is_template, is_component, filepath)
    check_c1_sheet_inside_mask(content, result, is_template, is_component, filepath)
    check_c1_entry_mapping(content, result, is_template, is_component, filepath)
    check_c1_entry_diversity(content, result, is_template, is_component, filepath)
    check_c1_info_entry_no_sheet(content, result, is_template, is_component, filepath)
    check_c1_no_inline_form(content, result, is_template, is_component, filepath)

    return result

# ============================================================
# 报告输出
# ============================================================

def print_report(filepath, result):
    """打印单个文件的检查报告"""
    filename = os.path.basename(filepath)
    print(f"\n{'━' * 60}")
    print(f"📋 Lint 报告: {filename}")
    print(f"{'━' * 60}")

    # 通过项
    if result.passed:
        print(f"\n✅ 通过 ({len(result.passed)} 项):")
        for rule_id, msg in result.passed:
            print(f"   ✓ [{rule_id}] {msg}")

    # 警告项
    if result.warnings:
        print(f"\n⚠️  警告 ({len(result.warnings)} 项):")
        for rule_id, msg in result.warnings:
            print(f"   ⚠ [{rule_id}] {msg}")

    # 失败项
    if result.failed:
        print(f"\n❌ 失败 ({len(result.failed)} 项):")
        for rule_id, msg in result.failed:
            print(f"   ✗ [{rule_id}] {msg}")

    # 汇总
    total = len(result.passed) + len(result.warnings) + len(result.failed)
    print(f"\n{'─' * 40}")
    print(f"汇总: {total} 项检查 | ✅ {len(result.passed)} 通过 | ⚠️  {len(result.warnings)} 警告 | ❌ {len(result.failed)} 失败")

    return result.exit_code

def print_summary(all_results):
    """打印总体汇总"""
    print(f"\n{'━' * 60}")
    print(f"📊 总体汇总")
    print(f"{'━' * 60}")

    total_files = len(all_results)
    total_pass = sum(len(r.passed) for _, r in all_results)
    total_warn = sum(len(r.warnings) for _, r in all_results)
    total_fail = sum(len(r.failed) for _, r in all_results)

    for filepath, result in all_results:
        filename = os.path.basename(filepath)
        status = "✅ 全部通过" if not result.failed else f"❌ {len(result.failed)} 项失败"
        print(f"  {filename}: {status}")

    print(f"\n总计: {total_files} 个文件 | ✅ {total_pass} 通过 | ⚠️  {total_warn} 警告 | ❌ {total_fail} 失败")

    if total_fail == 0:
        print(f"\n🎉 结论: 全部通过，可以交付")
    else:
        print(f"\n🚫 结论: 有 {total_fail} 项失败，禁止交付，请修复后重新检查")
        print(f"   修复策略: 直接修复 → 换方案 → 拆解问题 → 回退模板重新注入（最多 4 轮）")

    return 0 if total_fail == 0 else 1

# ============================================================
# 主入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description='PM Agent 交付物自动化 Lint 检查脚本',
        usage='python agent-lint.py <HTML文件1> <HTML文件2> ...'
    )
    parser.add_argument('files', nargs='+', help='要检查的 HTML 文件路径')
    parser.add_argument('--prd-mode', choices=['detailed', 'simple'], default='detailed',
                        help='PRD 文档模式：detailed=详细版(默认) / simple=简易版(无智能助手/搜索栏)')
    parser.add_argument('--verbose', '-v', action='store_true', help='显示详细输出')
    args = parser.parse_args()

    all_results = []
    exit_code = 0

    for filepath in args.files:
        if not os.path.exists(filepath):
            print(f"\n❌ 文件不存在: {filepath}")
            all_results.append((filepath, CheckResult()))
            exit_code = 1
            continue

        content = read_file(filepath)
        if content is None:
            print(f"\n❌ 无法读取文件: {filepath}")
            all_results.append((filepath, CheckResult()))
            exit_code = 1
            continue

        result = run_all_checks(filepath, content, prd_mode=args.prd_mode)
        file_exit = print_report(filepath, result)
        all_results.append((filepath, result))
        if file_exit != 0:
            exit_code = 1

    final_exit = print_summary(all_results)
    sys.exit(final_exit)

if __name__ == '__main__':
    main()
