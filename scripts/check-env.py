#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check-env.py — PM Agent 环境自检 + 自动安装（v5.25，M108 防护）

用途：任务开始前检查「Python + Playwright + Chromium」是否就绪；
      缺失则自动安装；自动安装失败则明确告知用户手动安装后才能继续使用。

用法：
    python scripts/check-env.py

退出码：
    0 = 环境就绪，可以开始任务
    1 = 环境缺失且自动安装失败（需用户手动安装）

设计说明：
    - Windows 与 macOS 通用：用 `sys.executable -m pip` 而非 pip/pip3，
      自动跟随当前 Python 解释器，避免 pip 指向别的 Python。
    - Playwright 仅用于浏览器断言（browser-check/ui-snapshot），
      未安装时 lint 第 1 层静态检查仍可拦截 100% P0（build 自动降级），
      但本脚本按 PM 要求「必须先装好才继续」，故缺失即自动安装。
    - 自动安装会联网下载 chromium（约 150MB），耗时 1-5 分钟，
      属用户授权的初始化步骤，非"无人值守"阶段的白名单外操作。
"""

import importlib.util
import os
import subprocess
import sys

# v5.41：Windows GBK 终端打印 ✅/❌ 等字符会抛 UnicodeEncodeError，统一 UTF-8 输出
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding='utf-8')
    except Exception:
        pass

OK = '✅'
WARN = '⚠️'
FAIL = '❌'


def run(cmd, timeout=900, capture=True):
    """执行命令，返回 (returncode, output)。timeout 超时视为失败。"""
    try:
        r = subprocess.run(cmd, capture_output=capture, text=True, timeout=timeout)
        out = (r.stdout or '') + (r.stderr or '')
        return r.returncode, out.strip()
    except subprocess.TimeoutExpired:
        return -1, f'命令超时（>{timeout}s）: {" ".join(cmd)}'
    except Exception as e:
        return -1, f'执行失败: {e}'


def have_module(name):
    """检测模块是否已安装"""
    return importlib.util.find_spec(name) is not None


def check_python():
    """Python 版本检测"""
    ver = sys.version_info
    if ver.major < 3 or (ver.major == 3 and ver.minor < 8):
        return False, f'Python 需 ≥3.8，当前 {ver.major}.{ver.minor}.{ver.micro}'
    return True, f'Python {ver.major}.{ver.minor}.{ver.micro}'


def check_playwright_pkg():
    """检测 playwright 包"""
    if have_module('playwright'):
        return True, 'playwright 包已安装'
    return False, 'playwright 包未安装'


def install_playwright_pkg():
    """自动安装 playwright 包"""
    print(f'  {WARN} 未检测到 playwright 包，开始自动安装（pip install playwright）...')
    rc, out = run([sys.executable, '-m', 'pip', 'install', '--quiet', 'playwright'])
    if rc != 0:
        return False, f'pip install playwright 失败:\n{out[-500:]}'
    if not have_module('playwright'):
        return False, f'pip install playwright 后仍检测不到模块（可能是 pip 与当前 Python 不匹配）:\n{out[-300:]}'
    return True, 'playwright 包安装成功'


def check_chromium():
    """检测 chromium 浏览器是否可用（实际 launch 一次最可靠）"""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        return True, 'Chromium 浏览器可用'
    except Exception as e:
        return False, f'Chromium 不可用: {str(e)[:200]}'


def install_chromium():
    """自动安装 chromium 浏览器（约 150MB，1-5 分钟）"""
    print(f'  {WARN} Chromium 浏览器未就绪，开始自动安装（playwright install chromium，约 150MB，请耐心等待）...')
    rc, out = run([sys.executable, '-m', 'playwright', 'install', 'chromium'])
    if rc != 0:
        return False, f'playwright install chromium 失败:\n{out[-500:]}'
    return True, 'Chromium 安装成功'


def main():
    print('🔒 PM Agent 环境自检 (check-env.py)')
    print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
    ok_all = True

    # 1. Python
    ok, msg = check_python()
    print(f"  {OK if ok else FAIL} [1/3] Python 检测：{msg}")
    if not ok:
        ok_all = False

    # 2. Playwright 包
    ok, msg = check_playwright_pkg()
    print(f"  {OK if ok else FAIL} [2/3] Playwright 包：{msg}")
    if not ok:
        ok, msg = install_playwright_pkg()
        print(f"  {OK if ok else FAIL} [2/3] Playwright 包安装：{msg}")
        if not ok:
            ok_all = False

    # 3. Chromium 浏览器
    ok, msg = check_chromium()
    print(f"  {OK if ok else FAIL} [3/3] Chromium 浏览器：{msg}")
    if not ok:
        ok, msg = install_chromium()
        print(f"  {OK if ok else FAIL} [3/3] Chromium 安装：{msg}")
        if not ok:
            ok_all = False

    print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
    if ok_all:
        print('🎉 环境就绪，可以开始 PM Agent 任务')
        sys.exit(0)

    print('❌ 环境未就绪，自动安装失败。请手动安装后重新运行本技能：')
    print()
    print('   ① 安装 Python 3.8+：')
    print('      - Windows: https://www.python.org/downloads/ 下载安装，勾选 "Add to PATH"')
    print('      - macOS:   brew install python  或系统自带 python3')
    print()
    print('   ② 安装 Playwright + Chromium（在技能目录下执行）：')
    print('      pip install playwright')
    print('      playwright install chromium')
    print()
    print('   安装完成后重新运行本技能即可。')
    sys.exit(1)


if __name__ == '__main__':
    main()
