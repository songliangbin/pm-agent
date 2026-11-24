# PRD 注入说明（简易版 · 子 Agent 读取，替代完整模板）

> 你**不需要**读取 `templates/prd-template-simple.html`（86KB）。只需按本文档产出 2 个注入文件，主 Agent 用 `scripts/build-prototype.py --prd-mode simple` 确定性拼装。
> **一个项目只产出一份 PRD**（由主 Agent 汇合生成），不产出分端 PRD 章节。
> 简易版面向**开发人员**，聚焦"功能逻辑与规则"，去除决策层调研、方案比选、成本排期、风险、接口/交互细节、附录与智能助手。

## 🚫 样式铁律（最高优先级，违反即回退）

**简易版 PRD 的「外观样式」必须与详细版 100% 一致——只能砍「内容」和「模块」，绝不能砍「样式」。**

- 简易版模板 `prd-template-simple.html` 是详细版模板 `prd-template.html` 的**样式克隆**，仅移除了「搜索栏 + 智能助手」两个模块的功能（其 HTML/CSS/JS）。
- **禁止删除任何共用样式**：侧栏菜单、导航项（`#home`/`#overview` 等）、内容区、章节、表格、卡片、徽标、配色（`--prd-*` 主题色变量）、字体、间距、Mermaid 图表、外部资源（Tailwind/字体/Font Awesome/Mermaid CDN）一律原样保留。
- 26 个 `--prd-*` 主题色变量必须与详细版逐一对齐，不得增减。
- 你产出的 `nav.html` / `sections.html` 必须**沿用详细版同一套 class 词汇**（`.nav-item`、`.nav-group`、`.tab-content`、`.prd-table`、`.section-title`、`.card` 等），不得自创样式或 class，否则生成后观感会与详细版不一致。
- **卡片类名铁律（D37）**：卡片容器统一写 `<div class="card">`（模板已内置 .card 兜底样式：白底/边框/圆角/内边距/阴影）。**禁止**只写 `class="card"` 以外的变体（如 `class="card-hover"`、`class="bg-white rounded-2xl"` 混用）——Tailwind 原子类仅在 CDN 加载时生效，模板 .card 兜底保证离线也正常。需要卡片 hover 效果时追加 `card-hover` 类：`class="card card-hover"`。
- **拦截保障**：`standards/agent-lint.py` 已加 **P34** 铁律——lint 简易模板时自动比对，其 CSS 必须是详细版 CSS 的**子集**（仅允许删 `.chat-*` / `.header-search*` / `.search-*` / `.header-ai-*` / 聊天动画 keyframes）。一旦砍了任何共用样式，P34 直接判失败、构建门禁不过。

## 与详细版的核心差异

| 维度 | 详细版 | 简易版 |
|:--|:--|:--|
| 模板 | `prd-template.html` | `prd-template-simple.html` |
| 智能助手 | 有（聊天问答） | **无** |
| 搜索栏 | 有（doSearch） | **无** |
| sectionIndex / knowledgeBase | 需产出 | **不产出**（无搜索/助手，注入文件不含这两项） |
| 章节数量 | 三层全量 | 9 个核心章节（见下） |
| 三层结构铁律 | 严格执行 | 放宽：不强制用户研究/业务目标层 |

## 你的产出（2 个文件）

| 文件 | 内容 | 大小上限 |
|:--|:--|:--|
| `nav.html` | 侧边栏导航（含分组标题） | ≤ 3KB |
| `sections.html` | 全部章节 HTML（tab-content 结构） | ≤ 55KB |

> 简易版**不产出** `section-index.js` / `knowledge-base.js`，config.json 中也**不要**包含 `sectionIndex` / `kb` 字段。
>
> 🔴 **config.json 键名铁律（M95 教训）**：PRD 的 config.json 中，章节内容键**必须用 `pages`**（`"pages": "work/prd/sections.html"`），主色键必须用 `--prd-primary` 系列（M93）。build 已兼容 `pages`/`sections` 两个别名且缺键直接报错，但**请统一写 `pages`** 避免混乱。

## 固定章节（简易版 nav 必含，按序排列）

| 分组 | 章节 | id |
|:--|:--|:--|
| 决策层 | 系统首页 | `#home` |
| 决策层 | 项目概述 | `#overview` |
| 决策层 | 功能规划 | `#feature-plan` |
| 方案层 | 系统架构 | `#architecture` |
| 实现层 | 角色权限 | `#roles` |
| 实现层 | 核心业务模块（按实体：状态机 + 流程图 + 规则表） | 各实体 id（如 `#order-module`） |
| 实现层 | 功能详细设计 | `#feature-detail` |
| 实现层 | 数据结构 | `#data-structure` |
| 实现层 | 测试验收 | `#testing` |
| 可选 | 原型与UI（标准结构：4 张原型卡 + 页面清单表，见下） | `#prototype` |

