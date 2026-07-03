<p align="center">
  <b>中文</b> | <a href="README.md">English</a>
</p>

<h1 align="center">DBVault</h1>

<p align="center">
  <b>集中式、无代理的数据库备份与恢复平台。</b>
</p>

<p align="center">
  <a href="https://github.com/mill413/dbvault/actions/workflows/build-and-release.yml">
    <img src="https://img.shields.io/github/actions/workflow/status/mill413/dbvault/build-and-release.yml?style=flat-square&label=CI" alt="CI">
  </a>
  <a href="https://github.com/mill413/dbvault/releases">
    <img src="https://img.shields.io/github/v/release/mill413/dbvault?style=flat-square&label=Release" alt="Release">
  </a>
  <a href="https://github.com/mill413/dbvault/blob/main/LICENSE">
    <img src="https://img.shields.io/github/license/mill413/dbvault?style=flat-square" alt="License">
  </a>
  <img src="https://img.shields.io/badge/Python-3.11+-blue?style=flat-square&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/Vue-3.x-brightgreen?style=flat-square&logo=vuedotjs" alt="Vue">
</p>

---

DBVault 提供统一的管理界面，用于调度、执行和监控跨基础设施的数据库备份任务。支持 MySQL、PostgreSQL 和 MariaDB，兼容本地文件系统和 S3 兼容存储后端。基于 **FastAPI** 和 **Vue 3** 构建，提供现代化 Web UI、完整的 REST API 以及 Kubernetes 集成。

## 目录

