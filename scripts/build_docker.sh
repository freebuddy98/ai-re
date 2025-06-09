#!/bin/bash
set -e

# 颜色设置
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# 默认设置
PUSH=false
ALL_SERVICES=false
USE_MIRROR=false
PIP_INDEX_URL="https://pypi.tuna.tsinghua.edu.cn/simple"

# 处理参数
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --service) SERVICE="$2"; shift ;;
        --all) ALL_SERVICES=true ;;
        --push) PUSH=true ;;
        --use-mirror) USE_MIRROR=true ;;
        --pip-index) PIP_INDEX_URL="$2"; shift ;;
        *) echo -e "${RED}未知参数: $1${NC}"; exit 1 ;;
    esac
    shift
done

# 获取服务列表
if [ "$ALL_SERVICES" = true ]; then
    SERVICES=$(ls -d services/*/ | cut -d'/' -f2)
else
    if [ -z "$SERVICE" ]; then
        echo -e "${RED}错误: 请指定服务名称 (--service) 或使用 --all 构建所有服务${NC}"
        exit 1
    fi
    SERVICES="$SERVICE"
fi

# 构建服务
for SERVICE in $SERVICES; do
    echo -e "${GREEN}开始构建 $SERVICE...${NC}"
    
    # 检查服务目录是否存在
    if [ ! -d "services/$SERVICE" ]; then
        echo -e "${RED}错误: 服务 $SERVICE 不存在${NC}"
        continue
    fi
    
    # 检查Dockerfile是否存在
    if [ ! -f "services/$SERVICE/Dockerfile" ]; then
        echo -e "${RED}错误: 服务 $SERVICE 的Dockerfile不存在${NC}"
        continue
    fi
    
    # 构建镜像
    echo -e "${YELLOW}构建 Docker 镜像: ai-re-$SERVICE:latest${NC}"
    
    # 使用国内镜像源构建
    if [ "$USE_MIRROR" = true ]; then
        echo -e "${YELLOW}使用PyPI镜像源: $PIP_INDEX_URL${NC}"
        docker build -t ai-re-$SERVICE:latest \
            --build-arg PIP_INDEX_URL="$PIP_INDEX_URL" \
            -f services/$SERVICE/Dockerfile .
    else
        docker build -t ai-re-$SERVICE:latest -f services/$SERVICE/Dockerfile .
    fi
    
    # 如果需要，推送镜像
    if [ "$PUSH" = true ]; then
        echo -e "${YELLOW}推送 Docker 镜像: ai-re-$SERVICE:latest${NC}"
        docker push ai-re-$SERVICE:latest
    fi
    
    echo -e "${GREEN}$SERVICE 构建完成${NC}"
done

echo -e "${GREEN}所有服务构建完成${NC}" 