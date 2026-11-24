#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
pm-review.py — PM Agent 产品逻辑评审门禁（2026-08-22 建立，第二期「PM/UI 专家」落地）

定位：与 agent-lint.py（查"代码/结构对不对"）互补，本脚本查"产品逻辑对不对"——
支付/下单流程是否有真实状态流转、列表是否有空态兜底、表单是否有必填校验、
二级页是否有返回闭环、列表数据量是否达标。这些是 lint 的 C1/M 系列不覆盖的
「产品逻辑」维度，用户多次强调"交互质量、产品逻辑"问题。

用法:
    python standards/pm-review.py <HTML文件1> <HTML文件2> ...

检查项（移动端产物；PRD/桌面端跳过）：
    R1 支付/下单流程闭环（fail）  存在支付类函数时，必须有真实状态流转或订单生成，
                                  禁止"只弹 Toast 不改数据"的假支付。
    R2 列表空态兜底（warning）    列表渲染函数（map→innerHTML）配套空态分支。
    R3 表单提交必填校验（warning）存在提交类函数时，必须有校验逻辑。
    R4 二级页返回闭环（fail）     每个 .sub-page 必须含返回按钮（.sub-page-back）。
    R5 列表数据量（warning）      列表数据数组元素数 < 6 提醒（注入说明要求 ≥ 6/主列表 ≥ 10）。
