#!/usr/bin/env bash
# Crayfish Grid Hunter - One-Click Installer
# Author: joensmoon

set -e

echo "================================================================"
echo "🦐 Crayfish Grid Hunter (小龙虾网格猎人) - 一键安装程序"
echo "================================================================"

# 检查 npx (OpenClaw 依赖)
if ! command -v npx &> /dev/null; then
    echo "❌ 错误: 未找到 npx。请先安装 Node.js 和 npm。"
    exit 1
fi

echo "📦 正在安装 Crayfish Grid Hunter 核心..."
npx skills add https://github.com/joensmoon/Crayfish-Grid-Hunter -a openclaw -y

echo "🔄 正在安装官方依赖 Skills..."
# 官方依赖列表
DEPENDENCIES=(
    "binance/derivatives-trading-usds-futures"
    "binance-web3/query-token-info"
    "binance-web3/trading-signal"
    "binance-web3/query-token-audit"
    "binance/assets"
)

for skill in "${DEPENDENCIES[@]}"; do
    echo "  -> 安装 $skill ..."
    npx skills add "$skill" -a openclaw -y
done

echo "✅ 安装完成！"
echo "🎉 欢迎使用 Crayfish Grid Hunter。您现在可以在 OpenClaw 中使用以下指令："
echo "   - '次新币网格'"
echo "   - '高波动套利'"
echo "   - '网格猎手'"
echo ""
echo "📖 详细文档请参阅: docs/QUICK_START.md"
echo "================================================================"

