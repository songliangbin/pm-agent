#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
deliverables-check.py — 多端项目交付物完整性核对脚本（D40 防护）

用途：多端编排（模式四）Phase 3 结束的机械门禁，防止"某端原型或统一 PRD 被流程遗漏"。
      Agent 在 Phase 3 汇合拼装后、进入步骤⑥之前**必须**运行本脚本核对。

用法：
    python scripts/deliverables-check.py --contract project-contract-{项目名}.md --outdir {交付目录}

行为：
    1. 解析契约文件第十一章「交付物清单」表格（| # | 交付物 | 输出文件名 | 类型 |），提取全部输出文件名
    2. 逐个核对 {outdir}/{文件名} 存在且非空（size > 0）
    3. 任一缺失/为空 → 列出缺失清单，退出码 1（禁止进入步骤⑥，Agent 必须返回补齐）
    4. 全部通过 → 打印 ✓ 清单，退出码 0

退出码：
    0 = 交付物完整，可以交付
    1 = 存在缺失（端原型或 PRD 未产出），禁止交付
"""

import os
import re
import sys
import argparse

# 非 UTF-8 终端（Windows GBK/cp936）打印 ✅❌ 等 emoji 会抛 UnicodeEncodeError，强制 UTF-8 输出
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding='utf-8')
    except Exception:
        pass


def parse_deliverables(contract_path):
    """从契约第十一章「交付物清单」表格提取 [(名称, 输出文件名, 类型)]"""
    if not os.path.exists(contract_path):
        raise ValueError(f'契约文件不存在: {contract_path}')
    with open(contract_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 定位"交付物清单"章节（支持 "十一、" 或 "11." 编号形式）
    m = re.search(r'#{1,6}\s*.*?交付物清单', content)
    if not m:
        raise ValueError('契约缺少「交付物清单」章节（第十一章）。请先在契约中按模板登记全部交付物（含 PRD）。')
    section = content[m.start():]
    # 截断到下一个章标题（"十二、" 或 "12."），避免后续章节的表格（如入口映射表）被误当成交付物
    next_ch = re.search(r'\n#{1,6}\s*(?:十二|十二、|12[、.\s])', section)
    if next_ch:
        section = section[:next_ch.start()]

    rows = []
    # 匹配表格行：| # | 交付物名称 | 输出文件名 | 类型 |
    for line in section.splitlines():
        line = line.strip()
        if not (line.startswith('|') and line.endswith('|')):
            continue
        cells = [c.strip() for c in line.strip('|').split('|')]
        if len(cells) < 3:
            continue
        # 跳过表头/分隔行（含 --- 或 # / 交付物 表头）
        if any(c in ('---', '#') or c.startswith('---') for c in cells[:3]):
            continue
        if cells[1] in ('交付物', '名称') or cells[2] in ('输出文件名',):
            continue
        num = cells[0]
        if not re.match(r'^\d+$', num):
            continue
        name = cells[1]
        fname = cells[2].strip()
        if not fname or fname.startswith('{'):
            continue
        ftype = cells[3] if len(cells) > 3 else ''
        rows.append((name, fname, ftype))
    if not rows:
        raise ValueError('契约「交付物清单」章节未解析到任何交付物行（格式应为 | # | 名称 | 输出文件名 | 类型 |）。')
    return rows


def main():
    parser = argparse.ArgumentParser(description='多端项目交付物完整性核对（D40 防护）')
    parser.add_argument('--contract', required=True, help='项目契约文件路径（project-contract-{项目名}.md）')
    parser.add_argument('--outdir', required=True, help='交付物输出目录（各端原型 + PRD 所在目录）')
    args = parser.parse_args()

    try:
        rows = parse_deliverables(args.contract)
    except ValueError as e:
        print(f'❌ {e}')
        sys.exit(1)

    if not os.path.isdir(args.outdir):
        print(f'❌ 交付目录不存在: {args.outdir}')
        sys.exit(1)

    print('🔄 交付物完整性核对')
    print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
    missing = []
    for name, fname, ftype in rows:
        path = os.path.join(args.outdir, fname)
        if not os.path.exists(path):
            missing.append((name, fname, '文件不存在'))
        elif os.path.getsize(path) == 0:
            missing.append((name, fname, '文件为空'))
        else:
            size_kb = os.path.getsize(path) / 1024
            print(f'  ✓ {name}：{fname}（{size_kb:.0f}KB）')

    if missing:
        print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
        print(f'❌ 交付物缺失 {len(missing)} 项，禁止进入步骤⑥:')
        for name, fname, reason in missing:
            print(f'  - {name}（{fname}）：{reason}')
        print('\n   处理：返回对应生成步骤补齐缺失交付物后，重新运行本脚本核对，全部通过才可交付。')
        print('   （若缺 PRD：按 SKILL.md 编排铁律 8 生成统一 PRD，注入文件须含 nav/sections/section-index/knowledge-base 四件）')
        sys.exit(1)

    print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
    print(f'结论: [ ✅ 交付物完整（{len(rows)} 项）] 可以进入步骤⑥')
    sys.exit(0)


if __name__ == '__main__':
    main()
