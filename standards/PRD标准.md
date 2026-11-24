# PRD 标准规范 v3.0

> 通用需求文档标准，适用于所有项目类型（电商 / SaaS / O2O / 社交 / 工具等）
> 基于「决策层 → 方案层 → 实现层」三层结构，确保 PRD 达到大厂交付标准
> Agent 按项目实际需求动态组装章节，不绑定特定行业
> 配色方案支持自定义 CSS 变量，每次生成时按项目调性设置

> **简易版 PRD（面向开发，聚焦功能逻辑与规则）**：当用户选择「简易版」时，仅产出 9 个核心章节（系统首页 / 项目概述 / 功能规划 / 系统架构 / 角色权限 / 核心业务模块 / 功能详细设计 / 数据结构 / 测试验收），无智能助手、无搜索栏，砍掉用户研究 / 业务目标 / 入口方案 / 方案对比 / 成本ROI / 项目排期 / 风险管理 / 接口设计 / 交互设计 / 错误码 / 附录。子 Agent 请读 `templates/注入说明-PRD-simple.md`，主 Agent 用 `build-prototype.py --prd-mode simple` 拼装。本规范的「三层结构铁律」在简易版下放宽（见 SKILL.md）。

---

## 一、文档三层结构（核心框架）

> **铁律**：每个 PRD 必须按「决策层 → 方案层 → 实现层」三层结构组织内容。禁止直接跳到实现层，缺少决策依据的 PRD 视为不合格。

| 层级 | 定位 | 目标读者 | 核心目标 |
|:-----|:-----|:---------|:---------|
| **第1层 决策层**（Why & What） | 领导、跨部门同事 | 说清楚「为什么要做」 |
| **第2层 方案层**（How） | 产品团队 | 说清楚「怎么做、为什么这样选」 |
| **第3层 实现层**（Detail） | 研发、测试 | 说清楚「具体怎么实现」 |

三层结构导航分组：
- **决策层**：项目概览 / 用户研究 / 业务目标与痛点 / 功能规划
- **方案层**：系统架构 / 方案对比 / 项目排期 / 风险管理 / 成本与 ROI
- **实现层**：角色权限 / 核心业务模块 / 各端功能 / 全局规则 / 数据与接口 / 测试验收
- **附录**：变更记录 / 待确认问题 / 评审意见 / 参考资料

---

## 二、决策层（Why & What）—— 每个 PRD 必有

### 2.1 系统首页（#home）

- **定位**：项目的仪表盘入口，打开文档即看到项目全貌
- **必须包含**：
  - **Hero 区域**：深色渐变背景 + 项目名称 + 版本号 + 一句话描述 + 三层结构标识（决策层/方案层/实现层）
  - **统计卡片**：关键数据摘要（几个端 / 几个核心模块 / 几种角色 / 预估人天），使用 `grid grid-cols-4 gap-6` 布局
  - **快速入口**：三层结构各章节的快捷跳转按钮
  - **核心规则摘要**：最重要的 3-5 条业务约束
  - **5分钟速读版**：为什么做 / 给谁做 / 做什么 / 什么时候上线 / 需要多少人

### 2.2 项目概述（#overview）

- **必须包含**：
  - 项目背景与目标（1-3 段文字）
  - **业务目标表**（prd-table）：维度 | 现状 | 目标 | 如何衡量
  - 价值说明：按参与方（用户 / 商家 / 平台 等）展示
  - 术语定义表（prd-table）：术语 | 定义 | 系统落点
  - 业务边界说明：当前范围（prd-tip）/ 需确认（prd-warn）/ 不在此版本（prd-error）

### 2.3 用户研究（#user-research）

- **必须包含**：
  - **用户画像卡片**：每个画像一张卡片，`grid grid-cols-{n}` 布局
    - 头像占位 + 姓名 + 身份标签
    - 一句话描述（核心需求和痛点）
    - 使用场景列表（3-5条）
    - 痛点列表（3-5条）
  - **用户痛点清单**（prd-table）：痛点 | 用户原话 | 影响人群 | 频次/严重度
    - 每条痛点必须有真实来源（访谈/工单/反馈），禁止凭空想象
  - **用户故事表**（prd-table）：作为__（角色），我想__（功能），以便__（价值），优先级
  - **典型使用场景**（场景卡片）：用户是谁 / 触发条件 / 使用频率 / 当前痛点 / 期望结果
  - **用户旅程地图**：发现需求 → 寻找入口 → 开始使用 → 完成任务 → 验证结果，标注各环节痛点

- **画像数量规则**：
  - 单端项目：3-4 个画像
  - 多端项目：每个端至少 1 个画像，总数 4-6 个

### 2.4 业务目标与数据支撑（#business-goals）

- **必须包含**：
  - **业务目标表**（prd-table）：维度 | 现状 | 目标 | 如何衡量
    - 示例维度：核心指标、商业价值、用户满意度
  - **数据支撑**（卡片列表）：数据点 | 来源 | 结论
    - 用具体数据证明需求的紧迫性
  - **不做的后果**（prd-warn 卡片）：
    - 短期影响（1-3个月）
    - 长期影响（3-6个月）
    - 竞争风险（竞品已做 / 用户会流失到竞品）
  - **成功标准**（prd-table）：指标类型 | 指标名称 | 当前值 | 目标值 | 观测周期
    - 北极星指标（1个核心指标）
    - 过程指标（2-3个中间指标）

### 2.5 功能规划（#feature-plan）

- **必须包含**：
  - **功能清单表**（prd-table）：功能 | 描述 | 优先级 | 理由 | 工作量
    - P0（必须做）：不做这个功能，整个需求就失败了
    - P1（推荐做）：做了用户体验会好很多，但不做不影响核心流程
    - P2（可以不做）：锦上添花，资源不够就先不做
  - **MVP 版本规划**：
    - 第一版（上线）：只列 P0 功能
    - 第二版（迭代）：P1 功能，根据第一版数据决定是否做
  - **不做功能清单**（prd-error）：功能 | 为什么不做 | 什么时候考虑做
    - 明确说「不做什么」，避免研发、设计、运营对需求范围产生误解

---

## 三、方案层（How）—— 每个 PRD 必有

### 3.1 系统架构（#architecture）

- **必须包含**：
  - 多端架构图：使用 biz-flow 的 biz-panorama 组件
  - 业务线全景图：用 biz-row + biz-node 组件展示核心业务线流向
  - 端侧说明表（prd-table）：端 | 定位 | 关键能力
  - 数据隔离原则列表
  - 关键集成表（prd-table）：集成方 | 能力 | 触发场景 | 注意事项
  - **跨端交互矩阵**（多端项目）：操作 | 端A | 端B | ... | 端N

### 3.2 功能入口方案对比（#entry-comparison）

- **必须包含**：
  - **入口方案对比表**（prd-table）：方案 | 示意图/描述 | 优点 | 缺点 | 预期影响
    - 至少对比 2 个备选方案
  - **推荐方案**：方案名称 + 决策理由（用数据支撑）
    - 示例理由：目标用户是谁，需要最高的可见性；竞品都是怎么做的

### 3.3 解决方案对比（#solution-comparison）

- **必须包含**：
  - **方案对比**（卡片组）：至少 2-3 个备选方案
    - 每个方案包含：描述、优点列表、缺点列表、成本（人天）、周期（周）
  - **方案决策**：推荐方案 + 决策理由（用数据说话）
    - 成本更低 / 周期更短 / 用户接受度更高 / 数据支撑
  - **💡 提示**：方案对比要客观，列出优缺点，用数据支撑决策

### 3.4 成本评估与 ROI（#cost-roi）

- **必须包含**：
  - **开发成本表**（prd-table）：角色 | 工作内容 | 人天 | 备注
    - 产品经理 / 交互设计师 / 视觉设计师 / 前端工程师 / 后端工程师 / 测试工程师
    - 总计人天和预估周期
  - **ROI 分析**（卡片组）：
    - 投入成本：人力成本 + 机会成本
    - 预期收益：核心指标提升 + 商业价值计算
    - ROI = 收益 / 投入，回本周期
    - 结论：ROI 是否值得优先做（ROI < 5 倍需重新评估优先级）

### 3.5 项目排期（#schedule）

- **必须包含**：
  - **项目排期表**（prd-table）：阶段 | 时间 | 交付物 | 责任人 | 状态
    - 需求评审 → 交互设计 → 视觉设计 → 前端开发 → 后端开发 → 联调测试 → 灰度上线 → 全量上线
  - **灰度方案**（prd-table）：阶段 | 时间 | 用户范围 | 目标 | 决策标准
    - 灰度1 → 灰度2 → 全量
    - 观测指标：稳定性（崩溃率）、效果（核心指标提升）

### 3.6 风险管理（#risk-management）