> 🔴 **内容区标准铁律（M100，用户核心要求）**：简易版内容区标准**必须与详细版一模一样**。只是左侧菜单可以少特定章节（如详细版的"用户研究/方案对比/成本ROI/排期/接口设计/变更记录"等，简易版不产），对应右侧也没有该章节内容。**但只要左右侧都有的章节，内容必须对齐详细版标准结构，禁止简化**：
> - `#home`：hero 渐变横幅 + 文档信息表 + 5 分钟速读 + 4 张 KPI 卡 + 核心规则摘要
> - `#overview`：业务目标表 + 3 张价值卡（用户/商家/平台）+ 术语定义表 + 业务边界（prd-tip/warn/error）
> - `#feature-plan`：功能清单表（含优先级 status-tag）+ 不做功能清单表
> - `#architecture`：端侧说明表（端/定位/关键能力）
> - `#roles`：角色定义表 + 权限矩阵表
> - `#data-structure`：表结构定义（字段名/类型/长度/必填/默认值/索引/说明）
> - `#testing`：功能验收表 + 核心链路测试用例 + 异常场景测试用例 + 性能兼容性要求
> - `#prototype`：原型卡 + 页面清单表（见下"原型与UI 章节标准结构"）
> - 样式用模板已内置的 Tailwind 等价类（bg-white rounded-2xl p-6 border border-gray-100 等），**离线断 CDN 也生效**，禁止自创简化结构
> 违反任何一条 = 内容区质量降级 = 用户验收不通过。

**被排除的章节（禁止出现）**：用户研究、业务目标、功能入口方案对比、解决方案对比、成本与ROI、项目排期、风险管理、接口设计、交互设计、错误码、附录（变更记录/待确认/评审/参考）。

## 各章节内容要点（developer-focused）

- **系统首页 #home**：项目名 + 版本 + 一句话描述 + 核心规则摘要（3-5 条业务约束）。不要"5 分钟速读版"等装饰。
- **项目概述 #overview**：背景与目标（1-2 段）+ 业务边界（当前范围 / 不在此版本）+ 术语表（prd-table：术语｜定义｜系统落点）。
- **功能规划 #feature-plan**：功能清单表（prd-table：功能｜描述｜优先级 P0/P1/P2｜工作量）+ MVP 规划（第一版只列 P0）。
- **系统架构 #architecture**：多端架构图（biz-flow 容器 + Tailwind grid）+ 端侧说明表（端｜定位｜关键能力）+ 数据隔离原则。
- **角色权限 #roles**：角色表 + 权限矩阵（prd-table：角色｜可操作功能｜数据范围），把"谁能做什么"讲清。
- **核心业务模块**：每个核心实体一节，必须含 **状态机（mermaid stateDiagram）+ 流程图（mermaid flowchart）+ 规则表（prd-table：规则｜触发条件｜处理逻辑｜异常）**。这是简易版的核心。
- **功能详细设计 #feature-detail**：按功能列"触发条件 → 输入 → 处理 → 输出 → 异常处理"五要素（prd-table 或列表）。
- **数据结构 #data-structure**：数据表清单（prd-table：表名｜字段｜类型｜说明），覆盖所有功能模块涉及的实体。
- **测试验收 #testing**：验收标准表（prd-table：功能｜验收点｜预期结果）。
- **原型与UI #prototype（可选）**：仅放"打开原型"按钮（见下方 P15 铁律）。

## nav.html 结构铁律（P13 防护：CSS/JS 类名必须与模板一致）

模板 CSS/JS 使用 `.nav-item` 类和 `onclick="showSection('id')"` 属性管理导航高亮。注入的 nav.html **必须遵守**：

1. 类名必须用 `nav-item`（禁止 `sidebar-item`、`menu-item` 等）
2. 必须保留 `href="#{章节id}"` 属性
3. 必须保留 `onclick="showSection('{章节id}')"` 属性
4. 分组标题用 `nav-group` + `nav-group-title`（禁止内联 style）
5. 图标用内联 SVG 加 `nav-icon` 类 或 Font Awesome `<i>`（全文档统一）
6. 默认选中项加 `active` 类（首页 `nav-item active`）

标准结构示例：

