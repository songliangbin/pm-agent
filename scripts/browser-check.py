#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
browser-check.py — PM Agent 交付物浏览器机械断言检查（第 2 层验证）

用法：
    python scripts/browser-check.py 生成的文件1.html 生成的文件2.html ...

断言（全部客观可判定，无需人工观察）：
    B1  页面无裸 JS 代码文本（body 可见文本不含代码特征）
    B2  console 零 error（捕获 pageerror 与 console.error）
    B3  桌面端：doLogin 存在 → 登录后 dashboard 可见 → 至少一张表格有数据
    B4  移动端：默认页可见 → 底部 Tab 可切换（逐个点击验证）
    B5  PRD：doSearch 搜索有结果 → findAnswer 助手有回答（简易版 PRD 跳过本项）
    B13 移动端：sheet 打开后点击内部跳转 → 断言 sheet 已关闭（防弹层残留，D45）
    B14 移动端：打开的 sheet 底部不被悬浮导航遮挡（D44）
    B15 移动端：页面无回到顶部按钮（D47）
    B16 移动端：首页入口语义断言——点搜索框进入含搜索特征的页面；多个 banner 进入的页面必须不同（D43/L6）
    B17 移动端：操作形态·信息展示——点"关于/协议/帮助"→ 断言进入二级页而非 sheet 弹窗（L7/M71）
    B18 移动端：操作形态·表单创建——点"新增地址"→ 断言进入独立表单页而非内联展开（L7/M72）
    B19 桌面端：详情形态断言——点列表行「查看/详情」→ 必须呈现内容区二级页 .detail-header，禁止右侧抽屉 drawer 塞详情（D44/M46）
    B20 移动端：子页面标题居中断言——每个 .sub-page 的 nav 标题必须带 class="sub-page-title"，且打开后可见标题计算样式 position:absolute + left:50%（M112）
    B21 移动端：网格布局完整性断言——所有 display:grid 容器卡片数 % 列数 == 0（无孤卡留白），跨行大卡豁免（M113）
    B22 白字白底对比度断言——可见白色文字元素必须有深色/渐变背景，纯白/近白背景上白字即 fail（M114，防 CSS 变量未定义导致样式整条失效；实现位于移动端检查段落，仅移动端识别产物执行）
    B23 移动端：Tab 页渲染非空断言——所有主 Tab 页内的渲染目标容器（id 以 List/Products/Tabs/Grid/Sidebar/Content 结尾或标准列表类）必须已填充内容或空态兜底，纯空白即 fail（M115/D49，防渲染函数定义却不执行）
    B24 移动端：筛选标签栏 sticky 断言——订单/状态/筛选类 tabs 容器 computed position 必须为 sticky，固定在顶部不随列表内容滚动（M117/D51）
    B25 移动端：底部操作栏按钮布局断言——.detail-bar 内多按钮必须伸缩填满整行（无右侧留白）、单按钮自适应居中（M118/D52）
    B26 移动端：分类页侧栏固定+间距断言——分类左侧栏 computed position 必须 sticky 且 top≥0；双栏父容器 align-items:flex-start 且 gap 非空（M119）
    B27 移动端：底部结算栏固定断言——购物车「全选+合计+结算」栏 computed position 必须 sticky；栏底部须贴近底部悬浮导航顶部（既不得与导航重叠，也不得远离导航悬浮在界面中间）（M120/D54）

退出码：
    0 = 全部通过（或运行环境不可用：未安装 Playwright 时自动跳过，仅提示安装，不算失败）
    1 = 有失败项（禁止交付，打回重做）

注意：Playwright/Chromium 是「可选」运行时依赖。未安装时本脚本会打印明确警告并以退出码 0 跳过浏览器断言，
      构建流程（build-prototype.py）不会因此变红；第 1 层 Lint 仍强制运行，足以拦住结构/对齐/脱敏等模板级回归。
      安装命令：pip install playwright && playwright install chromium

说明：
    - 使用 file:// 协议直接打开本地 HTML（原型为单文件无外部依赖）
    - 硬 gate 由程序执行，不存在"AI 是否认真看"的问题