- **必须包含**：
  - **风险清单表**（prd-table）：风险 | 发生概率 | 影响程度 | 应对方案 | 责任人
    - 高概率+高影响的风险，必须提前准备应对方案
  - 常见风险类型：技术实现延期、用户接受度低、数据不达标、第三方依赖风险

---

## 四、实现层（Detail）—— 按项目实际需求动态组装

### 4.1 角色与权限（#roles）

- **角色定义表**（prd-table）：角色（status-tag） | 使用端 | 核心权限 | 数据范围
- **权限矩阵**（prd-table）：功能 | 角色1 | 角色2 | ... | 角色N（使用 √ / - / 标注）
- 多角色说明：如有角色之间有特殊关系，需用 prd-warn 说明
- 入驻/开通流程（可选）：使用 biz-swimlane 泳道图展示跨角色入驻协作

### 4.2 核心业务模块（按实体动态组装）

> Agent 分析 PM 需求后，识别核心业务实体，按「实体生命周期」组织章节。

#### 每个业务实体章节必须包含：

1. **状态机图**（biz-timeline 或 Mermaid stateDiagram 或 biz-state-ladder）
2. **流程图**（biz-flow）—— 从用户触发到最终结果的完整流程
3. **泳道图**（biz-swimlane 或 Mermaid sequenceDiagram）—— 跨角色协作时序
4. **规则表**（prd-table）—— 触发条件、规则、约束、注意事项
5. **核心提示**（prd-tip）
6. **边界/异常说明**（prd-warn / prd-error）
7. **至少 1 个完整示例**—— 用时间线表格或场景卡片展示端到端流程
8. **实体间关系图**（Mermaid ER 图）—— 多个实体有交互时补充

#### 常见业务类型参考：

| 类型 | 典型实体链路 | 适用行业 |
|------|------------|---------|
| 交易型 | 商品→订单→支付→退款→分账 | 电商/O2O/本地生活/交易平台 |
| 社交型 | 内容→发布→互动→推荐→消息 | 社交/社区/内容平台 |
| 工具型 | 任务→执行→通知→统计 | 效率工具/SaaS/管理系统 |
| 会员型 | 会员→权益→券→核销→结算 | 会员制/订阅制/积分体系 |
| 服务型 | 需求→匹配→履约→评价→结算 | 家政/出行/教育/咨询 |
| 资讯型 | 素材→审核→发布→分发→数据 | 媒体/资讯/短视频/博客 |

### 4.3 功能详细设计（每个功能必须按此模板展开）

> **铁律**：每个功能必须包含完整的「触发条件 → 输入参数 → 处理逻辑 → 输出结果 → 异常处理」五要素。

#### 功能模板：

**功能名称**：xxx

**触发条件**：
- 入口位置：[具体位置，如：首页右下角"+"按钮]
- 权限要求：[登录用户 / VIP用户 / 特定角色]
- 前置条件：[如：必须先完成实名认证]

**输入参数表**（prd-table）：
| 参数名 | 类型 | 必填 | 默认值 | 校验规则 | 说明 | 示例 |
|--------|------|------|--------|----------|------|------|

**处理逻辑**：（用流程图或步骤列表描述）
1. 用户点击 xxx
2. 前端校验 xxx
3. 调用后端接口 xxx
4. ...

**输出结果**：
- ✅ 成功：页面跳转 / Toast提示 / 返回数据
- ❌ 失败：页面不跳转 / 错误提示 / 可重试说明

**异常处理表**（prd-table）：
| 异常场景 | 触发条件 | 处理方式 | 用户提示 | 是否可重试 |
|----------|----------|----------|----------|------------|

> **💡 提示**：所有用户可见的提示文案，都要在 PRD 里写清楚，避免研发自己编。

### 4.4 数据结构设计（#data-structure）

- **表结构定义**（prd-table）：字段名 | 类型 | 长度 | 必填 | 默认值 | 索引 | 说明 | 示例值
- **索引设计**：主键 / 普通索引 / 唯一索引 / 复合索引（说明用途）
- **💡 提示**：
  - 经常作为查询条件的字段，要加索引
  - 状态字段用 tinyint，节省空间
  - 计数字段设默认值 0，避免 NULL
  - 多对多关系需要用中间表

### 4.5 接口定义（#api-design）

- **接口文档**（每个接口必须包含）：
  - 基本信息：接口路径、接口说明、权限要求
  - 请求头：Content-Type / Authorization 等
  - 请求参数表（prd-table）：参数名 | 类型 | 必填 | 说明 | 示例
  - 请求示例（JSON 格式）
  - 返回结果（成功）：code / message / data
  - 返回结果（失败）：code / message / data
  - **错误码说明表**（prd-table）：错误码 | 说明 | 常见原因 | 解决方案

> **💡 提示**：
> - 所有接口都要返回统一格式：`{ code, message, data }`
> - 错误码要有明确说明，方便前端处理
> - 列表接口要返回总数（total），方便前端做分页

### 4.6 页面交互设计（#interaction-design）

- **页面布局**：（用文字描述或 ASCII 图描述页面结构）
- **页面元素交互表**（prd-table）：元素 | 交互行为 | 触发条件 | 反馈效果 | 备注
- **页面状态设计**（prd-table）：状态 | 触发条件 | 页面显示 | 用户操作
  - ✅ 正常状态（有数据）
  - 🔄 加载中（首次加载）
  - 📭 空状态（无数据）
  - ❌ 错误状态（网络错误/加载失败）
  - 🔍 搜索无结果
- **全局交互规范**（prd-table）：交互 | 规范
  - 按钮点击 / 页面跳转 / Toast提示 / 加载动画 / 下拉刷新

> **💡 提示**：
> - 每个交互都要说清楚：触发条件、反馈效果、动画效果
> - 空状态、加载中、错误状态都要设计，提升用户体验

### 4.7 各端功能清单（按端数量动态生成）

每个端一个章节（如 #user-app、#store-app、#admin 等），必须包含：

- **功能概览**：该端的定位和核心能力卡片
- **页面与功能表**（prd-table）：页面 | 功能点 | 说明 | 校验规则
- **关键交互规则**：核心操作的交互流程和约束（用 biz-flow 展示）
- **校验规则列表**：表单校验、业务校验（用 prd-table）
- **数据来源/归属**：该端数据的来源和可见范围

### 4.8 全局业务规则（#rules）

按主题分组，每组一个卡片或表格：

- 交易规则（价格/促销/优惠）
- 退款规则（退款条件/审核流程/时效）
- 入驻规则（商家/供应商入驻条件和流程）
- 商品规则（发布/审核/上下架）
- 资金规则（支付/分账/结算/提现）
- 通知规则（消息推送场景和触发条件）
- 数据规则（数据隔离/导出/保留）

### 4.9 订阅消息推送（#subscription-msg，如有消息通知需求）

- 消息场景表（prd-table）：消息类型 | 触发条件 | 推送内容模板 | 接收角色 | 备注
- 推送渠道说明（微信订阅消息 / 短信 / 站内信）
- 用户授权流程

### 4.10 定时任务（#jobs，如有自动化任务）

- 任务列表表（prd-table）：任务名称 | 触发条件 | 执行频率 | 执行逻辑 | 失败处理
- 幂等性说明
- 监控和告警规则

### 4.11 数据看板指标（#dashboard-metrics，如有后台管理端）

- 指标表（prd-table）：指标名称 | 定义 | 数据来源 | 展示位置 | 计算公式
- 按角色分组：运营看板 / 财务看板 / 商家看板
- 核心指标（GMV / 订单量 / 用户数等）

### 4.12 原型与UI（#prototypes）

- **必须包含**：该项目的所有原型和 UI 设计稿链接卡片
- **布局**：`grid grid-cols-2 gap-6`（或按端数量调整列数）
- **每个卡片包含**：图标区域 + 标题 + 副标题 + 描述文字 + 打开按钮
- **原型卡片色系**：管理端=紫色，用户端=绿色，门店端=橙色，UI设计稿=粉色
- **底部提示**：需求评审时以本文档规则为准，若原型与文档冲突，需在评审纪要中确认最终口径

### 4.13 错误码规范（#error-codes）

- 错误码表（prd-table）：错误码 | 错误类型 | 错误描述 | 触发场景 | 处理建议
- 编码规则说明（如：BIZ-001 ~ BIZ-099 业务错误，PAY-001 ~ PAY-099 支付错误）
- 前端错误提示映射

### 4.14 测试验收（#testing）

#### 功能验收标准
- **功能验收表**（prd-table）：功能模块 | 验收标准 | 验收方法 | 优先级 | 负责人
  - P0 功能必须 100% 通过，P1 功能可以允许少量问题

#### 性能验收标准
- **性能指标表**（prd-table）：指标 | 验收标准 | 验收方法
  - 页面加载速度：首屏加载时间 ≤ 2秒（4G网络）
  - 接口响应时间：95% 的接口响应时间 ≤ 500ms
  - 崩溃率：App 崩溃率 ≤ 0.1%
  - 内存占用：App 运行时内存占用 ≤ 200MB

