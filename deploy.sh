#!/bin/bash

echo "🚀 开始部署到 Vercel..."

# 检查是否安装了 Vercel CLI
if ! command -v vercel &> /dev/null; then
    echo "❌ Vercel CLI 未安装，正在安装..."
    npm install -g vercel
fi

# 检查是否已登录
if ! vercel whoami &> /dev/null; then
    echo "🔐 请先登录 Vercel..."
    vercel login
fi

# 部署到预览环境
echo "📦 部署到预览环境..."
vercel

echo "✅ 部署完成！"
echo "🌐 预览URL将在上方显示"
echo ""
echo "要部署到生产环境，请运行:"
echo "vercel --prod" 