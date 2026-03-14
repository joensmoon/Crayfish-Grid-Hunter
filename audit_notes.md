# Crayfish Grid Hunter v4.0.0 审查笔记

## 已发现的问题

### 严重问题（影响安装/使用）

1. **SKILL.md metadata 格式不符合 OpenClaw 规范**
   - 当前：多行 YAML `metadata:\n  version: 4.0.0\n  author: joensmoon`
   - OpenClaw 要求：单行 JSON `metadata: {"version":"4.0.0","author":"joensmoon"}`
   - 同样 `dependencies:` 也是多行 YAML，OpenClaw 不一定支持这种格式
   - 但 `npx skills add` 只解析 `name` 和 `description`，所以安装不受影响
   - 风险：ClawHub publish 时可能解析失败

2. **SKILL.md description 使用多行 YAML (`|`)** 
   - 当前：`description: |\n  Crayfish Grid Hunter is...`
   - 应该用引号包裹的单行字符串
   - `npx skills add --list` 可能无法正确显示描述

3. **Spot API 无 fallback 机制**
   - `SPOT_BASE_URL = "https://api.binance.com"` 硬编码
   - 在部分地区返回 HTTP 451，所有 Spot 功能失效
   - 需要添加 `data-api.binance.vision` 作为备用

4. **README.md 安装命令 URL 错误**
   - 第89行：`npx skills add https://github.com/joensmoon/123`
   - 应为：`npx skills add https://github.com/joensmoon/Crayfish-Grid-Hunter`

### 中等问题

5. **SKILL.md 中 trading-signal API 与 api_usage.md 不一致**
   - SKILL.md Step 3 使用 POST 方法和 URL: `.../web/signal/smart-money`
   - api_usage.md 第74行使用 GET 方法和 URL: `.../market/signal/smart-money/list`
   - 测试脚本使用 POST + `.../web/signal/smart-money`
   - 需要确认哪个是正确的

6. **SKILL.md 中 query-token-audit API 与 api_usage.md 不一致**
   - SKILL.md Step 4 使用 POST + `.../security/token/audit`
   - api_usage.md 使用 GET + `.../token/audit/query`
   - 测试脚本使用 POST + `.../security/token/audit`
   - 需要确认哪个是正确的

7. **LICENSE.md 版权持有人不是 joensmoon**
   - 当前：`Copyright (c) 2026 Grid Hunter Contributors`
   - 应为：`Copyright (c) 2026 joensmoon`

8. **测试脚本 Test 0 是假通过**
   - `record_test("Dependency Check", "PASS", "8/8 checks passed")` 直接硬编码 PASS
   - 没有实际检查任何依赖

9. **测试脚本 Test 6 给 BTCUSDT 硬编码加分**
   - `if symbol == "BTCUSDT": score += 15` 这是 mock 逻辑，不是真正的 Smart Money 验证

10. **测试脚本缺少 Test 7 (Breakout Alert)**
    - README 和 SKILL.md 描述了 Step 7 突破预警
    - 但测试脚本没有实现这个测试

### 轻微问题

11. **User-Agent 不一致**
    - SKILL.md 说 `crayfish-grid-hunter/4.0.0 (Skill)`
    - 测试脚本用 `grid-hunter/4.0.0 (Skill)`（缺少 crayfish- 前缀）

12. **测试脚本没有 breakout alert 测试**
    - TEST_RESULTS.md 声称 "Breakout Alert Logic: PASS"
    - 但测试脚本中没有这个测试

13. **api_usage.md 中 Kline 响应格式表不完整**
    - 只列出了 Index 0-6，缺少 7-11