#### 兼容性验收标准
- **兼容性表**（prd-table）：维度 | 验收标准
  - 系统版本：iOS 12+ / Android 8.0+
  - 屏幕尺寸：适配主流机型
  - 网络环境：4G / 5G / WiFi 都能正常使用
  - 弱网环境：2G 网络下功能可用（可降级显示）

#### 用户体验验收标准
- **体验指标表**（prd-table）：维度 | 验收标准 | 验收方法
  - 交互流畅性：页面滑动帧率 ≥ 55fps
  - 操作反馈：所有按钮点击都有视觉/触觉反馈
  - 异常提示：所有错误都有明确的提示文案
  - 无障碍支持：支持 VoiceOver/TalkBack 朗读

#### 测试用例示例
- **正常流程用例**：步骤 | 操作 | 预期结果
- **异常流程用例**：步骤 | 操作 | 预期结果
  - 每个用例要写清楚：步骤、操作、预期结果

---

## 五、附录（每个 PRD 必有）

### 5.1 变更记录（#changelog）

- **变更记录表**（prd-table）：版本 | 日期 | 变更内容 | 变更人 | 评审状态
  - 评审状态：🟡 草稿 / 🟢 评审中 / ✅ 已通过

### 5.2 待确认问题（#pending-questions）

- **问题跟踪表**（prd-table）：问题 | 描述 | 影响 | 负责人 | 截止日期 | 状态
  - 状态：⏳ 待确认 / ✅ 已解决 / ❌ 已取消
  - 问题要及时跟进，不要让问题堆积到开发阶段

### 5.3 评审意见记录（#review-records）

- **评审记录表**（prd-table）：评审人 | 角色 | 评审意见 | 处理结果 | 处理人
  - 处理结果：✅ 已采纳 / ❌ 不采纳 / ⏳ 待讨论

### 5.4 参考资料（#references）

- 用户研究：用户访谈记录 / 用户画像文档 / 用户反馈汇总
- 竞品分析：竞品功能对比表 / 竞品体验报告
- 数据支撑：数据分析报告 / AB 测试报告
- 设计资源：原型链接 / 视觉设计稿 / 设计规范

---

## 六、PRD 质量自检清单（交付前必须逐项检查）

Agent 生成 PRD HTML 后，交付前必须逐项自检以下清单。如有 3 项以上未达标，必须补充完善后再交付。

### 决策层检查
- [ ] **业务目标是否明确？** 有具体数据和衡量方式
- [ ] **用户痛点是否有真实来源？** 访谈/工单/反馈，附用户原话
- [ ] **成功标准是否可衡量？** 北极星指标 + 过程指标，有当前值和目标值
- [ ] **目标用户是否清晰？** 有用户分层和画像
- [ ] **功能优先级是否明确？** P0/P1/P2 标注，有不做功能清单
- [ ] **是否说明了「不做什么」？** 明确边界，避免期望偏差

### 方案层检查
- [ ] **是否对比了多个方案？** 至少 2 个备选方案（入口方案 + 解决方案）
- [ ] **推荐方案是否有理由？** 用数据支撑决策
- [ ] **排期是否合理？** 有缓冲时间，各阶段责任人和交付物明确
- [ ] **风险是否识别？** 高概率+高影响的风险有应对方案
- [ ] **ROI 是否计算？** 投入/产出比，回本周期

### 实现层检查
- [ ] **功能逻辑是否完整？** 覆盖所有分支（触发条件/输入/处理/输出/异常）
- [ ] **异常场景是否覆盖？** 权限不足/网络异常/数据为空/输入非法等
- [ ] **提示文案是否写清楚？** 所有用户可见文案都在 PRD 中定义
- [ ] **数据结构是否合理？** 考虑扩展性，索引设计有说明
- [ ] **接口定义是否完整？** 参数/返回值/错误码/请求示例
- [ ] **验收标准是否可量化？** 有具体数字，不是模糊的"快/好/稳定"
- [ ] **页面状态是否完整？** 正常/加载中/空状态/错误/搜索无结果
- [ ] **术语是否规范？** 所有业务黑话首次出现时有定义

### 文档质量检查
- [ ] **结构完整性**：三层结构齐全，固定章节无遗漏
- [ ] **可视化达标**：每个业务模块至少包含 1 个状态机 + 1 个流程图 + 1 个规则表
- [ ] **链路闭环**：资金链路/状态链路/操作链路完整无断点
- [ ] **搜索可用**：搜索功能覆盖所有章节关键词
- [ ] **智能助手**：≥ 8 条快捷问题，回答可跳转对应章节
- [ ] **零报错**：浏览器 console 无 JS 报错，Mermaid 渲染正常

---

## 七、配色系统（CSS 变量）

### 1.1 固定章节（每个 PRD 必有）

#### 1.1.1 系统首页（#home）

- **定位**：项目的仪表盘入口，打开文档即看到项目全貌
- **必须包含**：
  - **Hero 区域**：深色渐变背景 + 项目名称 + 版本号 + 一句话描述
  - **统计卡片**：关键数据摘要（几个端 / 几个核心模块 / 几种角色），使用 `grid grid-cols-4 gap-6` 布局
  - **快速入口**：核心功能模块的快捷跳转按钮，使用卡片或按钮组
  - **核心规则摘要**：最重要的 3-5 条业务约束，使用列表展示
- **设计风格**：深色渐变 Hero（`from-slate-950 via-{primary-dark} to-{primary}`） + 白色卡片网格 + card-hover 悬停效果
- **HTML 模板骨架**：

```html
<section id="home" class="tab-content active">
  <div class="max-w-7xl mx-auto">
    <!-- Hero -->
    <div class="bg-gradient-to-br from-slate-950 via-{primary-dark} to-{primary} rounded-3xl p-12 text-white mb-8 relative overflow-hidden">
      <div class="absolute top-0 right-0 w-96 h-96 bg-{primary}/20 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2"></div>
      <div class="relative z-10 max-w-4xl">
        <div class="flex items-center gap-3 mb-4">
          <span class="px-3 py-1 bg-white/20 rounded-full text-sm font-medium">V{版本号}</span>
          <span class="px-3 py-1 bg-emerald-400/20 text-emerald-100 rounded-full text-sm">{阶段}</span>
        </div>
        <h2 class="text-4xl font-bold mb-4">{项目名称}产品需求文档</h2>
        <p class="text-xl text-{primary-light}/80 mb-8 leading-relaxed">{一句话描述}</p>
        <div class="flex flex-wrap gap-4">
          <button onclick="showSection('{核心模块id}')" class="px-6 py-3 bg-white text-slate-950 rounded-xl font-semibold hover:bg-white/90 transition">
            <i class="fas fa-{icon} mr-2"></i>{按钮文案}
          </button>
          <!-- 更多快速入口按钮 -->
        </div>
      </div>
    </div>
    <!-- 统计卡片 -->
    <div class="grid grid-cols-4 gap-6 mb-8">
      <!-- 每个卡片: bg-white rounded-2xl p-6 card-hover border border-gray-100 -->
    </div>
    <!-- 快速入口 / 核心规则摘要 -->
    <div class="grid grid-cols-3 gap-6">
      <!-- 三列卡片区域 -->
    </div>
  </div>
</section>
```

#### 1.1.2 用户研究（#user-research，每个 PRD 必有）

- **必须包含**：
  - **用户画像卡片**：每个画像一张卡片，`grid grid-cols-{n}` 布局
  - 每个卡片包含：
    - 头像占位（40×40 圆形渐变色 + 名字缩写）
    - 姓名 + 身份标签（如"大二学生·买家"）
    - 一句话描述（ta的核心需求和痛点）
    - 使用场景列表（3-5条）
    - 痛点列表（3-5条）
  - **用户故事表**（prd-table）：作为__（角色），我想__（功能），以便__（价值），优先级
  - **使用旅程**：最核心的一条端到端用户旅程，用 biz-flow 步骤图展示

- **画像数量规则**：
  - 单端项目：3-4 个画像
  - 多端项目：每个端至少 1 个画像，总数 4-6 个

- **HTML 示例骨架**：
```html
<div class="grid grid-cols-3 gap-6 mb-8">
  <div class="bg-white rounded-2xl p-6 border border-gray-100 card-hover">
    <div class="flex items-center gap-3 mb-4">
      <div class="w-10 h-10 rounded-full bg-gradient-to-br from-teal-400 to-teal-600 flex items-center justify-center text-white font-bold text-sm">张</div>
      <div>
        <div class="font-semibold">张三 <span class="text-xs bg-teal-100 text-teal-700 px-2 py-0.5 rounded-full">买家</span></div>
        <div class="text-xs text-gray-500">大二学生 · 计算机系</div>
      </div>
    </div>
    <p class="text-sm text-gray-600 mb-3">想在校园里低价买到二手教材和电子产品，预算有限，对商品真伪和质量很担心。</p>
    <div class="text-xs text-gray-400 space-y-1">
      <div>📱 睡前刷一刷有什么好货</div>
      <div>📚 开学季集中买教材</div>
      <div>💬 先跟卖家聊几句再决定</div>
    </div>
  </div>
</div>
```

