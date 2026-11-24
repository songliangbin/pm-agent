#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
split-pitfalls.py — 踩坑库按端拆分生成器（D44 衍生工具，v5.19）

从唯一维护源 history-pitfalls.md 派生 4 个运行时子集文件：
    history-pitfalls-mobile.md   — 移动端专属（M 系列全量 72 条）
    history-pitfalls-prd.md      — PRD 专属（P 系列全量 35 条 + D38）
    history-pitfalls-desktop.md  — 桌面端专属（D 系列中桌面专属条目）
    history-pitfalls-common.md   — 跨端通用条目（全端约束，任何端生成都必须读）

设计原则（单一真相源）：
    - history-pitfalls.md 是唯一人工维护文件；子集全部由本脚本自动派生。
    - 通用条目（D5 编码 / D17 机制同步 / D27 Windows / D35 BROWSER-CHECK /
      D36 手机号 / D39 无人值守 / D40 多端编排）只存在 common 一份，
      避免"改一处漏一处"（零滚动条 M41/M54 双写教训）。
    - 运行角色读取：
        主 Agent 步骤①按项目类型读 {对应端子集} + {common}（多端项目读全量）
        子 Agent 步骤⑤生成前读 {对应端子集} + {common}（约束下沉到内容生产者）

用法:
    python scripts/split-pitfalls.py            # 生成/刷新 4 个子集文件
    python scripts/split-pitfalls.py --check    # 只校验：重生成后 diff 一致（供 verify-all 调用）
