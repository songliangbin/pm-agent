# UI 质感规范 v1.0

> 基于71张移动端UI设计图提炼的质感增强标准
> 所有移动端原型必须遵循本规范，确保产出具备参考图级别的专业质感

---

## 一、绝对禁令（违反任一条 = 产出失败）

| 编号 | 禁令 | 说明 |
|:--|:--|:--|
| B1 | **严禁使用 Emoji 作为图标** | 所有图标必须是 SVG（stroke 方式）或高质量图片。Emoji 会导致质感断崖式下降 |
| B2 | **严禁单层阴影冒充立体感** | 卡片阴影必须使用复合阴影（双层叠加），单层阴影会显得扁平廉价 |
| B3 | **严禁毛玻璃只有 blur 没有 saturate** | 毛玻璃必须同时包含 `blur(20px) saturate(180%)` |
| B4 | **严禁数字不等宽对齐** | 所有价格、统计数字必须使用 `font-variant-numeric: tabular-nums` |
| B5 | **严禁标题字距不收紧** | 标题字号 >=16px 时必须使用 `letter-spacing: -0.02em` |
| B6 | **严禁空白背景无层次** | 页面背景必须有 subtle 渐变或纹理，纯白背景不得直接用于主内容区 |

---

## 二、复合阴影系统（核心质感）

复合阴影 = 双层 `box-shadow` 叠加，创造真实的深度感。

### 2.1 阴影层级定义

| 层级 | 用途 | CSS 值 |
|:--|:--|:--|
| XS | 按钮按下、微浮起 | `0 1px 2px rgba(0,0,0,0.04), 0 1px 4px rgba(0,0,0,0.02)` |
| SM | 小型卡片、标签 | `0 2px 8px rgba(0,0,0,0.05), 0 1px 3px rgba(0,0,0,0.03)` |
| MD | 标准卡片、列表项 | `0 4px 20px rgba(0,0,0,0.07), 0 1px 3px rgba(0,0,0,0.04)` |
| LG | 大卡片、模态框 | `0 8px 30px rgba(0,0,0,0.1), 0 2px 8px rgba(0,0,0,0.04)` |
| XL | 手机外框、底部导航 | `0 12px 40px rgba(0,0,0,0.12), 0 4px 12px rgba(0,0,0,0.05)` |
| CTA | 主按钮悬浮状态 | `0 8px 24px rgba(var(--brand-rgb), 0.35), 0 2px 6px rgba(var(--brand-rgb), 0.15)` |

### 2.2 应用规则

- **每个使用阴影的地方，优先使用复合阴影**
- 基础层（第一条 shadow）负责"柔化浮起感"
- 焦点层（第二条 shadow）负责"清晰轮廓"
- 品牌色阴影（CTA 层级）的 `rgba()` 值必须根据品牌色动态计算，透明度固定 0.35/0.15

---

## 三、毛玻璃效果（Glassmorphism）

### 3.1 完整参数

```css
.glass {
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.3);
}
```

### 3.2 暗色模式毛玻璃

```css
.glass-dark {
  background: rgba(30, 30, 30, 0.65);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.08);
}
```

### 3.3 应用场景

- 底部悬浮导航：必须毛玻璃
- 顶部导航栏（iOS 风格）：必须毛玻璃
- 弹窗/模态框背景遮罩：必须毛玻璃
- 卡片内的小标签/徽章：可选毛玻璃增强层次

---

## 四、排版质感参数

### 4.1 字间距（Letter Spacing）

| 场景 | 字间距 | 说明 |
|:--|:--|:--|
| 大标题（>=20px） | `-0.02em` | 收紧字距，增强紧凑高级感 |
| 区块标题（16-18px） | `-0.01em` | 轻微收紧 |
| 正文（13-14px） | `0` | 标准字距 |
| 标签/辅助文字（<=12px） | `0.01em ~ 0.02em` | 微松，提升小字可读性 |
| 按钮文字 | `0.01em` | 微松，增加呼吸感 |
| 全大写英文 | `0.05em ~ 0.08em` | 显著放宽，补偿大写的紧凑感 |

### 4.2 数字等宽对齐

所有涉及数字对比的场景必须使用：

```css
.tabular-nums {
  font-variant-numeric: tabular-nums;
}
```

应用场景：价格、统计数据、时间、倒计时、排行榜数字。

### 4.3 字体栈

