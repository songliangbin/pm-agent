# 跨端通用踩坑库（全端约束）

> **由 `scripts/split-pitfalls.py` 从 `history-pitfalls.md` 自动派生，禁止手改；修改请到源头。**
> **任何端生成都必须先读本文件**（D5 编码 / D17 机制同步 / D27 工具 / D35 工具 / D36 手机号 / D39 无人值守 / D40 交付物核对）。

## 跨端通用条目（D5/D17/D27/D35/D36/D39/D40）

| # | 问题 | 根因 | 防护措施 |
|:--|:--|:--|:--|
| D5 | 文件编码导致中文乱码 | Agent 用 PowerShell 写入含中文 .html，默认 GBK | 含中文 .html 必须用 `Python open(path,'w',encoding='utf-8')` 写入，禁止 PowerShell 写入命令 |
| D17 | 用户长期偏好未回灌机制层，重生成复现老问题 | 仅改当次项目输出，模板/规范/lint 未同步 | 任何用户偏好变更须同步四层：模板 CSS + 注入说明 + lint 规则 + 本踩坑库（违反 M21 机制同步铁律） |
| D27 | [Windows] Playwright 检查完成后 `browser.close()` / with 退出时原生崩溃（进程直接终止、stdout 缓冲丢失、bash 后续命令不执行） | Windows 上 Chromium 关闭时资源释放触发访问违规（Python 异常捕获不到），导致 browser-check 检查完却崩溃、退出码错误 | browser-check 结尾**不调用 browser.close()**，改用 `os._exit(exit_code)` 立即终止（绕过 with 清理与浏览器关闭）；已修进 browser-check.py |
| D35 | [BROWSER-CHECK] 模板引用外部 CDN（Google Fonts / Font-Awesome），离线环境下 browser-check B0 超时（Page.goto: Timeout 15000ms）且直接 abort 会误伤 B2（net::ERR_FAILED console.error） | V2/V3 模板 `<head>` 含 `https://fonts.googleapis.com` 与 `https://cdnjs.cloudflare.com` 外链样式表；`waitUntil:'load'` 等待外网资源，断网/慢网时 load 事件挂起超时报 B0；若改用 `route.abort()` 阻断外链，又会触发 console.error 误报 B2 | browser-check 对 `http(s)://` 请求用 `route.fulfill(status=200, content_type='text/css', body='')` 空响应兜底（不 abort，避免 B2 误报），load 立即触发；路径先 `os.path.abspath` 再拼 `file:///`，避免相对路径生成 `file:///xxx` 错误 URL；原型布局 CSS 为内联，断言不依赖外网 |
| D36 | [V1/V2/V3/移动端] 生成原型中手机号/电话号码以明文出现（如 13800138001、0571-88886666），泄露用户隐私 | 数据层 work/*/data.js 的 members/users 数组直接写原始 11 位手机号；模板渲染时直接拼接 `m.phone` 无脱敏；早期 lint/browser-check 无手机号检查，泄露未被拦截 | 三层固化+约束：① 模板内置 `maskPhone(p)`（桌面 V1/V2/V3 + 移动端 + system-admin 组件），渲染 `maskPhone(m.phone)` 把 `13800138001`→`138****8001`、固话 `0571-88886666`→`0571-****6666`；② lint **C1-28** 扫描生成文件源码，含裸 11 位手机号（排除已 maskPhone 处理或已是 `138****8001` 形式）即 fail；③ browser-check **B10** 运行时扫描全页可见文本/表单值，含裸 11 位手机号即 fail；数据层约定 Agent 生成的 data.js 手机号默认以 `138****8001` 形式存储（C1-28 兜底拦截明文） |
| D39 | [全端] 生成阶段 Agent 自创"临时生成目录"并执行 `rm -rf` 清理，触发宿主确认弹窗，无人值守的 1-2 小时生成流程被卡死（用户实测：家政项目管理端生成中弹出"删除临时生成目录 `rm -rf gen`"确认框，PM 不在电脑前） | ① `cross-platform-diff.md` 曾写"临时脚本自检完成后可删除"，反向示范了"建临时文件→用完删除"模式，Agent 泛化为建 `gen` 目录再 `rm -rf`；② SKILL.md 此前无任何命令层约束（"禁止自创"全是 CSS 类名层面）；③ 标准流程本无临时目录概念（注入文件即正式工件），命令纯属 Agent 加戏 | ① SKILL.md 新增「无人值守铁律」命令白名单：生成阶段只准跑技能脚本 / python 写文件 / `ls`，禁 `rm`/`del`/`rmdir`、禁建临时目录，文件更新一律覆盖写入；② 「遇阻不停」：流程外操作被禁或失败直接跳过并记交付说明，禁止停下等 PM；③ 子 Agent 免确认模式派发；④ `cross-platform-diff.md` 删除"可删除"示范，`cross-diff.py` 固定命名长期保留 |
| D40 | [多端编排] PRD 被流程遗漏：`work/prd/` 目录建了但内容为空，三端原型拼装完成后直接交付，没有需求文档（用户实测：家政服务项目 Phase 1 三端子 Agent 完成后，主 Agent 先构建三端原型，PRD 生成步骤被跳过，交付物缺 PRD） | ① SKILL.md 模式四 Phase 3 把 PRD 生成写成普通子步骤②，无独立门禁，主 Agent 拼装完三端后注意力转移即漏掉；② 流程无"交付物完整性"机械检查，缺 PRD 不报错；③ 契约未登记交付物清单，无对照依据 | ① 新增 `scripts/deliverables-check.py` 机械门禁：解析契约第十一章「交付物清单」（含 PRD 行），核对端原型 + 统一 PRD 全部存在且非空，任一缺失退出码 1，禁止进入步骤⑥；② 契约模板新增第十一章「交付物清单」+ PRD 注入文件铁律（`work/prd/` 必须产出 nav/sections/section-index/knowledge-base 四件，任一缺失 = PRD 未生成）；③ SKILL.md 编排铁律 8「PRD 不可缺」+ 9「交付物核对」：Phase 3 完成、进入步骤⑥前必须跑 `deliverables-check.py`，缺则返回补齐，禁止口头声称"已交付" |