#### 1.1.3 项目概述（#overview）

- **必须包含**：
  - 项目背景与目标（1-3 段文字）
  - 价值说明：按参与方（用户 / 商家 / 平台 等）展示，使用 `grid grid-cols-{n}` 卡片布局
  - 术语定义表（prd-table）：术语 | 定义 | 系统落点
  - 业务边界说明：当前范围（prd-tip）/ 需确认（prd-warn）/ 不在此版本（prd-error）

#### 1.1.4 系统架构（#architecture）

- **必须包含**：
  - 多端架构图：使用 biz-flow 的 biz-panorama 组件（每个端一张卡片，含图标+名称+定位描述）
  - 业务线全景图：用 biz-row + biz-node 组件展示核心业务线流向
  - 端侧说明表（prd-table）：端 | 定位 | 关键能力
  - 数据隔离原则列表
  - 关键集成表（prd-table）：集成方 | 能力 | 触发场景 | 注意事项

#### 1.1.5 多端项目特殊规则（≥3 端的项目）

当项目涉及多个终端（如用户端+骑手端+商家端+管理后台）时：

- **必须引用项目契约**：PRD 文档开头必须有 `> 本文档配合「项目契约」使用，数据模型/状态枚举/配色以契约为准`
- **跨端交互矩阵**：在系统架构章节末尾增加跨端交互表（prd-table：操作 | 端A | 端B | ... | 端N）
- **分端功能清单**：每个端独立一个 PRD 章节，格式按 §1.4 规范
- **共享实体引用**：业务模块章节引用共享数据实体时，标注"参见项目契约 §4.x"
- **一致性强制要求**：PRD 中出现的状态值、字段名必须与项目契约中的值**逐字一致**

### 1.2 角色与权限（#roles，按端数量动态生成）

- **角色定义表**（prd-table）：角色（status-tag） | 使用端 | 核心权限 | 数据范围
- **权限矩阵**（prd-table）：功能 | 角色1 | 角色2 | ... | 角色N（使用 √ / - / 标注）
- **多角色说明**：如有角色之间有特殊关系（如用户可同时拥有商家身份），需用 prd-warn 说明
- **入驻/开通流程**（可选）：使用 biz-swimlane 泳道图展示跨角色入驻协作

### 1.3 核心业务模块（按项目实际业务动态组装）

> Agent 分析 PM 需求后，识别核心业务实体，按"实体生命周期"组织章节。
> 不是每个项目都有"商品体系"或"会员"，完全按需组装。

#### 实体识别方法：

根据 PM 需求文本，提取核心名词实体（如：订单、商品、任务、帖子、会员、券等），每个核心实体生成一个独立章节。

#### 每个业务实体章节必须包含：

1. **状态机图**（biz-timeline 或 Mermaid stateDiagram 或 biz-state-ladder）
2. **流程图**（biz-flow）
3. **泳道图**（biz-swimlane 或 Mermaid sequenceDiagram）——展示跨角色协作
4. **规则表**（prd-table）——触发条件、规则、约束、注意事项
5. **核心提示**（prd-tip）
6. **边界/异常说明**（prd-warn / prd-error）
7. **至少 1 个完整示例**——用时间线表格或场景卡片展示端到端流程
8. **实体间关系图**（Mermaid ER 图）——多个实体有交互时，补充 ER 图

#### 常见业务类型参考（Agent 自动识别并匹配）：

| 类型 | 典型实体链路 | 适用行业 |
|------|------------|---------|
| 交易型 | 商品→订单→支付→退款→分账 | 电商/O2O/本地生活/交易平台 |
| 社交型 | 内容→发布→互动→推荐→消息 | 社交/社区/内容平台 |
| 工具型 | 任务→执行→通知→统计 | 效率工具/SaaS/管理系统 |
| 会员型 | 会员→权益→券→核销→结算 | 会员制/订阅制/积分体系 |
| 服务型 | 需求→匹配→履约→评价→结算 | 家政/出行/教育/咨询 |
| 资讯型 | 素材→审核→发布→分发→数据 | 媒体/资讯/短视频/博客 |

### 1.4 各端功能清单（按端数量动态生成）

每个端一个章节（如 #user-app、#store-app、#admin 等），必须包含：

- **功能概览**：该端的定位和核心能力卡片
- **页面与功能表**（prd-table）：页面 | 功能点 | 说明 | 校验规则
- **关键交互规则**：核心操作的交互流程和约束（用 biz-flow 展示）
- **校验规则列表**：表单校验、业务校验（用 prd-table）
- **数据来源/归属**：该端数据的来源和可见范围

### 1.5 全局业务规则（#rules，跨端通用规则总表）

按主题分组，每组一个卡片或表格：

- 交易规则（价格/促销/优惠）
- 退款规则（退款条件/审核流程/时效）
- 入驻规则（商家/供应商入驻条件和流程）
- 商品规则（发布/审核/上下架）
- 资金规则（支付/分账/结算/提现）
- 通知规则（消息推送场景和触发条件）
- 数据规则（数据隔离/导出/保留）

### 1.6 订阅消息推送（#subscription-msg，如有消息通知需求）

- 消息场景表（prd-table）：消息类型 | 触发条件 | 推送内容模板 | 接收角色 | 备注
- 推送渠道说明（微信订阅消息 / 短信 / 站内信）
- 用户授权流程

### 1.7 定时任务（#jobs，如有自动化任务）

- 任务列表表（prd-table）：任务名称 | 触发条件 | 执行频率 | 执行逻辑 | 失败处理
- 幂等性说明
- 监控和告警规则

### 1.8 数据看板指标（#dashboard-metrics，如有后台管理端）

- 指标表（prd-table）：指标名称 | 定义 | 数据来源 | 展示位置 | 计算公式
- 按角色分组：运营看板 / 财务看板 / 商家看板
- 核心指标（GMV / 订单量 / 用户数等）

### 1.9 原型与UI（#prototypes，每个 PRD 必有）

- **必须包含**：该项目的所有原型和 UI 设计稿链接卡片
- **布局**：`grid grid-cols-2 gap-6`（或按端数量调整列数）
- **每个卡片包含**：
  - 图标区域（w-14 h-14 圆角卡片，带语义色背景）
  - 标题（端名称，如"管理端原型"/"用户端原型"/"UI 设计稿"）
  - 副标题（工具名 + 端类型，如"即时设计 · PC 管理后台"）
  - 描述文字（关键页面列表，1-2 行）
  - 打开按钮（带箭头的彩色按钮）
- **原型卡片色系**：
  - 管理端原型：紫色（bg-purple-100 / text-purple-600）
  - 用户端原型：绿色（bg-green-100 / text-green-600）
  - 门店端/其他端：橙色/青色等
  - UI 设计稿：粉色（bg-pink-100 / text-pink-600），col-span-2
- **底部提示**：`<div class="mt-8 prd-tip">需求评审时以本文档规则为准，以原型确认页面路径、交互层级和视觉布局。若原型与本文档规则存在冲突，需在评审纪要中确认最终口径后再进入开发。</div>`
- **无原型链接时**：卡片中 placeholder 展示，按钮文字改为"待补充"，链接为 `javascript:void(0)`

### 1.10 错误码规范（#error-codes，统一错误码表）

- 错误码表（prd-table）：错误码 | 错误类型 | 错误描述 | 触发场景 | 处理建议
- 编码规则说明（如：BIZ-001 ~ BIZ-099 业务错误，PAY-001 ~ PAY-099 支付错误，SYS-001 ~ SYS-099 系统错误）
- 前端错误提示映射

### 1.11 测试验收（#testing）

- **验收标准表**（prd-table）：验收项 | 通过标准
- **核心链路测试**列表：按模块列出核心测试路径（≥6 条）
- **异常场景测试**列表：边界情况/失败场景（≥4 条）
- **性能/兼容性要求**（可选）

---

## 二、配色系统（CSS 变量，每次生成时按项目调性设置）

> 主色由 Agent 根据项目类型自动推荐，PM 确认后写入 CSS 变量。
> 语义色、文字色、背景色、圆角、阴影为固定值，不做调整。