```css
font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", Roboto, "Helvetica Neue", "PingFang SC", "Microsoft YaHei", sans-serif;
```

数字优先使用 DIN、Roboto 或系统默认等宽数字。

---

## 五、装饰元素系统

### 5.1 径向光斑（Radial Glow）

用于营造空间深度和高级感，常见于头部背景、特殊卡片背景。

```css
.radial-glow {
  position: absolute;
  width: 300px;
  height: 300px;
  background: radial-gradient(circle, rgba(var(--brand-rgb), 0.15), transparent 70%);
  filter: blur(40px);
  pointer-events: none;
  z-index: 0;
}
```

- 颜色跟随品牌色，透明度 0.12-0.2
- 必须设置 `pointer-events: none`
- 必须设置 `z-index: 0` 且被内容层覆盖（z-index >= 1）

### 5.2 噪点纹理（Noise Texture）

用于消除纯色背景的"塑料感"，增加材质纹理。

```css
.noise-overlay::before {
  content: "";
  position: absolute;
  inset: 0;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.03'/%3E%3C/svg%3E");
  opacity: 0.4;
  mix-blend-mode: overlay;
  pointer-events: none;
  z-index: 1;
}
```

- `opacity: 0.3-0.5`（微妙，不可喧宾夺主）
- `mix-blend-mode: overlay`
- 应用场景：深色背景卡片、沉浸式头部、特殊运营区块

### 5.3 渐变叠加混合模式

渐变背景与内容叠加时，使用混合模式增强层次：

```css
.gradient-overlay {
  background: linear-gradient(135deg, var(--brand), var(--brand-light));
  position: relative;
}
.gradient-overlay::after {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, transparent 0%, rgba(0,0,0,0.08) 100%);
  mix-blend-mode: multiply;
  pointer-events: none;
}
```

---

## 六、SVG 图标规范

### 6.1 尺寸与描边

- 视图框：`viewBox="0 0 24 24"`
- 描边宽度：`stroke-width="1.5"` 或 `"2"`
- 描边端点：`stroke-linecap="round"`，`stroke-linejoin="round"`
- 填充：`fill="none"`
- 颜色：`stroke="currentColor"`，通过 CSS `color` 控制

### 6.2 图标底板（Icon Background Plate）

面性图标（如宫格入口）使用圆角底板：

```css
.icon-plate {
  width: 48px;
  height: 48px;
  border-radius: 14px;
  background: linear-gradient(135deg, var(--brand), var(--brand-light));
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}
```

### 6.3 禁止场景

- 任何位置禁止使用 Emoji 替代图标
- 禁止使用文字符号（如 `☆`、`→`）替代图标
- 底部导航、按钮、列表项、空状态必须使用 SVG

---

## 七、配色质感规范

### 7.1 完整灰阶

| Token | 色值 | 用途 |
|:--|:--|:--|
| `--text-1` | `#111827` | 主标题、正文 |
| `--text-2` | `#4B5563` | 次要文字、描述 |
| `--text-3` | `#9CA3AF` | 辅助文字、占位符 |
| `--text-4` | `#D1D5DB` | 禁用状态、分割线 |
| `--border` | `#F3F4F6` | 卡片边框、分割线 |
| `--border-strong` | `#E5E7EB` | 表单边框、强分割线 |
| `--bg` | `#F9FAFB` | 页面背景 |
| `--card` | `#FFFFFF` | 卡片背景 |

### 7.2 功能色

| 语义 | 色值 | 背景色 |
|:--|:--|:--|
| 成功 | `#10B981` | `#ECFDF5` |
| 警告 | `#F59E0B` | `#FFFBEB` |
| 错误 | `#EF4444` | `#FEF2F2` |
| 信息 | `#3B82F6` | `#EFF6FF` |

---

## 八、按钮质感

### 8.1 主按钮（CTA）

```css
.btn-primary {
  background: linear-gradient(135deg, var(--brand), var(--brand-light));
  color: white;
  border-radius: 14px;
  padding: 12px 24px;
  font-weight: 600;
  letter-spacing: 0.01em;
  box-shadow: 0 4px 16px rgba(var(--brand-rgb), 0.3), 0 1px 3px rgba(var(--brand-rgb), 0.1);
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}
.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(var(--brand-rgb), 0.35), 0 2px 6px rgba(var(--brand-rgb), 0.15);
}
.btn-primary:active {
  transform: translateY(0) scale(0.98);
}
```

### 8.2 次级按钮