"""

import io
import os
import re
import sys

# 非 UTF-8 终端（Windows GBK/cp936）打印 ✅❌ 会抛 UnicodeEncodeError
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding='utf-8')
    except Exception:
        pass

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(PROJECT, 'history-pitfalls.md')

# 派生文件清单（输出相对路径 → 用途）
OUT_FILES = {
    'history-pitfalls-mobile.md': '移动端专属',
    'history-pitfalls-prd.md': 'PRD 专属',
    'history-pitfalls-desktop.md': '桌面端专属',
    'history-pitfalls-common.md': '跨端通用',
}

# 跨端通用条目（D 系列编号）—— 判定依据：
#   D5  编码规则（全端适用，含中文 .html 必须 Python open 写入）
#   D17 机制同步铁律（全端流程约束）
#   D27 [Windows] browser-check 崩溃（工具层，三端验证共用）
#   D35 [BROWSER-CHECK] CDN 离线（工具层，三端验证共用）
#   D36 [V1/V2/V3/移动端] 手机号脱敏（明确含移动端）
#   D39 [全端] 无人值守铁律（命令白名单）
#   D40 [多端编排] 交付物核对（编排层约束）
COMMON_D_IDS = {'D5', 'D17', 'D27', 'D35', 'D36', 'D39', 'D40'}
# PRD 专属的 D 系列条目（D38 是 [PRD 详细/简易]，放 PRD 子集而非桌面）
PRD_D_IDS = {'D38'}


def parse_rows(text):
    """解析踩坑库表格行。返回 [(行原文, 系列, 编号)]，仅匹配表格数据行。"""
    rows = []
    for line in text.split('\n'):
        m = re.match(r'^\| (M\d+) \|', line)
        if m:
            rows.append((line, 'M', m.group(1)))
            continue
        m = re.match(r'^\| (P\d+) \|', line)
        if m:
            rows.append((line, 'P', m.group(1)))
            continue
        m = re.match(r'^\| (D\d+(?:-\d+)?) \|', line)
        if m:
            rows.append((line, 'D', m.group(1)))
    return rows


def build_subsets(text):
    """按规则把踩坑库切分为 {输出文件名: 行列表}。返回 (subsets, 明细)。"""
    lines = text.split('\n')

    # 定位分节标题，保留各段"表头 + 表头分隔行 + 数据行"
    # 分节：`## 移动端高频问题` / `## PRD 文档高频问题` / `## 桌面端高频问题`
    def section_start(idx, title):
        for i, ln in enumerate(lines):
            if ln.startswith('## ') and title in ln:
                return i
        return None

    m_start = section_start(0, '移动端高频问题')
    p_start = section_start(0, 'PRD 文档高频问题')
    d_start = section_start(0, '桌面端高频问题')
    assert None not in (m_start, p_start, d_start), '分节标题缺失，无法拆分'

    def table_block(start, end=None):
        """取从分节标题到下一个分节标题之间：标题行 + 表头 + 分隔行 + 数据行。"""
        stop = end if end is not None else len(lines)
        block = lines[start:stop]
        # 去掉尾部空行/`---`/footer 引用行
        while block and (not block[-1].strip() or block[-1].strip() == '---' or block[-1].startswith('>')):
            block = block[:-1]
        return block

    m_block = table_block(m_start, p_start)
    p_block = table_block(p_start, d_start)
    d_block = table_block(d_start)

    # 数据行按编号分类
    # 注意：移动端分节内除 M 系列外，还允许 `[移动端]` 标签的 D 系列条目（如 D46），
    # 它们属于移动端问题但沿用 D 编号，必须计入移动端子集而非桌面子集
    m_rows = [l for l in m_block if re.match(r'^\| (?:M\d+|D\d+(?:-\d+)?) \|', l)]
    p_rows = [l for l in p_block if re.match(r'^\| P\d+ \|', l)]
    d_rows = [l for l in d_block if re.match(r'^\| D\d+(?:-\d+)? \|', l)]

    common = []
    prd_d = []
    desktop = []
    for line in d_rows:
        m = re.match(r'^\| (D\d+(?:-\d+)?) \|', line)
        did = m.group(1)
        if did in COMMON_D_IDS:
            common.append(line)
        elif did in PRD_D_IDS:
            prd_d.append(line)
        else:
            desktop.append(line)

    # 每个子集 = 表头（含分节标题 + `| # | ...` + `|:--|`）+ 对应数据行
    def header_block(start_title_block):
        # 表头 = 分节标题行 + 表头行 + 分隔行
        hdr = []
        for ln in start_title_block:
            hdr.append(ln)
            if re.match(r'^\|:--\|', ln):
                break
        return hdr

    mobile_hdr = header_block(m_block)
    prd_hdr = header_block(p_block)
    desktop_hdr = header_block(d_block)
    # common 复用桌面分节的表头行，但子标题替换为「跨端通用条目」（避免误导）
    common_hdr = header_block(d_block)
    common_hdr[0] = '## 跨端通用条目（D5/D17/D27/D35/D36/D39/D40）'

    def compose(title, note, hdr, rows):
        out = [title, '', note, '']
        out.extend(hdr)
        for r in rows:
            out.append(r)
        out.append('')
        return out

    subsets = {
        'history-pitfalls-mobile.md': compose(
            '# 移动端踩坑库（M1-M72）',
            '> **由 `scripts/split-pitfalls.py` 从 `history-pitfalls.md` 自动派生，禁止手改；修改请到源头。**\n'
            '> **必读**：本文件（移动端专属）+ `history-pitfalls-common.md`（跨端通用），生成移动端原型前逐条对照。',
            mobile_hdr, m_rows),
        'history-pitfalls-prd.md': compose(
            '# PRD 踩坑库（P1-P35 + D38）',
            '> **由 `scripts/split-pitfalls.py` 从 `history-pitfalls.md` 自动派生，禁止手改；修改请到源头。**\n'
            '> **必读**：本文件（PRD 专属）+ `history-pitfalls-common.md`（跨端通用），生成需求文档前逐条对照。',
            prd_hdr, p_rows + prd_d),
        'history-pitfalls-desktop.md': compose(
            '# 桌面端踩坑库（D 系列桌面专属）',
            '> **由 `scripts/split-pitfalls.py` 从 `history-pitfalls.md` 自动派生，禁止手改；修改请到源头。**\n'
            '> **必读**：本文件（桌面端专属）+ `history-pitfalls-common.md`（跨端通用），生成桌面端原型前逐条对照。',
            desktop_hdr, desktop),
        'history-pitfalls-common.md': compose(
            '# 跨端通用踩坑库（全端约束）',
            '> **由 `scripts/split-pitfalls.py` 从 `history-pitfalls.md` 自动派生，禁止手改；修改请到源头。**\n'
            '> **任何端生成都必须先读本文件**（D5 编码 / D17 机制同步 / D27 工具 / D35 工具 / D36 手机号 / D39 无人值守 / D40 交付物核对）。',
            common_hdr, common),
    }

    detail = {
        'M': len(m_rows), 'P': len(p_rows),
        'D_common': len(common), 'D_prd': len(prd_d), 'D_desktop': len(desktop),
        'D_total': len(d_rows),
    }
    return subsets, detail


def main():
    check_only = '--check' in sys.argv

    with io.open(SRC, encoding='utf-8') as f:
        text = f.read()
    subsets, detail = build_subsets(text)

    # 一致性断言（拆分不丢不重）：
    #   M + P + D_total == 原表全量行数
    rows = parse_rows(text)
    total = len(rows)
    sum_sub = detail['M'] + detail['P'] + detail['D_total']
    assert sum_sub == total, f'拆分计数异常: 子集合计 {sum_sub} ≠ 源 {total}'
    assert detail['D_common'] + detail['D_prd'] + detail['D_desktop'] == detail['D_total'], \
        'D 系列分类未覆盖全量'

    changed = []
    for rel, out_lines in subsets.items():
        dst = os.path.join(PROJECT, rel)
        new_text = '\n'.join(out_lines)
        if os.path.exists(dst):
            with io.open(dst, encoding='utf-8') as f:
                old_text = f.read()
            if old_text != new_text:
                changed.append(rel)
        else:
            changed.append(rel)
        if not check_only:
            with io.open(dst, 'w', encoding='utf-8') as f:
                f.write(new_text)

    print(f'[split] 踩坑库拆分校验：M={detail["M"]} P={detail["P"]} '
          f'D(通用={detail["D_common"]}/PRD={detail["D_prd"]}/桌面={detail["D_desktop"]}) 总={total} 项')
    if check_only:
        if changed:
            print(f'❌ 子集文件与源不同步（{len(changed)} 个需重新生成）: {", ".join(changed)}')
            print('   运行: python scripts/split-pitfalls.py')
            return 1
        print('✅ 子集文件与源头完全一致')
        return 0
    if changed:
        print(f'✅ 已生成/刷新 {len(changed)} 个子集文件: {", ".join(changed)}')
    else:
        print('✅ 子集文件已是最新，无需刷新')
    return 0


if __name__ == '__main__':
    sys.exit(main())
