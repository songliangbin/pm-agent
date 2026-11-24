#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ui-snapshot.py — PM Agent UI 截图走查工具（第三期「UI 专家」落地）

用途：对移动端原型自动遍历关键页面并截图，供 UI 专家（主 Agent 或用户）走查视觉质量。
     截图按「主 Tab 页 + 二级子页面」分组，存入 {outdir}/ui/ 目录，并生成 index.html 图集。

用法：
    python scripts/ui-snapshot.py <产物.html> [--outdir 目录] [--tabs 0|1] [--subs 0|1]

可选运行时依赖：Playwright（未安装时降级为 DOM 结构走查报告，不截图）。

说明：
    - 与 browser-check.py 互补：browser-check 做机械断言，本工具做视觉走查素材采集
    - Windows Chromium 关闭崩溃（D27）：结尾用 os._exit 绕过浏览器清理
"""
import os
import re
import sys
import json
import argparse

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding='utf-8')
    except Exception:
        pass

OK = '✅'
FAIL = '❌'
WARN = '⚠️'


def is_mobile_file(content):
    return 'phone-frame' in content or 'phone-screen' in content


def read_file(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f'{FAIL} 读取失败: {e}')
        return None


def extract_tabs(content):
    """提取底部 Tab 名（data-tab）"""
    tabs = re.findall(r'class="[^"]*nav-tab[^"]*"[^>]*data-tab="([^"]+)"', content)
    if not tabs:
        # 兜底：主页面 id
        tabs = re.findall(r'<div\s+class="page[^"]*"\s+id="page-([^"]+)"', content)
    return list(dict.fromkeys(tabs))


def extract_subpages(content):
    """提取二级页面 id + 打开函数名（openSubPage('sub-xxx')）"""
    subs = []
    ids = re.findall(r'<div\s+class="sub-page"[^>]*id="(sub-[^"]+)"', content)
    # 收集真实打开入口
    for m in re.finditer(r'openSubPage\(\s*[\'"](sub-[^\'"]+)[\'"]\s*\)', content):
        sid = m.group(1)
        if sid in ids:
            subs.append(sid)
    # 补充有页面但无直接 openSubPage 文本入口的（可能由 JS 拼接）
    for sid in ids:
        if sid not in subs:
            subs.append(sid)
    return list(dict.fromkeys(subs))


def write_manifest(outdir, manifest):
    """落盘走查清单（v5.41）：G2 门禁依据。每次更新即覆盖写，保证崩溃场景下也是最新状态"""
    try:
        with open(os.path.join(outdir, 'manifest.json'), 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f'{WARN} manifest.json 写入失败: {e}')


def dom_walk_report(content, filepath):
    """DOM 结构走查报告（无 Playwright 降级方案）：输出页面清单 + 关键结构检查"""
    print(f"\n{WARN} Playwright 未安装，降级为 DOM 结构走查报告（不截图）")
    print(f"   安装命令: pip install playwright && playwright install chromium")
    tabs = extract_tabs(content)
    subs = extract_subpages(content)
    print(f"\n📋 页面清单: {os.path.basename(filepath)}")
    print(f"  主 Tab 页 ({len(tabs)}): {', '.join(tabs) if tabs else '无'}")
    print(f"  二级页面 ({len(subs)}): {', '.join(subs) if subs else '无'}")
    # 空态/图片/间距结构检查（静态兜底，弥补无截图时的视觉盲区）
    checks = []
    if 'empty-state' in content or 'emptyState(' in content:
        checks.append(f'{OK} 空态组件存在')
    else:
        checks.append(f'{WARN} 未检测到空态组件（empty-state/emptyState()）')
    if 'tabular-nums' in content:
        checks.append(f'{OK} 数字等宽（tabular-nums）存在')
    else:
        checks.append(f'{WARN} 未检测到 tabular-nums（价格/统计数字应有等宽）')
    img_count = len(re.findall(r'class="[^"]*product-card-img[^"]*"', content))
    if img_count:
        checks.append(f'{OK} 商品图区容器 {img_count} 处')
    else:
        checks.append(f'{WARN} 未检测到商品图区容器（product-card-img）')
    for c in checks:
        print(f"  {c}")
    return 0


def main():
    parser = argparse.ArgumentParser(description='PM Agent UI 截图走查工具')
    parser.add_argument('files', nargs='+', help='要截图走查的 HTML 文件路径')
    parser.add_argument('--outdir', default='_snapshots', help='截图输出目录（默认 _snapshots，相对当前工作目录）')
    parser.add_argument('--tabs', type=int, default=1, help='是否截主 Tab 页（1=是 0=否）')
    parser.add_argument('--subs', type=int, default=1, help='是否截二级子页面（1=是 0=否）')
    args = parser.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        # 降级：DOM 结构走查（v5.41：同样产出 manifest，mode='dom'——
        # G2 门禁视 DOM 走查为"未完成真实截图走查"，fail 并提示安装 Playwright）
        rc = 0
        import datetime as _dt2
        dom_manifest = {'generated_at': _dt2.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'tool': 'ui-snapshot.py', 'files': {}}
        outdir = os.path.abspath(args.outdir)
        os.makedirs(outdir, exist_ok=True)
        for f in args.files:
            if not os.path.exists(f):
                print(f"{FAIL} 文件不存在: {f}")
                rc = 1
                continue
            content = read_file(f)
            if content is None:
                rc = 1
                continue
            dom_walk_report(content, f)
            absf = os.path.abspath(f)
            dom_manifest['files'][absf] = {
                'mode': 'dom', 'file': os.path.basename(f),
                'expected_tabs': extract_tabs(content), 'expected_subs': extract_subpages(content),
                'captured_tabs': 0, 'captured_subs': 0,
                'tab_failures': ['未截图：Playwright 未安装，降级为 DOM 走查'],
                'sub_failures': []}
        write_manifest(outdir, dom_manifest)
        sys.exit(rc)

    outdir = os.path.abspath(args.outdir)
    ui_dir = os.path.join(outdir, 'ui')
    os.makedirs(ui_dir, exist_ok=True)

    print("━" * 60)
    print("📸 UI 截图走查 (ui-snapshot.py)")
    print("━" * 60)

    index_entries = []  # (文件名, 标题, 相对路径)
    total_rc = 0
    # v5.41：走查清单 manifest——记录每文件期望页/成功页/失败明细，
    # gate-check G2 据此判定"全部页面都被真实走查"，缺 manifest = 走查未完成
    import datetime as _dt
    manifest = {'generated_at': _dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'tool': 'ui-snapshot.py', 'files': {}}

    try:
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=True)
            except Exception as e:
                print(f"\n❌ Chromium 启动失败: {str(e)[:200]}")
                sys.exit(2)

            for filepath in args.files:
                if not os.path.exists(filepath):
                    print(f"\n{FAIL} 文件不存在: {filepath}")
                    total_rc = 1
                    continue
                content = read_file(filepath)
                if content is None:
                    total_rc = 1
                    continue
                if not is_mobile_file(content):
                    print(f"\n{WARN} 非移动端产物，跳过截图（当前仅移动端 phone-frame 走查）: {os.path.basename(filepath)}")
                    continue

                # v5.41：逐文件记录期望页清单与失败明细（G2 门禁据此判定走查完整性，
                # 杜绝"截图失败仍记 OK"的假素材假绿灯）
                entry = {'mode': 'browser', 'file': os.path.basename(filepath),
                         'expected_tabs': [], 'expected_subs': [],
                         'captured_tabs': 0, 'captured_subs': 0,
                         'tab_failures': [], 'sub_failures': []}

                print(f"\n📋 截图走查: {os.path.basename(filepath)}")
                page = browser.new_page(viewport={'width': 390, 'height': 844})

                # 阻断外部 CDN 请求（避免离线挂起）
                def _block_external(route):
                    if route.request.url.startswith(('http://', 'https://')):
                        route.fulfill(status=200, content_type='text/css', body='')
                    else:
                        route.continue_()
                try:
                    page.route('**/*', _block_external)
                except Exception:
                    pass

                abs_path = os.path.abspath(filepath)
                url = 'file:///' + abs_path.replace('\\', '/').replace(' ', '%20')
                try:
                    page.goto(url, wait_until='load', timeout=15000)
                    page.wait_for_timeout(800)
                except Exception as e:
                    print(f"  {FAIL} 页面加载失败: {str(e)[:200]}")
                    entry['page_failures'] = [f'页面加载失败: {str(e)[:120]}']
                    manifest['files'][abs_path] = entry
                    write_manifest(outdir, manifest)
                    total_rc = 1
                    page.close()
                    continue

                base = os.path.splitext(os.path.basename(filepath))[0]

                # ---- 1. 主 Tab 页截图 ----
                if args.tabs:
                    tabs = extract_tabs(content)
                    entry['expected_tabs'] = tabs
                    for name in tabs:
                        try:
                            page.evaluate(f"switchTab && switchTab('{name}')")
                            page.wait_for_timeout(350)
                        except Exception as e:
                            entry['tab_failures'].append(f'{name}: 切换异常 {str(e)[:80]}')
                            print(f"  {FAIL} Tab·{name} 切换失败")
                            continue
                        png = f"{base}__tab_{name}.png"
                        try:
                            page.screenshot(path=os.path.join(ui_dir, png))
                        except Exception as e:
                            entry['tab_failures'].append(f'{name}: 截图失败 {str(e)[:80]}')
                            print(f"  {FAIL} Tab·{name} 截图失败")
                            continue
                        entry['captured_tabs'] += 1
                        index_entries.append((filepath, f"Tab·{name}", f"ui/{png}"))
                        print(f"  {OK} Tab·{name} → {png}")

                # ---- 2. 二级子页面截图 ----
                if args.subs:
                    subs = extract_subpages(content)
                    entry['expected_subs'] = subs
                    for sid in subs:
                        try:
                            page.evaluate(f"openSubPage && openSubPage('{sid}')")
                            page.wait_for_timeout(450)
                        except Exception as e:
                            entry['sub_failures'].append(f'{sid}: 打开异常 {str(e)[:80]}')
                            print(f"  {FAIL} 子页·{sid} 打开失败")
                            continue
                        png = f"{base}__sub_{sid}.png"
                        try:
                            page.screenshot(path=os.path.join(ui_dir, png))
                        except Exception as e:
                            entry['sub_failures'].append(f'{sid}: 截图失败 {str(e)[:80]}')
                            print(f"  {FAIL} 子页·{sid} 截图失败")
                            continue
                        entry['captured_subs'] += 1
                        index_entries.append((filepath, f"子页·{sid}", f"ui/{png}"))
                        print(f"  {OK} 子页·{sid} → {png}")
                        try:
                            page.evaluate(f"closeSubPage && closeSubPage('{sid}')")
                            page.wait_for_timeout(250)
                        except Exception:
                            pass  # 关闭失败由下轮 openSubPage 幂等处理，不计失败

                page.close()
                n_tab_bad = len(entry['tab_failures'])
                n_sub_bad = len(entry['sub_failures'])
                if n_tab_bad or n_sub_bad:
                    total_rc = 1
                    print(f"  {FAIL} 该文件存在未成功走查页面（Tab 失败 {n_tab_bad} / 子页失败 {n_sub_bad}），退出码置红")
                manifest['files'][abs_path] = entry

            # 生成 index.html 图集
            if index_entries:
                idx_path = os.path.join(outdir, 'index.html')
                with open(idx_path, 'w', encoding='utf-8') as f:
                    f.write('<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">')
                    f.write('<title>UI 走查图集</title><style>')
                    f.write('body{font-family:-apple-system,sans-serif;background:#f5f5f7;margin:0;padding:24px}')
                    f.write('h1{font-size:18px}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:20px}')
                    f.write('.card{background:#fff;border-radius:12px;padding:12px;box-shadow:0 2px 8px rgba(0,0,0,.08)}')
                    f.write('.card h3{font-size:13px;margin:0 0 8px;color:#333;word-break:break-all}')
                    f.write('img{width:100%;border-radius:8px;border:1px solid #eee}')
                    f.write('</style></head><body><h1>UI 走查图集</h1><div class="grid">')
                    for src, title, rel in index_entries:
                        f.write(f'<div class="card"><h3>{title}</h3><img loading="lazy" src="{rel}" alt="{title}"></div>')
                    f.write('</div></body></html>')
                print(f"\n{OK} 图集已生成: {idx_path}")
                print(f"   打开后可逐屏走查视觉质量（间距/对齐/层级/空态）")
            else:
                print(f"\n{WARN} 未生成任何截图（可能非移动端或加载失败）")

    except Exception as e:
        print(f"\n{FAIL} 截图会话异常: {str(e)[:200]}")
        total_rc = 1

    # v5.41：无论成功/失败都会话结束落盘 manifest（G2 门禁依据）
    write_manifest(outdir, manifest)

    print(f"\n{'━' * 60}")
    print(f"{OK if total_rc == 0 else FAIL} UI 截图走查完成" + ("，全部成功" if total_rc == 0 else "，存在失败项"))
    sys.stdout.flush(); sys.stderr.flush()
    os._exit(total_rc)  # 绕过 Windows Chromium 关闭崩溃（D27）


if __name__ == '__main__':
    main()