"""
import os
import re
import sys

# 非 UTF-8 终端（Windows GBK）打印 emoji 抛异常，强制 UTF-8
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding='utf-8')
    except Exception:
        pass

OK = '✅'
FAIL = '❌'
WARN = '⚠️'


def read_file(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f'{FAIL} 读取失败: {e}')
        return None


def is_mobile_file(content):
    return 'phone-frame' in content or ('bottom-nav' in content and 'sub-page' in content)


# ---------------- 各检查项 ----------------

def r1_payment_flow(content):
    """R1: 支付/下单流程闭环 — 有支付函数必须有真实状态流转"""
    # 找支付类函数：function payOrder( / function pay( / payOrder = / const pay
    funcs = re.findall(
        r'function\s+(\w*[Pp]ay\w*)\s*\([^)]*\)\s*\{', content)
    if not funcs:
        return None  # 无支付场景，跳过
    issues = []
    for fn in funcs:
        # 提取函数体（到配对的 }）
        m = re.search(r'function\s+' + fn + r'\s*\([^)]*\)\s*\{', content)
        if not m:
            continue
        start = m.end()
        depth = 1
        i = start
        while i < len(content) and depth > 0:
            if content[i] == '{':
                depth += 1
            elif content[i] == '}':
                depth -= 1
            i += 1
        body = content[start:i - 1]
        # 必须有"状态流转"或"订单生成"或"跳转+成功反馈"
        has_state_change = re.search(r'\.status\s*=\s*[\'"]|status:\s*[\'"]|\.unshift\(|\.push\(|\.splice\(',
                                     body)
        has_feedback = re.search(r'showToast\([\'"]支付成功|showToast\([\'"]提交成功|showToast\([\'"].*成功',
                                 body)
        has_nav = re.search(r'switchTab\(|openSubPage\(|closeSubPage\(', body)
        if not has_state_change and not (has_feedback and has_nav):
            issues.append(f'支付函数 `{fn}()` 只有反馈/无真实状态流转或订单生成（禁止假支付：仅弹 Toast 不改数据）')
    if issues:
        return '；'.join(issues)
    return None


def r2_empty_state(content):
    """R2: 列表空态兜底 — 有 map→innerHTML 列表渲染时应配套空态分支"""
    # 检测列表渲染模式：innerHTML = ... .map( ... ).join('')
    has_list_render = re.search(
        r'innerHTML\s*=\s*[^;]*\.map\([^)]*\)\s*\.join\(', content)
    if not has_list_render:
        return None
    # 空态守卫：list.length ? ... : emptyState(...) 或 if(!xxx.length){...emptyState} 或 length===0
    has_guard = re.search(
        r'\.length\s*\?\s*[^;]*emptyState|!\w*\.length\s*\)?\s*\{[^}]*emptyState|\.length\s*===?\s*0[^;]*emptyState|emptyState\(',
        content)
    if not has_guard:
        return '检测到列表渲染（map→innerHTML）但未见空态兜底（应配套 emptyState() 或 `list.length ? … : emptyState(…)` 分支）'
    return None


def r3_form_validation(content):
    """R3: 表单提交必填校验 — 有提交类函数且读取输入时必须有校验逻辑"""
    # 只检测"表单/创建/保存/提交"类函数（含输入读取的才算表单提交）
    funcs = re.findall(
        r'function\s+(\w*(?:submit|Submit|save|Save|create|Create|add\w*Form|edit\w*Form)\w*)\s*\([^)]*\)\s*\{',
        content)
    if not funcs:
        return None
    issues = []
    for fn in funcs:
        m = re.search(r'function\s+' + fn + r'\s*\([^)]*\)\s*\{', content)
        if not m:
            continue
        start = m.end()
        depth = 1
        i = start
        while i < len(content) and depth > 0:
            if content[i] == '{':
                depth += 1
            elif content[i] == '}':
                depth -= 1
            i += 1
        body = content[start:i - 1]
        # 只检查确实读取了输入的提交函数（.value / getElementById / $('...')）
        has_input = re.search(r'\.value\b|getElementById\(|querySelector\(', body)
        if not has_input:
            continue
        # 必须有校验：if 里读 .value 判断空/必填，或 return 拒绝
        has_validation = re.search(
            r'if\s*\([^)]*(?:\.value|\.trim\(\)|required|length)[^)]*\)\s*\{[^}]{0,80}return', body)
        has_guard = re.search(
            r'if\s*\([^)]*!(?:.+?\.value|.+?\.trim\(\))[^)]*\)', body)
        if not has_validation and not has_guard:
            issues.append(f'提交函数 `{fn}()` 读取了输入但无必填校验（应校验后再提交，禁止直接成功）')
    if issues:
        return '；'.join(issues)
    return None


def r4_subpage_back(content):
    """R4: 二级页返回闭环 — 每个 .sub-page 必须有返回按钮"""
    subs = re.findall(r'<div\s+class="sub-page"\s+id="(sub-[^"]+)"', content)
    if not subs:
        return None
    missing = []
    for sid in subs:
        # 找该 sub-page 块
        m = re.search(r'<div\s+class="sub-page"\s+id="' + re.escape(sid) + r'"[^>]*>(.*?)(?=<div\s+class="sub-page"|</div>\s*</div>\s*<!--\s*END|$)', content, re.S)
        block = m.group(1) if m else ''
        if not block:
            # 兜底：截取到下一个 sub-page 或 phone-screen 结束
            idx = content.find(sid)
            nxt = content.find('class="sub-page"', idx + len(sid))
            block = content[idx: nxt if nxt > idx else idx + 3000]
        has_back = re.search(r'sub-page-back|closeSubPage\(\'' + re.escape(sid) + r'\'\)', block)
        if not has_back:
            missing.append(f'#{sid} 缺返回按钮（.sub-page-back 或 closeSubPage）')
    if missing:
        return '；'.join(missing)
    return None


def r5_list_data_volume(content):
    """R5: 列表数据量 — 数据数组元素数 < 6 提醒（仅统计纯对象/字符串数组）"""
    small = []
    # 匹配 const xxxData = [ ... ]; （数组到配对 ]，考虑嵌套）
    for m in re.finditer(r'const\s+(\w+Data)\s*=\s*\[', content):
        name = m.group(1)
        start = m.end()
        depth = 1
        i = start
        while i < len(content) and depth > 0:
            ch = content[i]
            if ch == '[':
                depth += 1
            elif ch == ']':
                depth -= 1
            i += 1
        arr_text = content[start:i - 1]
        if re.search(r'function|=>|\breturn\b', arr_text):
            continue  # 含函数的不算纯数据
        # 顶层对象元素计数：用顶层逗号分隔的 { } 或引号字符串计数
        depth = 0
        in_str = False
        str_ch = ''
        n = 0
        prev = ''
        for ch in arr_text:
            if in_str:
                if ch == str_ch and prev != '\\':
                    in_str = False
                prev = ch
                continue
            if ch in ('"', "'", '`'):
                in_str = True
                str_ch = ch
            elif ch in '[{':
                if depth == 0 and ch == '{':
                    n += 1
                depth += 1
            elif ch in ']}':
                depth = max(0, depth - 1)
            prev = ch
        if n and n < 6 and 'smokeData' not in name and 'smoke' not in name:
            small.append(f'{name} 仅 {n} 条（注入说明要求列表数据 ≥ 6 条）')
    if small:
        return '；'.join(small)
    return None


def run_review(filepath, content):
    """对单个文件跑全部评审项，返回 (fail数, warn数)"""
    fails = []
    warns = []

    if not is_mobile_file(content):
        return 0, 0  # 非移动端产物跳过（pm-review 定位移动端产品逻辑）

    for rid, fn, kind in (
        ('R1', r1_payment_flow, 'fail'),
        ('R2', r2_empty_state, 'warn'),
        ('R3', r3_form_validation, 'warn'),
        ('R4', r4_subpage_back, 'fail'),
        ('R5', r5_list_data_volume, 'warn'),
    ):
        msg = fn(content)
        if msg is None:
            print(f'   {OK} [{rid}] {_desc(rid)}：合规')
        elif kind == 'fail':
            fails.append(f'[{rid}] {msg}')
            print(f'   {FAIL} [{rid}] {msg}')
        else:
            warns.append(f'[{rid}] {msg}')
            print(f'   {WARN} [{rid}] {msg}')

    return len(fails), len(warns)


def _desc(rid):
    return {
        'R1': '支付/下单流程闭环',
        'R2': '列表空态兜底',
        'R3': '表单提交必填校验',
        'R4': '二级页返回闭环',
        'R5': '列表数据量',
    }.get(rid, rid)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    total_fail = 0
    total_warn = 0
    for filepath in sys.argv[1:]:
        if not os.path.exists(filepath):
            print(f'\n{FAIL} 文件不存在: {filepath}')
            total_fail += 1
            continue
        content = read_file(filepath)
        if content is None:
            total_fail += 1
            continue
        print(f'\n=== 产品逻辑评审: {os.path.basename(filepath)} ===')
        f, w = run_review(filepath, content)
        total_fail += f
        total_warn += w
        print(f'   本文件: {FAIL} {f} 失败 / {WARN} {w} 警告')
    print(f'\n总计: {len(sys.argv) - 1} 个文件 | {FAIL} {total_fail} 失败 | {WARN} {total_warn} 警告')
    if total_fail > 0:
        print('🚫 产品逻辑评审未通过，禁止交付')
        sys.exit(1)
    print('🎉 产品逻辑评审通过')
    sys.exit(0)


if __name__ == '__main__':
    main()