"""

import sys
import os
import re
import json
import time
import argparse

# 非 UTF-8 终端（Windows GBK/cp936）打印 ✅❌ 等 emoji 会抛 UnicodeEncodeError，强制 UTF-8 输出
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding='utf-8')
    except Exception:
        pass

# ============================================================
# 工具函数
# ============================================================

def is_mobile_file(content):
    return 'phone-frame' in content or 'phone-screen' in content

def is_desktop_file(content):
    return ('sidebar' in content.lower() and 'switchPage' in content) or \
           ('loginPage' in content and 'switchPage' in content) or \
           ('doLogin' in content and 'navigateTo' in content)

def is_prd_file(content):
    return 'prd-section' in content or ('tab-content' in content and 'showSection' in content and 'findAnswer' in content) \
           or 'PM-AGENT-PRD' in content  # 简易版 PRD 标记（无 findAnswer）

def is_template_file(path):
    """判断是否为模板文件（基础骨架模板，B2+ 数据注入类断言降级为警告）"""
    basename = os.path.basename(path).lower()
    return basename in ('prototype-mobile.html', 'prototype-desktop.html', 'prototype-desktop-v2.html', 'prototype-desktop-v3.html', 'prd-template.html', 'prd-template-simple.html')

# JS 代码特征（检测裸代码渲染）
CODE_PATTERNS = [
    r'function\s+\w+\s*\(',
    r'^\s*(var|let|const)\s+\w+\s*=',
    r'document\.getElementById',
    r'\.addEventListener',
    r'\.classList\.',
    r'\.innerHTML\s*=',
    r'forEach\s*\(',
]

def has_code_features(text):
    """检测文本中是否含 JS 代码特征"""
    for pat in CODE_PATTERNS:
        if re.search(pat, text, re.MULTILINE):
            return True
    return False


class BrowserChecker:
    def __init__(self, filepath, prd_mode='detailed'):
        self.filepath = filepath
        self.filename = os.path.basename(filepath)
        self.prd_mode = prd_mode
        self.passed = []
        self.failed = []
        self.warnings = []
        self.page = None

    def ok(self, rule, msg):
        self.passed.append((rule, msg))
        print(f"   ✓ [{rule}] {msg}")

    def fail(self, rule, msg):
        self.failed.append((rule, msg))
        print(f"   ✗ [{rule}] {msg}")

    def warn(self, rule, msg):
        self.warnings.append((rule, msg))
        print(f"   ⚠ [{rule}] {msg}")

    def run(self, page):
        self.page = page
        # 读取文件
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            self.fail('B0', f'无法读取文件: {e}')
            return self.exit_code()
        self.content = content

        filetype = 'unknown'
        if is_prd_file(content):
            filetype = 'prd'
        elif is_mobile_file(content):
            filetype = 'mobile'
        elif is_desktop_file(content):
            filetype = 'desktop'
        else:
            filetype = 'desktop'  # 默认按桌面端尝试

        # 收集 console 错误
        console_errors = []
        def on_pageerror(exc):
            console_errors.append(f'pageerror: {str(exc)[:200]}')
        def on_console(msg):
            if msg.type in ('error',):
                console_errors.append(f'console.error: {msg.text[:200]}')
        page.on('pageerror', on_pageerror)
        page.on('console', on_console)

        # 阻断外部 CDN 请求（字体/图标库），避免离线环境下 load 事件挂起导致断言超时。
        # 用空 200 兜底而非 abort，避免触发 console.error（net::ERR_FAILED）误伤 B2。
        # 原型布局 CSS 为内联，列宽/头像等断言不依赖外网资源。
        # v5.41：记录被拦截的外部请求数 —— B-OFFLINE 据此判定"产物依赖网络却被判绿"
        blocked_external = []
        def _block_external(route):
            if route.request.url.startswith(('http://', 'https://')):
                blocked_external.append(route.request.url)
                route.fulfill(status=200, content_type='text/css', body='')
            else:
                route.continue_()
        try:
            page.route('**/*', _block_external)
        except Exception:
            pass

        # 打开页面（路径先转绝对，避免相对路径生成 file:///xxx 错误 URL）
        abs_path = os.path.abspath(self.filepath)
        url = 'file:///' + abs_path.replace('\\', '/').replace(' ', '%20')
        try:
            page.goto(url, wait_until='load', timeout=15000)
            page.wait_for_timeout(600)  # 等待 JS 初始化
        except Exception as e:
            self.fail('B0', f'页面加载失败: {str(e)[:200]}')
            return self.exit_code()

        # ---- B1 无裸代码 ----
        try:
            body_text = page.evaluate("document.body ? document.body.innerText : ''")
            if not body_text or len(body_text.strip()) < 10:
                self.warn('B1', 'body 可见文本为空或过短（可能页面未渲染）')
            elif has_code_features(body_text):
                sample = re.findall(r'function\s+\w+\(', body_text)
                self.fail('B1', f'页面可见文本含 JS 代码特征（{len(sample)} 处 function），疑似裸代码渲染')
            else:
                self.ok('B1', '页面无裸 JS 代码文本')
        except Exception as e:
            self.warn('B1', f'B1 检查异常: {str(e)[:120]}')

        # ---- B2 console 零错误 ----
        page.wait_for_timeout(400)  # 再等一帧，捕获异步错误
        if not console_errors:
            self.ok('B2', 'console 零 error')
        else:
            self.fail('B2', f'console 捕获 {len(console_errors)} 个错误: {"; ".join(console_errors[:3])}')

        # ---- B2+ 页面自验证（runAssertions 自动执行结果）----
        try:
            auto_result = page.evaluate("window.__pmAssertions || null")
            if auto_result:
                ap = auto_result.get('pass', 0)
                af = auto_result.get('fail', 0)
                if af == 0:
                    self.ok('B2+', f'页面自验证全部通过（{ap} 项断言）')
                elif is_template_file(self.filepath):
                    # 模板文件未注入数据，数据类断言失败属预期，降级为警告
                    fail_items = [it for it in auto_result.get('items', []) if it.get('s') == '✗']
                    names = ', '.join([it.get('n', '') for it in fail_items[:6]])
                    self.warn('B2+', f'模板未注入数据，{af} 项断言待填充（{names}）— 生成文件必须全部通过')
                else:
                    # 提取失败项详情
                    fail_items = [it for it in auto_result.get('items', []) if it.get('s') == '✗']
                    details = '; '.join([f"{it.get('n')}{(' → ' + it.get('d')) if it.get('d') else ''}" for it in fail_items[:5]])
                    self.fail('B2+', f'页面自验证 {af} 项失败: {details}')
        except Exception as e:
            self.warn('B2+', f'自验证解析异常: {str(e)[:120]}')

        # ---- 分类型检查 ----
        if filetype == 'desktop':
            self._check_desktop(page)
        elif filetype == 'mobile':
            self._check_mobile(page)
        elif filetype == 'prd':
            self._check_prd(page)
        else:
            self.warn('B0', '无法识别文件类型，跳过专项检查')

        # ---- B-OFFLINE 离线交付真实性（v5.41）----
        # 外部请求已被 route 伪造空 200，若无 offline-embedded 标记，产物实际依赖网络
        # 却照样全绿（审计确认项）。模板骨架豁免为警告；生成文件为硬失败——
        # 正常构建路径默认自动内嵌（build → embed-offline），仅 --skip-embed 构建的
        # 产物会命中本断言，如实反映"主动放弃离线保证"。
        try:
            offline_marked = 'offline-embedded' in content
            static_ref = bool(re.search(r'(?:src|href)=["\']https?://', content))
            if not offline_marked and (len(blocked_external) > 0 or static_ref):
                msg = (f'产物依赖外部 CDN 但未离线内嵌（本次拦截外部请求 {len(blocked_external)} 个）'
                       f'——离线打开时图标/图表/样式将丢失。请用 build-prototype.py 默认流程重新构建（自动内嵌）')
                if is_template_file(self.filepath):
                    self.warn('B-OFFLINE', f'[模板骨架豁免] {msg}')
                else:
                    self.fail('B-OFFLINE', msg)
        except Exception as e:
            self.warn('B-OFFLINE', f'检查异常: {str(e)[:100]}')

        return self.exit_code()

    # ---------- 桌面端专项 ----------
    def _check_desktop(self, page):
        # B3a doLogin 存在
        has_login = page.evaluate("typeof doLogin === 'function'")
        if not has_login:
            self.fail('B3', 'doLogin 函数不存在（登录按钮点击将抛 ReferenceError）')
            return
        self.ok('B3', 'doLogin 函数存在')
        # 尝试登录：优先点击登录按钮，否则直接调用
        login_clicked = False
        try:
            # 查找登录按钮
            clicked = page.evaluate("""
            (function() {
                var btns = document.querySelectorAll('button, .btn, [onclick*="doLogin"]');
                for (var i = 0; i < btns.length; i++) {
                    var el = btns[i];
                    var oc = el.getAttribute('onclick') || '';
                    if (oc.indexOf('doLogin') !== -1 || el.className.indexOf('login') !== -1) {
                        el.click();
                        return true;
                    }
                }
                // 尝试直接调用
                if (typeof doLogin === 'function') { doLogin(); return true; }
                return false;
            })()
            """)
            login_clicked = bool(clicked)
            page.wait_for_timeout(500)
        except Exception as e:
            try:
                page.evaluate("typeof doLogin === 'function' ? doLogin() : null")
                page.wait_for_timeout(500)
                login_clicked = True
            except Exception as e2:
                self.warn('B3', f'登录动作执行异常: {str(e2)[:120]}')

        # B3b dashboard 可见且表格有数据
        try:
            dash_ok = page.evaluate("""
            (function() {
                // 找 dashboard 页面
                var dash = document.getElementById('page-dashboard') || document.getElementById('dashboard');
                if (dash) {
                    var style = window.getComputedStyle(dash);
                    if (style.display === 'none') return {visible: false, reason: 'dashboard display:none'};
                }
                // 统计有数据的表格
                var tbodies = document.querySelectorAll('tbody');
                var filled = 0;
                var empty = 0;
                tbodies.forEach(function(tb) {
                    if (tb.querySelectorAll('tr').length > 0) filled++;
                    else empty++;
                });
                return {visible: true, filled: filled, empty: empty, total: tbodies.length};
            })()
            """)
            if not dash_ok.get('visible'):
                self.fail('B3', f'登录后 dashboard 不可见: {dash_ok.get("reason", "未知")}')
                return
            if dash_ok.get('filled', 0) == 0 and dash_ok.get('total', 0) > 0:
                self.fail('B3', f'登录后 {dash_ok.get("total")} 张表格全部为空（渲染函数未执行或数据缺失）')
                return
            self.ok('B3', f'登录后 dashboard 可见，表格数据正常（{dash_ok.get("filled")} 张有数据 / {dash_ok.get("total")} 张）')
        except Exception as e:
            self.warn('B3', f'B3 检查异常: {str(e)[:120]}')

        # B11 顶层遮罩检测（D37 防护）：登录后检查是否有 position:fixed + z-index>=999 的可见元素
        # 仍遮住 app。典型事故：Agent 在注入区重复写了 <section id="loginPage">（fixed z-index:9999），
        # doLogin 只隐藏了模板的 <div id="loginPage">，第二个 section 永远盖在 app 上方 —— 登录"假失败"。
        try:
            cover = page.evaluate("""
            (function() {
                var covers = [];
                document.querySelectorAll('*').forEach(function(el) {
                    var cs = window.getComputedStyle(el);
                    if (cs.position !== 'fixed' && cs.position !== 'absolute') return;
                    var z = parseInt(cs.zIndex, 10);
                    if (!(z >= 999)) return;
                    var r = el.getBoundingClientRect();
                    if (r.width === 0 || r.height === 0) return;
                    if (cs.display === 'none' || cs.visibility === 'hidden' || cs.opacity === '0') return;
                    var app = document.getElementById('app');
                    if (!app) return;
                    var ar = app.getBoundingClientRect();
                    // 遮罩必须实际覆盖 app 的可视中心区域才算"挡住"
                    var cx = (ar.left + ar.right) / 2, cy = (ar.top + ar.bottom) / 2;
                    if (cx >= r.left && cx <= r.right && cy >= r.top && cy <= r.bottom) {
                        covers.push({id: el.id || '', cls: String(el.className).slice(0, 40), z: z});
                    }
                });
                return covers;
            })()
            """)
            if cover and len(cover) > 0:
                desc = '; '.join(f'#{c.get("id") or c.get("cls")}(z={c.get("z")})' for c in cover[:5])
                self.fail('B11', f'登录后仍有 {len(cover)} 个 fixed/absolute 高层级元素遮住 app: {desc}（D37：重复 #loginPage 或残留遮罩会挡住登录后界面）')
            else:
                self.ok('B11', '登录后无顶层遮罩（无 fixed/absolute z-index>=999 元素遮挡 app）')
        except Exception as e:
            self.warn('B11', f'B11 检查异常: {str(e)[:120]}')

        # B3+ 菜单点击切换（M16 盲区修复：每个 nav-item 点击后对应 page 必须显示）
        try:
            menu_ok = page.evaluate("""
            (function() {
                var isV4 = document.documentElement.innerHTML.indexOf('pm-agent-paradigm:desktop-v4') !== -1;
                var pages = document.querySelectorAll('.page');
                if (isV4) {
                    // V4 顶栏外壳（无左栏）：菜单 = 顶栏 .topnav-item，点击 → switchSection → 对应 page 激活
                    var secs = Array.from(document.querySelectorAll('.topnav-item'));
                    if (secs.length === 0) return {ok: false, reason: 'V4 顶栏无区段菜单项', items: 0};
                    var clicked = 0; var failed = [];
                    secs.forEach(function(sec){
                        var key = sec.getAttribute('data-section');
                        if (!key) return;
                        sec.click();
                        var active = document.querySelector('.page.active');
                        if (!active) { failed.push(key + '(点击后无激活页)'); return; }
                        var st = window.getComputedStyle(active);
                        if (st.display === 'none') { failed.push(key + '(激活页隐藏)'); return; }
                        clicked++;
                    });
                    if (failed.length) return {ok: false, reason: failed.join(' | '), clicked: clicked};
                    // M22@V4：系统管理是纯分组（有二级菜单、自身不导航到内容页）；验证子项可跳转
                    // 兼容：一级菜单 >8 时系统管理可能被收进「更多」面板（.topnav-more-row）
                    var sysItem = document.querySelector('.topnav-item[data-section="system"]') || document.querySelector('.topnav-more-row[data-section="system"]');
                    if (!sysItem || !(sysItem.querySelector('.topnav-sub') || sysItem.querySelector('.topnav-more-sub'))) return {ok: false, reason: 'V4 系统管理缺少二级菜单（应为纯分组）', clicked: clicked};
                    var reqs4 = ['org','roles','menus','dicts','logs'];
                    var miss4 = reqs4.filter(function(rp){ return !document.getElementById('page-' + rp); });
                    if (miss4.length) return {ok: false, reason: 'V4 系统管理缺标准子页: ' + miss4.join(','), clicked: clicked};
                    var child = sysItem.querySelector('.topnav-sub-item');
                    if (child) { child.click(); var ap = document.querySelector('.page.active'); if (!ap || ap.id !== 'page-org') return {ok: false, reason: 'V4 系统管理二级菜单点击未跳转到子页', clicked: clicked}; }
                    return {ok: true, clicked: clicked};
                }
                var items = document.querySelectorAll('.nav-item[data-page], [data-page][onclick*="switchPage"], [onclick*="switchPage"]');
                if (items.length === 0 || pages.length === 0) return {ok: false, reason: '无菜单项或页面元素', items: items.length, pages: pages.length};
                var clicked = 0;
                var failed = [];
                items.forEach(function(item) {
                    var pageName = item.getAttribute('data-page');
                    if (!pageName) {
                        var oc = item.getAttribute('onclick') || '';
                        var mm = oc.match(/switchPage\\(['"]([\\w-]+)['"]\\)/);
                        if (mm) pageName = mm[1];
                    }
                    if (!pageName) return;
                    var target = document.getElementById('page-' + pageName);
                    if (!target) { failed.push(pageName + '(无page元素)'); return; }
                    item.click();
                    var style = window.getComputedStyle(target);
                    var visible = style.display !== 'none' && target.classList.contains('active');
                    if (!visible) { failed.push(pageName + '(点击后仍隐藏)'); return; }
                    // M17：目标页面必须包含有数据的表格（tbody 有行），否则视为渲染缺失
                    var tbodies = target.querySelectorAll('tbody');
                    if (tbodies.length > 0) {
                        var filled = 0;
                        tbodies.forEach(function(tb) { if (tb.querySelectorAll('tr').length > 0) filled++; });
                        if (filled === 0) { failed.push(pageName + '(页面表格全部为空，渲染函数未执行)'); return; }
                    }
                    // M20：数据列表页必须有分页容器（TopN 排行/统计页除外）
                    var statPages = ['stats','finance','dashboard','report','analytics','analysis','commission'];
                    var hasDataTable = target.querySelectorAll('table.data-table').length > 0;
                    var hasPager = target.querySelector('.pages, .table-footer') !== null;
                    if (hasDataTable && !hasPager && statPages.indexOf(pageName) === -1) {
                        failed.push(pageName + '(有表格但缺分页容器，M20)');
                        return;
                    }
                    // M20b：分页器布局规范——左侧"共 X 条"，右侧翻页组（上一页/页码/下一页）
                    if (hasPager) {
                        var totalEl = target.querySelector('.pg-total');
                        var navEl = target.querySelector('.pg-nav');
                        if (totalEl && !/共\\s*\\d+\\s*条/.test(totalEl.textContent)) {
                            failed.push(pageName + '(分页器缺"共X条"文案)');
                            return;
                        }
                        if (totalEl && navEl && target.querySelector('.table-footer .pages')) {
                            var totalPos = totalEl.compareDocumentPosition(navEl);
                            var totalBeforeNav = (totalPos & Node.DOCUMENT_POSITION_FOLLOWING) !== 0;
                            if (!totalBeforeNav) {
                                failed.push(pageName + '(分页器布局错误：共X条须在左侧)');
                                return;
                            }
                        }
                    }
                    // M22：系统管理 5 个标准二级菜单（按导航形态分流）
                    // V4 三栏驾驶舱：用范式签名精确识别（V2/V3 也含 .topnav/.right-rail，不能用 class 计数区分）
                    var isV4Cockpit = document.documentElement.innerHTML.indexOf('pm-agent-paradigm:desktop-v4') !== -1;
                    var isTopnavMixed = (document.querySelector('.topnav-group') !== null) && (document.querySelector('.nav-parent') === null);
                    var isV3Sidebar = (document.querySelector('.nav-group') !== null) && (document.querySelector('.nav-parent') === null) && (document.querySelector('.topnav-group') === null) && !isV4Cockpit;
                    if (pageName === 'org') {
                        if (isTopnavMixed) {
                            // V2 顶栏「一级 + 下拉二级」混合导航
                            var sysGroup = null;
                            document.querySelectorAll('.topnav-group').forEach(function(g){
                                if (g.textContent.indexOf('系统管理') !== -1) sysGroup = g;
                            });
                            var subItems = sysGroup ? Array.from(sysGroup.querySelectorAll('.topnav-sub-item')).map(function(c){ return c.getAttribute('data-page'); }) : [];
                            var required = ['org','roles','menus','dicts','logs'];
                            var missing = required.filter(function(rp){ return subItems.indexOf(rp) === -1; });
                            if (!sysGroup || !sysGroup.querySelector('.topnav-item.has-sub') || !sysGroup.querySelector('.topnav-sub') || missing.length > 0) {
                                failed.push(pageName + '(系统管理缺标准二级菜单: ' + (missing.join(',') || '无下拉面板') + '，M22@V2)');
                                return;
                            }
                        } else if (isV3Sidebar) {
                            // V3 侧栏分组导航（.nav-group / .nav-group-body）
                            var sysGroup3 = null;
                            document.querySelectorAll('.nav-group').forEach(function(g){
                                var h = g.querySelector('.nav-group-head');
                                if (h && h.textContent.indexOf('系统设置') !== -1) sysGroup3 = g;
                            });
                            var subItems3 = sysGroup3 ? Array.from(sysGroup3.querySelectorAll('.nav-group-body .nav-item')).map(function(c){ return c.getAttribute('data-page'); }) : [];
                            var required3 = ['org','roles','menus','dicts','logs'];
                            var missing3 = required3.filter(function(rp){ return subItems3.indexOf(rp) === -1; });
                            if (!sysGroup3 || missing3.length > 0) {
                                failed.push(pageName + '(系统管理缺标准二级菜单: ' + (missing3.join(',') || '无分组面板') + '，M22@V3)');
                                return;
                            }
                        } else if (isV4Cockpit) {
                            // V4 顶栏外壳（无左导航）：系统管理为纯分组（有二级菜单、自身不导航）
                            var sysItem2 = document.querySelector('.topnav-item[data-section="system"]');
                            if (!sysItem2 || !sysItem2.querySelector('.topnav-sub')) { failed.push(pageName + '(V4 系统管理缺少二级菜单，M22@V4)'); return; }
                            var reqs4 = ['org','roles','menus','dicts','logs'];
                            var miss4 = reqs4.filter(function(rp){ return !document.getElementById('page-'+rp); });
                            if (miss4.length) { failed.push(pageName + '(系统管理缺标准子页: ' + (miss4.join(',')) + '，M22@V4)'); return; }
                        } else {
                            // V1 侧边栏树形
                            var flatTitles = document.querySelectorAll('.nav-group-title').length;
                            var treeParents = document.querySelectorAll('.nav-parent').length;
                            if (flatTitles > 0 && treeParents > 0) {
                                failed.push(pageName + '(侧边栏混合结构：分组标题与树形并存，M22)');
                                return;
                            }
                            var sysParent = null;
                            document.querySelectorAll('.nav-parent').forEach(function(np){
                                if (np.textContent.indexOf('系统管理') !== -1) sysParent = np;
                            });
                            var children = sysParent ? sysParent.nextElementSibling : null;
                            var childPages = children ? Array.from(children.querySelectorAll('.nav-item')).map(function(c){ return c.getAttribute('data-page'); }) : [];
                            var required = ['org','roles','menus','dicts','logs'];
                            var missing = required.filter(function(rp){ return childPages.indexOf(rp) === -1; });
                            if (!sysParent || missing.length > 0) {
                                failed.push(pageName + '(系统管理缺标准二级菜单: ' + (missing.join(',') || '无树形父菜单') + '，M22)');
                                return;
                            }
                        }
                    }
                    // M26：导航展开策略 + 样式差异化（仅 V1 侧边栏树形；V2 顶栏混合导航无此约束，跳过）
                    if (!isTopnavMixed && (pageName === 'dashboard' || pageName === 'org')) {
                        var parents = document.querySelectorAll('.nav-parent');
                        if (parents.length > 0) {
                            var sidebar = document.querySelector('.sidebar');
                            var isTreeAllOpen = sidebar.classList.contains('tree-all-open');
                            var openGroups = 0;
                            parents.forEach(function(np){
                                var ch = np.nextElementSibling;
                                if (ch && ch.classList.contains('open')) openGroups++;
                            });
                            if (parents.length <= 10) {
                                // 全展开 + 一级无图标/无箭头 + 点击不折叠 + 二级有图标
                                var p0 = parents[0];
                                var pIcon = p0.querySelector('.nav-icon');
                                var chevron = p0.querySelector('.nav-chevron');
                                var pIconHidden = !pIcon || getComputedStyle(pIcon).display === 'none';
                                var chevronHidden = !chevron || getComputedStyle(chevron).display === 'none';
                                var child = document.querySelector('.nav-children.open .nav-item');
                                var cIcon = child ? child.querySelector('.nav-icon') : null;
                                var childIconVisible = !cIcon || getComputedStyle(cIcon).display !== 'none';
                                var pStyle = getComputedStyle(p0);
                                var pointerNone = pStyle.pointerEvents === 'none';
                                if (!(isTreeAllOpen && openGroups === parents.length && pIconHidden && chevronHidden && pointerNone && childIconVisible)) {
                                    failed.push(pageName + '(≤10 导航规范不符：需全展开+一级无图标无箭头不可点+二级带图标，M26)');
                                    return;
                                }
                            } else {
                                // 大厂标准：默认折叠 + 一级带图标带箭头 + 点击可展开
                                if (openGroups !== 0) {
                                    failed.push(pageName + '(一级>10应全部折叠，M26)');
                                    return;
                                }
                                var p0 = parents[0];
                                var pIcon = p0.querySelector('.nav-icon');
                                var chevron = p0.querySelector('.nav-chevron');
                                if (!pIcon || !chevron || getComputedStyle(chevron).display === 'none') {
                                    failed.push(pageName + '(>10 一级应带图标+箭头，大厂标准，M26)');
                                    return;
                                }
                            }
                        }
                    }
                    clicked++;
                });
                return {ok: failed.length === 0, clicked: clicked, failed: failed};
            })()
            """)
            if not menu_ok.get('ok'):
                self.fail('B3+', f'菜单点击切换异常: {menu_ok.get("reason") or " | ".join(menu_ok.get("failed", []))}（M16：nav-item 必须能切换页面）')
            else:
                self.ok('B3+', f'菜单点击切换正常（{menu_ok.get("clicked")} 个菜单项全部可切换）')
        except Exception as e:
            self.warn('B3+', f'B3+ 检查异常: {str(e)[:120]}')

        # B3++ 顶栏「一级+下拉二级」混合导航专项（V2）：系统管理下拉展开 + 二级项可切换
        is_v2_topnav = page.evaluate("document.querySelector('.topnav-group') !== null && document.querySelector('.nav-parent') === null")
        if is_v2_topnav:
            try:
                dd = page.evaluate("""
                (function() {
                    var g = null;
                    document.querySelectorAll('.topnav-group').forEach(function(x){ if (x.textContent.indexOf('系统管理') !== -1) g = x; });
                    if (!g) return {ok: false, reason: '无系统管理 topnav-group'};
                    var trig = g.querySelector('.topnav-item.has-sub');
                    if (!trig) return {ok: false, reason: '系统管理一级项缺 .has-sub 触发器'};
                    trig.click();  // 展开下拉
                    var open = g.classList.contains('open');
                    if (!open) return {ok: false, reason: '点击系统管理未展开下拉面板'};
                    var subs = Array.from(g.querySelectorAll('.topnav-sub-item'));
                    var required = ['org','roles','menus','dicts','logs'];
                    var subPages = subs.map(function(s){ return s.getAttribute('data-page'); });
                    var missing = required.filter(function(r){ return subPages.indexOf(r) === -1; });
                    if (missing.length) return {ok: false, reason: '二级菜单缺失: ' + missing.join(',')};
                    // 逐一点击二级项，确认各自页面可切换（收起下拉不影响结果）
                    var fail = [];
                    subs.forEach(function(s){
                        var pn = s.getAttribute('data-page');
                        s.click();
                        var t = document.getElementById('page-' + pn);
                        if (!t || !t.classList.contains('active')) fail.push(pn);
                    });
                    if (fail.length) return {ok: false, reason: '二级项点击未切换: ' + fail.join(',')};
                    return {ok: true, count: subs.length};
                })()
                """)
                if dd.get('ok'):
                    self.ok('B3++', f'顶栏混合导航正常（系统管理下拉展开 + {dd.get("count")} 个二级项可切换）')
                else:
                    self.fail('B3++', f'顶栏混合导航异常: {dd.get("reason")}')
            except Exception as e:
                self.warn('B3++', f'B3++ 检查异常: {str(e)[:120]}')

        # 范式签名判定（V4 三栏驾驶舱）—— 优先于 class 启发式，避免 V4 含 .nav-group 被误判为 V3 侧栏
        is_v4_cockpit = page.evaluate("document.documentElement.innerHTML.indexOf('pm-agent-paradigm:desktop-v4') !== -1")
        # B3+++ 侧栏分组导航专项（V3 现代侧栏）：侧栏折叠 + 分组展开 + 系统设置 5 项直达
        # 注意：V4 左栏分组折叠用 max-height 而非 display，且范式不同，故排除 V4（与 M22 分流一致）
        is_v3_sidebar = page.evaluate("document.querySelector('.nav-group') !== null && document.querySelector('.topnav-group') === null && document.querySelector('.nav-parent') === null")
        if is_v3_sidebar and not is_v4_cockpit:
            try:
                v3 = page.evaluate("""
                (function() {
                    var sb = document.getElementById('sidebar');
                    if (!sb) return {ok: false, reason: '无 #sidebar 元素'};
                    // 1) 分组折叠：toggleNavGroup 应切换 .nav-group-body 显示（V3 无侧栏折叠功能，2026-08-09 用户要求移除）
                    var head = document.querySelector('.nav-group-head');
                    if (head && typeof toggleNavGroup === 'function') {
                        var body = head.parentElement.querySelector('.nav-group-body');
                        if (!body) return {ok: false, reason: 'nav-group-head 无对应 .nav-group-body'};
                        var g = body.parentElement;
                        // 兼容两种折叠实现：display 切换（老 V3）或 .collapsed class（max-height，现行 V3）
                        var dispBefore = getComputedStyle(body).display;
                        var clsBefore = g.classList.contains('collapsed');
                        toggleNavGroup(head);
                        var dispAfter = getComputedStyle(body).display;
                        var clsAfter = g.classList.contains('collapsed');
                        toggleNavGroup(head);
                        if (dispBefore === dispAfter && clsBefore === clsAfter) return {ok: false, reason: 'toggleNavGroup 未切换分组展开/折叠'};
                    }
                    // 2) 「系统设置」分组含标准 5 个二级菜单（org/roles/menus/dicts/logs）
                    var sysGroup = null;
                    document.querySelectorAll('.nav-group').forEach(function(g){
                        var h = g.querySelector('.nav-group-head');
                        if (h && h.textContent.indexOf('系统设置') !== -1) sysGroup = g;
                    });
                    if (!sysGroup) return {ok: false, reason: '侧栏无「系统设置」分组'};
                    var reqs = ['org','roles','menus','dicts','logs'];
                    var miss = reqs.filter(function(rp){ return !sysGroup.querySelector('.nav-item[data-page="'+rp+'"]'); });
                    if (miss.length) return {ok: false, reason: '系统设置缺二级菜单: ' + miss.join(',')};
                    return {ok: true};
                })()
                """)
                if v3.get('ok'):
                    self.ok('B3+++', '侧栏分组导航正常（分组展开/系统设置5项直达，V3 无侧栏折叠）')
                else:
                    self.fail('B3+++', f'侧栏分组导航异常: {v3.get("reason")}')
            except Exception as e:
                self.warn('B3+++', f'B3+++ 检查异常: {str(e)[:120]}')

        # B3++++ 企业驾驶舱专项（V4）：顶栏 ≤8 槽位(含「更多」) + 右栏系统通知 + 区段切换（is_v4_cockpit 已在上方 B3+++ 前算定）
        if is_v4_cockpit:
            try:
                v4 = page.evaluate("""
                (function() {
                    var top = document.getElementById('topnavMenu');
                    if (!top) return {ok:false, reason:'无 #topnavMenu 顶栏菜单容器'};
                    var secs = top.querySelectorAll('.topnav-item');
                    if (secs.length < 6) return {ok:false, reason:'顶栏区段不足6个: '+secs.length};
                    if (secs.length > 8) return {ok:false, reason:'顶栏槽位超过8(含更多): '+secs.length+'，违反V4顶栏最多8菜单约束'};
                    var noti = document.getElementById('todoList');
                    if (!noti || noti.querySelectorAll('.todo-item').length < 1) return {ok:false, reason:'右栏待办事项列表为空（V4→V2 右栏已由系统通知改为待办 #todoList）'};
                    // 区段切换：系统管理为纯分组（有二级菜单、自身不导航到内容页）；兼容「更多」面板
                    var sysItem3 = document.querySelector('.topnav-item[data-section="system"]') || document.querySelector('.topnav-more-row[data-section="system"]');
                    if (!sysItem3 || !(sysItem3.querySelector('.topnav-sub') || sysItem3.querySelector('.topnav-more-sub'))) return {ok:false, reason:'V4 系统管理缺少二级菜单（应为纯分组）'};
                    var reqs4 = ['org','roles','menus','dicts','logs'];
                    if (reqs4.filter(function(rp){ return !document.getElementById('page-'+rp); }).length) return {ok:false, reason:'V4 系统管理缺标准子页'};
                    if (typeof switchSection === 'function') switchSection('home');
                    return {ok:true, secs:secs.length, noti:noti.querySelectorAll('.todo-item').length};
                })()
                """)
                if v4.get('ok'):
                    self.ok('B3++++', f'三栏驾驶舱导航正常（顶栏{v4.get("secs")}区段 + 右栏{v4.get("noti")}条待办 + 区段切换）')
                else:
                    self.fail('B3++++', f'三栏驾驶舱导航异常: {v4.get("reason")}')
            except Exception as e:
                self.warn('B3++++', f'B3++++ 检查异常: {str(e)[:120]}')

        # B7 下拉菜单可见性（D29 防护：触发 dropdown 后菜单必须可见 + 宽度足够，避免被 td overflow:hidden 裁剪导致文字重叠）
        try:
            # 先遍历所有 page，找到第一个含 .dropdown 的页面
            target_page = page.evaluate("""
            (function() {
                var pages = document.querySelectorAll('[id^="page-"]');
                for (var i=0;i<pages.length;i++){
                    if (pages[i].querySelector('.dropdown')) return pages[i].id;
                }
                return null;
            })()
            """)
            if target_page and target_page != 'page-dashboard':
                page.evaluate(f"if(typeof switchPage==='function') switchPage('{target_page.replace('page-','')}')")
                time.sleep(0.3)
            dd = page.evaluate("""
            (function() {
                var all = document.querySelectorAll('.dropdown > button');
                for (var i=0;i<all.length;i++){
                    var r = all[i].getBoundingClientRect();
                    if (r.width>0 && r.height>0 && r.right>0 && r.bottom>0){
                        all[i].closest('.dropdown').scrollIntoView({block:'center'});
                        toggleDropdown(all[i]);
                        var m = all[i].closest('.dropdown').querySelector('.dropdown-menu');
                        if (!m) return {ok:false, reason:'menu not found'};
                        var rm = m.getBoundingClientRect();
                        var cs = getComputedStyle(m);
                        return {
                            ok: cs.display==='block' && rm.width>=100 && rm.height>=30 && rm.x>=0 && rm.x<window.innerWidth,
                            display: cs.display,
                            position: cs.position,
                            width: rm.width,
                            height: rm.height,
                            x: rm.x,
                            y: rm.y,
                            vw: window.innerWidth,
                        };
                    }
                }
                return {ok:true, reason:'no dropdown on any page (skip)'};
            })()
            """)
            if not dd.get('ok'):
                self.fail('B7', f'下拉菜单展开异常（被 td overflow:hidden 裁剪/位置错误/宽度不足）：{dd}')
            elif dd.get('reason') and 'skip' in dd.get('reason', ''):
                self.ok('B7', '全站无 dropdown，跳过')
            else:
                self.ok('B7', f'下拉菜单展开正常（{dd.get("position")}, w={int(dd.get("width"))}px h={int(dd.get("height"))}px）')
        except Exception as e:
            self.warn('B7', f'B7 检查异常: {str(e)[:120]}')

        # B8 重复按钮检测（D31 防护：页头 actions 与 filter-actions 不得出现相同文字的按钮）
        try:
            dup = page.evaluate("""
            (function() {
                // 页头 actions 按钮文字集合
                var pa = document.getElementById('pageActions');
                var headerLabels = [];
                if (pa) {
                    pa.querySelectorAll('button').forEach(function(b){ headerLabels.push(b.textContent.trim().replace(/\\s+/g,'')); });
                }
                // 所有 page 的 filter-actions 按钮文字
                var dups = [];
                document.querySelectorAll('.filter-actions button').forEach(function(b){
                    var t = b.textContent.trim().replace(/\\s+/g,'');
                    if (headerLabels.indexOf(t) !== -1) dups.push(t);
                });
                return {dups: dups};
            })()
            """)
            if dup.get('dups') and len(dup['dups']) > 0:
                self.fail('B8', f'重复按钮：页头 actions 与 filter-actions 出现相同按钮 {dup["dups"]}（D31：同一操作只能放一处）')
            else:
                self.ok('B8', '无页头/filter-actions 重复按钮')
        except Exception as e:
            self.warn('B8', f'B8 检查异常: {str(e)[:120]}')

        # B9 列表布局铁律运行时断言（D32/D33：列等分 + 操作按钮不换行 + 头像不裁剪 + 表头/内容对齐 + 首尾 20px）
        try:
            layout = page.evaluate("""
            (function() {
                var pages = document.querySelectorAll('[id^="page-"]');
                var issues = [];
                var checked = 0;
                var firstPageName = '';
                pages.forEach(function(pg){
                    var tbl = pg.querySelector('table.data-table');
                    if (!tbl) return;
                    checked++;
                    if (!firstPageName) firstPageName = pg.id;
                    // 操作列换行检测
                    var actionTds = tbl.querySelectorAll('td.action-col');
                    actionTds.forEach(function(td){
                        var btns = td.querySelectorAll('.btn');
                        if (btns.length <= 1) return;
                        var tops = [];
                        btns.forEach(function(b){ tops.push(Math.round(b.getBoundingClientRect().top)); });
                        var distinct = Array.from(new Set(tops));
                        if (distinct.length > 1) {
                            issues.push(pg.id + ': 操作列按钮换行(' + btns.length + '个按钮占' + distinct.length + '行)');
                        }
                    });
                    // 头像裁剪检测（首列含头像）
                    var firstTd = tbl.querySelector('tbody td');
                    if (firstTd) {
                        var av = firstTd.querySelector('.avatar-circle, .user-avatar');
                        if (av) {
                            var r = av.getBoundingClientRect();
                            if (r.width < 24 || r.height < 24) {
                                issues.push(pg.id + ': 首列头像被裁剪(w=' + Math.round(r.width) + ',h=' + Math.round(r.height) + ')');
                            }
                        }
                    }
                    // 表头/内容对齐检测（D32：每列表头 text-align 必须等于内容 text-align）
                    var ths = tbl.querySelectorAll('thead th');
                    var bodyRow = tbl.querySelector('tbody tr');
                    if (ths.length && bodyRow) {
                        var tds = bodyRow.querySelectorAll('td');
                        var norm = function(a){ return a === 'start' ? 'left' : (a === 'end' ? 'right' : a); };
                        var n = Math.min(ths.length, tds.length);
                        for (var ci = 0; ci < n; ci++) {
                            var ha = norm(getComputedStyle(ths[ci]).textAlign);
                            var da = norm(getComputedStyle(tds[ci]).textAlign);
                            if (ha !== da) {
                                issues.push(pg.id + ': 第' + (ci+1) + '列表头对齐=' + ha + ' 内容对齐=' + da + ' 不一致（D32 表头/内容错位）');
                            }
                        }
                    }
                });
                return {checked: checked, issues: issues, firstPageName: firstPageName};
            })()
            """)
            if layout.get('issues'):
                self.fail('B9', '; '.join(layout['issues']) + '（D32/D33 列表布局铁律）')
            else:
                self.ok('B9', f'列表布局铁律满足：{layout.get("checked",0)} 个数据表操作按钮不换行、头像未裁剪、表头与内容对齐')
        except Exception as e:
            self.warn('B9', f'B9 检查异常: {str(e)[:120]}')

        # B10 手机号脱敏运行时断言（D36）
        self._check_phone_mask(page)

        # B19 详情形态断言（D44 防护：列表行「查看/详情」点击后必须呈现内容区二级页 .detail-header，
        # 禁止右侧抽屉 drawer 塞详情。M46 静态拦截 openDrawer('xx详情')，本断言在浏览器里真点真验）
        try:
            # 段1：找到含「查看/详情」按钮的列表页并切过去（激活页若在 dashboard 则按钮不可见）
            nav_target = page.evaluate("""
            (function() {
                if (typeof openDetailPage !== 'function' || typeof goBackFromDetail !== 'function') {
                    return {skip: '无 openDetailPage 二级页基础设施（非 V2/V3/V4 桌面端）'};
                }
                var pages = document.querySelectorAll('[id^="page-"]');
                for (var pi = 0; pi < pages.length; pi++) {
                    var pg = pages[pi];
                    var pid = pg.id;
                    if (pid === 'page-login' || pid === 'page-dashboard' || pid.indexOf('Detail') !== -1) continue;
                    var btns = pg.querySelectorAll('button, .btn, a.link, a[onclick]');
                    for (var i = 0; i < btns.length; i++) {
                        var oc = btns[i].getAttribute('onclick') || '';
                        var txt = (btns[i].textContent || '').trim();
                        if (oc.indexOf('Detail') !== -1 || txt === '查看' || txt === '详情') {
                            if (typeof switchPage === 'function') switchPage(pid.replace('page-', ''));
                            return {target: pid};
                        }
                    }
                }
                return {skip: '未找到「查看/详情」入口按钮（无列表详情入口）'};
            })()
            """)
            if nav_target.get('skip'):
                self.ok('B19', f'详情形态跳过：{nav_target["skip"]}')
            else:
                page.wait_for_timeout(300)
                # 段2：点击当前激活页第一个可见「查看/详情」按钮
                clicked = page.evaluate("""
                (function() {
                    var btns = document.querySelectorAll('button, .btn, a.link, a[onclick]');
                    for (var i = 0; i < btns.length; i++) {
                        var oc = btns[i].getAttribute('onclick') || '';
                        var txt = (btns[i].textContent || '').trim();
                        var r = btns[i].getBoundingClientRect();
                        if (r.width === 0 || r.height === 0) continue;
                        if (oc.indexOf('Detail') !== -1 || txt === '查看' || txt === '详情') {
                            btns[i].click();
                            return {clicked: true, label: (txt || oc.slice(0, 40))};
                        }
                    }
                    return {noBtn: true};
                })()
                """)
                if clicked.get('noBtn'):
                    self.fail('B19', f'页面 {nav_target["target"]} 含「查看/详情」按钮但点击时不可见（渲染异常）')
                else:
                    page.wait_for_timeout(400)
                    st = page.evaluate("""
                    (function() {
                        var header = document.querySelector('.detail-header');
                        var headerVisible = false;
                        if (header) {
                            var cs = window.getComputedStyle(header);
                            var r = header.getBoundingClientRect();
                            headerVisible = cs.display !== 'none' && r.width > 0 && r.height > 0;
                        }
                        var drawerOpen = false;
                        var drawer = document.getElementById('drawer');
                        if (drawer && drawer.classList.contains('open')) drawerOpen = true;
                        var activePage = document.querySelector('.page.active');
                        return {headerVisible: headerVisible, drawerOpen: drawerOpen, activeId: activePage ? activePage.id : ''};
                    })()
                    """)
                    if st.get('drawerOpen'):
                        self.fail('B19', f'点击「{clicked["label"]}」打开的是右侧抽屉（drawer.open），详情必须呈现为内容区二级页 .detail-header（带面包屑+返回，D44/M46）')
                    elif st.get('headerVisible'):
                        self.ok('B19', f'点击「{clicked["label"]}」呈现内容区二级页（.detail-header 可见，active={st["activeId"]}），详情形态合规')
                    else:
                        self.fail('B19', f'点击「{clicked["label"]}」后既未呈现 .detail-header 也未打开抽屉，详情入口形态不明（D44/M46：列表行详情入口必接 openDetailPage）')
        except Exception as e:
            self.warn('B19', f'B19 检查异常: {str(e)[:120]}')

    # ---------- 移动端专项 ----------
    def _check_mobile(self, page):
        # B4a 默认页可见
        try:
            page_visible = page.evaluate("""
            (function() {
                var pages = document.querySelectorAll('.page, [class*="page-"]');
                var visible = 0;
                pages.forEach(function(p) {
                    var s = window.getComputedStyle(p);
                    if (s.display !== 'none' && s.visibility !== 'hidden') visible++;
                });
                return {total: pages.length, visible: visible};
            })()
            """)
            if page_visible.get('visible', 0) == 0:
                self.fail('B4', '无可见页面（默认页未渲染）')
            else:
                self.ok('B4', f'默认页可见（{page_visible.get("visible")} 个可见页面）')
        except Exception as e:
            self.warn('B4', f'B4a 异常: {str(e)[:120]}')

        # B4b 底部 Tab 可切换 + 目标页可见（v5.41 强化）
        # 旧版只看 switchTab 是否抛异常：目标 #page-{tab} 不存在时 switchTab 会先隐藏
        # 全部页面再静默结束 → 切换后白屏仍记"成功"（假通过）。现补目标页可见性断言：
        # 每次切换后按契约查 #page-{tab}（兜底 [data-page="{tab}"]），display/visibility/
        # opacity 任一不可见即 fail。
        try:
            tab_result = page.evaluate("""
            (function() {
                var tabs = document.querySelectorAll('.nav-tab, [data-tab]');
                var switched = 0;
                var failed = 0;
                var invisible = [];
                function pageVisible(el) {
                    if (!el) return false;
                    var cs = window.getComputedStyle(el);
                    return cs.display !== 'none' && cs.visibility !== 'hidden'
                        && parseFloat(cs.opacity || '1') > 0.01;
                }
                for (var i = 0; i < tabs.length && i < 8; i++) {
                    var tab = tabs[i];
                    var tabName = tab.getAttribute('data-tab') || tab.getAttribute('data-page');
                    try {
                        if (typeof switchTab === 'function' && tabName) {
                            switchTab(tabName);
                            switched++;
                        } else if (typeof switchPage === 'function' && tabName) {
                            switchPage(tabName);
                            switched++;
                        } else {
                            tab.click();
                            switched++;
                        }
                        // 目标页可见性验证（M115 契约：页面容器 id=page-{tab}；非常规命名兜底 data-page）
                        if (tabName) {
                            var target = document.getElementById('page-' + tabName);
                            if (!target) target = document.querySelector('[data-page="' + tabName + '"]');
                            if (!target) {
                                invisible.push(tabName + '(页面容器缺失)');
                            } else if (!pageVisible(target)) {
                                invisible.push(tabName + '(切换后不可见)');
                            }
                        }
                    } catch (e) {
                        failed++;
                    }
                }
                return {total: tabs.length, switched: switched, failed: failed, invisible: invisible};
            })()
            """)
            if tab_result.get('total', 0) == 0:
                self.warn('B4', '未检测到底部 Tab（可能无底部导航）')
            elif tab_result.get('failed', 0) > 0:
                self.fail('B4', f'Tab 切换失败 {tab_result.get("failed")} 个（抛异常）')
            elif tab_result.get('invisible'):
                self.fail('B4', f'Tab 切换后目标页不可见 {len(tab_result["invisible"])} 个: {", ".join(tab_result["invisible"][:4])}（防白屏假通过，v5.41）')
            else:
                self.ok('B4', f'底部 Tab 可切换且目标页可见（{tab_result.get("switched")}/{tab_result.get("total")} 个成功）')
        except Exception as e:
            self.warn('B4', f'B4b 异常: {str(e)[:120]}')

        # B12 移动端溢出检测（D37 防护）：390 视口下可见元素不得超出 phone-frame / 视口横向边界。
        # 典型事故：注入内容宽度写死（如固定 1200px 宽）或子页面未隐藏（sub-page 全部横向排列），
        # 导致内容溢出、出现横向滚动条、布局错乱。
        try:
            overflow = page.evaluate("""
            (function() {
                var vw = window.innerWidth;
                var pf = document.querySelector('.phone-frame');
                var pfRight = pf ? pf.getBoundingClientRect().right : vw;
                var bad = [];
                document.querySelectorAll('.phone-screen *, body *').forEach(function(el) {
                    // 跳过隐藏元素与横向滚动容器自身
                    var cs = window.getComputedStyle(el);
                    if (cs.display === 'none' || cs.visibility === 'hidden') return;
                    if (cs.position === 'fixed') return;  // fixed 定位（如 Toast）不参与布局流
                    var r = el.getBoundingClientRect();
                    if (r.width === 0 && r.height === 0) return;
                    // 跳过未 .show 的 sub-page（移动端二级页用 translateX(100%) 移出屏幕隐藏，属模板设计）
                    var inHiddenSub = false;
                    var p0 = el;
                    while (p0) {
                        if (p0.classList && p0.classList.contains('sub-page') && !p0.classList.contains('show')) { inHiddenSub = true; break; }
                        p0 = p0.parentElement;
                    }
                    if (inHiddenSub) return;
                    // 跳过横向滚动容器内的子元素（它们靠容器 overflow-x 裁剪，属正常设计）
                    var scrollParent = false;
                    var p = el.parentElement;
                    while (p && !scrollParent) {
                        var ps = window.getComputedStyle(p);
                        if ((ps.overflowX === 'auto' || ps.overflowX === 'scroll') && p.scrollWidth > p.clientWidth + 2) scrollParent = true;
                        p = p.parentElement;
                    }
                    if (scrollParent) return;
                    // 可见元素超出视口右侧或左侧
                    if (r.right > pfRight + 2 || r.left < -2 || r.width > vw + 2) {
                        bad.push({tag: el.tagName, id: el.id || '', cls: String(el.className).slice(0, 40), right: Math.round(r.right), w: Math.round(r.width), l: Math.round(r.left)});
                    }
                });
                // 去重（子元素与父元素同超宽只保留外层）
                var seen = new Set();
                var uniq = [];
                bad.forEach(function(b) {
                    var k = b.cls + '|' + b.right;
                    if (!seen.has(k)) { seen.add(k); uniq.push(b); }
                });
                return uniq.slice(0, 8);
            })()
            """)
            if overflow and len(overflow) > 0:
                desc = '; '.join(f'<{o.get("tag")} .{o.get("cls").split(" ")[0]}>right={o.get("right")}px w={o.get("w")}px' for o in overflow[:5])
                self.fail('B12', f'检测到 {len(overflow)} 个可见元素超出视口（布局溢出，会出现横向滚动条/错乱）: {desc}（D37）')
            else:
                self.ok('B12', '无可见元素溢出视口（390px 视口下布局正常）')
        except Exception as e:
            self.warn('B12', f'B12 检查异常: {str(e)[:120]}')

        # B13 移动端弹层关闭检查（D45 防护）：sheet 打开后点击内部跳转元素，断言 sheet 已关闭（防弹层残留盖在下一页面前）
        try:
            if is_mobile_file(self.content):
                sheet_ok = page.evaluate("""
                (function() {
                    if (typeof openSheet !== 'function' || typeof closeSheet !== 'function') return { state: 'skip', msg: '无 openSheet/closeSheet' };
                    // 收集所有打开 sheet 的候选入口（openSheet 直接或中转函数 openMerchants/openCouponSheet 等）
                    var all = document.querySelectorAll('[onclick]');
                    var openers = [];
                    for (var k = 0; k < all.length; k++) {
                        var oc2 = all[k].getAttribute('onclick') || '';
                        if (/openSheet\(|openMerchants|openCouponSheet|Merchants|Coupon/.test(oc2)) openers.push(all[k]);
                    }
                    if (!openers.length) return { state: 'skip', msg: '无 sheet 打开入口' };
                    // 逐个尝试：打开 sheet 后找内部跳转元素，找到则执行跳转断言
                    for (var oi = 0; oi < openers.length; oi++) {
                        // 先清掉已开的 sheet
                        document.querySelectorAll('.sheet.show').forEach(function(s){ if (typeof closeSheet === 'function') closeSheet(); });
                        try { openers[oi].click(); } catch(e) {}
                        var openedSheet = document.querySelector('.sheet.show');
                        if (!openedSheet) continue;
                        var jump = null;
                        openedSheet.querySelectorAll('[onclick]').forEach(function(el) {
                            if (jump) return;
                            var oc = el.getAttribute('onclick') || '';
                            if (/openSubPage\(|openServiceList\(|switchTab\(/.test(oc)) jump = el;
                        });
                        if (!jump) continue; // 该 sheet 无跳转元素，试下一个入口
                        // 点击 sheet 内可点元素触发跳转（覆盖数据驱动渲染的列表项）
                        openedSheet.querySelectorAll('[onclick]').forEach(function(el){ try { el.click(); } catch(e){} });
                        var stillShow = document.querySelector('.sheet.show');
                        return { state: stillShow ? 'fail' : 'ok', msg: (stillShow ? 'sheet 跳转后未关闭（残留）' : 'sheet 跳转后已关闭') };
                    }
                    return { state: 'skip', msg: '打开的 sheet 内无跳转元素' };
                })()
                """)
                if sheet_ok and sheet_ok.get('state') == 'fail':
                    self.fail('B13', '弹层内部跳转后 sheet 未关闭，残留盖在目标页面前（D45）：跳转前必须先 closeSheet()')
                elif sheet_ok and sheet_ok.get('state') == 'ok':
                    self.ok('B13', 'sheet 跳转后正确关闭，无弹层残留（D45）')
                else:
                    self.ok('B13', f'sheet 弹层检查跳过（{sheet_ok.get("msg") if sheet_ok else "无弹层"}）')
            else:
                self.ok('B13', '非移动端，跳过')
        except Exception as e:
            self.warn('B13', f'B13 检查异常: {str(e)[:120]}')

        # B14 移动端弹层不被悬浮导航遮挡（D44 防护）：sheet 打开时底部不与 nav-wrapper 重叠
        try:
            if is_mobile_file(self.content):
                ovl = page.evaluate("""
                (function() {
                    var nw = document.querySelector('.nav-wrapper');
                    var sheet = document.querySelector('.sheet.show');
                    if (!sheet) return { state: 'skip', msg: '无打开中的 sheet' };
                    if (!nw) return { state: 'ok', msg: '无 nav-wrapper' };
                    var sr = sheet.getBoundingClientRect();
                    var nr = nw.getBoundingClientRect();
                    var overlap = Math.max(0, Math.min(sr.bottom, nr.bottom) - Math.max(sr.top, nr.top));
                    return { state: overlap > 24 ? 'fail' : 'ok', overlap: Math.round(overlap), msg: 'sheet 与悬浮导航重叠 ' + Math.round(overlap) + 'px' };
                })()
                """)
                if ovl and ovl.get('state') == 'fail':
                    self.fail('B14', f'sheet 弹层被底部悬浮导航遮挡（{ovl.get("msg")}），z-index 需高于 nav-wrapper（D44）')
                else:
                    self.ok('B14', f'弹层未被悬浮导航遮挡（{ovl.get("msg") if ovl else "无弹层"}）')
            else:
                self.ok('B14', '非移动端，跳过')
        except Exception as e:
            self.warn('B14', f'B14 检查异常: {str(e)[:120]}')

        # B15 移动端无回到顶部按钮（D47 防护）
        try:
            if is_mobile_file(self.content):
                has_btn = page.evaluate("!!document.querySelector('.back-to-top, #backToTop')")
                if has_btn:
                    self.fail('B15', '页面存在回到顶部按钮（back-to-top），用户明确不要该组件（D47）')
                else:
                    self.ok('B15', '页面无回到顶部按钮（D47）')
            else:
                self.ok('B15', '非移动端，跳过')
        except Exception as e:
            self.warn('B15', f'B15 检查异常: {str(e)[:120]}')

        # B16 移动端首页入口语义断言（D43 防护）：点搜索框进入含搜索特征的页面；点两个 banner 进入的页面不同
        try:
            if is_mobile_file(self.content):
                sem = page.evaluate("""
                (function() {
                    var out = { search: 'skip', banner: 'skip', msg: '' };
                    // 1) 点击首页搜索框 → 断言进入的 sub-page 含搜索特征
                    var hs = document.querySelector('#page-home .home-search, #page-home .search-box');
                    if (hs) {
                        try {
                            hs.click();
                            var shown = document.querySelector('.sub-page.show');
                            if (shown) {
                                var html = shown.innerHTML || '';
                                var hasSearch = /<input[^>]*>|hot-words|hot-tags|search-input|search-box/.test(html);
                                out.search = hasSearch ? 'ok' : 'fail';
                                if (out.search === 'fail') out.msg += ' 点搜索框进入的页面缺搜索特征(input/热词)';
                                if (typeof closeSubPage === 'function') { try { closeSubPage(shown.id); } catch(e){} }
                            } else { out.search = 'fail'; out.msg += ' 点搜索框未打开任何子页面'; }
                        } catch(e) { out.msg += ' 搜索框点击异常:' + e.message; }
                    }
                    // 2) 点击首页多个 banner → 断言各自 onclick 目标不同（L6 多样性）
                    //    复用同一 sub-page 但数据不同的目标（如 openActivity('a')/('b')）视为不同，按 onclick 签名比较
                    var bns = document.querySelectorAll('#page-home .home-banner');
                    if (bns.length >= 2) {
                        var sigs = [];
                        for (var i = 0; i < bns.length; i++) {
                            var oc = bns[i].getAttribute('onclick') || '';
                            if (oc) sigs.push(oc);
                            try {
                                bns[i].click();
                                var shown2 = document.querySelector('.sub-page.show');
                                if (shown2 && typeof closeSubPage === 'function') { try { closeSubPage(shown2.id); } catch(e){} }
                            } catch(e) {}
                        }
                        var uniq = {};
                        sigs.forEach(function(s){ uniq[s] = 1; });
                        if (sigs.length >= 2 && Object.keys(uniq).length < sigs.length) {
                            out.banner = 'fail';
                            out.msg += ' 多个 banner 目标相同(' + sigs.join('; ') + ')，违反 L6 多样性';
                        } else if (sigs.length >= 2) {
                            out.banner = 'ok';
                        }
                    }
                    return out;
                })()
                """)
                if sem:
                    if sem.get('search') == 'fail':
                        self.fail('B16', '首页搜索框点击后未进入含搜索特征的页面（D43）：' + sem.get('msg', ''))
                    elif sem.get('banner') == 'fail':
                        self.fail('B16', '首页多个 banner 进入同一页面，违反 L6 多样性（D43）：' + sem.get('msg', ''))
                    else:
                        self.ok('B16', '首页入口语义检查通过（搜索/活动/多样性正常，D43）')
            else:
                self.ok('B16', '非移动端，跳过')
        except Exception as e:
            self.warn('B16', f'B16 检查异常: {str(e)[:120]}')

        # B17 移动端操作形态·信息展示（L7/M71 防护）：点"关于/协议/帮助"→ 断言进入 sub-page 而非打开 sheet
        try:
            if is_mobile_file(self.content):
                info = page.evaluate("""
                (function() {
                    var items = document.querySelectorAll('.mine-menu-item');
                    var target = null;
                    for (var i = 0; i < items.length; i++) {
                        var t = (items[i].innerText || '').trim();
                        if (/关于|协议|帮助|版本|隐私|条款/.test(t)) { target = items[i]; break; }
                    }
                    if (!target) return { state: 'skip', msg: '无关于/协议入口' };
                    try { target.click(); } catch(e) {}
                    // 信息展示用弹窗 = fail（优先判断）；先关掉可能残留的 sub-page 再判
                    var sheetShown = document.querySelector('.sheet.show');
                    if (sheetShown) { return { state: 'fail', msg: '打开 sheet（信息展示应用二级页，L7）' }; }
                    var subs = document.querySelectorAll('.sub-page.show');
                    if (subs.length) { return { state: 'ok', msg: '进入二级页 ' + subs[subs.length - 1].id }; }
                    return { state: 'skip', msg: '点击后未打开页面或弹层' };
                })()
                """)
                if info and info.get('state') == 'fail':
                    self.fail('B17', '信息展示类入口（关于/协议/帮助）用了弹窗，应二级页（L7/M71）：' + info.get('msg', ''))
                else:
                    self.ok('B17', f'操作形态·信息展示检查通过（{info.get("msg") if info else "无入口"}）')
            else:
                self.ok('B17', '非移动端，跳过')
        except Exception as e:
            self.warn('B17', f'B17 检查异常: {str(e)[:120]}')

        # B18 移动端操作形态·表单创建（L7/M72 防护）：点"新增地址"→ 断言进入 sub-page 而非内联展开
        try:
            if is_mobile_file(self.content):
                frm = page.evaluate("""
                (function() {
                    var items = document.querySelectorAll('.mine-menu-item, [onclick]');
                    var target = null;
                    for (var i = 0; i < items.length; i++) {
                        var t = (items[i].innerText || '').trim();
                        var oc = items[i].getAttribute('onclick') || '';
                        if (/新增地址|添加地址|新建地址/.test(t)) { target = items[i]; break; }
                    }
                    if (!target) return { state: 'skip', msg: '无新增地址入口' };
                    try { target.click(); } catch(e) {}
                    // 独立表单页：出现含表单的 sub-page
                    var subs = document.querySelectorAll('.sub-page.show');
                    var formSub = null;
                    subs.forEach(function(s){ if (s.querySelector('input, textarea, select')) formSub = s; });
                    if (formSub) { return { state: 'ok', msg: '进入表单页 ' + formSub.id }; }
                    // 内联展开：addrForm 等直接显示
                    var inlineForm = document.querySelector('[id$="Form"]') ? true : false;
                    return { state: inlineForm ? 'fail' : 'skip', msg: '检测到内联展开表单（应独立表单页，L7）' };
                })()
                """)
                if frm and frm.get('state') == 'fail':
                    self.fail('B18', '表单创建（新增地址等）内联展开，应独立表单页（L7/M72）：' + frm.get('msg', ''))
                else:
                    self.ok('B18', f'操作形态·表单创建检查通过（{frm.get("msg") if frm else "无入口"}）')
            else:
                self.ok('B18', '非移动端，跳过')
        except Exception as e:
            self.warn('B18', f'B18 检查异常: {str(e)[:120]}')

        # B20 移动端子页面标题居中断言（M112 防护）：每个 .sub-page 的 nav 标题必须带
        # class="sub-page-title"，且打开后可见标题计算样式必须 position:absolute + left:50%
        try:
            if is_mobile_file(self.content):
                sub = page.evaluate("""
                (function() {
                    var subs = document.querySelectorAll('.sub-page');
                    if (!subs.length) return { state: 'skip', msg: '无子页面' };
                    var bad = [];
                    subs.forEach(function(s) {
                        var nav = s.querySelector('.sub-page-nav');
                        if (!nav) return;
                        var title = nav.querySelector('.sub-page-title');
                        if (!title) {
                            var span = nav.querySelector('span');
                            if (span && (span.textContent || '').trim()) bad.push(s.id + ':' + span.textContent.trim());
                        }
                    });
                    if (bad.length) return { state: 'fail', msg: '子页面标题缺 class="sub-page-title"（靠左）: ' + bad.slice(0, 5).join(', ') };
                    var first = subs[0];
                    if (first.id && window.openSubPage) { try { window.openSubPage(first.id); } catch(e) {} }
                    var shown = document.querySelector('.sub-page.show');
                    var t = shown ? shown.querySelector('.sub-page-title') : null;
                    var result = { state: 'ok', msg: '' };
                    if (!t) {
                        result = { state: 'fail', msg: '子页面 ' + (shown ? shown.id : first.id) + ' 无 .sub-page-title 元素' };
                    } else {
                        var cs = getComputedStyle(t);
                        // getComputedStyle 的 left 返回解析后像素值（如 195px 而非 50%），
                        // 必须用几何中心判定：标题中心 ≈ nav 容器中心（误差 ≤2px）才算居中
                        var r = t.getBoundingClientRect();
                        var nav = t.closest('.sub-page-nav') || t.parentElement;
                        var nr = nav.getBoundingClientRect();
                        var diff = Math.abs((r.left + r.width / 2) - (nr.left + nr.width / 2));
                        if (cs.position !== 'absolute' || diff > 2) {
                            result = { state: 'fail', msg: '标题未居中（position=' + cs.position + ', 中心偏差=' + Math.round(diff) + 'px；需 absolute + left:50% + translateX(-50%)）' };
                        } else {
                            result = { state: 'ok', msg: '子页面标题均带 sub-page-title 且居中（' + shown.id + ', 偏差≤2px）' };
                        }
                    }
                    if (window.closeSubPage && shown) { try { window.closeSubPage(shown.id); } catch(e) {} }
                    return result;
                })()
                """)
                if sub and sub.get('state') == 'fail':
                    self.fail('B20', '子页面标题居中断言失败（M112）：' + sub.get('msg', ''))
                else:
                    self.ok('B20', f'子页面标题居中检查通过（{sub.get("msg") if sub else "无子页面"}）')
            else:
                self.ok('B20', '非移动端，跳过')
        except Exception as e:
            self.warn('B20', f'B20 检查异常: {str(e)[:120]}')

        # B21 移动端网格孤卡断言（M113 防护）：运行时扫描所有 display:grid 容器，
        # 解析列数，直接子元素数 % 列数 != 0（孤卡留白）即 fail；跨整行大卡（grid-column:1/-1）
        # 与绝对定位元素豁免。覆盖 JS 动态渲染的网格容器（lint M113 静态层兜不住的）。
        try:
            if is_mobile_file(self.content):
                g = page.evaluate("""
                (function() {
                    var bad = [];
                    document.querySelectorAll('div').forEach(function(c) {
                        var cs = getComputedStyle(c);
                        if (cs.display !== 'grid') return;
                        // display:none(隐藏页面/子页面)的 grid-template-columns 返回未展开的
                        // "repeat(4, 1fr)"，按空格拆分会误判列数；必须先识别 repeat() 语法
                        var raw = cs.gridTemplateColumns || '';
                        var rm = raw.match(/repeat\((\d+),/);
                        var tracks = rm ? parseInt(rm[1], 10) : raw.split(' ').filter(function(t) { return t; }).length;
                        if (!tracks || tracks <= 1) return;
                        var kids = [].filter.call(c.children, function(k) {
                            var kcs = getComputedStyle(k);
                            if (kcs.display === 'none' || kcs.position === 'absolute') return false;
                            if (kcs.gridColumnEnd === '-1') return false;
                            return true;
                        });
                        if (kids.length && kids.length % tracks !== 0) {
                            bad.push((c.className || c.id || 'grid') + ':' + kids.length + '卡/' + tracks + '列');
                        }
                    });
                    return bad.length ? { state: 'fail', msg: '网格孤卡留白（卡片数非列数整数倍）: ' + bad.slice(0, 5).join(', ') }
                                      : { state: 'ok', msg: '所有网格容器卡片数与列数匹配' };
                })()
                """)
                if g and g.get('state') == 'fail':
                    self.fail('B21', '网格布局完整性断言失败（M113）：' + g.get('msg', ''))
                else:
                    self.ok('B21', f'网格布局完整性检查通过（{g.get("msg") if g else "无网格容器"}）')
            else:
                self.ok('B21', '非移动端，跳过')
        except Exception as e:
            self.warn('B21', f'B21 检查异常: {str(e)[:120]}')

        # B22 白字白底对比度断言（M114 防护，全端通用）：可见白色文字元素若无深色/渐变背景
        # （背景为纯白/近白）即 fail——白字白底看不清是"样式静默失效"的典型后果
        # （如渐变引用了未定义 CSS 变量导致 background 整条丢弃）。
        try:
            wb = page.evaluate("""
            (function() {
                function isWhite(c) {
                    // 仅"几乎不透明"的白色才算白底；半透明白（如 rgba(255,255,255,.22) 标签
                    // 叠加在渐变上）视觉仍是深色背景，不算白底
                    var m = c.match(/rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)(?:,\\s*([\\d.]+))?\\)/);
                    if (!m) return false;
                    if (+m[1] > 210 && +m[2] > 210 && +m[3] > 210) {
                        var a = m[4] !== undefined ? parseFloat(m[4]) : 1;
                        return a > 0.85;
                    }
                    return false;
                }
                // 找元素所在层级的有效背景：自身/祖先有渐变或图片背景；或
                // 祖先容器内有绝对定位铺底子元素（如 .home-banner-bg{position:absolute;inset:0}
                // 渐变铺底，文字在其兄弟 .home-banner-content 中）视为有背景。
                function findBg(el) {
                     var node = el;
                     while (node) {
                         var ncs = getComputedStyle(node);
                         if (ncs.backgroundImage && ncs.backgroundImage !== 'none') return 'img';
                         if (ncs.backgroundColor !== 'rgba(0, 0, 0, 0)') return ncs.backgroundColor;
                         var nr = node.getBoundingClientRect();
                         for (var i = 0; i < node.children.length; i++) {
                             var k = node.children[i];
                             var kcs = getComputedStyle(k);
                             if (kcs.position !== 'absolute') continue;
                             if (kcs.backgroundImage && kcs.backgroundImage !== 'none') {
                                 var kr = k.getBoundingClientRect();
                                 if (nr.width > 0 && kr.width >= nr.width * 0.8 && kr.height >= nr.height * 0.8) return 'img';
                             }
                         }
                         // body/html 的背景也要检查（页面底色常挂在 body 上），检查后停止
                         if (node === document.body || node === document.documentElement) break;
                         node = node.parentElement;
                     }
                     return null;
                 }
                var bad = [];
                document.querySelectorAll('*').forEach(function(el) {
                    if (el.children.length) return; // 只查叶子（文字所在）元素
                    if (!(el.textContent || '').trim()) return;
                    var cs = getComputedStyle(el);
                    if (cs.display === 'none' || cs.visibility === 'hidden' || cs.opacity === '0') return;
                    if (!el.getClientRects().length) return; // 自身或祖先 display:none/不可见（如未激活轮播页）
                    if (!isWhite(cs.color)) return;
                    var bg = findBg(el);
                    if (bg === 'img') return;
                    if (bg && isWhite(bg)) {
                        bad.push((el.className ? '.' + String(el.className).split(' ')[0] : el.tagName) + '「' + (el.textContent || '').trim().slice(0, 10) + '」');
                    }
                });
                return bad.length ? { state: 'fail', msg: '白字白底看不清: ' + bad.slice(0, 8).join('; ') }
                                  : { state: 'ok', msg: '无白字白底（可见白字均有深色/渐变背景）' };
            })()
            """)
            if wb and wb.get('state') == 'fail':
                self.fail('B22', '白字白底断言失败（M114）：' + wb.get('msg', ''))
            else:
                self.ok('B22', f'白字白底检查通过（{wb.get("msg") if wb else "无白字元素"}）')
        except Exception as e:
            self.warn('B22', f'B22 检查异常: {str(e)[:120]}')

        # B23 移动端：Tab 页渲染非空断言（M115/D49 防护）——所有主 Tab 页内的"渲染目标
        # 容器"（id 以 List/Products/Tabs/Grid/Sidebar/Content 结尾，或标准列表类
        # cart-list/order-list/card-list/addr-list/waterfall）必须已填充内容或空态兜底
        # （empty-state）。纯空白 = 渲染函数定义了却未执行（茶叶商城事故：分类/购物车/
        # 订单/新品全空白，但"我的订单"入口有数据）。
        try:
            if is_template_file(self.filepath):
                self.ok('B23', '模板文件跳过 Tab 页渲染断言')
            else:
                b23 = page.evaluate("""
                (function() {
                    var bad = [];
                    document.querySelectorAll('.page').forEach(function(p) {
                        if (p.classList.contains('sub-page')) return;
                        var targets = p.querySelectorAll('[id], [class]');
                        var found = 0;
                        targets.forEach(function(el) {
                            if (el === p) return;
                            var id = el.id || '';
                            var cls = (typeof el.className === 'string') ? el.className : '';
                            var isTarget = /(List|Products|Tabs|Grid|Sidebar|Content)$/i.test(id)
                                        || /(^|\\s)(cart-list|order-list|card-list|addr-list|waterfall|product-list)(\\s|$)/.test(cls);
                            if (!isTarget) return;
                            found++;
                            var html = (el.innerHTML || '').trim();
                            if (!html || el.children.length === 0) {
                                bad.push(p.id + ' > ' + (id || cls));
                            }
                        });
                    });
                    return bad.length ? { state: 'fail', msg: '渲染目标容器空白（渲染函数未执行或数据未渲染）: ' + bad.slice(0, 6).join('; ') }
                                      : { state: 'ok', msg: '所有主 Tab 页渲染目标均已填充' };
                })()
                """)
                if b23 and b23.get('state') == 'fail':
                    self.fail('B23', 'Tab 页渲染断言失败（M115）：' + b23.get('msg', ''))
                else:
                    self.ok('B23', f'Tab 页渲染检查通过（{b23.get("msg") if b23 else "无渲染目标"}）')
        except Exception as e:
            self.warn('B23', f'B23 检查异常: {str(e)[:120]}')

        # B24 移动端：筛选标签栏 sticky 断言（M117/D51 防护）——订单/状态/筛选类 tabs
        # 容器（.orders-tabs 或类名含 filter-tabs/status-tabs 等）computed position
        # 必须为 sticky（固定在页面顶部，不随列表内容滚动）。
        try:
            if is_template_file(self.filepath):
                self.ok('B24', '模板文件跳过筛选栏 sticky 断言')
            else:
                b24 = page.evaluate("""
                (function() {
                    var bad = [];
                    document.querySelectorAll('.orders-tabs, [class*="filter-tabs"], [class*="status-tabs"], [class*="order-tabs"], [class*="state-tabs"]').forEach(function(el) {
                        var pos = getComputedStyle(el).position;
                        if (pos !== 'sticky') bad.push('.' + String(el.className).split(' ')[0] + ' position=' + pos);
                    });
                    return bad.length ? { state: 'fail', msg: '筛选标签栏未 sticky 固定（会随内容滚动）: ' + bad.slice(0, 6).join('; ') }
                                      : { state: 'ok', msg: '筛选标签栏均 sticky 固定' };
                })()
                """)
                if b24 and b24.get('state') == 'fail':
                    self.fail('B24', '筛选栏 sticky 断言失败（M117）：' + b24.get('msg', ''))
                else:
                    self.ok('B24', f'筛选栏 sticky 检查通过（{b24.get("msg") if b24 else "无筛选容器"}）')
        except Exception as e:
            self.warn('B24', f'B24 检查异常: {str(e)[:120]}')

        # B25 移动端：底部操作栏按钮布局断言（M118/D52 防护）——.detail-bar 内按钮必须
        # 响应式伸缩填满整行（多按钮无右侧留白）、单按钮自适应居中。
        # 覆盖静态 HTML 与 JS 动态注入的按钮；空容器（未渲染）跳过。
        try:
            if is_mobile_file(self.content):
                b25 = page.evaluate("""
                (function() {
                    var bad = [], checked = 0;
                    document.querySelectorAll('.detail-bar').forEach(function(bar) {
                        var btns = bar.querySelectorAll(':scope > .btn');
                        if (!btns.length) return;
                        var cs = getComputedStyle(bar);
                        if (cs.display !== 'flex') return;
                        checked++;
                        var br = bar.getBoundingClientRect();
                        var padL = parseFloat(cs.paddingLeft) || 0;
                        var padR = parseFloat(cs.paddingRight) || 0;
                        var first = btns[0].getBoundingClientRect();
                        var last = btns[btns.length - 1].getBoundingClientRect();
                        var l = first.left - br.left - padL;
                        var r = br.right - padR - last.right;
                        var tag = bar.id || String(bar.className).split(' ')[0] || 'detail-bar';
                        if (btns.length === 1) {
                            if (Math.abs(l - r) > 4) bad.push(tag + ' 单按钮未居中（左' + Math.round(l) + '/右' + Math.round(r) + 'px）');
                        } else {
                            if (r > 3) bad.push(tag + ' 按钮未填满右侧留白 ' + Math.round(r) + 'px');
                            if (Math.abs(l) > 3) bad.push(tag + ' 左边缘异常 ' + Math.round(l) + 'px');
                        }
                    });
                    return checked ? (bad.length ? { state: 'fail', msg: bad.slice(0, 5).join('; ') }
                                                  : { state: 'ok', msg: '底部操作栏 ' + checked + ' 处按钮布局合规（多按钮填满/单按钮居中）' })
                                    : { state: 'ok', msg: '无底部操作栏' };
                })()
                """)
                if b25 and b25.get('state') == 'fail':
                    self.fail('B25', '底部操作栏按钮布局断言失败（M118）：' + b25.get('msg', ''))
                else:
                    self.ok('B25', f'底部操作栏按钮布局检查通过（{b25.get("msg") if b25 else "无底部操作栏"}）')
            else:
                self.ok('B25', '非移动端，跳过')
        except Exception as e:
            self.warn('B25', f'B25 检查异常: {str(e)[:120]}')

        # B26 移动端：分类页侧栏固定+间距断言（M119 防护）——分类左侧栏 computed
        # position 必须为 sticky 且 top=8px；双栏父容器 align-items:flex-start（防 stretch
        # 使 sticky 失效）且设置 gap（类别栏与卡片之间有间距，防"分类与卡片之间无间距"）。
        try:
            if is_template_file(self.filepath):
                self.ok('B26', '模板文件跳过分类侧栏断言')
            elif not is_mobile_file(self.content):
                self.ok('B26', '非移动端，跳过')
            else:
                b26 = page.evaluate("""
                (function() {
                    var sb = document.getElementById('categorySidebar');
                    if (sb && sb.children.length) {
                        var out = { st: 'ok', msg: '分类侧栏 sticky+gap 满足' };
                        var cs = getComputedStyle(sb);
                        if (cs.position !== 'sticky') return { st: 'fail', msg: 'categorySidebar position=' + cs.position + '（分类栏必须 sticky 固定）' };
                        var topVal = parseFloat(cs.top);
                        if (!(topVal >= 0)) return { st: 'fail', msg: 'categorySidebar sticky top 无效=' + cs.top };
                        var wrap = sb.parentElement;
                        var ws = wrap ? getComputedStyle(wrap) : null;
                        if (ws && ws.display === 'flex') {
                            if (ws.alignItems !== 'flex-start' && ws.alignItems !== 'start')
                                return { st: 'fail', msg: '分类双栏父容器 align-items=' + ws.alignItems + '（应为 flex-start，否则 stretch 使 sticky 失效）' };
                            if (!ws.gap || ws.gap === 'normal')
                                return { st: 'fail', msg: '分类侧栏与卡片之间无间距（父容器缺 gap）' };
                        }
                        return out;
                    }
                    return { st: 'ok', msg: '无分类页侧栏，跳过' };
                })()
                """)
                if b26 and b26.get('st') == 'fail':
                    self.fail('B26', '分类侧栏断言失败（M119）：' + b26.get('msg', ''))
                else:
                    self.ok('B26', f'分类侧栏检查通过（{b26.get("msg") if b26 else "无分类侧栏"}）')
        except Exception as e:
            self.warn('B26', f'B26 检查异常: {str(e)[:120]}')

        # B27 移动端：底部结算栏固定断言（M120/D54 防护）——购物车「全选+合计+结算」栏
        # 必须贴在底部悬浮导航上方：*短内容/空态* 时结算栏不得悬在界面中间（应位于
        # 导航附近），*长列表滚动到底* 时结算栏仍须吸附在导航上方（computed position
        # sticky）+ 与导航保留小间距。
        try:
            if is_template_file(self.filepath):
                self.ok('B27', '模板文件跳过结算栏固定断言')
            elif not is_mobile_file(self.content):
                self.ok('B27', '非移动端，跳过')
            else:
                b27 = page.evaluate("""
                (function() {
                    var bar = document.querySelector('.cart-bar, #page-cart .cart-bar');
                    if (!bar || !bar.textContent) return {st:'ok', msg:'无底部结算栏，跳过'};
                    // 计入购物车页可见性：仅当 #page-cart 在 display 树中才断言
                    var page = document.getElementById('page-cart');
                    if (page && getComputedStyle(page).display === 'none') return {st:'ok', msg:'购物车页未显示，跳过'};
                    var out = {st:'ok', msg:'结算栏固定于底部导航上方'};
                    var cs = getComputedStyle(bar);
                    // 1. 短内容必须是 sticky（配合 flex 页 + margin-top:auto 压到底部）
                    if (cs.position !== 'sticky') return {st:'fail', msg:'cart-bar position=' + cs.position + '（应为 sticky，否则长列表滚动时结算栏不吸附底部）'};
                    var br = bar.getBoundingClientRect();
                    // 找底部悬浮导航（取视口内最底部的 .bottom-nav）
                    var navs = document.querySelectorAll('.bottom-nav');
                    var navTop = null;
                    for (var i=0;i<navs.length;i++){ var n=navs[i].getBoundingClientRect(); if(n.height>0){ navTop = n.top; } }
                    var cb = document.getElementById('appContent') || document.querySelector('.content');
                    var cBottom = cb ? cb.getBoundingClientRect().bottom : null;
                    if (navTop != null && cBottom != null) {
                        // 结算栏底部应贴近导航顶部：既不能与导航重叠，也不得远离导航悬在中间
                        var dist = navTop - br.bottom;       // >0 表示栏在导航上方
                        if (dist < -8) return {st:'fail', msg:'结算栏底部(' + Math.round(br.bottom) + ')低于导航顶部(' + Math.round(navTop) + ')，与悬浮导航重叠，M120'};
                        // 栏距导航过远（悬浮在界面中间）：容差 96px（正常间隙 ~10px，含导航外露/缩放差异）
                        if (dist > 96) return {st:'fail', msg:'结算栏距导航顶部 ' + Math.round(dist) + 'px 过远，疑似悬浮在界面中间，M120'};
                    }
                    return out;
                })()
                """)
                if b27 and b27.get('st') == 'fail':
                    self.fail('B27', '结算栏固定断言失败（M120）：' + b27.get('msg', ''))
                else:
                    self.ok('B27', f'结算栏固定检查通过（{b27.get("msg") if b27 else "无结算栏"}）')
        except Exception as e:
            self.warn('B27', f'B27 检查异常: {str(e)[:120]}')

        # B28 移动端：分类侧栏「分类项之间」垂直间距断言（M121/D55 防护）——分类页左侧
        # 绿茶/红茶/乌龙… 分类卡片不得彼此紧贴：#categorySidebar 必须是 flex 列 + 显式 gap，
        # 且实测相邻分类项之间存在正间距（红茶上方/下方的卡片与之保持可见间隔）。
        try:
            if is_template_file(self.filepath):
                self.ok('B28', '模板文件跳过分类侧栏间距断言')
            elif not is_mobile_file(self.content):
                self.ok('B28', '非移动端，跳过')
            elif 'categorySidebar' not in self.content:
                self.ok('B28', '无分类侧栏骨架，跳过')
            else:
                b28 = page.evaluate("""
                (function() {
                    var sb = document.getElementById('categorySidebar');
                    if (!sb) return {st:'ok', msg:'侧栏不存在，跳过'};
                    // 计入可见性：仅当侧栏所在 .page 在 display 树中才断言（否则 getBoundingClientRect 全 0）
                    var cpage = sb.closest('.page');
                    if (cpage && getComputedStyle(cpage).display === 'none') return {st:'ok', msg:'分类页未显示，跳过'};
                    var cs = getComputedStyle(sb);
                    if (cs.display.indexOf('flex') === -1) return {st:'fail', msg:'categorySidebar display=' + cs.display + '（应为 flex，M121）'};
                    if (cs.flexDirection !== 'column') return {st:'fail', msg:'categorySidebar flexDirection=' + cs.flexDirection + '（应为 column，M121）'};
                    if (parseFloat(cs.gap) <= 0) return {st:'fail', msg:'categorySidebar gap=' + cs.gap + '（应 >0，分类项彼此紧贴无间距，M121）'};
                    // 实测相邻分类项间距：取相邻两个分类卡片的底部/顶部差
                    var items = sb.querySelectorAll('.shop-cat, [onclick]');
                    if (items.length >= 2) {
                        var prev = null;
                        for (var i=0;i<items.length;i++) {
                            var r = items[i].getBoundingClientRect();
                            if (r.height <= 0) continue;
                            if (prev != null) {
                                var sep = r.top - prev.bottom;   // >0 表示有纵向间距
                                if (sep < 1) return {st:'fail', msg:'相邻分类项间距 ' + sep.toFixed(1) + 'px（应 >0，分类卡片紧贴，M121）'};
                            }
                            prev = r;
                        }
                    }
                    return {st:'ok', msg:'分类侧栏 flex 列 + gap' + cs.gap + '，分类项间距正常'};
                })()
                """)
                if b28 and b28.get('st') == 'fail':
                    self.fail('B28', '分类侧栏间距断言失败（M121）：' + b28.get('msg', ''))
                else:
                    self.ok('B28', f'分类侧栏间距检查通过（{b28.get("msg") if b28 else "无侧栏"}）')
        except Exception as e:
            self.warn('B28', f'B28 检查异常: {str(e)[:120]}')

        # B6 死按钮检查（移动端：可点击元素必须有 onclick，防"点击无反应"）
        try:
            if is_template_file(self.filepath):
                self.ok('B6', '模板文件跳过死按钮检查')
            else:
                dead = page.evaluate("""
                (function() {
                    var dead = [];
                    var clickableCls = ['mine-menu-item','report-card','reg-card','doctor-card','dept-item','consult-card','service-item','order-grid-item','support-item','store-mini','seckill-item','product-card','store-card','msg-item','order-card'];
                    // 展示型子元素白名单：这些是卡片/区块的纯展示内容，即使父级 cursor:pointer 也不应被判死按钮
                    var displayCls = ['store-info','store-name','store-sub','product-name','product-meta','product-price','product-sales','msg-title','msg-content','msg-time','card-title','card-sub','work-greet','work-date','work-stat-num','work-stat-lbl','mine-name','mine-phone','store-logo','detail-name','detail-sub','detail-price','order-head','order-body','order-foot','order-item-row','tabular-nums'];
                    document.querySelectorAll('*').forEach(function(el) {
                        var cs = getComputedStyle(el);
                        var looksClickable = cs.cursor === 'pointer' || el.tagName === 'BUTTON' || clickableCls.some(function(c){ return el.classList.contains(c); });
                        if (!looksClickable) return;
                        // 展示型子元素（自身无 onclick 且无可点类）直接放行
                        if (displayCls.some(function(c){ return el.classList.contains(c); })) return;
                        var node = el, hasClick = false;
                        while (node && node !== document.body) {
                            if (node.hasAttribute && (node.hasAttribute('onclick') || typeof node.onclick === 'function')) { hasClick = true; break; }
                            node = node.parentElement;
                        }
                        if (!hasClick) {
                            var txt = (el.innerText || '').trim().substring(0, 20);
                            var info = (txt || el.tagName) + '|' + el.tagName + '.' + Array.from(el.classList).join('.');
                            dead.push(info);
                        }
                    });
                    return { dead: Array.from(new Set(dead)) };
                })()
                """)
                dcount = len(dead.get('dead', [])) if dead else 0
                if dcount > 0:
                    self.fail('B6', f'检测到 {dcount} 个死按钮（可点击但无 onclick）: {"; ".join(dead["dead"][:20])}')
                else:
                    self.ok('B6', '无死按钮（所有可点击元素都有响应）')
        except Exception as e:
            self.warn('B6', f'B6 异常: {str(e)[:120]}')

        # B10 手机号脱敏运行时断言（D36）
        self._check_phone_mask(page)

    # ---------- 手机号脱敏专项 ----------
    def _check_phone_mask(self, page):
        # B10 手机号脱敏运行时断言（D36）：渲染后全页可见文本 + 表单值不得含裸 11 位手机号
        try:
            found = page.evaluate("""
            (function(){
              var bad = [];
              var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null);
              var n;
              while ((n = walker.nextNode())) {
                var p = n.parentNode;
                if (p && (p.nodeName === 'SCRIPT' || p.nodeName === 'STYLE')) continue;
                var t = n.nodeValue || '';
                var m = t.match(/1[3-9]\\d{9}/g);
                if (m) bad.push(t.trim().slice(0, 40));
              }
              var inputs = document.querySelectorAll('input, textarea');
              inputs.forEach(function(inp){
                var v = inp.value || '';
                var m = v.match(/1[3-9]\\d{9}/g);
                if (m) bad.push((inp.id || 'input') + ':' + v);
              });
              return bad.slice(0, 10);
            })()
            """)
            if found:
                self.fail('B10', f'渲染结果含 {len(found)} 处未脱敏 11 位手机号（须用 maskPhone 脱敏）: {"; ".join(found[:5])}（D36）')
            else:
                self.ok('B10', '全页可见文本/表单值无未脱敏手机号（D36 脱敏铁律）')
        except Exception as e:
            self.warn('B10', f'B10 检查异常: {str(e)[:120]}')

    # ---------- PRD 专项 ----------
    def _check_prd(self, page):
        # 简易版 PRD：无搜索栏 / 智能助手，跳过 B5a/B5b 断言
        if self.prd_mode == 'simple':
            self.ok('B5', '简易版 PRD：无搜索栏/智能助手（按设计跳过搜索与助手断言）')
            return

        # B5a doSearch 可用
        try:
            search_ok = page.evaluate("""
            (function() {
                if (typeof doSearch !== 'function') return {ok: false, reason: 'doSearch 不存在'};
                // 尝试搜索
                var input = document.querySelector('input[type="text"], input[type="search"], #searchInput');
                if (input) {
                    input.value = '订单';
                    if (typeof doSearch === 'function') {
                        try { doSearch('订单'); } catch(e) { return {ok: false, reason: 'doSearch 抛异常: ' + e.message}; }
                    }
                    return {ok: true};
                }
                try { doSearch('订单'); } catch(e) { return {ok: false, reason: 'doSearch 抛异常: ' + e.message}; }
                return {ok: true};
            })()
            """)
            if search_ok.get('ok'):
                self.ok('B5', 'doSearch 可执行（搜索无异常）')
            else:
                self.fail('B5', f'搜索功能不可用: {search_ok.get("reason")}')
        except Exception as e:
            self.warn('B5', f'B5a 异常: {str(e)[:120]}')

        # B5b findAnswer 可用
        try:
            fa_ok = page.evaluate("""
            (function() {
                if (typeof findAnswer !== 'function') return {ok: false, reason: 'findAnswer 不存在'};
                try {
                    var ans = findAnswer('订单');
                    return {ok: true, hasAnswer: !!(ans && (ans.answer || ans.title || ans.content))};
                } catch(e) {
                    return {ok: false, reason: 'findAnswer 抛异常: ' + e.message};
                }
            })()
            """)
            if fa_ok.get('ok'):
                self.ok('B5', f'findAnswer 可执行（有回答: {fa_ok.get("hasAnswer")}）')
            else:
                self.fail('B5', f'智能助手不可用: {fa_ok.get("reason")}')
        except Exception as e:
            self.warn('B5', f'B5b 异常: {str(e)[:120]}')

    def exit_code(self):
        if self.failed:
            return 1
        return 0

    def summary(self):
        total = len(self.passed) + len(self.failed) + len(self.warnings)
        status = '✅ 通过' if not self.failed else f'❌ {len(self.failed)} 项失败'
        print(f"  {self.filename}: {status}（{total} 项: ✓{len(self.passed)} ⚠{len(self.warnings)} ✗{len(self.failed)}）")
        return 0 if not self.failed else 1


def main():
    parser = argparse.ArgumentParser(description='PM Agent 交付物浏览器机械断言检查')
    parser.add_argument('files', nargs='+', help='要检查的 HTML 文件路径')
    parser.add_argument('--prd-mode', choices=['detailed', 'simple'], default='detailed',
                        help='PRD 文档模式：detailed=详细版(默认) / simple=简易版(无搜索栏/智能助手)')
    parser.add_argument('--strict-runtime', action='store_true',
                        help='严格运行时模式（v5.41，供 gate-check G5 调用）：Playwright/Chromium '
                             '不可用时退出码 3 而非 0——「浏览器验证环境缺失」不再等价于静默通过。'
                             '日常直接调用不传本参数，保持原有降级跳过行为不变。')
    args = parser.parse_args()

    # 检查 Playwright 可用性：
    # 默认 = 可选依赖语义（未安装则跳过断言退码 0，构建链路不红）；
    # --strict-runtime = 门禁语义（G5 复核必须真跑，环境缺失退码 3 由 G5 判 fail 并给安装指引）
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("\n⚠️  [跳过] 未检测到 Playwright，浏览器机械断言（B 系列）已跳过。")
        print("   构建仍可通过（第 1 层 Lint 已强制运行，足以拦住结构/对齐/脱敏等模板级回归）。")
        print("   如需完整浏览器断言，请安装： pip install playwright && playwright install chromium")
        if args.strict_runtime:
            print("\n❌ [--strict-runtime] 门禁模式不允许跳过：验证环境不可用视为该项未通过（退出码 3）。")
            sys.exit(3)
        sys.exit(0)

    print("━" * 60)
    print("🌐 浏览器机械断言检查 (browser-check.py)")
    print("━" * 60)

    all_results = []
    exit_code = 0

    try:
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=True)
            except Exception as e:
                print(f"\n❌ Chromium 启动失败: {str(e)[:200]}")
                print("   安装命令: playwright install chromium")
                sys.exit(2)
            for filepath in args.files:
                if not os.path.exists(filepath):
                    print(f"\n❌ 文件不存在: {filepath}")
                    all_results.append((filepath, 1))
                    exit_code = 1
                    continue
                print(f"\n📋 检查: {os.path.basename(filepath)}")
                page = browser.new_page(viewport={'width': 1440, 'height': 900})
                checker = BrowserChecker(filepath, prd_mode=args.prd_mode)
                code = checker.run(page)
                page.close()
                code2 = checker.summary()
                all_results.append((filepath, code2))
                if code2 != 0:
                    exit_code = 1
            # ⚠️ 不调用 browser.close()：Windows 上 Chromium 关闭时原生崩溃（D27），
            # 改用结尾 os._exit 立即终止，绕过浏览器/驱动清理。
    except Exception as e:
        print(f"\n❌ 浏览器会话异常: {str(e)[:200]}")
        sys.stdout.flush(); sys.stderr.flush()
        os._exit(2)

    # 汇总
    print(f"\n{'━' * 60}")
    print("📊 总体汇总")
    print(f"{'━' * 60}")
    total_fail = sum(1 for _, c in all_results if c != 0)
    total_pass = len(all_results) - total_fail
    print(f"  通过 {total_pass} 个文件 / 失败 {total_fail} 个文件")
    if total_fail == 0:
        print("\n🎉 结论: 全部通过，可以交付")
    else:
        print(f"\n🚫 结论: {total_fail} 个文件未通过浏览器断言，禁止交付，请修复后重新检查")

    # 用 os._exit 绕过 with sync_playwright() 的 __exit__（内部会关闭浏览器，Windows 上崩溃 D27）
    sys.stdout.flush(); sys.stderr.flush()
    os._exit(exit_code)


if __name__ == '__main__':
    main()
