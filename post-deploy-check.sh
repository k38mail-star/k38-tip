#!/bin/bash
# 部署后自动验证脚本
# 用法: ./post-deploy-check.sh

set -e

echo "🚀 开始部署后验证..."

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 配置
URL="https://boboji.beer"
MAX_RETRIES=5
RETRY_DELAY=10

# 1. 等待服务器重启
echo "⏳ 等待服务器重启..."
sleep 5

# 2. 检查API可用性
echo "📡 检查API健康状态..."
for i in $(seq 1 $MAX_RETRIES); do
  if curl -sf "$URL/api/version" > /dev/null; then
    echo -e "${GREEN}✅ API响应正常${NC}"
    break
  else
    echo -e "${YELLOW}⚠️  API未响应，重试 $i/$MAX_RETRIES...${NC}"
    sleep $RETRY_DELAY
  fi
  if [ $i -eq $MAX_RETRIES ]; then
    echo -e "${RED}❌ API检查失败${NC}"
    exit 1
  fi
done

# 3. 检查版本号
echo "🔍 检查部署版本..."
DEPLOYED_VERSION=$(curl -s "$URL/api/version" | jq -r '.version')
DEPLOYED_COMMIT=$(curl -s "$URL/api/version" | jq -r '.commit' | cut -c1-7)
echo -e "${GREEN}✅ 部署版本: $DEPLOYED_VERSION ($DEPLOYED_COMMIT)${NC}"

# 4. 运行Playwright视觉测试
echo "🎭 运行Playwright视觉测试..."
cd "$(dirname "$0")"
npx playwright test --reporter=line

if [ $? -eq 0 ]; then
  echo -e "${GREEN}✅ 所有视觉测试通过${NC}"
else
  echo -e "${RED}❌ 视觉测试失败${NC}"
  exit 1
fi

# 5. 快速烟雾测试
echo "💨 执行快速烟雾测试..."

# 检查首页可访问
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$URL")
if [ "$HTTP_CODE" == "200" ]; then
  echo -e "${GREEN}✅ 首页响应正常 (HTTP $HTTP_CODE)${NC}"
else
  echo -e "${RED}❌ 首页响应异常 (HTTP $HTTP_CODE)${NC}"
  exit 1
fi

# 检查API返回数据
MATCH_COUNT=$(curl -s "$URL/api/candidates?limit=5" | jq '.matches | length')
if [ "$MATCH_COUNT" -gt 0 ]; then
  echo -e "${GREEN}✅ API返回 $MATCH_COUNT 场比赛数据${NC}"
else
  echo -e "${RED}❌ API未返回数据${NC}"
  exit 1
fi

# 6. 生成报告
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}🎉 部署验证完成！${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "版本: $DEPLOYED_VERSION"
echo "提交: $DEPLOYED_COMMIT"
echo "URL: $URL"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

exit 0
