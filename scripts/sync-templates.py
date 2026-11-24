#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync-templates.py — PM Agent 技能副本同步脚本

把「项目副本」的关键文件同步到「技能副本」，保证两份全文件树一致（作者本地双副本开发流专用）。
分发给他人后，技能文件夹本身就是唯一副本，本脚本会自动跳过、绝不改动用户机器上的其它目录。

用法:
    python scripts/sync-templates.py          # 同步（项目 → 副本，覆盖同名文件）
    python scripts/sync-templates.py --check  # 只检查不一致（差异即非 0 退出码，供 verify-all 门禁调用）

同步清单（项目路径 → 副本路径，均为相对技能根目录）:
    templates/*  standards/*  scripts/{build-prototype,browser-check,verify-all,deliverables-check,split-pitfalls}.py
    SKILL.md  history-pitfalls*.md  cross-platform-diff.md  components/*
"""

import os
import sys
import shutil
import filecmp

# 非 UTF-8 终端（Windows GBK/cp936）打印 ✅❌ 等 emoji 会抛 UnicodeEncodeError，强制 UTF-8 输出
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding='utf-8')
    except Exception:
        pass

# 项目根（本脚本位于 scripts/ 下）
PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 技能副本根：默认等于自身 PROJECT（纯单副本安装形态）。
# 只有作者本地「双副本开发流」才用环境变量 PM_AGENT_SKILL_DIR 显式指向另一份副本以启用同步。
SKILL = os.environ.get('PM_AGENT_SKILL_DIR', PROJECT)

# 需要保持一致的相对路径清单（目录整体同步）
SYNC_DIRS = ['templates', 'standards', 'components']
SYNC_FILES = [
    'SKILL.md',
    'history-pitfalls.md',
    'history-pitfalls-mobile.md',
    'history-pitfalls-prd.md',
    'history-pitfalls-desktop.md',
    'history-pitfalls-common.md',
    'cross-platform-diff.md',
]
# scripts 仅同步核心脚本（一次性历史脚本不传播）
# 注意：必须包含 sync-templates.py 自身，否则技能副本永远缺它，
# 导致 verify-all.py 的副本一致性检查环节误报失败（鸡生蛋问题，2026-08-17 修复）
SYNC_SCRIPTS = ['build-prototype.py', 'browser-check.py', 'verify-all.py', 'deliverables-check.py', 'split-pitfalls.py', 'sync-templates.py']


def build_manifest():
    """返回 [(相对路径, 项目绝对路径, 副本绝对路径)]"""
    items = []
    for d in SYNC_DIRS:
        src = os.path.join(PROJECT, d)
        if not os.path.isdir(src):
            continue
        for root, dirs, files in os.walk(src):
            dirs[:] = [d for d in dirs if d != '__pycache__']  # 排除 pyc 缓存，避免同步垃圾文件
            for f in files:
                rel = os.path.relpath(os.path.join(root, f), PROJECT)
                items.append((rel, os.path.join(PROJECT, rel), os.path.join(SKILL, rel)))
    for f in SYNC_FILES:
        rel = f
        items.append((rel, os.path.join(PROJECT, rel), os.path.join(SKILL, rel)))
    for f in SYNC_SCRIPTS:
        rel = os.path.join('scripts', f)
        items.append((rel, os.path.join(PROJECT, rel), os.path.join(SKILL, rel)))
    return items


def main():
    check_only = '--check' in sys.argv

    # 单副本守卫：分发给他人后，技能文件夹本身就是唯一副本（PROJECT == SKILL），
    # 此时没有任何"另一端"可同步，必须安全跳过，绝不误写用户机器上的其它目录。
    if os.path.abspath(SKILL) == os.path.abspath(PROJECT):
        if check_only:
            print('✅ 单副本安装（即分发形态），无需同步，副本一致性天然成立')
            sys.exit(0)
        print('ℹ️  单副本安装（即分发形态），无需同步，已跳过。')
        sys.exit(0)
    # 作者本地双副本开发流：若未显式指定 PM_AGENT_SKILL_DIR 且默认目录不存在，也安全退出。
    if not os.path.isdir(SKILL):
        print('ℹ️  未检测到第二份副本（单副本安装形态），无需同步，已跳过。')
        print('   （如需本地双副本开发流，请用环境变量 PM_AGENT_SKILL_DIR 指向另一份副本）')
        sys.exit(0)

    items = build_manifest()
    missing_src = [(rel, src) for rel, src, _ in items if not os.path.exists(src)]
    if missing_src:
        print('❌ 项目源文件缺失:')
        for rel, src in missing_src[:10]:
            print(f'   {rel} ({src})')
        sys.exit(1)

    if not os.path.isdir(SKILL):
        print(f'❌ 副本根目录不存在: {SKILL}')
        print('   可用环境变量 PM_AGENT_SKILL_DIR 指定')
        sys.exit(1)

    diff = []
    copied = []
    for rel, src, dst in items:
        if not os.path.exists(dst) or not filecmp.cmp(src, dst, shallow=False):
            diff.append((rel, src, dst))

    if check_only:
        if diff:
            print(f'❌ 技能副本与项目不一致（{len(diff)} 个文件需同步）:')
            for rel, _, _ in sorted(diff)[:20]:
                print(f'   - {rel}')
            print('\n   运行: python scripts/sync-templates.py  进行同步')
            sys.exit(1)
        print(f'✅ 技能副本与项目完全一致（{len(items)} 个文件）')
        sys.exit(0)

    # 同步模式
    for rel, src, dst in diff:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(rel)
    if copied:
        print(f'✅ 已同步 {len(copied)} 个文件到技能副本:')
        for rel in sorted(copied):
            print(f'   + {rel}')
    else:
        print(f'✅ 无需同步，技能副本与项目完全一致（{len(items)} 个文件）')


if __name__ == '__main__':
    main()