```css
:root {
  /* ===== 主色 — 每次按项目品牌色设置 ===== */
  --prd-primary: {{主色}};         /* 如 #2563eb(蓝)、#7c3aed(紫)、#059669(绿)、#ea580c(橙) */
  --prd-primary-dark: {{主色深}};   /* 主色加深 15%，用于渐变终点 */
  --prd-primary-light: {{主色浅}};   /* 主色加亮 20%，用于低饱和度场景 */
  --prd-primary-bg: {{主色背景}};   /* 主色 10% 透明度背景，用于 tip 组件 */

  /* ===== 语义色 — 固定不变 ===== */
  --prd-success: #22c55e;
  --prd-success-bg: #f0fdf4;
  --prd-warning: #f59e0b;
  --prd-warning-bg: #fffbeb;
  --prd-error: #ef4444;
  --prd-error-bg: #fef2f2;
  --prd-info: #3b82f6;
  --prd-info-bg: #eff6ff;

  /* ===== 文字 ===== */
  --prd-text-1: #0f172a;       /* 标题/正文主色 */
  --prd-text-2: #475569;       /* 次要文字/表头 */
  --prd-text-3: #94a3b8;       /* 辅助说明/占位符 */
  --prd-text-4: #cbd5e1;       /* 禁用/边框装饰 */

  /* ===== 背景 ===== */
  --prd-bg: #f8fafc;            /* 页面整体背景 */
  --prd-card: #ffffff;         /* 卡片/内容块背景 */
  --prd-border: #e2e8f0;        /* 主边框色 */
  --prd-border-light: #f1f5f9;  /* 浅边框/表格行分隔 */

  /* ===== 圆角 ===== */
  --prd-r-sm: 6px;              /* 标签/小按钮 */
  --prd-r-md: 12px;             /* 提示框/表头装饰 */
  --prd-r-lg: 16px;             /* 时间线容器/流程图容器 */
  --prd-r-xl: 20px;             /* 卡片/泳道图/流程图 */
  --prd-r-2xl: 28px;            /* Hero 区域 */

  /* ===== 阴影 ===== */
  --prd-shadow-sm: 0 1px 3px rgba(0,0,0,0.06);
  --prd-shadow-md: 0 4px 16px rgba(0,0,0,0.08);
  --prd-shadow-lg: 0 12px 40px rgba(0,0,0,0.12);
}
```

### 配色方案参考表（Agent 自动推荐）

| 行业/调性 | 主色 | 深色 | 浅色 | 背景 |
|-----------|------|------|------|------|
| 商务/企业 | #2563eb | #1d4ed8 | #60a5fa | #eff6ff |
| 金融/理财 | #059669 | #047857 | #34d399 | #ecfdf5 |
| 生活/社交 | #7c3aed | #6d28d9 | #a78bfa | #f5f3ff |
| 电商/交易 | #ea580c | #c2410c | #fb923c | #fff7ed |
| 高端/奢华 | #1e293b | #0f172a | #475569 | #f8fafc |
| 健康/医疗 | #0891b2 | #0e7490 | #22d3ee | #ecfeff |
| 教育/知识 | #4f46e5 | #4338ca | #818cf8 | #eef2ff |
| 工具/效率 | #0ea5e9 | #0284c7 | #38bdf8 | #f0f9ff |

> Agent 判断项目类型后，自动匹配配色方案并输出给 PM 确认。PM 也可自定义任何主色值。

---

## 三、CSS 组件规范（对标 index.html 实际代码）

> 以下组件代码必须从 index.html 实际样式中提取，保证视觉一致性。
> Agent 生成 PRD 时，直接复用这些 CSS class。

### 3.1 基础布局

```css
/* 侧边栏 */
aside { position: fixed; left: 0; top: 64px; bottom: 0; width: 18rem; background: #fff; border-right: 1px solid var(--prd-border); overflow-y: auto; z-index: 40; }
aside::-webkit-scrollbar { width: 4px; }
aside::-webkit-scrollbar-thumb { background: var(--prd-text-4); border-radius: 2px; }

/* 主内容 */
main { flex: 1; margin-left: 18rem; padding: 2rem; }

/* 顶部导航 */
header { position: fixed; top: 0; left: 0; right: 0; background: rgba(255,255,255,0.95); backdrop-filter: blur(12px); border-bottom: 1px solid var(--prd-border); z-index: 50; }
```

### 3.2 导航与交互

```css
/* 侧边栏分组 */
.sidebar-group-title { font-size: 11px; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; }
.sidebar-item { transition: all 0.2s ease; border-radius: 8px; padding: 10px 16px; font-size: 14px; }
.sidebar-item:hover { background: rgba(var(--prd-primary-rgb), 0.1); }
.sidebar-item.active { background: rgba(var(--prd-primary-rgb), 0.15); border-right: 3px solid var(--prd-primary); }

/* Tab 切换 */
.tab-content { display: none; }
.tab-content.active { display: block; animation: fadeIn 0.25s ease; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }

/* 章节标题 */
.section-title { font-size: 30px; font-weight: 800; color: var(--prd-text-1); margin-bottom: 6px; }
.section-subtitle { color: #64748b; margin-bottom: 28px; }
```

### 3.3 prd-table（需求表格）

```css
.prd-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}
.prd-table thead th {
  background: #f8fafc;
  font-weight: 700;
  color: #475569;
  padding: 12px 14px;
  text-align: left;
  border-bottom: 2px solid #e2e8f0;
  font-size: 13px;
  white-space: nowrap;
}
.prd-table tbody td {
  padding: 11px 14px;
  border-bottom: 1px solid #f1f5f9;
  vertical-align: top;
  line-height: 1.65;
}
.prd-table tbody tr:hover { background: #f8fafc; }
```

- 全宽、无边框外框
- 表头 `#f8fafc` 背景、深色加粗（#475569）、底部 2px 边框（#e2e8f0）
- 行悬停背景 `#f8fafc`
- 单元格垂直对齐 top、行高 1.65

### 3.4 biz-flow（业务流程图）

```css
.biz-flow {
  background: linear-gradient(180deg, #f8fafc 0%, #ffffff 60%);
  border-radius: 20px;
  padding: 28px 32px 20px;
  overflow-x: auto;
  border: 1px solid #e2e8f0;
}
.biz-flow-title { font-size: 15px; font-weight: 700; color: #475569; margin-bottom: 20px; display: flex; align-items: center; gap: 8px; }
```

**节点配色**（必须支持以下全部颜色 class）：

| class | 渐变 | 文字色 |
|-------|------|--------|
| `.biz-node.blue` | #3b82f6 → #2563eb | #fff |
| `.biz-node.light-blue` | #60a5fa → #3b82f6 | #fff |
| `.biz-node.dark-blue` | #1e40af → #1e3a8a | #fff |
| `.biz-node.sky` | #7dd3fc → #38bdf8 | #0c4a6e |
| `.biz-node.green` | #22c55e → #16a34a | #fff |
| `.biz-node.red` | #ef4444 → #dc2626 | #fff |
| `.biz-node.orange` | #f97316 → #ea580c | #fff |
| `.biz-node.purple` | #a855f7 → #7c3aed | #fff |
| `.biz-node.gray` | #f1f5f9 → #e2e8f0 | #475569（带 1px #cbd5e1 边框） |

**箭头组件**：

- `.biz-arrow` — 实线箭头（水平连接）
- `.biz-arrow.long` — 长距离实线箭头（width: 48px）
- `.biz-dash-down` — 虚线向下分支箭头
- `.biz-dash-h` — 虚线水平箭头
- `.biz-label` — 分支条件标签（11px 灰色背景小标签）
- `.biz-step` — 步骤编号圆圈（白色半透明，18px）
- `.biz-note` — 流程图底部备注（12px 灰色）

**全景图组件** `.biz-panorama`：

- `grid grid-cols-{n} gap-4`，每个端一张卡片
- 卡片含图标（44px 圆角方块）+ 名称 + 描述
- 颜色按端区分（用户=green，门店=orange，供应商=cyan，后台=purple）

### 3.5 biz-timeline（状态时间线）

```css
.biz-timeline-wrap {
  background: #f8fafc;
  border-radius: 16px;
  padding: 20px 24px;
  border: 1px solid #e2e8f0;
}
.biz-timeline {
  display: grid;
  gap: 0;
  padding: 8px 0 16px;
  overflow-x: auto;
  min-width: max-content;
}
.biz-timeline.c4 { grid-template-columns: repeat(4, 1fr); }
.biz-timeline.c5 { grid-template-columns: repeat(5, 1fr); }
.biz-timeline.c6 { grid-template-columns: repeat(6, 1fr); }
```

**节点圆点** `.biz-tl-dot`（30px 圆形，渐变色）：

| class | 颜色 | 用途 |
|-------|------|------|
| `.gray` | #cbd5e1 | 未到达/禁用状态 |
| `.blue` | #3b82f6 → #2563eb | 进行中/可操作状态 |
| `.green` | #22c55e → #16a34a | 已完成/成功状态 |
| `.red` | #ef4444 → #dc2626 | 异常/失败/取消状态 |
| `.orange` | #f97316 → #ea580c | 警告/待处理状态 |