- [功能特性](#功能特性)
- [系统架构](#系统架构)
- [技术栈](#技术栈)
- [界面预览](#界面预览)
- [快速开始](#快速开始)
  - [Docker Compose（推荐）](#docker-compose推荐)
  - [预构建镜像](#预构建镜像)
  - [本地开发](#本地开发)
- [升级指南](#升级指南)
- [配置说明](#配置说明)
- [API 文档](#api-文档)
- [项目结构](#项目结构)
- [开发指南](#开发指南)
- [CI/CD](#cicd)
- [参与贡献](#参与贡献)
- [许可证](#许可证)

## 功能特性

### 核心能力

- **无代理备份** — 通过 `mysqldump`/`pg_dump` 进行远程逻辑备份，无需在目标主机安装任何代理
- **多数据库支持** — MySQL、PostgreSQL、MariaDB，可扩展的驱动架构便于未来添加新数据库类型
- **Kubernetes 集成** — 通过 kubeconfig 对数据库 Pod 进行备份和恢复，支持命名空间/Pod/标签选择
- **灵活存储** — 本地文件系统、MinIO 及 S3 兼容对象存储，可插拔的存储驱动设计
- **定时任务** — 基于 APScheduler 的 Cron 和间隔调度，支持一次性任务
- **备份校验** — SHA256/MD5 校验和，恢复前自动进行完整性验证
- **压缩支持** — zstd（默认，高压缩比）和 gzip
- **一键恢复** — 支持恢复到原实例或新实例，带进度追踪和事件日志

### 安全与权限控制

- **基于角色的访问控制（RBAC）** — Admin、User 两种角色，细粒度权限管理
- **JWT 认证** — Access/Refresh Token 双令牌机制，可配置过期时间
- **凭据加密** — 数据库连接凭据使用 Fernet 对称加密存储
- **完整审计日志** — 所有操作均记录用户、动作、资源和时间戳

### 运维与监控

- **仪表盘** — 实时备份趋势、存储容量使用和告警概览，基于 ECharts 可视化
- **存储容量监控** — 按存储设置容量上限，超阈值自动告警
- **告警系统** — 备份失败、恢复失败、存储异常、容量预警
- **审计追踪** — 完整的操作历史，满足合规和排障需求

### 开发者体验

- **RESTful API** — 完整的 CRUD 接口，自动生成 OpenAPI/Swagger 文档
- **国际化** — 完整的中英文界面支持
- **CI/CD** — 基于 GitHub Actions 自动构建 Docker 镜像并发布到 Releases
- **自助注册** — 可配置的用户自助注册开关

## 系统架构

```
┌──────────────────────────────────────────────────────────────────┐
│                        Vue 3 前端                                 │
│            Element Plus · ECharts · Pinia · Axios                │
└─────────────────────────────┬────────────────────────────────────┘
                              │ REST API
┌─────────────────────────────┴────────────────────────────────────┐
│                       FastAPI 后端                                │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  ┌───────────────┐  │
│  │ 认证与    │  │ 备份     │  │ 恢复      │  │ 调度器        │  │
│  │ RBAC     │  │ 服务     │  │ 服务      │  │ (APScheduler) │  │
│  └──────────┘  └──────────┘  └───────────┘  └───────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                     驱动注册中心                           │   │
│  │  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │   │
│  │  │  数据库驱动  │  │  存储驱动     │  │  压缩驱动      │  │   │
│  │  │ MySQL/PgSQL  │  │ Local/S3     │  │ zstd/gzip      │  │   │
│  │  └─────────────┘  └──────────────┘  └────────────────┘  │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────┬────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────┴───────┐   ┌────────┴────────┐   ┌────────┴────────┐
│  PostgreSQL   │   │  目标数据库      │   │  存储后端        │
│  （元数据）    │   │  MySQL/PgSQL    │   │  本地 FS / S3   │
│               │   │  MariaDB/K8s    │   │  MinIO          │
└───────────────┘   └─────────────────┘   └─────────────────┘
```

> 完整设计文档请参阅 [design.md](design.md)。

## 技术栈

| 层级 | 技术选型 |
| --- | --- |
| **后端** | Python 3.11+、FastAPI、SQLAlchemy 2.0、Alembic、structlog |
| **前端** | Vue 3、Element Plus、ECharts、Pinia、Axios、vue-i18n |
| **元数据库** | PostgreSQL 16（生产环境）、SQLite（开发环境） |
| **存储** | 本地文件系统、MinIO、S3 兼容存储（boto3） |
| **任务调度** | APScheduler（Cron / Interval / 一次性） |
| **认证** | JWT (python-jose)、bcrypt、passlib、Fernet 加密 |
| **容器化** | Docker、Docker Compose |
| **CI/CD** | GitHub Actions |
| **测试** | pytest、pytest-cov、ruff |

## 界面预览

| 仪表盘 | 数据库管理 |
| --- | --- |
| ![仪表盘](docs/screenshots/dashboard.png) | ![数据库管理](docs/screenshots/databases.png) |

| 备份管理 | 定时任务 |
| --- | --- |
| ![备份管理](docs/screenshots/backups.png) | ![定时任务](docs/screenshots/jobs.png) |

## 快速开始

### Docker Compose（推荐）

最快的启动方式。该命令会构建 API 和前端镜像，并启动包含 PostgreSQL 和 Redis 的完整技术栈。

```bash
cd docker
./deploy.sh -b
```

启动成功后：

- **前端界面：** `http://localhost:5173`
- **API 服务：** `http://localhost:8000`
- **API 文档：** `http://localhost:8000/docs`

**默认凭据：** `admin` / `admin123456789`

> **注意：** 生产环境请务必修改 `DBVAULT_JWT_SECRET`，默认值仅用于开发环境。

#### 部署脚本使用说明

```bash
./deploy.sh [选项]

选项：
  -p <project>             项目名称（默认：dbvault）
  -b, --build              部署前构建镜像
  -n, --no-build           使用已有镜像（默认）
  -a, --api-only           仅构建/部署 API 服务
  -f, --frontend-only      仅构建/部署前端服务
  -d, --down               停止并移除所有容器
  -D, --down-v             停止并移除容器和数据卷
  -e, --export             导出镜像为 tar 包
  -o, --output <dir>       指定导出目录（默认：当前目录）
  -h, --help               显示帮助信息
```

**示例：**

```bash
./deploy.sh -b                    # 构建所有镜像并部署
./deploy.sh -b -a                 # 仅重建并部署 API
./deploy.sh -b -f                 # 仅重建并部署前端
./deploy.sh -p myproject -b       # 使用自定义项目名部署
./deploy.sh -e -o /tmp            # 导出已构建镜像到 /tmp
./deploy.sh -d                    # 停止所有服务
./deploy.sh -D                    # 停止所有服务并删除数据卷
```

### 预构建镜像

预构建的 Docker 镜像随每次推送到 `main` 发布至 [GitHub Releases](https://github.com/mill413/dbvault/releases)。

```bash
# 下载最新版本
gh release download --repo mill413/dbvault -p '*.tar.gz'

# 加载镜像
docker load -i dbvault-images-*.tar.gz

# 启动服务
docker compose -f docker/docker-compose.yml up -d
```

### 本地开发

适用于不使用 Docker 的开发场景。需要 Python 3.11+ 和 Node.js 18+。

**前置条件：**

- PostgreSQL 16+（或使用默认配置中的 SQLite）
- Redis 7+
- Node.js 18+ 和 npm

**后端：**

```bash
# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -e ".[dev]"

# 配置环境变量
cp .env.example .env
# 根据需要编辑 .env

# 执行数据库迁移
alembic upgrade head

# 启动 API 服务（支持热重载）
uvicorn app.main:app --reload --port 8000
```

**前端：**

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器（自带 API 代理）
npm run dev
```

**数据库迁移：**

```bash
# 应用所有待执行的迁移
alembic upgrade head

# 模型变更后创建新迁移
alembic revision --autogenerate -m "描述信息"

# 回滚最近一次迁移
alembic downgrade -1
```

## 升级指南

升级正在运行的服务前，应先备份元数据库和 DBVault 本地数据卷，确保 Git 工作区、Docker 镜像和 Alembic 迁移处于同一版本，执行 `alembic upgrade head` 后再重启 API 与前端容器。

源码升级、发布镜像升级、升级后验证和回滚步骤见 [docs/UPGRADE_CN.md](docs/UPGRADE_CN.md)。

## 配置说明

所有配置通过环境变量管理（前缀 `DBVAULT_`）。完整配置参考 [`.env.example`](.env.example)。

### 应用配置

| 变量名 | 默认值 | 说明 |
| --- | --- | --- |
| `DBVAULT_ENV` | `dev` | 运行环境（`dev` / `prod`） |
| `DBVAULT_LOG_LEVEL` | `INFO` | 日志级别（`DEBUG` / `INFO` / `WARNING` / `ERROR`） |
| `DBVAULT_OPENAPI_ENABLED` | `true` | 启用/禁用 `/docs` 的 Swagger UI |

### 数据库

| 变量名 | 默认值 | 说明 |
| --- | --- | --- |
| `DBVAULT_DATABASE_URL` | `sqlite:///./dbvault.db` | 元数据库连接字符串 |

> 生产环境请使用 `postgresql+psycopg://user:pass@host:port/db`。

### 认证与安全

| 变量名 | 默认值 | 说明 |
| --- | --- | --- |
| `DBVAULT_JWT_SECRET` | `change-me-in-production` | **生产环境必填。** JWT 签名密钥 |
| `DBVAULT_ENCRYPTION_KEY` | *（自动生成）* | 用于加密存储凭据的 Fernet 密钥 |
| `DBVAULT_ENABLE_REGISTRATION` | `false` | 是否允许用户自助注册 |
| `DBVAULT_INITIAL_ADMIN_USERNAME` | `admin` | 首次启动时的默认管理员用户名 |
| `DBVAULT_INITIAL_ADMIN_PASSWORD` | `admin123456789` | 首次启动时的默认管理员密码（最少 12 位） |

### 存储配置

| 变量名 | 默认值 | 说明 |
| --- | --- | --- |
| `DBVAULT_BACKUP_TMP_DIR` | `./dbvault_tmp` | 备份处理临时目录 |
| `DBVAULT_LOCAL_STORAGE_ROOT` | `./dbvault_backups` | 本地存储后端根目录 |
| `DBVAULT_KUBECONFIG_DIR` | `/var/lib/dbvault/kubeconfigs` | 上传 kubeconfig 文件的保存目录 |

### 高级配置

| 变量名 | 默认值 | 说明 |
| --- | --- | --- |
| `DBVAULT_REDIS_URL` | `redis://localhost:6379/0` | Redis 连接地址 |
| `DBVAULT_SCHEDULER_ENABLED` | `true` | 启用/禁用后台任务调度器 |
| `DBVAULT_RUN_BACKGROUND_TASKS_INLINE` | `false` | 同步运行后台任务（仅开发/测试环境） |
| `DBVAULT_INITIAL_ADMIN_USERNAME` | `admin` | 首次启动时创建的管理员用户名 |
| `DBVAULT_INITIAL_ADMIN_PASSWORD` | `admin123456789` | 首次启动时创建的管理员密码 |

## API 文档

API 按以下模块组织：

| 模块 | 路径前缀 | 说明 |
| --- | --- | --- |
| **认证** | `/api/v1/auth` | 登录、令牌刷新、用户信息 |
| **用户** | `/api/v1/users` | 用户管理和角色控制 |
| **数据库** | `/api/v1/databases` | 数据库实例注册与连通性测试 |
| **存储** | `/api/v1/storages` | 存储后端管理 |
| **备份** | `/api/v1/backups` | 备份执行、下载和元数据管理 |
| **恢复** | `/api/v1/restore`、`/api/v1/restore-tasks` | 恢复执行和进度追踪 |
| **任务** | `/api/v1/jobs` | 定时任务配置和控制 |
| **告警** | `/api/v1/alerts` | 告警查询和确认 |
| **审计** | `/api/v1/audit-logs` | 操作审计日志 |
| **Kubeconfig** | `/api/v1/kubeconfigs` | Kubernetes 集群配置管理 |
| **仪表盘** | `/api/v1/dashboard` | 统计摘要和趋势数据 |

当 `DBVAULT_OPENAPI_ENABLED=true` 时，可通过 `http://localhost:8000/docs` 访问交互式 API 文档。

## 项目结构

```text
dbvault/
├── app/                        # 后端应用
│   ├── api/v1/                 # REST API 端点处理器
│   │   ├── auth.py             #   认证（登录/刷新）
│   │   ├── backups.py          #   备份操作
│   │   ├── databases.py        #   数据库实例管理
│   │   ├── jobs.py             #   定时任务管理
│   │   ├── restores.py         #   恢复操作
│   │   ├── storages.py         #   存储后端管理
│   │   └── router.py           #   API 路由注册
│   ├── core/                   # 框架层
│   │   ├── config.py           #   配置管理（pydantic-settings）
│   │   ├── database.py         #   SQLAlchemy 引擎与会话
│   │   ├── encryption.py       #   Fernet 凭据加密
│   │   ├── errors.py           #   自定义异常处理
│   │   ├── logging.py          #   结构化日志（structlog）
│   │   └── security.py         #   JWT 与密码工具
│   ├── drivers/                # 可插拔驱动系统
│   │   ├── database/           #   MySQL、PostgreSQL、K8s 驱动
│   │   ├── storage/            #   本地 FS、S3 驱动
│   │   ├── compression/        #   zstd、gzip 驱动
│   │   ├── bootstrap.py        #   驱动自动注册
│   │   └── registry.py         #   驱动注册中心
│   ├── models/                 # SQLAlchemy ORM 模型
│   ├── schemas/                # Pydantic 请求/响应模型
│   ├── services/               # 业务逻辑层
│   ├── scheduler/              # APScheduler 集成
│   └── main.py                 # FastAPI 应用入口
├── alembic/                    # 数据库迁移脚本
├── frontend/                   # Vue 3 前端应用
│   ├── src/
│   │   ├── api/                #   API 客户端模块
│   │   ├── assets/             #   全局样式
│   │   ├── locales/            #   国际化翻译（中/英）
│   │   ├── router/             #   Vue Router 路由配置
│   │   ├── stores/             #   Pinia 状态管理
│   │   ├── utils/              #   工具函数
│   │   ├── views/              #   页面组件
│   │   ├── App.vue             #   根组件
│   │   └── main.js             #   应用入口
│   └── vite.config.js          #   Vite 构建配置
├── docker/                     # 容器配置
│   ├── Dockerfile              #   API 服务镜像（多阶段构建，含 kubectl）
│   ├── Dockerfile.frontend     #   前端服务镜像
│   ├── docker-compose.yml      #   开发环境编排
│   └── deploy.sh               #   部署自动化脚本
├── tests/                      # 后端测试套件
├── .github/workflows/          # GitHub Actions CI/CD
├── design.md                   # 详细设计文档
├── pyproject.toml              # Python 项目配置
└── .env.example                # 环境变量参考
```

## 开发指南

### 测试

```bash
# 运行所有测试并生成覆盖率报告
pytest

# 运行指定测试文件
pytest tests/test_auth_rbac.py

# 详细输出模式
pytest -v

# 运行基于 Docker 的 MySQL、PostgreSQL 和 MinIO 真实集成测试
scripts/run_integration_tests.sh
```

### 代码质量

```bash
# 检查所有 Python 代码
ruff check app tests alembic

# 自动修复代码问题
ruff check --fix app tests alembic
```

### 添加新驱动

驱动系统支持可插拔扩展。添加新的数据库、存储或压缩驱动：

1. 在 `app/drivers/<type>/` 下创建新模块
2. 实现对应的基类（`BaseDatabaseDriver`、`BaseStorageDriver` 或 `BaseCompressionDriver`）
3. 在 `app/drivers/bootstrap.py` 中注册

可参考现有驱动的实现作为示例。

## CI/CD

每次推送到 `main` 分支会触发 [GitHub Actions](.github/workflows/build-and-release.yml) 工作流：

1. 运行 Ruff、pytest 和前端生产构建
2. 构建 API 和前端 Docker 镜像
3. 使用 commit SHA 和时间戳进行标记
4. 导出为 `.tar.gz` 归档文件
5. 创建 GitHub Release 并附带归档文件

## 参与贡献

欢迎贡献代码，请遵循以下流程：

1. Fork 本仓库
2. 创建功能分支（`git checkout -b feature/amazing-feature`）
3. 保持提交聚焦，并使用 conventional commit，例如 `fix(restore): require target database`
4. 运行 `ruff check app tests alembic`、`pytest` 和 `cd frontend && npm run build`
5. 前端可见变更需要附截图
6. 推送分支并发起 Pull Request，说明变更内容和验证结果

## 许可证

本项目基于 MIT 许可证开源。详见 [LICENSE](LICENSE) 文件。
