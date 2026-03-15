# 故障排除指南 (Troubleshooting Guide)

本指南旨在帮助用户解决在 OpenClaw 环境中使用 **Crayfish Grid Hunter v1.0.0** 时可能遇到的常见问题。

## 1. 安装与环境问题

### 1.1 `skills add` 命令失败
*   **现象**: 提示 `Command not found` 或 `Invalid URL`。
*   **解决方法**:
    *   确保已安装 OpenClaw CLI 并正确配置。
    *   检查网络连接，确保能访问 GitHub。
    *   使用完整命令：`skills add https://github.com/joensmoon/Crayfish-Grid-Hunter`。

### 1.2 依赖缺失
*   **现象**: 运行脚本时提示 `ModuleNotFoundError`。
*   **解决方法**:
    *   Crayfish Grid Hunter 依赖于以下币安官方 Skills。请运行以下命令确保所有依赖已安装：
        ```bash
        npx skills add binance/derivatives-trading-usds-futures -a openclaw -y
        npx skills add binance-web3/query-token-info -a openclaw -y
        ```
    *   或者直接运行一键安装脚本，它会自动安装所有依赖：
        ```bash
        curl -s https://raw.githubusercontent.com/joensmoon/Crayfish-Grid-Hunter/main/install.sh | bash
        ```

## 2. API 与连接问题

### 2.1 451 Unavailable For Legal Reasons
*   **现象**: 访问 `fapi.binance.com` 报错。
*   **原因**: 币安合约 API 在某些地区受到限制。
*   **解决方法**:
    *   系统会自动切换到 `testnet.binancefuture.com` 作为备用数据源。
    *   如果在 OpenClaw 桌面端运行，请确保您的网络环境可以访问币安合约服务。

### 2.2 query-token-info 返回空数据
*   **现象**: 无法获取市值（Market Cap）数据，Category B 筛选无结果。
*   **解决方法**:
    *   检查 `web3.binance.com` 的连接性。
    *   这是由于币安 Web3 接口频率限制导致的，请稍后重试。

## 3. 策略与逻辑问题

### 3.1 筛选结果为空
*   **现象**: 运行扫描后提示“暂无符合条件的标的”。
*   **解决方法**:
    *   这是正常现象，说明当前市场没有符合严格筛选条件的币种。
    *   您可以尝试**自定义参数**来放宽限制，例如：
        > "帮我筛选高波动套利，市值范围放宽到1亿到50亿，换手率降低到30%"

### 3.2 止损频繁触发
*   **现象**: 网格运行不久即触发止损。
*   **解决方法**:
    *   检查 `stop_loss_pct` 参数。默认 5% 在极高波动品种上可能较窄。
    *   建议将杠杆调低（如 2x-3x）并适当放宽止损位。

## 4. 性能监控问题

### 4.1 Webhook 通知不工作
*   **现象**: 配置了 Webhook 但收不到警报。
*   **解决方法**:
    *   确保 Webhook URL 正确且支持 POST 请求。
    *   检查 `monitor.py` 中的日志输出，确认是否有发送失败的错误信息。

---
*如遇到其他无法解决的问题，请在 GitHub 仓库提交 Issue。*