**连接线**：每个 `.biz-tl-item::after` 从圆点中心延伸到下一节点
- completed 节点连线：绿色渐变
- current 节点连线：蓝色渐变 + `.pulse` 呼吸动画
- danger 节点连线：红色渐变

**分支节点** `.biz-tl-branch`：虚线向下延伸 + 22px 小圆点 + 标签

### 3.6 biz-state-ladder（阶梯式状态图）

> 适用于状态流转有回退/循环的场景（如商品上下架、审核驳回等）。

```css
.biz-ladder-wrap {
  background: #f8fafc;
  border-radius: 16px;
  padding: 20px 24px;
  border: 1px solid #e2e8f0;
}
.biz-ladder-card {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border-radius: 12px;
  font-size: 13px;
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
```

- 阶梯连接：`.biz-ladder-arrow`（垂直线+水平箭头+方向可逆）
- 回退箭头：`.biz-ladder-back`（虚线从右向左）
- 节点配色同 biz-node 系列

### 3.7 biz-swimlane（泳道图）

```css
.biz-swimlane {
  background: linear-gradient(180deg, #f8fafc 0%, #ffffff 60%);
  border-radius: 20px;
  padding: 24px 28px;
  border: 1px solid #e2e8f0;
  overflow-x: auto;
  min-width: max-content;
}
```

**角色泳道** `.sw-lane`：

- `.sw-lane-label` — 角色标签（120px 宽，含 28px 头像 + 文字）
- `.sw-lane-body` — 节点序列区域

**节点颜色区分角色**（Agent 根据项目角色动态选择颜色）：

| 角色类型 | 颜色 class | 头像背景 |
|---------|-----------|---------|
| 用户/C端 | `.sw-node.blue` | blue 渐变 |
| 系统/平台 | `.sw-node.purple` | purple 渐变 |
| 门店/服务方 | `.sw-node.orange` | orange 渐变 |
| 供应商/第三方 | `.sw-node.sky` | cyan 浅色 |
| 外部/支付 | `.sw-node.green` | green 渐变 |
| 中性/等待 | `.sw-node.gray` | gray 渐变 |

**连接组件**：
- `.sw-arrow` — 实线连接箭头
- `.sw-arrow.green` — 绿色连接（表示成功/完成）
- `.sw-dash-arrow` — 虚线分支箭头
- `.sw-trigger` — 跨泳道触发标注
- `.sw-reject-branch` — 驳回/回退分支（红色）
- `.sw-note` — 泳道图底部注释（12px 灰色圆角块）
- `.sw-step-num` — 步骤序号标记（绝对定位在节点上方）

### 3.8 mermaid-wrapper（图表容器）

```css
.mermaid-wrapper {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 18px;
  padding: 28px 24px;
  margin-bottom: 24px;
  overflow-x: auto;
}
.mermaid-wrapper .mermaid-title {
  font-size: 14px;
  font-weight: 700;
  color: #64748b;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}
```

### 3.9 status-tag（状态标签）

```css
.status-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}
```

- 使用 Tailwind 语义色：`bg-{color}-100 text-{color}-700`
- 常用配色：green（完成）/ blue（进行中）/ orange（待处理）/ red（异常）/ purple（特殊）

### 3.10 prd-tip / prd-warn / prd-error（提示框）

```css
.prd-tip {
  background: #eff6ff;
  border-left: 4px solid #2563eb;
  padding: 14px 18px;
  border-radius: 0 12px 12px 0;
  font-size: 14px;
  color: #1e40af;
  line-height: 1.8;
}
.prd-warn {
  background: #fffbeb;
  border-left: 4px solid #f59e0b;
  padding: 14px 18px;
  border-radius: 0 12px 12px 0;
  font-size: 14px;
  color: #92400e;
  line-height: 1.8;
}
.prd-error {
  background: #fef2f2;
  border-left: 4px solid #ef4444;
  padding: 14px 18px;
  border-radius: 0 12px 12px 0;
  font-size: 14px;
  color: #991b1b;
  line-height: 1.8;
}
```

- 左侧 4px 色条 + 浅色背景 + 右侧圆角 12px
- 蓝色=tip（提示/原则）、橙色=warn（警告/注意）、红色=error（错误/禁止）

### 3.11 card-hover（卡片悬停效果）

```css
.card-hover { transition: all 0.25s ease; }
.card-hover:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 36px rgba(15, 23, 42, 0.1);
}
```

### 3.12 其他辅助样式

```css
/* 代码片段 */
code { background: #f1f5f9; padding: 2px 6px; border-radius: 6px; color: #334155; }

/* 装饰性状态标签 */
.state-pill {
  display: inline-flex;
  align-items: center;
  padding: 6px 14px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 700;
  border: 1px solid #bfdbfe;
  background: #eff6ff;
  color: #1d4ed8;
  white-space: nowrap;
}
```

---

## 四、可视化规范

### 4.1 每个业务模块必须包含的可视化元素

| 元素 | 推荐组件 | 说明 |
|------|---------|------|
| 状态机 | biz-timeline / biz-state-ladder / Mermaid stateDiagram | 展示实体所有状态及流转路径 |
| 流程图 | biz-flow | 展示核心操作流程（从用户触发到最终结果） |
| 泳道图 | biz-swimlane / Mermaid sequenceDiagram | 展示跨角色协作时序 |
| 规则表 | prd-table | 展示触发条件、业务规则、约束、注意事项 |
| 核心提示 | prd-tip | 展示该模块最重要的 1-3 条原则 |
| 完整示例 | 时间线表格 / 场景卡片 | 展示一个端到端的完整业务场景 |

### 4.2 复杂规则展示方式

- **分支场景**：用彩色卡片区分，每个分支用 `.p-5 bg-{color}-50 rounded-xl border border-{color}-100` 包裹
- **金额计算**：用网格卡片展示，`.grid grid-cols-4 gap-4`，每个卡片展示一项金额明细
- **对比分析**：用双列或三列布局 `.grid grid-cols-2 gap-6`
- **条件分支**：用 biz-flow 的 branch 模式 + biz-dash-down + biz-label

### 4.3 Mermaid 使用规范

```javascript
// 初始化配置（固定不变）
mermaid.initialize({
  startOnLoad: false,        // 不在页面加载时渲染，按需渲染
  theme: 'neutral',
  securityLevel: 'loose',
  flowchart: { useMaxWidth: true, htmlLabels: true, curve: 'basis' },
  stateDiagram: { useMaxWidth: true }
});

// 渲染时机：用户切换到对应 tab 时
async function showSection(id) {
  // ...切换 section...
  // 渲染当前可见区域的 Mermaid 图表
  const mermaidBlocks = section.querySelectorAll('pre.mermaid');
  for (const block of mermaidBlocks) {
    if (block.querySelector('svg')) continue;
    const id = 'mermaid-' + Math.random().toString(36).substr(2, 9);
    const { svg } = await mermaid.render(id, block.textContent);
    block.innerHTML = svg;
  }
}
```

- 每个图表用 `.mermaid-wrapper` 容器包裹（白色背景、圆角 18px、1px 边框、标题行含图标+文字）
- 决策节点用菱形 `{条件}`
- 起止节点用圆角 `(["描述"])`
- 节点使用 `:::classDef` 统一配色

### 4.5 布局铁律（防止 header 遮挡内容）

> 这是经过实际验证的布局方案，必须严格遵守，否则部分页面内容会被 fixed header 遮挡。

#### 布局结构

```
body
  └── header (fixed, top:0, 高度约80px, z-index:50)
  └── 主体容器 (padding-top:80px, height:100vh, overflow:hidden)
      └── aside (fixed, top:80px, bottom:0, 独立滚动)
      └── main (flex:1, overflow-y:auto, height:calc(100vh-80px), 独立滚动)
```

#### CSS 要求

```css
/* 全局滚动补偿 */
* { scroll-behavior: smooth; scroll-padding-top: 80px; }

/* header 高度由内容决定（约80px），不显式设置 height */
header { position: fixed; top: 0; left: 0; right: 0; z-index: 50; }

/* 主体容器：固定视口高度，禁止自身滚动 */
/* 使用 inline style 确保 Tailwind CDN 不会忽略任意值 */
/* padding-top:80px; height:100vh; overflow:hidden; */

/* aside：从 header 底部开始 */
aside { position: fixed; top: 80px; bottom: 0; overflow-y: auto; }

/* main：独立滚动区域 */
main { flex: 1; overflow-y: auto; height: calc(100vh - 80px); }
```

#### JS 要求

Tab 切换时，**必须滚动 main 元素**，而不是 window：

```javascript
// 正确 ✅
var mainEl = document.querySelector('main');
if (mainEl) mainEl.scrollTop = 0;
document.documentElement.scrollTop = 0;
document.body.scrollTop = 0;

// 错误 ❌ — 会导致部分页面被 header 遮挡
window.scrollTo({ top: 0, behavior: 'smooth' });
```

#### 关键原则