```html
<div class="nav-group">
  <div class="nav-group-title">决策层</div>
  <a href="#home" class="nav-item active" onclick="showSection('home')">
    <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M9 22V12h6v10"/></svg>
    <span>系统首页</span>
  </a>
  <a href="#overview" class="nav-item" onclick="showSection('overview')">
    <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M16 13H8"/><path d="M16 17H8"/><path d="M10 9H8"/></svg>
    <span>项目概述</span>
  </a>
</div>
```

> **禁止**：自创类名、省略 href、用内联 style 替代 nav-group-title、混用 Font Awesome 和 SVG 图标。

## 货币符号铁律（P14 防护：禁止美元符号 $）

文档中所有涉及金额的地方**必须使用人民币符号 ¥**，禁止使用美元符号 $。（同详细版，全域适用）

## 原型链接铁律（P15 防护：原型入口必须可跳转）

若包含"原型与UI"章节，"打开原型"按钮**必须使用相对路径指向实际原型文件**，禁止 `javascript:void(0)` 空链接。

```html
<a href="用户端原型.html" target="_blank" class="...">
  <i class="fas fa-external-link-alt"></i> 打开原型
</a>
```

## 配色方案一致性铁律（P19 防护：PRD 主色必须与项目契约一致）

PRD 文档的 CSS 主色变量**必须与项目契约中约定的配色方案一致**，禁止使用模板默认色。主 Agent 生成时第一步即从契约读取主色并替换模板默认值。

## 原型与UI 章节标准结构（M99 防护：内容不可被简化）

简易版"原型与UI"章节**不可被简化**为"几个按钮横排"——用户明确要求"右侧内容区一点质量都不能降低"。最低标准：

```html
<section id="prototype" class="tab-content">
  <h2 class="section-title">原型与UI</h2>
  <p class="section-subtitle">Prototype & UI · 三端交付物</p>

  <!-- 4 张原型卡：每端一个 + 配色规范卡（参考详细版布局） -->
  <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px">
    <div class="card card-hover" style="padding:20px">
      <div style="...图标盒（彩底+FA 图标）..."></div>
      <h4>用户端原型</h4>
      <p>移动端 H5（X 页）</p>
      <p>核心功能描述</p>
      <a href="用户端原型.html" target="_blank">打开原型</a>
    </div>
    <!-- 商家端 / 平台端 / 配色规范 同样 4 张 -->
  </div>

  <!-- 页面清单表（必含） -->
  <div class="card">
    <div class="card-header"><i class="fas fa-list"></i>原型页面清单</div>
    <table class="prd-table">
      <thead><tr><th>端</th><th>页面数</th><th>页面清单</th></tr></thead>
      <tbody>
        <tr><td>用户端</td><td>实际页数</td><td>页面列表（反映实际 page/sub-page）</td></tr>
        ...
      </tbody>
    </table>
  </div>
</section>
```

**必须包含**：
1. 4 张原型卡（图标盒 + 副标题 + 核心描述 + 打开按钮），用 grid 2 列布局
2. 1 张"原型页面清单表"（端/页数/页面清单），页数必须反映实际 page/sub-page 数量
3. 所有跳转链接相对路径正确指向产物 HTML 文件
4. 卡片样式用内联 style（不依赖 Tailwind CDN，离线仍正常）

## 简易版适用的其余防护铁律

- **P13** nav 结构（上）
- **P14** 货币符号 ¥
- **P15** 原型链接可跳转（若含原型章节）
- **P19** 配色与契约一致
- **P28** CSS 交互元素颜色使用 `var(--prd-primary)` 变量，禁止硬编码 `#2563eb`

## 简易版不适用的铁律（详细版专属，简易版无需遵守）

P16 API 参数一致性 / P17 功能参数表相关性 / P18 评审意见一致性 / P20 页面数量统一 / P21 工作量计算说明 / P22 数据结构覆盖 / P23 文档信息表 / P24 交互设计覆盖所有端 / P27 架构图布局 / 智能助手相关红线（搜索有结果、助手有回答）。

## 章节 HTML 规范（sections.html）

- 每个章节：`<section id="{name}" class="tab-content">`，首页 section 加 `active`
- 章节标题：`<h2 class="section-title">` + `<p class="section-subtitle">`
- 表格：`<table class="prd-table">`（表头 thead + tbody），数据表 ≥ 3 行
- 业务模块必须含：状态机（mermaid stateDiagram-v2）+ 流程图（mermaid flowchart）+ 规则表（prd-table）
- 用户可见提示文案必须写清楚（禁止"开发中"占位）
