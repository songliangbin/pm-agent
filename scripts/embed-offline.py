#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
embed-offline.py — CDN 资源离线内嵌（v5.26，M109 防护）

用途：把交付物 HTML 中的外部 CDN 引用（Font Awesome / Mermaid / Tailwind / Google Fonts）
      替换为 base64 内嵌资源，使产物 100% 离线可用（图标/图表/样式不丢）。

用法：
    python scripts/embed-offline.py --input 产物.html [--output 产物-离线.html]
    （--output 缺省时原地覆盖）

特性：
    1. 缓存：资源下载到 <技能目录>/assets/vendor/，只下载一次，后续秒级内嵌
    2. 幂等：已内嵌的产物再次运行不重复处理
    3. 降级：某资源下载失败 → 保留原 CDN 引用 + 告警，不阻塞构建（其余照常内嵌）
    4. 平台无关：Windows/macOS 通用

内嵌映射：
    Font Awesome CSS  → <style> 内联（@font-face 字体 woff2 一并 base64）
    Mermaid JS        → <script> 内联
    Tailwind Browser  → <script> 内联（@tailwindcss/browser，Play CDN 官方等价物）
    Google Fonts CSS  → <style> 内联（woff2 字体 base64）
"""

import base64
import os
import re
import sys
import argparse
import urllib.request

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding='utf-8')
    except Exception:
        pass

OK = '✅'
WARN = '⚠️'
FAIL = '❌'

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENDOR_DIR = os.path.join(SKILL_DIR, 'assets', 'vendor')

# 资源缓存文件名映射（按 CDN URL 定位）
CACHE_NAME = {
    'cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css': 'fa-6.4.0-all.min.css',
    'cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css': 'fa-6.5.1-all.min.css',
    'cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js': 'mermaid-10.min.js',
    'cdn.jsdelivr.net/npm/@tailwindcss/browser@4/dist/index.global.js': 'tailwind-browser-4.global.js',
    'cdn.tailwindcss.com': 'tailwind-play-cdn.js',
    'fonts.googleapis.com/css2': 'google-fonts.css',
}


def _http_get(url, timeout=30):
    """下载 URL 返回 bytes，失败抛异常"""
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (PM-Agent-offline-embed)',
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _b64(data):
    return base64.b64encode(data).decode('ascii')


def fetch_cached(url):
    """优先读缓存，否则下载并缓存。返回 (cache_path, is_new)"""
    name = None
    for key, val in CACHE_NAME.items():
        if key in url:
            name = val
            break
    if not name:
        # 未知 URL 用 URL 的 md5 命名（简化：取域名+路径尾）
        import hashlib
        name = hashlib.md5(url.encode()).hexdigest()[:16] + os.path.splitext(url.split('/')[-1])[1]
    cache_path = os.path.join(VENDOR_DIR, name)
    if os.path.exists(cache_path) and os.path.getsize(cache_path) > 0:
        return cache_path, False
    os.makedirs(VENDOR_DIR, exist_ok=True)
    data = _http_get(url)
    with open(cache_path, 'wb') as f:
        f.write(data)
    return cache_path, True


def embed_fa(css_url):
    """FA CSS 内嵌：下载 CSS，解析 @font-face 的 woff2 字体 URL 并一并 base64 内嵌"""
    css_path, new = fetch_cached(css_url)
    css = open(css_path, 'r', encoding='utf-8', errors='replace').read()
    # 解析 CSS 中的相对字体 URL（../webfonts/fa-solid-900.woff2）
    font_urls = re.findall(r"url\(\.\./webfonts/([\w.\-]+)\)", css)
    for fn in font_urls:
        font_cdn = f"https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/{fn}" if '6.4.0' in css_url else \
                   f"https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/webfonts/{fn}"
        fpath, _ = fetch_cached(font_cdn)
        with open(fpath, 'rb') as f:
            font_b64 = _b64(f.read())
        # 替换相对路径为 base64 data URI（保持格式：url(...) format('woff2')）
        css = css.replace(f"url(../webfonts/{fn})", f"url(data:font/woff2;base64,{font_b64})")
    return f'<style>{css}</style>'


def embed_js(url, tag='script'):
    """JS 资源内嵌为 <script>...</script>"""
    jpath, new = fetch_cached(url)
    with open(jpath, 'r', encoding='utf-8', errors='replace') as f:
        js = f.read()
    return f'<{tag}>{js}</{tag}>'


def embed_google_fonts(css_url):
    """Google Fonts CSS 内嵌：下载 CSS，解析 woff2 并 base64 内嵌"""
    css_path, new = fetch_cached(css_url)
    css = open(css_path, 'r', encoding='utf-8', errors='replace').read()
    # Google Fonts CSS 里字体是绝对 URL
    font_urls = re.findall(r"url\((https://fonts\.gstatic\.com/[^)]+\.woff2)\)", css)
    for fu in font_urls:
        fpath, _ = fetch_cached(fu)
        with open(fpath, 'rb') as f:
            font_b64 = _b64(f.read())
        css = css.replace(fu, f"data:font/woff2;base64,{font_b64}")
    return f'<style>{css}</style>'


def embed_file(html, out_path):
    """处理单个 HTML：内嵌所有 CDN 引用，幂等"""
    processed = 0
    failed = []

    # 1. Font Awesome <link>
    def _fa_replace(m):
        nonlocal processed
        url = m.group(1)
        try:
            inline = embed_fa(url)
            processed += 1
            print(f'  {OK} Font Awesome 内嵌: {url}')
            return inline
        except Exception as e:
            failed.append(f'Font Awesome ({url}): {e}')
            print(f'  {WARN} Font Awesome 内嵌失败（保留 CDN 引用）: {e}')
            return m.group(0)

    html = re.sub(
        r'<link[^>]*href="(https://cdnjs\.cloudflare\.com/ajax/libs/font-awesome/[^"]+\.css)"[^>]*>',
        _fa_replace, html)

    # 2. Mermaid <script>
    def _mermaid_replace(m):
        nonlocal processed
        url = m.group(1)
        try:
            inline = embed_js(url)
            processed += 1
            print(f'  {OK} Mermaid JS 内嵌: {url}')
            return inline
        except Exception as e:
            failed.append(f'Mermaid ({url}): {e}')
            print(f'  {WARN} Mermaid 内嵌失败（保留 CDN 引用）: {e}')
            return m.group(0)

    html = re.sub(
        r'<script[^>]*src="(https://cdn\.jsdelivr\.net/npm/mermaid@10/[^"]+\.js)"[^>]*></script>',
        _mermaid_replace, html)

    # 3. Tailwind Play CDN
    def _tw_replace(m):
        nonlocal processed
        url = m.group(1)
        # Play CDN (cdn.tailwindcss.com) 403 拒绝下载 → 用 npm 等价物 @tailwindcss/browser@4
        try:
            if 'tailwindcss.com' in url:
                url = 'https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4/dist/index.global.js'
            inline = embed_js(url)
            processed += 1
            print(f'  {OK} Tailwind JS 内嵌: {url}')
            return inline
        except Exception as e:
            failed.append(f'Tailwind ({url}): {e}')
            print(f'  {WARN} Tailwind 内嵌失败（保留 CDN 引用）: {e}')
            return m.group(0)

    html = re.sub(
        r'<script[^>]*src="(https://cdn\.tailwindcss\.com)"[^>]*></script>',
        _tw_replace, html)

    # 4. Google Fonts
    def _gf_replace(m):
        nonlocal processed
        url = m.group(1)
        try:
            inline = embed_google_fonts(url)
            processed += 1
            print(f'  {OK} Google Fonts 内嵌: {url}')
            return inline
        except Exception as e:
            failed.append(f'Google Fonts ({url}): {e}')
            print(f'  {WARN} Google Fonts 内嵌失败（保留 CDN 引用）: {e}')
            return m.group(0)

    html = re.sub(
        r'<link[^>]*href="(https://fonts\.googleapis\.com/[^"]+)"[^>]*>',
        _gf_replace, html)

    # M109 标记：离线内嵌完成（lint C1-6 检测到该标记跳过类名覆盖检查，
    # 因为内嵌的 Tailwind/Mermaid 运行时动态生成 CSS，静态类名无法验证）
    if processed > 0 and 'offline-embedded' not in html:
        html = html.replace('<head>', '<head>\n    <meta name="offline-embedded" content="1">', 1)

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f'\n内嵌完成: {out_path} ({len(html)/1024:.0f}KB, 内嵌 {processed} 项资源)')
    return processed, failed
def main():
    parser = argparse.ArgumentParser(description='CDN 资源离线内嵌')
    parser.add_argument('--input', required=True, help='输入 HTML 路径')
    parser.add_argument('--output', help='输出路径（缺省=原地覆盖）')
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f'{FAIL} 输入文件不存在: {args.input}')
        sys.exit(1)

    with open(args.input, 'r', encoding='utf-8') as f:
        html = f.read()

    out = args.output or args.input
    out_dir = os.path.dirname(os.path.abspath(out))
    os.makedirs(out_dir, exist_ok=True)
    print(f'🔒 CDN 资源离线内嵌: {os.path.basename(args.input)}')
    print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
    processed, failed = embed_file(html, out)

    if failed:
        print(f'\n{WARN} {len(failed)} 项资源内嵌失败（已保留 CDN 引用，联网时正常，离线时该项降级）:')
        for fmsg in failed:
            print(f'  - {fmsg}')
        sys.exit(1)
    print(f'\n🎉 全部资源已内嵌，产物 100% 离线可用')
    sys.exit(0)


if __name__ == '__main__':
    main()
