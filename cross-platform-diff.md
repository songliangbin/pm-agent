# 跨端一致性自动 diff 检查

> 多端项目（≥2 端）在步骤⑥自检后、步骤⑦交付前，**必须**执行跨端 diff 检查。

---

## 执行方式

Agent 读取各端 HTML 文件，提取关键配置进行文本对比。

## 检查维度

| 维度 | 对比内容 | 不一致则失败 |
|:--|:--|:--|
| 配色 | 各端 `:root` 中的 `--accent`（或 `--brand`/`--primary`）主色值 | 必须完全一致 |
| 术语 | 各端导航项/页面标题中的功能名称 | 必须完全一致（如"订单"不能一端叫"订单"另一端叫"单据"） |
| 状态枚举 | 各端中订单/任务等状态的标签值 | 必须完全一致（如"待支付"/"已完成"） |
| Toast 函数 | 各端 `showToast` 的实现方式和调用方式 | 必须一致 |
| Tab 切换 | 各端底部导航/侧边栏的切换机制 | 必须一致 |

## diff 输出格式

```
🔄 跨端一致性 diff 检查
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
配色对比：用户端 #FF6B35 vs 骑手端 #FF6B35 ✓
术语对比：订单 ✓ / 首页 ✓ / 我的 ✓
状态枚举对比：待支付 ✓ / 已完成 ✓ / 已取消 ✓
Toast 对比：showToast(msg, type) ✓
Tab 切换：switchTab(tab) ✓
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
结论: [ ✅ 全部一致 / ❌ 发现 N 处不一致 ]
```

## 修复规则

- 不一致时**必须修复**，修复后重新跑 diff，直到全部一致才能交付
- 修复时优先统一术语和枚举值，其次检查模板变量是否正确替换

---

## 自动化 diff 脚本（推荐执行）

> **说明**：以下脚本在步骤⑥自检阶段使用。将脚本内容写入各端 HTML 所在目录下的 `cross-diff.py`（**固定文件名，写一次长期保留，禁止删除**），运行 `python cross-diff.py`。按 SKILL.md「无人值守铁律」：该脚本是流程内正式工具而非"临时文件"，**不创建临时目录、不做任何清理/删除操作**；最终交付物为 HTML 原型和 PRD 文档，辅助脚本留在工作目录不影响交付。

### 使用方法

将此脚本保存为 `cross-diff.py`，放在包含各端 HTML 的目录中运行：

```bash
python cross-diff.py 用户端.html 骑手端.html 商家端.html 管理端.html
```

### 脚本内容

```python
"""跨端一致性自动检查"""
import re, sys

def extract_vars(html, label):
    \"\"\"从 HTML 中提取关键配置\"\"\"
    # 提取主色 (--accent / --brand / --primary)
    accent = re.search(r'--(?:accent|brand|primary)\s*:\s*(#[0-9a-fA-F]+)', html)
    # 提取导航项文字
    navs = re.findall(r'(?:navigateTo|switchPage|switchTab)\s*\(\s*['\"]([^'\"]+)['\"]', html)
    # 提取状态枚举（如表中的状态标签）
    statuses = set(re.findall(r'(待[^<"\'|]+|已[^<"\'|]+|[^<"\'|]*中)', html))
    # 提取 showToast 调用方式
    toasts = re.findall(r'(showToast\s*\([^)]+\))', html)
    return {
        "accent": accent.group(1) if accent else "NOT FOUND",
        "navs": list(dict.fromkeys(navs)),
        "statuses": sorted(s for s in statuses if len(s) > 1),
        "toast_pattern": toasts[0] if toasts else "NOT FOUND",
    }

def diff_check(files):
    results = {fn: extract_vars(open(fn, "r", encoding="utf-8").read(), fn) for fn in files}
    
    print("🔄 跨端一致性 diff 检查")
    print("━" * 40)
    
    # 检查配色
    colors = [f"{fn}: {d['accent']}" for fn, d in results.items()]
    all_same = len(set(d['accent'] for d in results.values())) == 1
    print(f"配色对比：{' ✓ '.join(colors)} {'✓' if all_same else '❌ 不一致！'}")
    
    # 检查术语（导航项）
    nav_sets = [set(d['navs']) for d in results.values()]
    union_navs = set.union(*nav_sets) if nav_sets else set()
    for nav in sorted(union_navs):
        ends = [f"{fn}: {'✓' if nav in d['navs'] else '✗'}" for fn, d in results.items()]
        print(f"  导航「{nav}」: {' | '.join(ends)}")
    
    # 检查 Toast
    toast_sets = set(d['toast_pattern'].split("(")[0] if "(" in d['toast_pattern'] else d['toast_pattern'] for d in results.values())
    print(f"Toast 调用: {'✓ 一致' if len(toast_sets) == 1 else '❌ 不一致: ' + str(toast_sets)}")
    
    print("━" * 40)
    all_ok = all_same and len(toast_sets) == 1
    print(f"结论: {'✅ 全部一致' if all_ok else '❌ 发现不一致项，请修复后重新检查'}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python cross-diff.py 端1.html 端2.html [...]")
        sys.exit(1)
    diff_check(sys.argv[1:])
```

### 输出示例

```
🔄 跨端一致性 diff 检查
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
配色对比：用户端: #FF6B35 ✓ 商家端: #FF6B35 ✓
Toast 调用: ✓ 一致
导航「订单」: 用户端: ✓ | 商家端: ✓
导航「首页」: 用户端: ✓ | 商家端: ✓
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
结论: ✅ 全部一致
```

### 集成到自检流程

在 `cross-platform-diff.md` 和 `SKILL.md` 的步骤⑥之间打通：

```
步骤⑤ 生成完成
    ↓
步骤⑤.5 运行 cross-diff.py
    ├─ 全部一致 → 进入步骤⑥ 自检
    └─ 发现不一致 → 修复 → 重新运行 → 进入步骤⑥
    ↓
步骤⑥ 质量自检
```