```css
.btn-secondary {
  background: rgba(var(--brand-rgb), 0.08);
  color: var(--brand);
  border-radius: 14px;
  padding: 12px 24px;
  font-weight: 600;
}
```

---

## 九、卡片质感

### 9.1 标准卡片

```css
.card {
  background: var(--card);
  border-radius: 18px;
  padding: 16px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.07), 0 1px 3px rgba(0,0,0,0.04);
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}
.card:active {
  transform: scale(0.985);
}
```

### 9.2 大卡片（运营位、Banner）

```css
.card-large {
  background: var(--card);
  border-radius: 24px;
  overflow: hidden;
  box-shadow: 0 8px 30px rgba(0,0,0,0.1), 0 2px 8px rgba(0,0,0,0.04);
  position: relative;
}
```

---

## 十、质感自检清单（生成后必跑）

Agent 生成原型后，必须逐项自检：

### 阴影检查
- [ ] 所有卡片使用复合阴影（双层 box-shadow）
- [ ] 主按钮悬浮态有品牌色阴影
- [ ] 底部导航阴影为 XL 层级
- [ ] 无单层阴影冒充立体感的情况

### 毛玻璃检查
- [ ] 底部导航 backdrop-filter 包含 blur(20px) saturate(180%)
- [ ] 顶部导航（如有）也是完整毛玻璃参数
- [ ] 毛玻璃层有半透明边框 `rgba(255,255,255,0.3)`

### 图标检查
- [ ] 全站零 Emoji
- [ ] 底部导航图标是 24x24 SVG，stroke 1.5
- [ ] 按钮、列表项、空状态均无 Emoji

### 排版检查
- [ ] 标题（>=16px）有 `letter-spacing: -0.02em`
- [ ] 标签文字有 `letter-spacing: 0.01em`
- [ ] 价格/统计数字有 `font-variant-numeric: tabular-nums`

### 装饰检查
- [ ] 沉浸式头部或有特殊质感的区块有径向光斑
- [ ] 深色背景卡片有噪点纹理
- [ ] 渐变背景有叠加混合模式增强层次

### 交互检查
- [ ] 所有按钮有 `:active` 状态（scale 或背景变化）
- [ ] 卡片点击有 `transform: scale(0.985)` 反馈
- [ ] Tab 切换有 `transition: 0.35s cubic-bezier(0.16,1,0.3,1)`

---

## 十一、快速引用 CSS 变量模板

在 `:root` 中定义以下变量：

```css
:root {
  /* 品牌色（按项目动态设置） */
  --brand: #6366F1;
  --brand-light: #818CF8;
  --brand-bg: #EEF2FF;
  --brand-rgb: 99, 102, 241; /* 用于 rgba() 阴影 */

  /* 功能色 */
  --success: #10B981; --success-bg: #ECFDF5;
  --warning: #F59E0B; --warning-bg: #FFFBEB;
  --danger: #EF4444;  --danger-bg: #FEF2F2;
  --info: #3B82F6;    --info-bg: #EFF6FF;

  /* 中性色 */
  --text-1: #111827; --text-2: #4B5563;
  --text-3: #9CA3AF; --text-4: #D1D5DB;
  --border: #F3F4F6; --border-strong: #E5E7EB;
  --bg: #F9FAFB;     --card: #FFFFFF;

  /* 复合阴影 */
  --shadow-xs: 0 1px 2px rgba(0,0,0,0.04), 0 1px 4px rgba(0,0,0,0.02);
  --shadow-sm: 0 2px 8px rgba(0,0,0,0.05), 0 1px 3px rgba(0,0,0,0.03);
  --shadow-md: 0 4px 20px rgba(0,0,0,0.07), 0 1px 3px rgba(0,0,0,0.04);
  --shadow-lg: 0 8px 30px rgba(0,0,0,0.1), 0 2px 8px rgba(0,0,0,0.04);
  --shadow-xl: 0 12px 40px rgba(0,0,0,0.12), 0 4px 12px rgba(0,0,0,0.05);
  --shadow-cta: 0 4px 16px rgba(var(--brand-rgb),0.3), 0 1px 3px rgba(var(--brand-rgb),0.1);

  /* 圆角 */
  --r-xs: 6px;  --r-sm: 10px; --r-md: 14px;
  --r-lg: 18px; --r-xl: 22px; --r-2xl: 28px;
  --r-full: 9999px;
}
```
