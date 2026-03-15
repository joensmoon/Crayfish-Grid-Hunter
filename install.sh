#!/usr/bin/env bash
# Crayfish Grid Hunter - One-Click Installer
# Author: joensmoon
# Version: 1.0.0

set -e

echo "================================================================"
echo "  🦞 Crayfish Grid Hunter v1.0.0 — 一键安装程序"
echo "================================================================"

# 检查 npx (OpenClaw 依赖)
if ! command -v npx &> /dev/null; then
    echo "❌ 错误: 未找到 npx。请先安装 Node.js 和 npm。"
    exit 1
fi

echo ""
echo "📦 [1/3] 正在安装 Crayfish Grid Hunter 核心..."
npx skills add https://github.com/joensmoon/Crayfish-Grid-Hunter -a openclaw -y

echo ""
echo "🔄 [2/3] 正在安装官方依赖 Skills..."
# 官方依赖列表（仅列出实际使用的 Skills）
DEPENDENCIES=(
    "binance/derivatives-trading-usds-futures"
    "binance-web3/query-token-info"
)

for skill in "${DEPENDENCIES[@]}"; do
    echo "  -> 安装 $skill ..."
    npx skills add "$skill" -a openclaw -y
done

echo ""
echo "🔍 [3/3] 正在验证安装..."
echo "  ✓ 核心引擎: grid_hunter_v5.py"
echo "  ✓ 官方依赖: derivatives-trading-usds-futures (合约数据)"
echo "  ✓ 官方依赖: query-token-info (市值数据)"

echo ""
echo "================================================================"
echo "  ✅ 安装完成！Crayfish Grid Hunter v1.0.0 已就绪"
echo "================================================================"
echo ""
echo "  🎯 触发指令（在 OpenClaw 对话框中输入）："
echo "     • '次新币网格'   — 扫描上线≤90天的次新币横盘机会"
echo "     • '高波动套利'   — 扫描48h内波动剧烈的热点币种"
echo "     • '网格猎手'     — 同时运行两类扫描，汇总最优结果"
echo ""
echo "  🔧 自定义参数（直接用自然语言调整）："
echo "     • '次新币网格，杠杆3倍，市值上限1亿'"
echo "     • '高波动套利，筛选前5名，止损设为3%'"
echo "     • '网格猎手，上线天数改为60天，涨跌幅15%以上'"
echo ""
echo "  📚 官方 Skill 依赖："
echo "     • derivatives-trading-usds-futures (币安合约数据)"
echo "     • query-token-info (币安 Web3 市值数据)"
echo ""
echo "  📖 详细文档: docs/QUICK_START.md | USER_GUIDE.md"
echo "================================================================"