| 原则 | 说明 |
|------|------|
| 不用 Tailwind 任意值做偏移 | `pt-[68px]` 等任意值可能不被 CDN 编译，用 inline style 代替 |
| main 必须独立滚动 | `overflow-y:auto` + 固定高度，否则长内容会撑开 body 导致布局错乱 |
| scrollTo 目标是 main | `window.scrollTo` 无法控制 main 内部滚动位置 |
| header 高度不用硬编码 CSS | 由内容自然撑开（py-3 + 内容），用 80px 安全值做偏移 |

---

## 五、交互规范

### 5.1 左侧导航

- 固定宽度 `18rem`，固定在页面左侧
- 按「项目概览 / 核心业务 / 端功能 / 规则与运营 / 测试验收」分组
- 分组标题样式：`text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2`
- 活跃项样式：背景色 + 右侧 3px 主色边框
- 导航图标使用 Font Awesome 6，每个图标宽度 `w-5 text-center`
- 滚动条自定义样式（4px 宽、圆角、#cbd5e1 颜色）

### 5.2 Tab 切换

- `showSection(id)` 函数切换 active class
- 切换时淡入动画（fadeIn 0.25s ease）
- 切换后自动滚动到页面顶部（`window.scrollTo({ top: 0, behavior: 'smooth' })`）
- 切换时渲染当前 section 的 Mermaid 图表（按需渲染，`startOnLoad: false`）

### 5.3 智能助手

- **位置**：右下角固定定位
- **触发按钮**：60px 圆形，渐变色背景（primary → cyan），呼吸动画（robotBreath + robotPulse）
- **聊天窗口**：380px × 520px，白色背景，圆角 18px，阴影 48px
- **头部**：渐变色（与按钮同色），标题 + 关闭按钮
- **消息区**：#f8fafc 背景，自定义滚动条
- **消息气泡**：
  - 机器人：白色背景 + 1px 边框，左上角直角（border-top-left-radius: 4px）
  - 用户：渐变色背景 + 白色文字，右上角直角
- **打字动画**：3 个灰色圆点 bounce 动画（typingBounce 1.2s）
- **快捷问题**：8 个标签按钮，pill 样式（rounded-full），hover 变主色
- **知识库**：
  - 关键词匹配 + 同义词扩展
  - 回答附带「查看相关章节」链接（使用 `goto` 字段跳转）
  - 数量按需：简单项目 8-12 条，复杂项目 15-20 条

### 5.4 顶部搜索

- **搜索框**：220px 宽，聚焦时展开到 280px，边框变主色 + 3px 主色 focus 光晕
- **搜索图标**：左侧绝对定位，12px 灰色
- **搜索按钮**：右侧 26px 方形按钮，hover 变主色
- **搜索结果**：下拉框，12px 圆角，最多展示 6 个结果
- **搜索算法**：章节索引 + 关键词评分匹配
  - 标题完全匹配 +30 分
  - 关键词包含 +15 分
  - 关键词被包含 +10 分
  - 按分数降序排列
- **无结果**：显示引导文案 + 「试试问智能助手」链接（自动打开助手并填入问题）

### 5.5 顶部导航栏

- 固定在顶部，白色半透明背景 + 毛玻璃效果（backdrop-blur-md）
- 左侧：项目图标（44px 圆角方块 + 渐变色）+ 项目名称 + 版本描述
- 右侧：搜索框 + 智能助手按钮 + 更新时间

---

## 六、技术依赖（CDN）

所有 PRD HTML 统一使用以下 CDN 资源，Agent 生成时直接引用：

```
Tailwind CSS:    https://cdn.tailwindcss.com
Font Awesome 6:  https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css
Google Fonts:    https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;700;900&display=swap
Mermaid 10:      https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js
```

- 字体：Noto Sans SC（全局 font-family）
- 图标：Font Awesome 6（所有功能模块配图标）
- Tailwind：使用 CDN 版本，不本地安装
- Mermaid：v10 版本，`startOnLoad: false`

---

## 七、HTML 模板规范

### 7.1 章节容器模板

```html
<section id="{section-id}" class="tab-content">
  <div class="max-w-6xl mx-auto">
    <h2 class="section-title">{章节中文标题}</h2>
    <p class="section-subtitle">{English Subtitle}</p>
    <!-- 内容区域 -->
  </div>
</section>
```

### 7.2 规则表格模板

```html
<div class="bg-white rounded-2xl p-8 border border-gray-100 mb-6">
  <h3 class="text-xl font-bold mb-4 flex items-center gap-2">
    <i class="fas fa-{icon} text-{color}-600"></i>{表格标题}
  </h3>
  <div class="overflow-hidden rounded-xl border border-slate-100">
    <table class="prd-table">
      <thead><tr><th>列1</th><th>列2</th><th>列3</th></tr></thead>
      <tbody>
        <tr><td>数据</td><td>数据</td><td>数据</td></tr>
      </tbody>
    </table>
  </div>
</div>
```

### 7.3 提示框模板

```html
<div class="prd-tip mb-6">
  <strong>核心原则：</strong>说明文字
</div>
<div class="prd-warn mb-6">
  <strong>注意事项：</strong>说明文字
</div>
<div class="prd-error mb-6">
  <strong>禁止事项：</strong>说明文字
</div>
```

### 7.4 卡片组模板

```html
<!-- 两列 -->
<div class="grid grid-cols-2 gap-6 mb-6">
  <div class="bg-white rounded-2xl p-6 border border-gray-100">
    <!-- 内容 -->
  </div>
  <div class="bg-white rounded-2xl p-6 border border-gray-100">
    <!-- 内容 -->
  </div>
</div>

<!-- 三列 -->
<div class="grid grid-cols-3 gap-6 mb-6">
  <div class="bg-white rounded-2xl p-6 border border-gray-100 card-hover">
    <!-- 图标 + 标题 + 内容 -->
  </div>
</div>

<!-- 四列统计卡片 -->
<div class="grid grid-cols-4 gap-6 mb-8">
  <div class="bg-white rounded-2xl p-6 card-hover border border-gray-100">
    <div class="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center mb-4">
      <i class="fas fa-{icon} text-blue-600 text-xl"></i>
    </div>
    <div class="text-3xl font-bold text-gray-900">{数字}</div>
    <div class="text-sm text-gray-500">{说明}</div>
  </div>
</div>
```

---

## 八、质量门禁（PRD 专项，交付前自检）

Agent 生成 PRD HTML 后，交付前必须逐项自检以下清单：

- [ ] **结构完整性**：固定章节齐全（首页/概述/架构/角色权限），业务模块按实际需求覆盖无遗漏
- [ ] **术语规范**：所有业务黑话首次出现时有定义（术语表中可查）
- [ ] **可视化达标**：每个业务模块至少包含 1 个状态机 + 1 个流程图 + 1 个泳道图
- [ ] **示例充分**：每个复杂规则至少有 1 个完整时间线示例或场景卡片
- [ ] **链路闭环**：资金链路（支付→退款→分账→结算）、状态链路（创建→流转→完结）、操作链路（用户触发→系统处理→结果反馈）完整无断点
- [ ] **全局规则**：跨端规则集中在「全局业务规则」章节，无遗漏
- [ ] **错误码完整**：统一错误码表，覆盖所有异常场景，编码规则一致
- [ ] **测试用例充足**：核心链路 ≥ 6 条测试路径，异常场景 ≥ 4 条
- [ ] **搜索可用**：搜索功能覆盖所有章节关键词，sectionIndex 与实际章节一致
- [ ] **智能助手**：≥ 8 条快捷问题，回答可跳转对应章节（goto 字段有效）
- [ ] **配色一致**：使用 CSS 变量，主色与项目调性一致，语义色/文字色/背景色使用标准值
- [ ] **零报错**：浏览器 console 无 JS 报错，Mermaid 渲染正常，Tab 切换流畅

---

## 九、Agent 生成 PRD 工作流

### Step 1：分析需求

- 读取 PM 提供的需求描述
- 识别项目类型（电商/SaaS/O2O/社交/工具/会员/服务/资讯）
- 提取核心业务实体（订单/商品/任务/内容/会员等）
- 识别参与角色和端数量
- 识别业务关系类型（交易型/社交型/工具型/会员型/服务型）

### Step 2：输出《PRD 章节规划表》

格式示例：

