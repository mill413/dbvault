# DBVault

**中文** | **[English](README.md)**

**集中式、无代理的数据库备份与恢复平台。**

DBVault 提供统一的管理界面，用于调度、执行和监控跨基础设施的数据库备份任务。基于 FastAPI 和 Vue 3 构建，支持 MySQL、PostgreSQL 和 MariaDB，兼容本地文件系统和 S3 兼容存储后端。

---

## 功能特性

- **无代理备份** — 无需在目标主机安装代理即可进行远程逻辑备份
- **多数据库支持** — MySQL、PostgreSQL、MariaDB（可扩展架构）
- **Kubernetes 集成** — 通过 kubeconfig 对数据库 Pod 进行备份和恢复，支持命名空间/Pod/标签选择
- **灵活存储** — 本地文件系统、MinIO 及 S3 兼容对象存储
- **定时任务** — 基于 APScheduler 的 Cron 和间隔调度
- **备份校验** — SHA256/MD5 校验和，恢复前完整性检查
- **压缩支持** — zstd（默认）和 gzip
- **基于角色的访问控制** — Admin、Operator、Viewer 三种角色，完整审计日志
- **存储容量监控** — 按存储设置容量上限，超限告警
- **自助注册** — 可配置的用户自助注册开关
- **仪表盘** — 实时备份趋势、存储用量和告警概览
- **RESTful API** — 完整的 CRUD 接口，自动生成 OpenAPI 文档
- **CI/CD** — 基于 GitHub Actions 自动构建 Docker 镜像并发布到 Releases
- **国际化** — 完整的中英文界面支持

## 技术栈

| 层级 | 技术选型 |
| ---- | -------- |
| 后端 | Python 3.11+, FastAPI, SQLAlchemy 2.0, Alembic |
| 前端 | Vue 3, Element Plus, ECharts, Pinia, Axios |
| 数据库 | PostgreSQL（元数据），目标数据库（备份源） |
| 存储 | 本地文件系统, MinIO/S3（基于 boto3） |
| 任务调度 | APScheduler |
| 认证 | JWT (python-jose), bcrypt, passlib |
| 容器化 | Docker, Docker Compose |

## 快速开始

### Docker Compose（推荐）

```bash
cd docker
./deploy.sh -b
```

该命令会构建 API 和前端镜像，并启动完整的技术栈，包括用于测试的示例 MySQL 和 PostgreSQL 实例。

**默认凭据：** `admin` / `admin123456789`

### 部署脚本使用说明

```bash
./deploy.sh [选项]

选项：
  -p <project>             项目名称（默认：dbvault）
  -b, --build              部署前构建镜像
  -n, --no-build           使用已有镜像（默认）
  -a, --api-only           仅构建/部署 API 服务
  -f, --frontend-only      仅构建/部署前端服务
  -d, --down               停止并移除所有容器
  -D, --down-v             停止并移除所有容器和数据卷
  -h, --help               显示帮助信息
```

**示例：**

```bash
./deploy.sh -b                    # 构建所有镜像并部署
./deploy.sh -b -a                 # 仅重建并部署 API
./deploy.sh -b -f                 # 仅重建并部署前端
./deploy.sh -p myproject -b       # 使用自定义项目名部署
./deploy.sh -d                    # 停止所有服务
./deploy.sh -D                    # 停止所有服务并删除数据卷
```

### 本地开发

**后端：**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

**前端：**

```bash
cd frontend
npm install
npm run dev
```

**数据库迁移：**

```bash
alembic upgrade head          # 应用所有迁移
alembic revision --autogenerate -m "description"   # 创建新迁移
```

## 配置

所有配置通过环境变量管理（前缀 `DBVAULT_`）：

| 变量名 | 默认值 | 说明 |
| ------ | ------ | ---- |
| `DBVAULT_DATABASE_URL` | `postgresql+psycopg://dbvault:dbvault@db:5432/dbvault` | 元数据库连接字符串 |
| `DBVAULT_JWT_SECRET` | *(必填)* | JWT 令牌签名密钥 |
| `DBVAULT_ENABLE_REGISTRATION` | `false` | 启用/禁用用户自助注册 |
| `DBVAULT_OPENAPI_ENABLED` | `true` | 启用/禁用 OpenAPI 文档端点 |
| `DBVAULT_BACKUP_TMP_DIR` | `/tmp/dbvault-backups` | 备份处理临时目录 |
| `DBVAULT_LOCAL_STORAGE_ROOT` | `/var/lib/dbvault/backups` | 本地存储后端根目录 |
| `DBVAULT_RUN_BACKGROUND_TASKS_INLINE` | `false` | 同步运行后台任务（仅开发环境） |

完整配置参考 [`.env.example`](.env.example)。

## 项目结构

```text
dbvault/
├── app/                    # 后端应用
│   ├── api/v1/            # REST API 端点
│   ├── core/              # 配置、安全、日志
│   ├── drivers/           # 数据库和存储驱动实现
│   ├── models/            # SQLAlchemy 模型
│   ├── schemas/           # Pydantic 请求/响应模型
│   └── services/          # 业务逻辑层
├── alembic/               # 数据库迁移
├── frontend/              # Vue 3 前端应用
│   ├── src/
│   │   ├── api/           # API 客户端模块
│   │   ├── views/         # 页面组件
│   │   ├── stores/        # Pinia 状态管理
│   │   ├── locales/       # 国际化翻译
│   │   └── utils/         # 共享工具函数
│   └── vite.config.js
├── docker/                # Docker 配置和部署脚本
│   ├── Dockerfile         # API 服务镜像（多阶段构建含 kubectl）
│   ├── Dockerfile.frontend # 前端服务镜像
│   ├── docker-compose.yml
│   └── deploy.sh          # 部署自动化脚本
├── .github/workflows/     # GitHub Actions CI/CD
├── tests/                 # 后端测试套件
├── design.md              # 详细设计文档
└── pyproject.toml         # Python 项目配置
```

## 测试

```bash
# 运行所有测试并生成覆盖率报告
pytest

# 代码检查和类型检查
ruff check app tests alembic
```

## 示例数据库（Docker Compose）

开发环境包含预配置的示例数据库：

| 数据库类型   | 主机      | 端口  | 数据库名  | 用户名   | 密码              |
| ------------ | --------- | ----- | --------- | -------- | ----------------- |
| MySQL        | localhost | 3306  | `orders`  | `backup` | `backup-password` |
| PostgreSQL   | localhost | 15432 | `reports` | `backup` | `backup-password` |

## 架构设计

```text
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  Vue 3 前端  │────▶│  FastAPI API  │────▶│   PostgreSQL    │
│             │     │   (Uvicorn)   │     │    (元数据库)    │
└─────────────┘     └──────┬───────┘     └─────────────────┘
                           │
                    ┌──────┴───────┐
                    │    驱动层     │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┬────────────┐
              ▼            ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
        │  MySQL   │ │PostgreSQL│ │  K8s Pod │ │  MinIO   │
        │  目标库   │ │  目标库   │ │ (kubectl │ │   S3     │
        │          │ │          │ │   exec)  │ │          │
        └──────────┘ └──────────┘ └──────────┘ └──────────┘
```

## CI/CD

每次推送到 `main` 分支时，GitHub Actions 会自动构建 Docker 镜像并发布到 Releases。

**下载并加载预构建镜像：**

```bash
gh release download --repo mill413/dbvault -p '*.tar.gz'
docker load -i dbvault-images-*.tar.gz
docker compose -f docker/docker-compose.yml up -d
```

## 许可证

本项目仅供内部使用。
