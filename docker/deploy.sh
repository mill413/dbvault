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
    echo "  -a, --api-only           仅构建/部署/导出 API 服务"
    echo "  -f, --frontend-only      仅构建/部署/导出前端服务"
    echo "  -d, --down               停止并删除所有容器"
    echo "  -D, --down-v             停止并删除所有容器和数据卷"
    echo "  -e, --export             导出镜像为 tar 包"
    echo "  -o, --output <dir>       指定导出目录（默认: 当前目录）"
    echo "  -h, --help               显示帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 -p myproject               # 使用 myproject 作为项目名部署"
    echo "  $0 -p myproject -b            # 构建所有镜像后部署"
    echo "  $0 -p myproject -b -a         # 仅构建 API 镜像后部署"
    echo "  $0 -e                         # 导出所有镜像到当前目录"
    echo "  $0 -e -a -o /tmp              # 仅导出 API 镜像到 /tmp"
    echo "  $0 -d                         # 停止所有容器"
    echo "  $0 -D                         # 停止所有容器并删除数据卷"
    echo ""
    echo "环境变量:"
    echo "  默认读取项目根目录的 .env 文件；当前 shell 已设置的变量优先。"
    echo ""
    echo "K8s 支持说明:"
    echo "  K8s 集群配置现在通过前端界面管理，无需手动配置 kubeconfig。"
    echo "  部署后在前端的「数据库实例」页面中添加 K8s 类型的数据库时，"
    echo "  可以直接上传 kubeconfig 文件。"
}

PROJECT_NAME="dbvault"
BUILD=false
API_ONLY=false
FRONTEND_ONLY=false
DOWN=false
DOWN_V=false
EXPORT=false
OUTPUT_DIR="."

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
        -e|--export)
            EXPORT=true
            shift
            ;;
        -o|--output)
            OUTPUT_DIR="$2"
            shift 2
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

set_compose_placeholder_env() {
    export DBVAULT_POSTGRES_PASSWORD="${DBVAULT_POSTGRES_PASSWORD:-unused-for-compose-down}"
    export DBVAULT_JWT_SECRET="${DBVAULT_JWT_SECRET:-unused-for-compose-down}"
    export DBVAULT_ENCRYPTION_KEY="${DBVAULT_ENCRYPTION_KEY:-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=}"
}

print_secret_help() {
    echo ""
    echo "请使用强随机密钥部署，例如："
    echo "  export DBVAULT_POSTGRES_PASSWORD='请替换为强密码'"
    echo "  export DBVAULT_JWT_SECRET='请替换为强随机字符串'"
    echo "  export DBVAULT_ENCRYPTION_KEY=\"\$(python3 -c 'import base64, os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())')\""
    echo "  $0 -b"
}

load_env_file() {
    local env_file="$PROJECT_ROOT/.env"
    if [ ! -f "$env_file" ]; then
        return
    fi

    echo "加载环境变量: $env_file"
    local existing_names=()
    local existing_values=()
    local line name
    while IFS= read -r line || [ -n "$line" ]; do
        if [[ "$line" =~ ^[[:space:]]*(export[[:space:]]+)?([A-Za-z_][A-Za-z0-9_]*)[[:space:]]*= ]]; then
            name="${BASH_REMATCH[2]}"
            if [[ -v "$name" ]]; then
                existing_names+=("$name")
                existing_values+=("${!name}")
            fi
        fi
    done < "$env_file"

    set -a
    # shellcheck disable=SC1090
    . "$env_file"
    set +a

    for i in "${!existing_names[@]}"; do
        export "${existing_names[$i]}=${existing_values[$i]}"
    done
}

require_env() {
    local name="$1"
    if [ -z "${!name:-}" ]; then
        echo "错误: 缺少环境变量 $name"
        return 1
    fi
}

validate_encryption_key() {
    python3 - "$DBVAULT_ENCRYPTION_KEY" <<'PY'
import base64
import binascii
import sys

key = sys.argv[1].encode("utf-8")
try:
    decoded = base64.urlsafe_b64decode(key)
except (binascii.Error, ValueError):
    sys.exit(1)
if len(decoded) != 32:
    sys.exit(1)
PY
}

validate_deploy_env() {
    local ok=true
    require_env DBVAULT_POSTGRES_PASSWORD || ok=false
    require_env DBVAULT_JWT_SECRET || ok=false
    require_env DBVAULT_ENCRYPTION_KEY || ok=false

    if [ "$ok" != true ]; then
        print_secret_help
        exit 1
    fi

    if ! command -v python3 >/dev/null 2>&1; then
        echo "错误: 需要 python3 来校验 DBVAULT_ENCRYPTION_KEY。"
        exit 1
    fi

    if ! validate_encryption_key; then
        echo "错误: DBVAULT_ENCRYPTION_KEY 必须是 32 字节 URL-safe base64 编码的 Fernet 密钥。"
        echo "当前值无法用于生产环境加密。"
        print_secret_help
        exit 1
    fi
}

load_env_file
cd "$SCRIPT_DIR"

export COMPOSE_PROJECT_NAME="$PROJECT_NAME"

if [ "$DOWN_V" = true ]; then
    echo "停止并删除所有容器和数据卷..."
    set_compose_placeholder_env
    docker compose down -v
    exit 0
fi

if [ "$DOWN" = true ]; then
    echo "停止并删除所有容器..."
    set_compose_placeholder_env
    docker compose down
    exit 0
fi

if [ "$EXPORT" = true ]; then
    TIMESTAMP=$(date +%Y%m%d-%H%M%S)
    mkdir -p "$OUTPUT_DIR"

    if [ "$API_ONLY" = true ]; then
        echo "导出 API 镜像..."
        docker save dbvault-api:latest -o "$OUTPUT_DIR/dbvault-api-${TIMESTAMP}.tar"
        echo "API 镜像已导出: $OUTPUT_DIR/dbvault-api-${TIMESTAMP}.tar"
    elif [ "$FRONTEND_ONLY" = true ]; then
        echo "导出前端镜像..."
        docker save dbvault-frontend:latest -o "$OUTPUT_DIR/dbvault-frontend-${TIMESTAMP}.tar"
        echo "前端镜像已导出: $OUTPUT_DIR/dbvault-frontend-${TIMESTAMP}.tar"
    else
        echo "导出所有镜像..."
        docker save dbvault-api:latest dbvault-frontend:latest -o "$OUTPUT_DIR/dbvault-all-${TIMESTAMP}.tar"
        echo "所有镜像已导出: $OUTPUT_DIR/dbvault-all-${TIMESTAMP}.tar"
    fi
    exit 0
fi

validate_deploy_env

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

if [ "$FRONTEND_ONLY" != true ]; then
    echo "执行数据库迁移..."
    docker compose up -d postgres redis
    docker compose run --rm api alembic upgrade head
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
