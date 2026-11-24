# PRD 踩坑库（P1-P35 + D38）

> **由 `scripts/split-pitfalls.py` 从 `history-pitfalls.md` 自动派生，禁止手改；修改请到源头。**
> **必读**：本文件（PRD 专属）+ `history-pitfalls-common.md`（跨端通用），生成需求文档前逐条对照。

## PRD 文档高频问题（P1-P35）

| # | 问题 | 根因 | 防护措施 |
|:--|:--|:--|:--|
| P1 | 搜索功能不可用 | Agent 注入覆盖了 `doSearch` 函数 | `doSearch` 在 `Agent:SEARCH_DATA_END` 之后，禁止覆盖 |
| P2 | 智能助手不可用 | Agent 注入覆盖了 `findAnswer` 函数 | `findAnswer` 在 `Agent:DATA_END` 之后，禁止覆盖 |
| P3 | HTML 注释暴露为页面文本 | HTML 注释内嵌套了 `<!-- ... -->` 导致浏览器过早关闭注释 | Agent 注入的 HTML 注释内禁止包含 `<!--` 或 `-->` |
| P4 | 页面内容被 header 遮挡 | main 容器未设置 `padding-top:80px` | main 必须有 `padding-top:80px; height:100vh; overflow:hidden` |
| P5 | 知识库条数不足 | Agent 只填充 3-5 条知识库 | 知识库最少 8 条，同义词映射最少 10 组 |
| P6 | PRD 缺少决策层，直接写功能 | Agent 跳过「Why & What」直接跳到实现层 | 严格执行三层结构：决策层（业务目标+用户研究+功能规划）→ 方案层 → 实现层 |
| P7 | PRD 方案层缺失或只有唯一方案 | Agent 只写了一个方案，无对比 | 方案层必须 ≥2 个备选方案（入口+解决），每个有优缺点/成本周期，推荐方案有数据支撑 |
| P8 | PRD 用户画像无真实来源 | Agent 凭空想象用户痛点 | 每条痛点标注来源（访谈/工单/反馈统计），画像含姓名/身份/场景/真实痛点 |
| P9 | PRD 缺少成本 ROI 分析 | Agent 只列功能清单 | 方案层含开发成本表（角色×人天）+ ROI 分析，ROI < 5 倍需重新评估优先级 |
| P10 | PRD 功能描述不完整，缺异常处理 | 只写正常流程 | 每个功能含「触发→输入→处理→输出→异常」五要素 + 异常场景表（权限/网络/空数据/非法输入） |
| P11 | PRD 分端章节与统一文档规则矛盾 | 双重生成多份文档各自为政 | PRD 单一化：一个项目只产出一份统一 PRD；子 Agent 只产出端功能清单（≤2KB） |
| P12 | sectionIndex 为空数组导致搜索失效 | 搜索索引占位被注释、注入遗漏 | build 脚本强制注入 sectionIndex；B5 实际执行搜索验证 |
| P13 | 导航点击无高亮，hover/active 失效 | 模板 CSS 用 .sidebar-item，注入用 .nav-item 且省 href | 统一 `.nav-item` + 保留 href；JS 选择器不依赖 href；Lint check_prd_nav_class |
| P14 | 出现 $ 美元符号（含 $ 形状 SVG 图标） | Agent 默认用 $ 未切人民币 | 货币符号铁律：金额必须 ¥ 禁 $（JS 模板字符串 ${} 除外），SVG 图标也禁 $ 形状；Lint check_prd_currency_symbol |
| P15 | "打开原型"无反应；文件名无统一规范 | href 用 `javascript:void(0)` 空链接；命名不一致 | 契约端矩阵加"输出文件名"列；href 必须用契约文件名 + target="_blank"；Lint check_prd_prototype_link |
| P16 | 接口设计复制粘贴残留无关参数 | 复制接口模板未清理 | API 参数一致性铁律（与功能匹配，公共分页参数除外）；Lint check_prd_api_param_residue |
| P17 | 功能参数表混入无关字段（发布含审核字段） | 从其他功能复制未清理 | 功能设计参数铁律（字段必须与功能直接相关）；Lint check_prd_func_param_relevance |
| P18 | 评审意见与实际内容数值不一致 | 修改内容后未同步评审意见 | 评审一致性铁律（关键数值全文档统一）；Lint check_prd_review_consistency |
| P19 | --prd-primary 用模板默认蓝 #2563eb | 未按契约替换主色 | 配色铁律：--prd-primary 必须用契约主色；Lint check_prd_color_scheme |
| P20 | 不同位置页面数量不一致 | 各章节独立生成 | 页面数量以功能模块清单为基准；Lint check_prd_page_count_consistency |
| P21 | 工作量统计只有数字无说明 | 只输出数字未附说明 | 工作量铁律：必须有计算说明列、分角色估算、总计行；Lint check_prd_workload_explanation |
| P22 | 数据结构缺辅助表、接口缺配套 | 只覆盖核心表 | 数据结构完整性铁律（覆盖所有功能模块涉及的表，接口与表配套）；Lint check_prd_data_structure_coverage |
| P23 | 缺标准文档信息表 | 跳过元信息直接写内容 | 文档信息表 9 个标准字段；Lint check_prd_doc_info_table |
| P24 | 页面交互设计只写用户端 | 未覆盖管理端 | 交互完整性铁律（覆盖所有端 + 关键流程 + 异常交互）；Lint check_prd_interaction_coverage |
| P25 | 缺"功能模块清单"章节 | 跳过直接写详细设计 | 模块清单铁律（列表格式、覆盖完整、分端标注）；Lint check_prd_module_list |
| P26 | 原型与UI章节只有入口按钮缺页面清单 | 只放跳转链接 | 原型页面清单铁律（分端列出所有页面，数量与统计一致）；Lint check_prd_prototype_page_list |
| P27 | 架构图卡片仅占 25% 宽、文字竖排 | biz-panorama（4列grid）与内部 grid 混用 | 架构图用 biz-flow 禁 biz-panorama；Lint check_prd_biz_panorama_misuse |
| P28 | hover/active/阴影硬编码 #2563eb 蓝 | 模板 CSS 直接写死而非 var | 模板改用 var(--prd-primary)/rgba(var(--prd-primary-rgb))；Lint P28 检查 |
| P29 | 导航线条型图标不可见、闭合型变黑块 | .nav-icon 无 fill/stroke，默认 fill:black | `.nav-icon{fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}` |
| P30 | 导航图标太丑、分组标题用 Emoji | 手绘简单 path；Emoji 触发 T1 | 用 **Lucide 线性图标**官方 path（全内联 SVG，禁手绘）；分组标题禁 Emoji |
| P31 | 需求文档只有详细版，日常开发过重 | 无轻量档位 | PRD 双模式（步骤④三项必选中由 PM 强制二选一，**无默认值**，2026-08-21 起废止"默认详细"）：简易版固定 9 核心章节、无搜索栏/智能助手；build 路由 --prd-mode |
| P32 | PRD 构建报缺 NAV_END，完全无法生成 | 模板 NAV 区只有 START 无 END，replace_between 抛错 | NAV/SECTION 标记必须成对标对（START/END）；注入说明强调 |
| P33 | 简易/详细 PRD 被 lint 误判失败（M47/M49/D9） | PRD 是文档被当原型检查 | D9/M47/M49 开头加 is_prd_file 豁免 |
| P34 | 简易模板维护时易误删共用样式 | 简易版被当"可随意精简"的副本 | **P34 样式铁律**：lint 简易模板自动比对 CSS 必须是详细版子集（仅允许删 chat/search 相关），砍共用样式即判失败 |
| P35 | 简易模板 NAV/SECTION 示例骨架与 9 章规范脱节 | 从详细版整体复制未同步精简 | 示例区重组为 9 章（一字不动 <style>，P34 保护）；修正 showSection 死链 |
| D38 | [PRD 详细/简易] 内容区卡片透明无边框无内边距，大量样式"消失"（用户实测：便民上门服务需求文档-简易版内容区排版全无） | 模板 `.card` 元素样式靠 Tailwind 原子类（`bg-white rounded-2xl p-6`），模板 CSS 无 `.card{}` 规则；注入说明把 `.card` 列入 class 词汇，Agent 产出纯 `class="card"` → 无任何样式匹配（透明/无 padding/无阴影）；且 Tailwind CDN 加载失败/离线时原子类全部失效 | ① 两个 PRD 模板加 `.card{}` 兜底 CSS（白底/边框/圆角/22px 内边距/阴影，详细版与简易版完全一致保持 P34 子集）；② 注入说明-PRD*.md 加「卡片类名铁律」：统一写 `class="card"`，禁止 `card-hover`/`bg-white rounded-2xl` 等变体；③ 兜底保证：有 Tailwind 时原子类覆盖、无 Tailwind/离线时 .card 基础样式生效 |
