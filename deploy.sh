#!/bin/bash
# K38 波波鸡 部署脚本 (新加坡服务器)
# Usage: bash deploy.sh

set -euo pipefail

APP_DIR="/opt/k38"
SERVICE="k38"
BRANCH="main"

echo "🐔 波波鸡部署开始..."

cd "$APP_DIR"

# Pull latest code
echo "📥 拉取最新代码..."
git fetch origin "$BRANCH"
git reset --hard "origin/$BRANCH"

# Install dependencies
echo "📦 安装依赖..."
pip install -r requirements.txt --quiet

# Copy nginx config if changed
if ! diff -q nginx.conf /etc/nginx/sites-enabled/k38.conf &>/dev/null 2>&1; then
    echo "🔧 更新 nginx 配置..."
    sudo cp nginx.conf /etc/nginx/sites-enabled/k38.conf
    sudo nginx -t && sudo systemctl reload nginx
fi

# Restart service
echo "🔄 重启服务..."
sudo systemctl restart "$SERVICE"

# Health check
sleep 2
if curl -sf http://127.0.0.1:5000/ > /dev/null; then
    echo "✅ 部署成功！服务运行正常"
else
    echo "❌ 健康检查失败！检查日志: journalctl -u $SERVICE -n 50"
    exit 1
fi
