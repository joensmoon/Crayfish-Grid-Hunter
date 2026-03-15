# 🦞 Crayfish Grid Hunter v1.0.0

**币安 Agent 比赛参赛作品 — 专业的智能网格策略猎手**

Crayfish Grid Hunter 是一款专为币安 USDS-M 永续合约设计的智能策略插件。它结合了实时市场扫描、双分类筛选引擎和等比中性网格算法，旨在帮助用户在波动市场中捕捉套利机会。

---

## 🌟 核心特性

- **双分类筛选引擎**:
  - **Category A (次新币横盘)**: 专门筛选上线 ≤90 天、市值 $10M-$200M、进入缩量横盘阶段的次新币。适合低风险稳健网格。
  - **Category B (高波动套利)**: 捕捉 48 小时涨跌幅 >10%、换手率极高、波动率剧增的热点币种。适合高收益激进套利。
- **等比中性网格算法**: 采用工业级 `r = (upper/lower)^(1/n)` 算法，确保价格在任何区间波动时的百分比利润完全一致。
- **全自动参数优化**: 基于 ATR（平均真实波幅）和布林带（Bollinger Bands）自动计算最优价格区间、格数和止损位。
- **防伪签名机制**: 每份输出均包含唯一的执行 ID 和加密签名，彻底杜绝 AI 幻觉，确保数据真实来自币安 API 实时执行。
- **OpenClaw 原生支持**: 完美适配 OpenClaw Skill 规范，支持 `{baseDir}` 自动注入和一键安装。

---

## 🚀 快速开始

### 1. 安装 (OpenClaw 环境)

```bash
# 使用 ClawHub 安装 (推荐)
clawhub install joensmoon/crayfish-grid-hunter

# 或使用一键安装脚本
curl -s https://raw.githubusercontent.com/joensmoon/Crayfish-Grid-Hunter/main/install.sh | bash
```

### 2. 触发指令

在 OpenClaw 对话框中输入以下指令即可触发：

- `次新币网格` — 扫描最近 90 天上线的潜力币种
- `高波动套利` — 扫描 48 小时内波动剧烈的热点币种
- `网格猎手` — 同时运行两类扫描并汇总结果

### 3. 自定义参数 (可选)

你可以通过自然语言直接调整参数：
- *"次新币网格，杠杆 3 倍，市值上限 1 亿"*
- *"高波动套利，筛选前 5 名，止损设为 3%"*

---

## 📚 完整文档体系

为了帮助不同阶段的用户快速上手，我们提供了完整的文档体系：

*   [**用户使用手册 (USER_GUIDE.md)**](USER_GUIDE.md): 从安装到结果解读，最详尽的用户指南。
*   [**快速开始 (QUICK_START.md)**](docs/QUICK_START.md): 5分钟快速开始指南。
*   [**示例 (EXAMPLES.md)**](docs/EXAMPLES.md): 丰富的自然语言触发示例。
*   [**配置 (CONFIGURATION.md)**](docs/CONFIGURATION.md): 详细的参数配置说明。
*   [**高级指南 (ADVANCED.md)**](docs/ADVANCED.md): API 接口、Webhook 和回测集成的高级指南。
*   [**故障排除 (TROUBLESHOOTING.md)**](TROUBLESHOOTING.md): 常见问题与故障排除指南。

---

## 📂 项目结构

```text
Crayfish-Grid-Hunter/
├── skills/crayfish-grid-hunter/
│   ├── SKILL.md            # OpenClaw 核心指令集 (v1.0.0)
│   ├── grid_hunter_v5.py   # 核心筛选与计算引擎
│   ├── backtester.py       # 历史回测系统
│   ├── progress.py         # 实时进度条与输出增强
│   ├── param_advisor.py    # 参数优化建议引擎
│   └── api_server.py       # REST API 与 Webhook 支持
├── docs/                   # 完整文档体系
├── install.sh              # 一键安装脚本
├── USER_GUIDE.md           # 用户使用手册
└── README.md               # 项目主页
```

---

## 🛡️ 安全与风险提示

- **数据真实性**: 请务必检查输出末尾是否包含 `CRAYFISH-XXXXXXXXXXXX` 签名。
- **风险控制**: 脚本默认强制设置 5% 止损位，并提供预估强平价参考。
- **投资风险**: 网格交易在单边行情下存在破位风险，请根据个人风险承受能力设置杠杆。

---

## 🤝 贡献者

- **joensmoon** (唯一贡献者)

---

## 📄 开源协议

MIT License. 本项目仅供学习和研究使用，不构成任何投资建议。
