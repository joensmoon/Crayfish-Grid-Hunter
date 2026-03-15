# 高级使用指南 (Advanced Guide)

本指南面向有经验的交易者，介绍 Crayfish Grid Hunter 的高级功能和内部机制。

## 1. 等比中性网格 (Geometric Neutral Grid) 机制

### 1.1 为什么选择等比网格？
对于高波动资产（尤其是加密货币合约），价格可能在短时间内发生剧烈变动。等差网格（Arithmetic）在价格高位时，单格利润率会显著下降。
Crayfish 采用**等比网格 (Geometric)**，其核心公式为：
$r = (Upper / Lower)^{(1 / GridCount)}$
这保证了在任何价格水平下，每一格的**利润百分比是恒定的**。

### 1.2 最低利润强制执行
由于币安合约存在 0.04% 的 Maker 费率（买卖双边共 0.08%），如果网格过密，利润会被手续费吞噬。
Crayfish 内置了 `MIN_GRID_PROFIT = 0.8%` 的硬性要求。
如果在计算时发现单格利润低于此值，算法会**自动减少网格数量**，重新计算，直到满足利润要求。

## 2. 资金费率套利 (Funding Rate Arbitrage)

在 `monitor.py` 的实时监控中，系统会密切关注资金费率：
*   如果资金费率为**极度负值**（如 < -0.1%），做多（Long）的网格将获得额外的资金费收益。
*   系统会计算预计的年化资金费率收益，并在仪表板中显示为 `Funding Alpha`。

## 3. Webhook 预警集成

您可以将 Crayfish 的监控模块与您的 Telegram、Discord 或企业微信机器人集成。

### 3.1 预警级别
*   `INFO`: 日常播报（如 PnL 达到里程碑）。
*   `MEDIUM`: 市场条件变化（如波动率放大、API 延迟）。
*   `HIGH`: 风险警告（如接近止损位、回撤过大）。
*   `CRITICAL`: 紧急事件（如触发止损、接近强平价）。

### 3.2 配置方法
目前支持在运行环境中配置环境变量 `WEBHOOK_URL`。
当警报触发时，`monitor.py` 会向该 URL 发送包含 JSON 数据的 POST 请求。

```json
{
  "level": "CRITICAL",
  "symbol": "BTCUSDT",
  "message": "价格已跌破止损位",
  "timestamp": "2026-03-15T12:00:00Z"
}
```

## 4. 未来计划：Smart Money 信号集成

未来版本计划集成币安 Web3 的 `trading-signal` Skill，用于验证推荐标的的 Smart Money 流向。当某个标的近期出现 Smart Money 大量买入信号时，其排名得分将获得加权提升。

> **注意**：当前 v1.0.0 版本尚未实现此功能。当前版本仅依赖 `derivatives-trading-usds-futures` 和 `query-token-info` 两个官方 Skills。

