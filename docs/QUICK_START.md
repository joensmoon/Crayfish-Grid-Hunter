# 5分钟快速开始 (Quick Start)

欢迎使用 Crayfish Grid Hunter！本指南将帮助您在5分钟内完成安装并在 OpenClaw 中运行您的第一个网格策略。

## 1. 安装

在您的终端中运行以下一键安装脚本：

```bash
curl -s https://raw.githubusercontent.com/joensmoon/Crayfish-Grid-Hunter/main/install.sh | bash
```

此脚本会自动将 Crayfish Grid Hunter 及其所有依赖的币安官方 Skills 安装到您的 OpenClaw 环境中。

## 2. 基础配置 (可选)

虽然您可以直接使用，但为了获得最佳体验（如账户余额检查和费用优化），建议配置币安 API 密钥：

```bash
export BINANCE_API_KEY="您的API_KEY"
export BINANCE_API_SECRET="您的API_SECRET"
```

## 3. 运行您的第一个策略

在 OpenClaw 的对话框中，输入以下指令：

> **"帮我运行次新币网格策略"**

### 发生了什么？
1. **扫描市场**：Agent 会扫描上线 90 天内且处于横盘状态的合约。
2. **生成网格**：自动计算等比中性网格的上下轨、网格数和止损位。
3. **历史回测**：使用过去 30 天的数据验证该策略的有效性。
4. **输出报告**：您将看到包含策略参数、预计收益和风险提示的完整报告。

## 4. 下一步

*   查看 [EXAMPLES.md](EXAMPLES.md) 了解更多触发词和自定义参数。
*   查看 [CONFIGURATION.md](CONFIGURATION.md) 了解如何微调策略参数。
*   如果遇到问题，请参考 [TROUBLESHOOTING.md](../TROUBLESHOOTING.md)。