| 章节类型 | 章节名称 | 章节ID | 说明 |
|---------|---------|--------|------|
| 固定 | 系统首页 | home | Hero + 统计 + 快速入口 |
| 固定 | 项目概述 | overview | 背景/价值/术语/边界 |
| 固定 | 系统架构 | architecture | 端架构/技术栈/集成 |
| 固定 | 角色权限 | roles | 3个角色 + 权限矩阵 |
| 业务 | {实体1名称} | {entity1} | 状态机+流程图+泳道图+规则表 |
| 业务 | {实体2名称} | {entity2} | ... |
| ... | ... | ... | ... |
| 功能 | {端1名称} | {app1} | 页面/功能/交互/校验 |
| 功能 | {端2名称} | {app2} | ... |
| 规则 | 全局业务规则 | rules | 按主题分组的跨端规则 |
| 规则 | 订阅消息推送 | subscription-msg | 消息场景和模板 |
| 规则 | 定时任务 | jobs | 自动化任务列表 |
| 数据 | 数据看板指标 | dashboard-metrics | 后台看板指标定义 |
| 规范 | 错误码规范 | error-codes | 统一错误码表 |
| 验收 | 测试验收 | testing | 验收标准+测试用例 |

等待 PM 确认。

### Step 3：输出《配色方案推荐》

根据项目类型自动匹配配色，格式示例：

> 根据您的项目类型（电商/交易），推荐以下配色方案：
>
> | 项目 | 值 |
> |------|-----|
> | 主色 | #ea580c |
> | 深色 | #c2410c |
> | 浅色 | #fb923c |
> | 背景 | #fff7ed |
> | 调性 | 电商/交易 |
>
> 如需自定义主色，请提供色值。

等待 PM 确认。

### Step 4：生成 PRD HTML（模板注入模式）

> **核心原则：Agent 不从头写整个 HTML，而是读取模板骨架，只生成变化的部分。**
> 这样可以节省 40-50% token，且 CSS/JS 基础设施质量有保障。

#### 4.1 读取模板骨架

```
读取路径：templates/prd-template.html
```

模板中约 70% 是固定骨架（CSS 960行 + JS 300行 + HTML结构 200行），Agent **禁止修改**这些部分。

#### 4.2 替换 CSS 变量（4 个主色值）

找到模板中的 `/* ===== Agent: 替换以下 4 个主色值 ===== */` 标记，替换：

| 变量 | 说明 | 示例（校园/teal） |
|------|------|-------------------|
| `--prd-primary` | 主色 | #0d9488 |
| `--prd-primary-dark` | 主色深 | #0f766e |
| `--prd-primary-light` | 主色浅 | #2dd4bf |
| `--prd-primary-bg` | 主色背景 | #f0fdfa |

同时替换 `--chat-primary` 对应的颜色（如果 chat 渐变色中有硬编码主色）。

#### 4.3 替换文本占位符

| 占位符 | 替换为 | 出现位置 |
|--------|--------|----------|
| `{{项目名称}}` | 实际项目名 | title、header、home Hero |
| `{{版本号}}` | V1.0 等 | title、header、home Hero |
| `{{阶段}}` | MVP / 内测 / 正式版 | home Hero |
| `{{项目描述}}` | 一句话描述 | home Hero |
| `{{更新日期}}` | YYYY-MM-DD | header 右侧 |

#### 4.4 生成 sidebar 导航

找到 `<!-- Agent:NAV_START -->` 和 `<!-- Agent:NAV_END -->`，替换中间内容。

按 Step 2 确认的章节规划，生成分组标题 + 导航项：
```html
<!-- Agent:NAV_START -->
<div style="padding:12px 16px 6px;font-size:11px;font-weight:700;color:#94a3b8;...">📋 项目概览</div>
<a href="#home" class="sidebar-item active ..." onclick="showSection('home')">
  <i class="fas fa-home w-5 text-center text-{主色}-600"></i><span>系统首页</span>
</a>
...
<!-- Agent:NAV_END -->
```

#### 4.5 生成各 section 内容（核心工作）

找到 `<!-- Agent:SECTION_START -->` 和 `<!-- Agent:SECTION_END -->`，替换中间内容。

这是 Agent **唯一需要发挥创造力的部分**。每个 section 必须按第三章「文档结构」的要求编写：
- 固定章节：首页（Hero+统计+入口）、概述（背景+术语+边界）、架构（端架构+全景图）
- 业务章节：状态机 + 流程图 + 泳道图 + 规则表 + 示例
- 功能章节：页面功能表 + 交互规则 + 校验规则
- 规则/测试章节：规则表 + 错误码 + 测试用例

#### 4.6 填充数据数组（关键：只替换数组，不碰函数）

找到 `// Agent:DATA_START` 和 `// Agent:DATA_END`，**只替换数据数组内容**，不得删除或修改标记之间的任何函数定义。

模板已将基础设施函数（doSearch / findAnswer / expandSynonyms）移至 DATA_END 之后，Agent 注入数据时**禁止覆盖这些函数**。

| 数组 | 注入标记 | 最少条数 | 说明 |
|------|---------|---------|------|
| `sectionIndex` | `Agent:SEARCH_DATA_START` ~ `SEARCH_DATA_END` | = 章节数 | 每个章节的 id + title + keywords |
| `knowledgeBase` + `synonymMap` | `Agent:DATA_START` ~ `DATA_END` | ≥ 10 | 智能助手问答 + 同义词映射 |

**🔴 绝对禁止**：
- 删除 DATA_START/END 标记本身
- 删除标记之间的任何函数（doSearch / findAnswer）
- 将函数定义放入 DATA_START/END 之间

#### 4.7 禁止修改清单

以下部分在模板中已完善，Agent **不得重写或修改**：

- ❌ 所有 `<style>` 中的 CSS（960+ 行组件库）
- ❌ header / chat-widget / chat-window 的 HTML 结构
- ❌ showSection / doSearch / findAnswer / ScrollSpy / 智能助手的 JS 逻辑
- ❌ 主体容器的布局样式（padding-top:80px / height:100vh / overflow）
- ❌ Mermaid 初始化配置
- ❌ CDN 依赖链接

#### 4.8 PRD ↔ 原型联动（同项目联合生成时）

当 Agent 同时生成 PRD 和原型时，必须遵守以下联动规则：

**1. 章节标注**
PRD 的每个主要功能章节末尾增加原型链接标注：
> 详见「管理后台原型」→ 商品管理（/goods）

**2. 术语一致性**
PRD 中出现的功能模块名称必须与原型侧边栏导航名称完全一致。

**3. 数据结构一致性**
PRD 中的数据模型（字段名、状态值枚举）必须与原型中的示例数据保持一致。例如：
- PRD 中定义订单状态为 `pending/done/cancelled` → 原型中表格的 status 标签也必须使用这 3 个值
- PRD 中分类使用 `电子产品/学习资料/生活用品` → 原型中的筛选下拉和表格数据也要对应

**4. 配色一致性**
PRD 文档的强调色（--accent）必须与原型的主色一致（使用同一套颜色变量值）。

### Step 5：自检质量门禁

逐项检查第八章「质量门禁」清单，不达标项修复后重新检查。

### Step 6：交付

输出 PRD HTML 文件，告知 PM 检查结果和章节结构概览。

---

## 十、无障碍基本原则

原型面向演示和开发沟通，但应保持基础无障碍意识：

- 触摸目标最小 44×44px（按钮、可点击区域）
- 文字与背景的对比度 ≥ 3:1
- 不使用颜色作为唯一的信息区分手段（配图标或文字）
- 可交互元素有清晰的视觉边界
- 表格支持横向滚动（overflow-x: auto）
- 图表区域可横向滚动，不溢出容器

---

## 附录：index.html 组件速查表

> 以下为 index.html 中所有自定义 CSS 组件的 class 速查，Agent 生成时直接复用。

| 组件 | class | 用途 |
|------|-------|------|
| 需求表格 | `.prd-table` | 规则表/定义表/验收表 |
| 业务流程图 | `.biz-flow` + `.biz-row` + `.biz-node.{color}` + `.biz-arrow` | 操作流程展示 |
| 全景图 | `.biz-panorama` + `.biz-panorama-card` | 多端/多角色概览 |
| 状态时间线 | `.biz-timeline-wrap` + `.biz-timeline.c{n}` + `.biz-tl-item` + `.biz-tl-dot.{color}` | 订单/任务状态机 |
| 阶梯状态图 | `.biz-ladder-wrap` + `.biz-ladder-row` + `.biz-ladder-card.{color}` + `.biz-ladder-arrow` | 有回退的状态机 |
| 泳道图 | `.biz-swimlane` + `.sw-lane` + `.sw-node.{color}` + `.sw-arrow` | 跨角色协作时序 |
| Mermaid 容器 | `.mermaid-wrapper` + `.mermaid-title` | Mermaid 图表外框 |
| 状态标签 | `.status-tag` | 角色标签/状态标记 |
| 提示框 | `.prd-tip` / `.prd-warn` / `.prd-error` | 提示/警告/错误 |
| 卡片悬停 | `.card-hover` | 白色卡片悬停效果 |
| 装饰标签 | `.state-pill` | 圆角药丸标签 |
| 分支标签 | `.biz-label` | 流程图条件标注 |
| 步骤编号 | `.biz-step` | 流程节点步骤号 |
| 底部备注 | `.biz-note` / `.sw-note` | 流程图/泳道图注释 |
