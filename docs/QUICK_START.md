# 5分钟快速开始 (Quick Start)

欢迎使用 Crayfish Grid Hunter！本指南将帮助您在5分钟内完成安装并在 OpenClaw 中运行您的第一个网格策略。

## 1. 安装

在您的终端中运行以下一键安装脚本：

```bash
curl -s https://raw.githubusercontent.com/joensmoon/Crayfish-Grid-Hunter/main/install.sh | bash
```

此脚本会自动完成以下操作：
- 安装 Crayfish Grid Hunter 核心引擎
- 安装官方依赖 Skills：`derivatives-trading-usds-futures`（合约数据）和 `query-token-info`（市值数据）
- 验证安装完整性

## 2. 官方 Skill 依赖

本 Skill 依赖以下币安官方 Skills（安装脚本会自动安装）：

| 依赖 Skill | 用途 |
| :--- | :--- |
| `derivatives-trading-usds-futures` | 合约列表、K线数据、资金费率 |
| `query-token-info` | 代币市值、24h 交易量 |

如需手动安装依赖：
```bash
npx skills add binance/derivatives-trading-usds-futures -a openclaw -y
npx skills add binance-web3/query-token-info -a openclaw -y
```

## 3. 运行您的第一个策略

在 OpenClaw 的对话框中，输入以下指令：

> **"帮我运行次新币网格策略"**

### 发生了什么？
1. **扫描市场**：Agent 会扫描上线 90 天内且处于横盘状态的合约。
2. **生成网格**：自动计算等比中性网格的上下轨、网格数和止损位。
3. **历史回测**：使用过去 30 天的数据验证该策略的有效性。
4. **输出报告**：您将看到包含策略参数、预计收益和风险提示的完整报告。

## 4. 自定义参数

您可以通过自然语言直接调整参数，无需修改任何代码：

- *"次新币网格，杠杆 3 倍，市值上限 1 亿"*
- *"高波动套利，筛选前 5 名，止损设为 3%"*
- *"网格猎手，上线天数改为 60 天，涨跌幅 15% 以上"*

完整的参数列表请参阅 [CONFIGURATION.md](CONFIGURATION.md)。

## 5. 下一步

*   查看 [EXAMPLES.md](EXAMPLES.md) 了解更多触发词和自定义参数。
*   查看 [CONFIGURATION.md](CONFIGURATION.md) 了解如何微调策略参数。
*   如果遇到问题，请参考 [TROUBLESHOOTING.md](../TROUBLESHOOTING.md)。

