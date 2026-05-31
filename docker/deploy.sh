#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

usage() {
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -p <project>             指定项目名称（默认: dbvault）"
    echo "  -b, --build              构建镜像后再部署"
    echo "  -n, --no-build           使用已有镜像部署（默认）"
    echo "  -a, --api-only           仅构建/部署 API 服务"
    echo "  -f, --frontend-only      仅构建/部署前端服务"
    echo "  -d, --down               停止并删除所有容器"
    echo "  -D, --down-v             停止并删除所有容器和数据卷"
    echo "  -h, --help               显示帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 -p myproject               # 使用 myproject 作为项目名部署"
    echo "  $0 -p myproject -b            # 构建所有镜像后部署"
    echo "  $0 -p myproject -b -a         # 仅构建 API 镜像后部署"
    echo "  $0 -d                         # 停止所有容器"
    echo "  $0 -D                         # 停止所有容器并删除数据卷"
}

PROJECT_NAME="dbvault"
BUILD=false
API_ONLY=false
FRONTEND_ONLY=false
DOWN=false
DOWN_V=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -p)
            PROJECT_NAME="$2"
            shift 2
            ;;
        -b|--build)
            BUILD=true
            shift
            ;;
        -n|--no-build)
            BUILD=false
            shift
            ;;
        -a|--api-only)
            API_ONLY=true
            shift
            ;;
        -f|--frontend-only)
            FRONTEND_ONLY=true
            shift
            ;;
        -d|--down)
            DOWN=true
            shift
            ;;
        -D|--down-v)
            DOWN_V=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "未知选项: $1"
            usage
            exit 1
            ;;
    esac
done

cd "$SCRIPT_DIR"

export COMPOSE_PROJECT_NAME="$PROJECT_NAME"

if [ "$DOWN_V" = true ]; then
    echo "停止并删除所有容器和数据卷..."
    docker compose down -v
    exit 0
fi

if [ "$DOWN" = true ]; then
    echo "停止并删除所有容器..."
    docker compose down
    exit 0
fi

if [ "$BUILD" = true ]; then
    echo "构建镜像..."
    if [ "$API_ONLY" = true ]; then
        echo "构建 API 镜像..."
        docker build -t dbvault-api:latest -f "$SCRIPT_DIR/Dockerfile" "$PROJECT_ROOT"
    elif [ "$FRONTEND_ONLY" = true ]; then
        echo "构建前端镜像..."
        docker build -t dbvault-frontend:latest -f "$SCRIPT_DIR/Dockerfile.frontend" "$PROJECT_ROOT/frontend"
    else
        echo "构建 API 镜像..."
        docker build -t dbvault-api:latest -f "$SCRIPT_DIR/Dockerfile" "$PROJECT_ROOT"
        echo "构建前端镜像..."
        docker build -t dbvault-frontend:latest -f "$SCRIPT_DIR/Dockerfile.frontend" "$PROJECT_ROOT/frontend"
    fi
    echo "镜像构建完成"
fi

echo "启动服务..."
if [ "$API_ONLY" = true ]; then
    docker compose up -d api
elif [ "$FRONTEND_ONLY" = true ]; then
    docker compose up -d frontend
else
    docker compose up -d
fi

echo "部署完成"
