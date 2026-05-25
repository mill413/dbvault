# DBVault 数据库备份平台详细设计文档

版本：v1.0  
来源：基于 `draft.md` 扩展  
适用阶段：MVP 设计评审、研发拆解、接口联调、部署验收

---

## 1. 文档目标

本文档用于描述 DBVault 数据库备份平台的详细技术设计，覆盖系统目标、架构、模块、数据模型、接口、任务流转、安全、部署、测试、运维和阶段规划。

本文档重点解决以下问题：

- 平台要解决哪些备份与恢复问题。
- MVP 阶段支持哪些数据库、存储和操作流程。
- 后端、前端、调度器、存储服务、备份驱动之间如何协作。
- 备份任务、恢复任务、定时任务的状态如何流转。
- 元数据、审计日志、校验信息、生命周期策略如何落库。
- 权限、安全、密钥、凭据、审计和操作风险如何控制。
- 后续扩展新数据库、新存储、新压缩算法时如何接入。

---

## 2. 背景与问题

部门内部存在大量数据库实例，包含 MySQL、PostgreSQL、MongoDB、Redis、ClickHouse、MariaDB 等。当前备份方式主要依赖人工维护脚本和零散存储，缺少统一平台能力。

现状问题如下：

| 问题 | 说明 | 风险 |
| --- | --- | --- |
| 脚本分散 | 不同团队、不同实例使用不同脚本 | 难以维护、不可复用 |
| 缺少统一调度 | 定时任务散落在 crontab 或服务器脚本中 | 任务不可见、失败不易发现 |
| 缺少统一权限 | 任何持有脚本权限的人都可能执行备份或恢复 | 误操作、越权操作 |
| 缺少备份校验 | 只生成文件，不验证文件完整性 | 备份不可用时无法提前发现 |
| 缺少恢复验证 | 未定期验证备份是否可恢复 | 灾难恢复时失败风险高 |
| 缺少生命周期管理 | 备份文件长期堆积或被误删 | 存储成本高、合规风险 |
| 缺少可视化 | 无法统一查看备份状态、容量趋势、失败原因 | 运维效率低 |
| 缺少统一存储 | 本地磁盘、NFS、对象存储混用 | 数据分散、迁移困难 |

DBVault 的目标是提供一个轻量化、可扩展、以 Python 技术栈为核心的统一数据库备份与恢复平台。

---

## 3. 建设目标

### 3.1 核心目标

DBVault 首期需要具备以下核心能力：

- 支持远程数据库逻辑备份。
- 支持 Agentless 模式，不要求目标数据库主机安装 Agent。
- 支持手动上传备份文件并纳入平台管理。
- 支持本地文件系统、MinIO、S3 Compatible 存储。
- 支持定时任务、手动任务和一次性任务。
- 支持备份文件压缩、哈希校验和恢复前校验。
- 支持一键恢复、恢复到新实例、备份文件下载。
- 支持 RESTful API 和 OpenAPI 文档。
- 支持用户、角色、权限和审计日志。
- 支持基础告警，包括备份失败、校验失败、恢复失败、存储异常。

### 3.2 MVP 范围

MVP 优先支持：

| 能力 | MVP 支持范围 |
| --- | --- |
| 数据库 | MySQL、PostgreSQL、MariaDB |
| 存储 | Local FS、MinIO |
| 任务 | 手动备份、Cron 定时备份、Interval 定时备份 |
| 恢复 | 下载恢复、恢复到新实例、原实例恢复需要强确认 |
| 校验 | SHA256 必选，MD5 可选 |
| 压缩 | zstd 默认，gzip 可选 |
| 权限 | Admin、Operator、Viewer |
| API | 完整 CRUD 和任务执行接口 |
| 前端 | Vue3 + Element Plus 管理台 |

### 3.3 非目标

以下能力不纳入 MVP，但保留扩展点：

- 物理备份。
- 增量备份。
- 跨地域灾备编排。
- 自动恢复验证环境的完整生命周期管理。
- 多租户强隔离。
- Agent 模式。
- Restic 去重存储。
- Oracle、SQLServer、TiDB、Elasticsearch。

---

## 4. 术语定义

| 术语 | 定义 |
| --- | --- |
| Database Instance | 平台管理的数据库连接对象，例如一个 MySQL 实例 |
| Backup | 一次备份产物及其元数据 |
| Backup Task | 一次备份执行任务，包含执行状态、日志、耗时等 |
| Restore Task | 一次恢复执行任务 |
| Job | 定时任务定义，用于周期性触发备份 |
| Storage | 备份文件存储后端，如 Local FS、MinIO、S3 |
| Driver | 数据库、存储、压缩等适配层 |
| Checksum | 文件哈希校验值，默认 SHA256 |
| Retention | 备份保留策略 |
| Agentless | 平台通过远程连接数据库执行备份，不在目标机器部署 Agent |

---

## 5. 总体架构

### 5.1 架构图

```text
                           ┌─────────────────────┐
                           │      Web Console     │
                           │ Vue3 + Element Plus  │
                           └──────────┬──────────┘
                                      │ HTTPS / REST
                           ┌──────────▼──────────┐
                           │      FastAPI API     │
                           │ OpenAPI / Pydantic   │
                           └──────────┬──────────┘
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        │                             │                             │
┌───────▼────────┐          ┌─────────▼─────────┐          ┌────────▼────────┐
│ Auth Service   │          │ Backup Service    │          │ Restore Service │
│ JWT / RBAC     │          │ Driver Orchestrat │          │ Validate / Exec │
└───────┬────────┘          └─────────┬─────────┘          └────────┬────────┘
        │                             │                             │
        │                   ┌─────────▼─────────┐                   │
        │                   │ Scheduler Service │                   │
        │                   │ APScheduler       │                   │
        │                   └─────────┬─────────┘                   │
        │                             │                             │
        │                   ┌─────────▼─────────┐                   │
        │                   │ Task Executor     │                   │
        │                   │ Process / Queue   │                   │
        │                   └─────────┬─────────┘                   │
        │                             │                             │
┌───────▼────────┐          ┌─────────▼─────────┐          ┌────────▼────────┐
│ PostgreSQL     │          │ Driver Registry   │          │ Audit / Logging │
│ Metadata DB    │          │ DB/Storage/Compress│         │ Event Records   │
└────────────────┘          └─────────┬─────────┘          └─────────────────┘
                                      │
                        ┌─────────────┼─────────────┐
                        │                           │
               ┌────────▼────────┐         ┌────────▼────────┐
               │ Database Driver │         │ Storage Driver  │
               │ mysqldump/pg_dump│        │ Local/MinIO/S3  │
               └────────┬────────┘         └────────┬────────┘
                        │                           │
              ┌─────────▼─────────┐       ┌─────────▼─────────┐
              │ Source Databases  │       │ Backup Repository │
              │ MySQL/PostgreSQL  │       │ FS / Object Store │
              └───────────────────┘       └───────────────────┘
```

### 5.2 架构说明

系统采用单体优先、模块化分层的架构。MVP 阶段不引入过重的微服务拆分，避免增加部署和故障排查复杂度。模块边界通过 Python 包、接口抽象和数据库表结构实现。

主要组件如下：

| 组件 | 说明 |
| --- | --- |
| Web Console | 前端管理台，负责实例、备份、恢复、任务、存储、日志可视化 |
| FastAPI API | 后端 API 层，负责鉴权、参数校验、OpenAPI、业务入口 |
| Auth Service | 用户认证、Token 签发、RBAC 权限校验 |
| Backup Service | 备份编排，选择数据库驱动、压缩驱动、存储驱动并执行任务 |
| Restore Service | 恢复编排，负责下载、校验、解压、执行恢复命令 |
| Scheduler Service | 定时任务管理，MVP 使用 APScheduler |
| Task Executor | 实际执行长耗时任务的运行层，MVP 可使用进程池或后台线程，后续迁移 Celery |
| Driver Registry | 数据库、存储、压缩驱动注册和发现 |
| Metadata DB | PostgreSQL，保存业务元数据 |
| Redis | 缓存、分布式锁、后续 Celery Broker |
| Storage Backend | 本地文件系统、MinIO、AWS S3、NFS |

### 5.3 分层设计

```text
app/
  api/                 API 路由和请求响应模型
  core/                配置、日志、鉴权、安全、异常
  models/              SQLAlchemy ORM 模型
  schemas/             Pydantic Schema
  repositories/        数据访问封装
  services/            业务编排服务
  drivers/             数据库、存储、压缩驱动
  scheduler/           APScheduler 封装
  tasks/               长任务入口
  utils/               通用工具
```

分层职责：

| 层级 | 职责 | 禁止事项 |
| --- | --- | --- |
| API 层 | HTTP 参数校验、权限校验、调用 Service | 不直接拼命令、不直接写存储 |
| Service 层 | 业务流程编排、状态流转、事务控制 | 不暴露 HTTP 细节 |
| Repository 层 | 数据库 CRUD、查询条件封装 | 不包含业务流程 |
| Driver 层 | 适配外部工具、存储 SDK、压缩工具 | 不依赖 API 层 |
| Task 层 | 后台任务入口、长耗时执行 | 不决定权限策略 |

---

## 6. 技术选型

### 6.1 后端技术栈

| 类别 | 技术 | 说明 |
| --- | --- | --- |
| Web 框架 | FastAPI | 异步友好、OpenAPI 自动生成、生态成熟 |
| ORM | SQLAlchemy 2.0 | 类型友好、支持同步和异步模式 |
| Migration | Alembic | 数据库变更管理 |
| Schema | Pydantic | 请求响应模型、配置校验 |
| 元数据库 | PostgreSQL | 保存平台元数据 |
| 缓存 | Redis | 锁、缓存、后续队列 |
| 调度 | APScheduler | MVP 足够轻量 |
| 任务队列 | Celery | Phase 2/3 引入 |
| 对象存储 | boto3 / minio | 兼容 S3 协议 |
| 压缩 | zstd | 压缩比和速度平衡 |
| 加密 | cryptography | AES-GCM 或 Fernet |
| Hash | hashlib | SHA256、MD5 |
| 日志 | structlog / logging | 结构化日志 |
| 测试 | pytest | 单元测试和接口测试 |

### 6.2 前端技术栈

| 类别 | 技术 | 说明 |
| --- | --- | --- |
| 框架 | Vue3 | 组件化、生态稳定 |
| UI | Element Plus | 管理后台组件丰富 |
| 状态管理 | Pinia | 用户状态、权限、全局配置 |
| HTTP | Axios | API 调用和拦截器 |
| 图表 | ECharts | 备份趋势、容量趋势、失败统计 |
| 构建 | Vite | 快速构建 |

### 6.3 外部依赖命令

平台执行逻辑备份依赖数据库官方工具。API 容器或任务执行容器需要安装：

| 数据库 | 备份工具 | 恢复工具 |
| --- | --- | --- |
| MySQL | mysqldump | mysql |
| MariaDB | mysqldump / mariadb-dump | mysql / mariadb |
| PostgreSQL | pg_dump | psql / pg_restore |
| MongoDB | mongodump | mongorestore |
| Redis | redis-cli / 文件采集 | redis-cli |
| ClickHouse | clickhouse-client BACKUP | clickhouse-client RESTORE |

MVP 阶段至少安装 `mysqldump`、`mysql`、`pg_dump`、`psql`、`zstd`。

---

## 7. 核心业务流程

### 7.1 手动备份流程

```text
用户点击立即备份
  ↓
API 校验权限和参数
  ↓
创建 backup_tasks 记录，状态 PENDING
  ↓
提交后台任务
  ↓
任务状态变更为 RUNNING
  ↓
读取数据库实例与存储配置
  ↓
选择 Database Driver
  ↓
执行 dump 命令并流式输出
  ↓
执行压缩
  ↓
计算 SHA256 / MD5
  ↓
上传到存储后端
  ↓
写入 backups 元数据
  ↓
任务状态变更为 SUCCESS
  ↓
触发生命周期清理和告警事件
```

### 7.2 定时备份流程

```text
用户创建 Job
  ↓
保存 jobs 记录
  ↓
注册到 APScheduler
  ↓
到达触发时间
  ↓
Scheduler 生成 Backup Task
  ↓
执行手动备份相同流程
  ↓
更新 Job last_run_at / next_run_at
```

### 7.3 文件上传备份流程

```text
用户选择数据库实例和备份文件
  ↓
API 校验文件类型、大小、权限
  ↓
生成上传任务
  ↓
服务端接收文件并落临时目录
  ↓
计算校验值
  ↓
可选压缩或保持原文件
  ↓
上传到目标存储
  ↓
登记 backups 元数据
  ↓
清理临时文件
```

### 7.4 恢复流程

```text
用户选择备份记录和恢复目标
  ↓
API 校验权限
  ↓
如果恢复到原实例，要求二次确认
  ↓
创建 restore_tasks 记录
  ↓
下载备份文件到临时目录
  ↓
校验 SHA256
  ↓
解压文件
  ↓
选择 Database Driver
  ↓
执行恢复命令
  ↓
收集 stdout/stderr 和退出码
  ↓
更新恢复任务状态
  ↓
写审计日志
```

### 7.5 生命周期清理流程

```text
备份任务完成或定时清理触发
  ↓
读取数据库实例或 Job 绑定的 retention 策略
  ↓
查询候选备份记录
  ↓
按规则计算需要删除的备份
  ↓
删除远端存储对象
  ↓
更新 backups 状态为 DELETED
  ↓
记录审计日志和清理结果
```

---

## 8. 模块详细设计

## 8.1 用户与权限模块

### 8.1.1 功能范围

用户模块负责：

- 用户登录。
- 用户登出。
- Token 刷新。
- 修改密码。
- 管理用户。
- 分配角色。
- 查询当前用户权限。
- 记录登录审计。

### 8.1.2 角色设计

| 角色 | 说明 | 权限范围 |
| --- | --- | --- |
| Admin | 系统管理员 | 用户、存储、实例、备份、恢复、任务、审计全部权限 |
| Operator | 运维操作员 | 实例查看、备份执行、恢复执行、任务管理、日志查看 |
| Viewer | 只读用户 | 只允许查看实例、备份、任务、日志和统计 |

### 8.1.3 权限点设计

| 权限点 | Admin | Operator | Viewer |
| --- | --- | --- | --- |
| user:read | 是 | 否 | 否 |
| user:write | 是 | 否 | 否 |
| database:read | 是 | 是 | 是 |
| database:write | 是 | 是 | 否 |
| backup:read | 是 | 是 | 是 |
| backup:run | 是 | 是 | 否 |
| backup:delete | 是 | 是 | 否 |
| restore:run | 是 | 是 | 否 |
| job:read | 是 | 是 | 是 |
| job:write | 是 | 是 | 否 |
| storage:read | 是 | 是 | 是 |
| storage:write | 是 | 否 | 否 |
| audit:read | 是 | 否 | 否 |

### 8.1.4 Token 设计

采用 Access Token + Refresh Token：

| Token | 默认有效期 | 用途 |
| --- | --- | --- |
| Access Token | 2 小时 | API 鉴权 |
| Refresh Token | 7 天 | 换取新的 Access Token |

Access Token Claims：

```json
{
  "sub": "user_id",
  "username": "admin",
  "role": "Admin",
  "type": "access",
  "iat": 1779696000,
  "exp": 1779703200
}
```

Refresh Token 需要服务端可撤销。建议将 refresh token 的 `jti` 存入数据库或 Redis，用于登出、密码变更、强制下线。

### 8.1.5 密码策略

- 密码使用 `bcrypt` 或 `argon2` 哈希保存。
- 不允许明文保存用户密码。
- 默认密码必须在首次登录后修改。
- 密码长度不少于 12 位。
- 管理员重置密码需要写入审计日志。

---

## 8.2 数据库实例管理模块

### 8.2.1 功能范围

数据库实例模块负责：

- 新增数据库实例。
- 编辑数据库实例。
- 删除数据库实例。
- 查询实例列表。
- 查询实例详情。
- 测试连接。
- 管理标签。
- 管理 SSL 配置。
- 管理数据库凭据。

### 8.2.2 支持字段

| 字段 | 说明 |
| --- | --- |
| name | 实例名称，平台内唯一 |
| db_type | 数据库类型，如 mysql、postgresql、mariadb |
| host | 数据库地址 |
| port | 数据库端口 |
| username | 数据库用户名 |
| password_encrypted | 加密后的数据库密码 |
| database_name | 默认数据库名，可为空 |
| ssl_enabled | 是否启用 SSL |
| ssl_config | SSL CA、证书、私钥引用 |
| tags | 标签 |
| environment | 环境，如 prod、staging、dev |
| owner | 负责人 |
| description | 备注 |

### 8.2.3 连接测试

连接测试需要满足：

- 不泄露密码和连接串。
- 设置超时时间，默认 10 秒。
- 捕获错误并转换为平台错误码。
- 成功时返回数据库版本和连接耗时。

MySQL 连接测试：

```text
mysql --host HOST --port PORT --user USER --password=*** --connect-timeout=10 -e "SELECT VERSION();"
```

PostgreSQL 连接测试：

```text
PGPASSWORD=*** psql --host HOST --port PORT --username USER --dbname DB --command "SELECT version();"
```

命令执行时禁止将明文密码写入日志。

### 8.2.4 凭据加密

数据库密码使用应用级加密保存：

- 算法建议使用 AES-256-GCM。
- 主密钥通过环境变量或密钥管理系统注入。
- 加密字段保存 nonce、ciphertext、tag。
- 密钥轮换需要提供重新加密脚本。

---

## 8.3 备份核心模块

### 8.3.1 备份类型

| 类型 | 说明 | MVP |
| --- | --- | --- |
| 逻辑备份 | 调用数据库官方 dump 工具生成逻辑文件 | 是 |
| 文件上传 | 用户上传已有备份文件 | 是 |
| 物理备份 | 复制数据目录或使用物理备份工具 | 否 |
| 增量备份 | 通过 binlog/WAL/oplog 等实现 | 否 |

### 8.3.2 Backup Driver 抽象

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

@dataclass
class BackupContext:
    task_id: int
    database_id: int
    output_dir: Path
    timeout_seconds: int
    include_databases: list[str] | None = None
    exclude_databases: list[str] | None = None

@dataclass
class BackupResult:
    raw_file: Path
    format: str
    stdout_tail: str
    stderr_tail: str
    duration_seconds: float

class BackupDriver(ABC):
    db_type: str

    @abstractmethod
    async def test_connection(self) -> dict:
        ...

    @abstractmethod
    async def backup(self, context: BackupContext) -> BackupResult:
        ...

    @abstractmethod
    async def restore(self, context) -> dict:
        ...

    @abstractmethod
    async def validate(self, backup_file: Path) -> dict:
        ...
```

### 8.3.3 Driver Registry

```python
class DriverRegistry:
    def __init__(self):
        self._database_drivers = {}
        self._storage_drivers = {}
        self._compression_drivers = {}

    def register_database(self, db_type: str, driver_cls):
        self._database_drivers[db_type] = driver_cls

    def get_database(self, db_type: str):
        if db_type not in self._database_drivers:
            raise UnsupportedDriverError(db_type)
        return self._database_drivers[db_type]
```

注册示例：

```python
registry.register_database("mysql", MySQLDriver)
registry.register_database("mariadb", MariaDBDriver)
registry.register_database("postgresql", PostgreSQLDriver)
```

### 8.3.4 MySQL/MariaDB 备份设计

默认命令：

```bash
mysqldump \
  --host=<host> \
  --port=<port> \
  --user=<user> \
  --single-transaction \
  --routines \
  --triggers \
  --events \
  --hex-blob \
  --set-gtid-purged=OFF \
  --databases <database>
```

关键参数说明：

| 参数 | 说明 |
| --- | --- |
| --single-transaction | 对 InnoDB 表减少锁影响 |
| --routines | 导出存储过程和函数 |
| --triggers | 导出触发器 |
| --events | 导出事件 |
| --hex-blob | 正确导出二进制字段 |
| --set-gtid-purged=OFF | 避免 GTID 导入冲突，适合通用恢复 |

注意事项：

- MyISAM 表无法通过 `--single-transaction` 保证一致性。
- 大实例备份需要设置任务超时和输出限速。
- 不应将密码放入命令参数日志。
- 推荐通过临时 defaults-extra-file 或环境变量传递密码。

### 8.3.5 PostgreSQL 备份设计

默认命令：

```bash
pg_dump \
  --host=<host> \
  --port=<port> \
  --username=<user> \
  --dbname=<database> \
  --format=plain \
  --no-owner \
  --no-privileges
```

可选自定义格式：

```bash
pg_dump \
  --format=custom \
  --file=<output.dump> \
  --dbname=<database>
```

MVP 建议：

- 默认使用 plain SQL 格式，方便下载和人工恢复。
- 对大型库可配置 custom 格式，恢复时使用 `pg_restore`。
- 密码通过 `PGPASSWORD` 环境变量注入，但日志中必须脱敏。

### 8.3.6 MongoDB 备份设计

Phase 2 支持：

```bash
mongodump \
  --uri=<mongodb_uri> \
  --archive=<output.archive>
```

MVP 可先保留 Driver 接口，不实现。

### 8.3.7 Redis 备份设计

Phase 2 支持两类方式：

- 通过 `BGSAVE` 触发 RDB 生成后采集文件。
- 采集 AOF 文件。

Agentless 模式对 Redis 文件采集能力有限，因此 Redis 更适合后续 Agent 模式。

### 8.3.8 ClickHouse 备份设计

Phase 2/3 支持：

```sql
BACKUP DATABASE db TO S3(...)
```

ClickHouse 原生 BACKUP 能直接写对象存储，平台负责调度、元数据登记和校验。

---

## 8.4 压缩模块

### 8.4.1 支持算法

| 算法 | 优点 | 缺点 | 使用建议 |
| --- | --- | --- | --- |
| zstd | 速度快、压缩率高、支持多线程 | 需要安装 zstd | 默认 |
| gzip | 兼容性好 | 慢、压缩率一般 | 下载兼容场景 |
| lz4 | 极快 | 压缩率低 | 速度优先场景 |
| none | 无压缩 | 占用存储高 | 已压缩文件或调试 |

### 8.4.2 压缩流程

```text
dump stdout/file
  ↓
compress stream
  ↓
write temp compressed file
  ↓
checksum
  ↓
upload
```

### 8.4.3 Compression Driver 抽象

```python
class CompressionDriver:
    name: str
    extension: str

    async def compress(self, source, target) -> dict:
        ...

    async def decompress(self, source, target) -> dict:
        ...
```

### 8.4.4 默认 zstd 参数

```bash
zstd -T0 -3 <input> -o <output.zst>
```

默认级别为 3，理由：

- 压缩速度较快。
- CPU 占用可控。
- 压缩率足够满足数据库逻辑备份场景。

---

## 8.5 校验模块

### 8.5.1 校验算法

| 算法 | 用途 | MVP |
| --- | --- | --- |
| SHA256 | 主校验算法 | 必选 |
| MD5 | 兼容历史系统和快速比对 | 可选 |

### 8.5.2 校验时机

| 时机 | 动作 |
| --- | --- |
| 上传前 | 计算本地文件 SHA256 |
| 上传后 | 对支持读取的存储可重新下载或读取对象元数据验证 |
| 下载前 | 检查元数据是否存在 |
| 下载后 | 重新计算 SHA256 |
| 恢复前 | 强制校验 |
| 生命周期删除前 | 可选校验对象存在性 |

### 8.5.3 Metadata 示例

```json
{
  "filename": "mysql-prod-20260525-010000.sql.zst",
  "size_bytes": 123123123,
  "md5": "optional",
  "sha256": "required",
  "compressed": true,
  "compression": "zstd",
  "content_type": "application/zstd",
  "created_at": "2026-05-25T01:00:00+08:00"
}
```

---

## 8.6 存储模块

### 8.6.1 支持后端

| 存储 | MVP | 说明 |
| --- | --- | --- |
| Local FS | 是 | 适合单机和开发环境 |
| MinIO | 是 | 推荐生产内网部署 |
| AWS S3 | Phase 2 | 公有云对象存储 |
| NFS | Phase 2 | 共享文件系统 |

### 8.6.2 Storage Driver 抽象

```python
class StorageDriver:
    storage_type: str

    async def upload(self, local_path, object_key, metadata) -> dict:
        ...

    async def download(self, object_key, local_path) -> dict:
        ...

    async def exists(self, object_key) -> bool:
        ...

    async def delete(self, object_key) -> dict:
        ...

    async def stat(self, object_key) -> dict:
        ...
```

### 8.6.3 对象路径规范

对象路径格式：

```text
{db_type}/{environment}/{database_name}/{yyyy}/{mm}/{dd}/{backup_id}-{timestamp}.{ext}
```

示例：

```text
mysql/prod/order-db/2026/05/25/10001-20260525T010000.sql.zst
postgresql/staging/report-db/2026/05/25/10002-20260525T020000.sql.zst
```

路径规范要求：

- 所有路径使用小写数据库类型。
- 实例名需要进行安全化处理，只允许字母、数字、短横线、下划线。
- 对象路径中必须包含 backup_id，避免同名覆盖。
- 禁止使用用户输入直接拼接路径。

### 8.6.4 Local FS 目录结构

```text
/data/dbvault/backups/
  mysql/
    prod/
      order-db/
        2026/
          05/
            25/
              10001-20260525T010000.sql.zst
```

### 8.6.5 MinIO/S3 配置

配置项：

| 字段 | 说明 |
| --- | --- |
| endpoint_url | MinIO 或 S3 Endpoint |
| bucket | Bucket 名称 |
| region | 区域 |
| access_key_encrypted | 加密后的 Access Key |
| secret_key_encrypted | 加密后的 Secret Key |
| use_ssl | 是否使用 HTTPS |
| path_style | 是否启用 path-style |

---

## 8.7 恢复模块

### 8.7.1 恢复模式

| 模式 | 说明 | 风险级别 |
| --- | --- | --- |
| 文件下载 | 用户下载备份文件后自行恢复 | 低 |
| 恢复到新实例 | 将备份恢复到指定新实例 | 中 |
| 原实例恢复 | 覆盖或写入原实例 | 高 |
| 在线恢复 | 平台直接连接目标执行恢复 | 高 |

### 8.7.2 恢复安全控制

原实例恢复必须满足：

- 用户具备 `restore:run` 权限。
- 二次确认，确认文本包含实例名。
- 恢复前强制校验备份文件。
- 记录审计日志。
- 可配置仅 Admin 允许原实例恢复。
- 可配置业务时间窗口限制。

### 8.7.3 Dry-run 设计

Dry-run 用于在恢复前进行可行性检查：

- 备份文件是否存在。
- SHA256 是否匹配。
- 压缩算法是否支持。
- 目标数据库是否可连接。
- 恢复工具是否安装。
- 目标库是否存在。
- 目标库是否为空。
- 用户权限是否满足。

Dry-run 不执行实际数据写入。

### 8.7.4 MySQL 恢复

普通 SQL 文件：

```bash
mysql \
  --host=<host> \
  --port=<port> \
  --user=<user> \
  <database> < backup.sql
```

压缩文件恢复流程：

```text
download backup.sql.zst
  ↓
zstd -d backup.sql.zst -o backup.sql
  ↓
mysql < backup.sql
```

### 8.7.5 PostgreSQL 恢复

Plain SQL：

```bash
psql \
  --host=<host> \
  --port=<port> \
  --username=<user> \
  --dbname=<database> \
  --file=backup.sql
```

Custom 格式：

```bash
pg_restore \
  --host=<host> \
  --port=<port> \
  --username=<user> \
  --dbname=<database> \
  --clean \
  backup.dump
```

---

## 8.8 定时任务模块

### 8.8.1 调度方案

MVP 使用 APScheduler：

- 部署简单。
- 与 FastAPI 可在同一进程或独立 worker 进程中运行。
- 支持 Cron、Interval、Date Trigger。

生产建议：

- API 进程和 Scheduler 进程分离。
- 同一环境只允许一个 Scheduler 实例激活。
- 使用 Redis 或数据库锁避免多实例重复调度。

### 8.8.2 任务类型

| 类型 | 字段 | 示例 |
| --- | --- | --- |
| Cron | cron_expr | `0 1 * * *` |
| Interval | interval_seconds | `21600` |
| One-time | run_at | `2026-05-25T01:00:00+08:00` |

### 8.8.3 Job 状态

| 状态 | 说明 |
| --- | --- |
| ENABLED | 启用 |
| DISABLED | 停用 |
| PAUSED | 暂停 |
| DELETED | 已删除 |

### 8.8.4 调度防重

同一 Job 不允许并发执行，策略如下：

- 如果上一次任务仍在 RUNNING，则跳过本次触发。
- 记录 skipped_count。
- 产生 warning 级别任务事件。
- 可配置 `allow_concurrent=false`。

---

## 8.9 日志与审计模块

### 8.9.1 任务日志

任务日志用于定位备份或恢复失败原因。

记录内容：

- 任务开始时间。
- 任务结束时间。
- 当前阶段。
- dump 命令退出码。
- 压缩耗时。
- 上传耗时。
- 文件大小。
- 错误摘要。
- stdout/stderr 尾部内容。

敏感信息处理：

- 密码、Access Key、Secret Key、Token 必须脱敏。
- 命令日志中不能出现明文密码。
- stderr 中如果包含连接串，需要执行脱敏。

### 8.9.2 审计日志

审计日志用于追踪用户行为。

必须审计的操作：

- 登录成功和失败。
- 登出。
- 创建、编辑、删除数据库实例。
- 创建、编辑、删除存储。
- 手动执行备份。
- 删除备份。
- 执行恢复。
- 修改用户、角色和密码。
- 修改生命周期策略。

审计字段：

| 字段 | 说明 |
| --- | --- |
| actor_user_id | 操作用户 |
| action | 操作类型 |
| resource_type | 资源类型 |
| resource_id | 资源 ID |
| ip_address | 客户端 IP |
| user_agent | 客户端 UA |
| request_id | 请求 ID |
| result | success / failed |
| reason | 失败原因 |
| created_at | 操作时间 |

---

## 8.10 告警模块

### 8.10.1 告警渠道

| 渠道 | MVP | 说明 |
| --- | --- | --- |
| Email | 是 | 基础通知 |
| Webhook | 是 | 通用集成 |
| 企业微信 | Phase 2 | 国内常用 |
| Slack | Phase 2 | 海外团队 |

### 8.10.2 告警场景

| 场景 | 等级 | 触发条件 |
| --- | --- | --- |
| 备份失败 | Critical | backup_task 状态 FAILED |
| 恢复失败 | Critical | restore_task 状态 FAILED |
| 校验失败 | Critical | checksum mismatch |
| 存储上传失败 | Critical | upload exception |
| 存储容量不足 | Warning | Local FS 剩余容量低于阈值 |
| 定时任务连续跳过 | Warning | skipped_count 超过阈值 |
| 备份超过 SLA | Warning | 最近成功备份时间超过策略 |

### 8.10.3 告警抑制

避免告警风暴：

- 同一资源、同一错误在 10 分钟内只发送一次。
- 恢复成功后发送恢复通知。
- 告警事件单独落库，便于查询。

---

## 9. 状态机设计

## 9.1 备份任务状态

```text
PENDING
  ↓
RUNNING
  ├── DUMPING
  ├── COMPRESSING
  ├── CHECKSUMING
  ├── UPLOADING
  ├── VERIFYING
  ↓
SUCCESS

RUNNING / 子状态
  ↓
FAILED

PENDING / RUNNING
  ↓
CANCELLED
```

状态说明：

| 状态 | 说明 |
| --- | --- |
| PENDING | 已创建，等待执行 |
| RUNNING | 正在执行 |
| DUMPING | 正在导出数据库 |
| COMPRESSING | 正在压缩 |
| CHECKSUMING | 正在计算校验值 |
| UPLOADING | 正在上传 |
| VERIFYING | 正在验证上传结果 |
| SUCCESS | 成功 |
| FAILED | 失败 |
| CANCELLED | 已取消 |

### 9.2 恢复任务状态

```text
PENDING
  ↓
RUNNING
  ├── DOWNLOADING
  ├── VERIFYING
  ├── DECOMPRESSING
  ├── RESTORING
  ↓
SUCCESS

RUNNING / 子状态
  ↓
FAILED
```

### 9.3 备份记录状态

| 状态 | 说明 |
| --- | --- |
| AVAILABLE | 可用于恢复或下载 |
| VERIFY_FAILED | 校验失败 |
| DELETING | 正在删除 |
| DELETED | 已删除 |
| EXPIRED | 已过期 |
| LOST | 元数据存在但存储对象不存在 |

---

## 10. 数据库设计

### 10.1 命名规范

- 表名使用复数形式，例如 `users`、`backups`。
- 主键统一为 `id BIGSERIAL` 或 UUID。
- 时间字段统一使用 `TIMESTAMPTZ`。
- 软删除字段使用 `deleted_at`。
- 状态字段使用 `VARCHAR(32)` 或枚举约束。
- JSON 配置字段使用 `JSONB`。

### 10.2 users

```sql
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(64) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(128),
    email VARCHAR(255),
    role VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    last_login_at TIMESTAMPTZ,
    password_changed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ
);
```

### 10.3 database_instances

```sql
CREATE TABLE database_instances (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(128) NOT NULL UNIQUE,
    db_type VARCHAR(32) NOT NULL,
    host VARCHAR(255) NOT NULL,
    port INTEGER NOT NULL,
    username VARCHAR(128) NOT NULL,
    password_encrypted TEXT NOT NULL,
    database_name VARCHAR(128),
    ssl_enabled BOOLEAN NOT NULL DEFAULT false,
    ssl_config JSONB,
    environment VARCHAR(32) NOT NULL DEFAULT 'prod',
    owner VARCHAR(128),
    tags JSONB NOT NULL DEFAULT '[]'::jsonb,
    description TEXT,
    created_by BIGINT REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_database_instances_db_type ON database_instances(db_type);
CREATE INDEX idx_database_instances_environment ON database_instances(environment);
```

### 10.4 storages

```sql
CREATE TABLE storages (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(128) NOT NULL UNIQUE,
    storage_type VARCHAR(32) NOT NULL,
    config_encrypted TEXT NOT NULL,
    is_default BOOLEAN NOT NULL DEFAULT false,
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    created_by BIGINT REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ
);
```

`config_encrypted` 解密后的示例：

```json
{
  "bucket": "dbvault-backups",
  "endpoint_url": "https://minio.example.com",
  "region": "us-east-1",
  "access_key": "xxx",
  "secret_key": "xxx",
  "use_ssl": true,
  "path_style": true
}
```

### 10.5 backups

```sql
CREATE TABLE backups (
    id BIGSERIAL PRIMARY KEY,
    database_id BIGINT NOT NULL REFERENCES database_instances(id),
    storage_id BIGINT NOT NULL REFERENCES storages(id),
    backup_task_id BIGINT,
    backup_type VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL,
    object_key TEXT NOT NULL,
    filename VARCHAR(255) NOT NULL,
    file_format VARCHAR(32) NOT NULL,
    size_bytes BIGINT NOT NULL DEFAULT 0,
    compressed BOOLEAN NOT NULL DEFAULT true,
    compression VARCHAR(32),
    md5 VARCHAR(64),
    sha256 VARCHAR(128) NOT NULL,
    database_version VARCHAR(255),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by BIGINT REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_backups_database_id ON backups(database_id);
CREATE INDEX idx_backups_status ON backups(status);
CREATE INDEX idx_backups_created_at ON backups(created_at);
CREATE INDEX idx_backups_expires_at ON backups(expires_at);
```

### 10.6 backup_tasks

```sql
CREATE TABLE backup_tasks (
    id BIGSERIAL PRIMARY KEY,
    database_id BIGINT NOT NULL REFERENCES database_instances(id),
    storage_id BIGINT NOT NULL REFERENCES storages(id),
    job_id BIGINT,
    status VARCHAR(32) NOT NULL,
    phase VARCHAR(32),
    trigger_type VARCHAR(32) NOT NULL,
    progress INTEGER NOT NULL DEFAULT 0,
    error_code VARCHAR(64),
    error_message TEXT,
    stdout_tail TEXT,
    stderr_tail TEXT,
    size_bytes BIGINT,
    duration_seconds NUMERIC(12, 3),
    config JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by BIGINT REFERENCES users(id),
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_backup_tasks_database_id ON backup_tasks(database_id);
CREATE INDEX idx_backup_tasks_status ON backup_tasks(status);
CREATE INDEX idx_backup_tasks_created_at ON backup_tasks(created_at);
```

### 10.7 restore_tasks

```sql
CREATE TABLE restore_tasks (
    id BIGSERIAL PRIMARY KEY,
    backup_id BIGINT NOT NULL REFERENCES backups(id),
    source_database_id BIGINT REFERENCES database_instances(id),
    target_database_id BIGINT REFERENCES database_instances(id),
    restore_mode VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL,
    phase VARCHAR(32),
    dry_run BOOLEAN NOT NULL DEFAULT false,
    confirm_text VARCHAR(255),
    progress INTEGER NOT NULL DEFAULT 0,
    error_code VARCHAR(64),
    error_message TEXT,
    stdout_tail TEXT,
    stderr_tail TEXT,
    duration_seconds NUMERIC(12, 3),
    config JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by BIGINT REFERENCES users(id),
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 10.8 jobs

```sql
CREATE TABLE jobs (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    database_id BIGINT NOT NULL REFERENCES database_instances(id),
    storage_id BIGINT NOT NULL REFERENCES storages(id),
    schedule_type VARCHAR(32) NOT NULL,
    cron_expr VARCHAR(128),
    interval_seconds INTEGER,
    run_at TIMESTAMPTZ,
    timezone VARCHAR(64) NOT NULL DEFAULT 'Asia/Shanghai',
    enabled BOOLEAN NOT NULL DEFAULT true,
    allow_concurrent BOOLEAN NOT NULL DEFAULT false,
    retention_policy JSONB NOT NULL DEFAULT '{}'::jsonb,
    backup_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    last_run_at TIMESTAMPTZ,
    next_run_at TIMESTAMPTZ,
    last_status VARCHAR(32),
    skipped_count INTEGER NOT NULL DEFAULT 0,
    created_by BIGINT REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ
);
```

### 10.9 audit_logs

```sql
CREATE TABLE audit_logs (
    id BIGSERIAL PRIMARY KEY,
    actor_user_id BIGINT REFERENCES users(id),
    action VARCHAR(64) NOT NULL,
    resource_type VARCHAR(64),
    resource_id VARCHAR(64),
    request_id VARCHAR(64),
    ip_address INET,
    user_agent TEXT,
    result VARCHAR(32) NOT NULL,
    reason TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_audit_logs_actor ON audit_logs(actor_user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);
```

### 10.10 task_events

```sql
CREATE TABLE task_events (
    id BIGSERIAL PRIMARY KEY,
    task_type VARCHAR(32) NOT NULL,
    task_id BIGINT NOT NULL,
    level VARCHAR(32) NOT NULL,
    phase VARCHAR(32),
    message TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_task_events_task ON task_events(task_type, task_id);
```

### 10.11 alerts

```sql
CREATE TABLE alerts (
    id BIGSERIAL PRIMARY KEY,
    alert_type VARCHAR(64) NOT NULL,
    severity VARCHAR(32) NOT NULL,
    resource_type VARCHAR(64),
    resource_id VARCHAR(64),
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'OPEN',
    dedupe_key VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ
);

CREATE INDEX idx_alerts_status ON alerts(status);
CREATE INDEX idx_alerts_dedupe_key ON alerts(dedupe_key);
```

---

## 11. API 设计

### 11.1 通用约定

API 前缀：

```text
/api/v1
```

认证方式：

```http
Authorization: Bearer <access_token>
```

统一错误响应：

```json
{
  "error": {
    "code": "DATABASE_CONNECTION_FAILED",
    "message": "Failed to connect database",
    "details": {
      "database_id": 1
    },
    "request_id": "req_abc123"
  }
}
```

分页响应：

```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "total": 100
}
```

### 11.2 Auth API

| Method | Path | 权限 | 说明 |
| --- | --- | --- | --- |
| POST | `/auth/login` | 无 | 登录 |
| POST | `/auth/refresh` | Refresh Token | 刷新 Token |
| POST | `/auth/logout` | 登录用户 | 登出 |
| GET | `/auth/me` | 登录用户 | 当前用户 |
| POST | `/auth/change-password` | 登录用户 | 修改密码 |

登录请求：

```json
{
  "username": "admin",
  "password": "password"
}
```

登录响应：

```json
{
  "access_token": "xxx",
  "refresh_token": "xxx",
  "token_type": "bearer",
  "expires_in": 7200,
  "user": {
    "id": 1,
    "username": "admin",
    "role": "Admin"
  }
}
```

### 11.3 Users API

| Method | Path | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | `/users` | user:read | 用户列表 |
| POST | `/users` | user:write | 创建用户 |
| GET | `/users/{id}` | user:read | 用户详情 |
| PUT | `/users/{id}` | user:write | 更新用户 |
| DELETE | `/users/{id}` | user:write | 删除用户 |
| POST | `/users/{id}/reset-password` | user:write | 重置密码 |

### 11.4 Databases API

| Method | Path | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | `/databases` | database:read | 实例列表 |
| POST | `/databases` | database:write | 创建实例 |
| GET | `/databases/{id}` | database:read | 实例详情 |
| PUT | `/databases/{id}` | database:write | 更新实例 |
| DELETE | `/databases/{id}` | database:write | 删除实例 |
| POST | `/databases/test` | database:write | 测试临时连接 |
| POST | `/databases/{id}/test` | database:read | 测试已保存实例 |

创建实例请求：

```json
{
  "name": "order-prod",
  "db_type": "mysql",
  "host": "10.0.1.10",
  "port": 3306,
  "username": "backup_user",
  "password": "secret",
  "database_name": "order",
  "ssl_enabled": false,
  "environment": "prod",
  "tags": ["order", "critical"]
}
```

### 11.5 Storages API

| Method | Path | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | `/storages` | storage:read | 存储列表 |
| POST | `/storages` | storage:write | 创建存储 |
| GET | `/storages/{id}` | storage:read | 存储详情 |
| PUT | `/storages/{id}` | storage:write | 更新存储 |
| DELETE | `/storages/{id}` | storage:write | 删除存储 |
| POST | `/storages/{id}/test` | storage:read | 测试存储 |

### 11.6 Backups API

| Method | Path | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | `/backups` | backup:read | 备份列表 |
| POST | `/backups/run` | backup:run | 立即备份 |
| POST | `/backups/upload` | backup:run | 上传备份 |
| GET | `/backups/{id}` | backup:read | 备份详情 |
| GET | `/backups/{id}/download` | backup:read | 下载备份 |
| POST | `/backups/{id}/verify` | backup:run | 校验备份 |
| DELETE | `/backups/{id}` | backup:delete | 删除备份 |

立即备份请求：

```json
{
  "database_id": 1,
  "storage_id": 1,
  "compression": "zstd",
  "checksum": ["sha256", "md5"],
  "retention": {
    "keep_days": 30,
    "keep_last": 10
  }
}
```

立即备份响应：

```json
{
  "task_id": 10001,
  "status": "PENDING"
}
```

### 11.7 Backup Tasks API

| Method | Path | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | `/backup-tasks` | backup:read | 任务列表 |
| GET | `/backup-tasks/{id}` | backup:read | 任务详情 |
| GET | `/backup-tasks/{id}/events` | backup:read | 任务事件 |
| POST | `/backup-tasks/{id}/cancel` | backup:run | 取消任务 |

### 11.8 Restore API

| Method | Path | 权限 | 说明 |
| --- | --- | --- | --- |
| POST | `/restore/dry-run` | backup:read | 恢复预检查 |
| POST | `/restore/run` | restore:run | 执行恢复 |
| GET | `/restore-tasks` | backup:read | 恢复任务列表 |
| GET | `/restore-tasks/{id}` | backup:read | 恢复任务详情 |
| GET | `/restore-tasks/{id}/events` | backup:read | 恢复任务事件 |

恢复请求：

```json
{
  "backup_id": 10001,
  "target_database_id": 2,
  "restore_mode": "NEW_INSTANCE",
  "dry_run": false,
  "confirm_text": "restore order-prod"
}
```

### 11.9 Jobs API

| Method | Path | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | `/jobs` | job:read | 定时任务列表 |
| POST | `/jobs` | job:write | 创建定时任务 |
| GET | `/jobs/{id}` | job:read | 定时任务详情 |
| PUT | `/jobs/{id}` | job:write | 更新定时任务 |
| DELETE | `/jobs/{id}` | job:write | 删除定时任务 |
| POST | `/jobs/{id}/enable` | job:write | 启用 |
| POST | `/jobs/{id}/disable` | job:write | 停用 |
| POST | `/jobs/{id}/run-now` | backup:run | 立即执行 |

创建 Job 请求：

```json
{
  "name": "order-prod-daily",
  "database_id": 1,
  "storage_id": 1,
  "schedule_type": "CRON",
  "cron_expr": "0 1 * * *",
  "timezone": "Asia/Shanghai",
  "retention_policy": {
    "keep_days": 30,
    "keep_last": 10,
    "keep_monthly": 6
  },
  "backup_config": {
    "compression": "zstd",
    "checksum": ["sha256"]
  }
}
```

### 11.10 Audit API

| Method | Path | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | `/audit-logs` | audit:read | 审计日志 |

### 11.11 Metrics API

| Method | Path | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | `/dashboard/summary` | backup:read | 首页统计 |
| GET | `/dashboard/backup-trends` | backup:read | 备份趋势 |
| GET | `/dashboard/storage-usage` | backup:read | 存储使用 |

---

## 12. 错误码设计

| 错误码 | HTTP 状态码 | 说明 |
| --- | --- | --- |
| UNAUTHORIZED | 401 | 未登录或 Token 无效 |
| FORBIDDEN | 403 | 权限不足 |
| RESOURCE_NOT_FOUND | 404 | 资源不存在 |
| VALIDATION_ERROR | 422 | 参数校验失败 |
| DATABASE_CONNECTION_FAILED | 400 | 数据库连接失败 |
| DATABASE_DRIVER_NOT_FOUND | 400 | 不支持的数据库类型 |
| BACKUP_TASK_ALREADY_RUNNING | 409 | 备份任务已在运行 |
| BACKUP_COMMAND_FAILED | 500 | 备份命令失败 |
| CHECKSUM_MISMATCH | 500 | 校验失败 |
| STORAGE_UPLOAD_FAILED | 500 | 上传失败 |
| STORAGE_DOWNLOAD_FAILED | 500 | 下载失败 |
| RESTORE_COMMAND_FAILED | 500 | 恢复命令失败 |
| CONFIRM_TEXT_INVALID | 400 | 二次确认文本错误 |
| SCHEDULE_INVALID | 400 | 调度表达式错误 |

---

## 13. 安全设计

### 13.1 传输安全

- 生产环境必须启用 HTTPS。
- 内部 MinIO/S3 访问建议使用 TLS。
- Cookie 场景需要启用 Secure、HttpOnly、SameSite。

### 13.2 凭据安全

- 数据库密码加密保存。
- 存储 Access Key 和 Secret Key 加密保存。
- JWT Secret、AES Key 通过环境变量或密钥管理系统注入。
- 日志脱敏。
- API 返回中永不返回明文凭据。

### 13.3 命令执行安全

备份和恢复需要调用外部命令，必须遵守：

- 使用参数数组执行命令，避免 shell 拼接。
- 禁止把用户输入直接拼入 shell 字符串。
- 对文件路径做规范化和白名单检查。
- 限制临时目录在平台控制范围内。
- 设置超时时间。
- 限制 stdout/stderr 最大保存长度。
- 日志中脱敏密码、Token 和连接串。

### 13.4 API 安全

- JWT 鉴权。
- RBAC 权限控制。
- Rate Limit。
- CORS 白名单。
- 请求体大小限制。
- 上传文件大小限制。
- OpenAPI 在生产环境可配置是否公开。

### 13.5 恢复风险控制

- 原实例恢复默认关闭，可通过配置启用。
- 原实例恢复要求 Admin 或 Operator 权限。
- 恢复操作必须写审计。
- 恢复前必须校验备份文件。
- 恢复任务必须记录目标实例。

---

## 14. 生命周期策略设计

### 14.1 策略字段

```json
{
  "keep_days": 30,
  "keep_last": 10,
  "keep_weekly": 8,
  "keep_monthly": 6,
  "delete_after_days": 180
}
```

### 14.2 保留规则

规则优先级：

1. 永久保留标记的备份不删除。
2. 保留最近 N 个成功备份。
3. 保留指定天数内所有成功备份。
4. 保留每周最后一个成功备份。
5. 保留每月最后一个成功备份。
6. 删除超过最终过期时间的备份。

### 14.3 删除策略

删除过程采用两阶段：

1. 将备份状态置为 `DELETING`。
2. 删除存储对象。
3. 删除成功后置为 `DELETED` 并设置 `deleted_at`。
4. 删除失败则恢复为 `AVAILABLE` 并记录错误。

---

## 15. 可观测性设计

### 15.1 结构化日志

日志字段：

| 字段 | 说明 |
| --- | --- |
| timestamp | 时间 |
| level | 日志级别 |
| request_id | 请求 ID |
| user_id | 用户 ID |
| task_id | 任务 ID |
| action | 动作 |
| resource | 资源 |
| duration_ms | 耗时 |
| error_code | 错误码 |

### 15.2 指标

建议暴露 Prometheus 指标：

| 指标 | 类型 | 说明 |
| --- | --- | --- |
| dbvault_backup_total | Counter | 备份任务总数 |
| dbvault_backup_failed_total | Counter | 备份失败总数 |
| dbvault_restore_total | Counter | 恢复任务总数 |
| dbvault_backup_duration_seconds | Histogram | 备份耗时 |
| dbvault_backup_size_bytes | Histogram | 备份文件大小 |
| dbvault_storage_upload_duration_seconds | Histogram | 上传耗时 |
| dbvault_scheduler_skipped_total | Counter | 调度跳过次数 |

### 15.3 Dashboard

首页展示：

- 数据库实例数量。
- 存储后端数量。
- 今日备份成功数。
- 今日备份失败数。
- 最近 7 天备份趋势。
- 最近 7 天备份容量趋势。
- 最近失败任务列表。
- 存储容量使用情况。

---

## 16. 前端页面设计

### 16.1 页面结构

```text
登录页
  ↓
管理后台
  ├── 仪表盘
  ├── 数据库实例
  ├── 备份记录
  ├── 备份任务
  ├── 恢复任务
  ├── 定时任务
  ├── 存储管理
  ├── 告警中心
  ├── 审计日志
  └── 系统设置
```

### 16.2 数据库实例页面

能力：

- 表格展示实例名称、类型、环境、地址、负责人、最近备份时间、最近备份状态。
- 支持按类型、环境、标签、状态筛选。
- 支持新增、编辑、删除。
- 支持连接测试。
- 支持从实例详情页发起立即备份。

### 16.3 备份记录页面

能力：

- 展示备份 ID、实例、状态、大小、压缩算法、校验状态、创建时间、过期时间。
- 支持下载。
- 支持校验。
- 支持删除。
- 支持发起恢复。
- 支持查看元数据。

### 16.4 任务页面

能力：

- 展示任务状态和当前阶段。
- 支持查看任务事件。
- 支持查看失败原因。
- RUNNING 任务显示实时进度。
- 支持取消可取消任务。

### 16.5 恢复页面

能力：

- 从备份详情进入恢复。
- 选择恢复目标实例。
- Dry-run 预检查。
- 原实例恢复显示强风险确认。
- 展示恢复日志和执行结果。

---

## 17. 部署设计

### 17.1 Docker Compose 组件

MVP 推荐 Docker Compose：

```text
dbvault-api
dbvault-scheduler
postgres
redis
minio
nginx
```

### 17.2 API 容器

API 容器职责：

- 提供 FastAPI HTTP 服务。
- 执行短耗时业务逻辑。
- 调用后台任务入口。
- 暴露 OpenAPI。

### 17.3 Scheduler 容器

Scheduler 容器职责：

- 加载启用的 jobs。
- 注册 APScheduler trigger。
- 到点创建 backup_task。
- 提交任务执行。

### 17.4 Worker 容器

MVP 可以和 Scheduler 合并，生产建议独立：

- 执行备份。
- 执行恢复。
- 处理压缩和上传。
- 写任务事件。

### 17.5 环境变量

| 变量 | 说明 |
| --- | --- |
| DBVAULT_ENV | 环境 |
| DBVAULT_DATABASE_URL | 元数据库连接串 |
| DBVAULT_REDIS_URL | Redis 地址 |
| DBVAULT_JWT_SECRET | JWT 密钥 |
| DBVAULT_ENCRYPTION_KEY | 凭据加密密钥 |
| DBVAULT_BACKUP_TMP_DIR | 备份临时目录 |
| DBVAULT_LOG_LEVEL | 日志级别 |
| DBVAULT_OPENAPI_ENABLED | 是否启用 OpenAPI |

### 17.6 临时目录

建议：

```text
/var/lib/dbvault/tmp
```

要求：

- 容量充足。
- 任务结束后自动清理。
- 定时清理遗留临时文件。
- 权限仅 DBVault 进程可读写。

---

## 18. 高可用与扩展

### 18.1 MVP 可用性

MVP 可以使用单 API + 单 Scheduler + 多 Worker 的形态。平台元数据依赖 PostgreSQL，备份文件依赖 MinIO 或 Local FS。

### 18.2 Scheduler 高可用

如果部署多个 Scheduler，需要分布式锁：

- 使用 PostgreSQL advisory lock。
- 或使用 Redis lock。
- 同一时刻只有一个 Scheduler 实例注册和触发任务。

### 18.3 Worker 扩展

备份和恢复是资源密集型任务，应限制并发：

| 维度 | 策略 |
| --- | --- |
| 全局并发 | 默认 5 |
| 单数据库并发 | 默认 1 |
| 单存储并发上传 | 默认 5 |
| 单任务超时 | 默认 6 小时 |

Phase 2 引入 Celery 后：

- Redis 作为 Broker。
- Worker 按数据库类型或任务类型分队列。
- 大任务可以独立队列。

---

## 19. 性能与容量设计

### 19.1 指标目标

| 指标 | 目标 |
| --- | --- |
| 普通 API 响应 | P95 < 200ms |
| 任务列表查询 | P95 < 500ms |
| 并发任务 | MVP 10，后续 100 |
| 单文件大小 | MVP 500GB，后续 5TB |
| 元数据保留 | 至少 3 年 |
| 可用性 | MVP 99%，生产目标 99.9% |

### 19.2 大文件处理

要求：

- 避免一次性读取全文件到内存。
- 压缩、校验、上传采用流式或分块方式。
- 对象存储使用 multipart upload。
- 断点续传作为后续增强。

### 19.3 元数据查询优化

备份记录可能快速增长，需要：

- 按 `database_id`、`created_at`、`status` 建索引。
- 列表默认按创建时间倒序。
- 限制最大 page_size。
- 对历史数据可做分区表，Phase 2 再引入。

---

## 20. 测试设计

### 20.1 单元测试

覆盖：

- 权限判断。
- Token 签发和刷新。
- 凭据加解密。
- Driver Registry。
- 对象路径生成。
- 生命周期策略计算。
- 状态机流转。
- 错误码转换。

### 20.2 集成测试

使用 Docker 启动：

- PostgreSQL 元数据库。
- MinIO。
- MySQL 测试库。
- PostgreSQL 测试库。

测试场景：

- MySQL 连接测试成功/失败。
- PostgreSQL 连接测试成功/失败。
- MySQL 备份到 Local FS。
- MySQL 备份到 MinIO。
- PostgreSQL 备份到 Local FS。
- 备份校验成功。
- 校验失败被识别。
- 生命周期删除成功。
- 权限不足返回 403。

### 20.3 恢复测试

场景：

- MySQL 备份恢复到新实例。
- PostgreSQL plain SQL 恢复到新实例。
- SHA256 不匹配时阻止恢复。
- 原实例恢复确认文本错误时拒绝。
- 恢复命令失败时记录 stderr_tail。

### 20.4 安全测试

场景：

- 日志中不出现数据库密码。
- API 不返回存储密钥。
- Viewer 无法执行备份。
- Viewer 无法执行恢复。
- 无 Token 请求被拒绝。
- 过期 Token 请求被拒绝。

---

## 21. 研发实施计划

### 21.1 Phase 1 MVP

目标：完成可用的备份平台闭环。

范围：

- FastAPI 项目骨架。
- PostgreSQL 元数据库和 Alembic。
- 用户登录、JWT、RBAC。
- 数据库实例 CRUD。
- 存储 CRUD。
- Local FS Storage Driver。
- MinIO Storage Driver。
- MySQL Driver。
- PostgreSQL Driver。
- zstd 压缩。
- SHA256 校验。
- 手动备份。
- APScheduler 定时备份。
- 备份记录查询、下载、删除。
- 基础前端页面。
- Docker Compose 部署。

验收标准：

- 可以创建 MySQL 和 PostgreSQL 实例。
- 可以测试连接。
- 可以手动备份到 Local FS 和 MinIO。
- 可以创建每天执行的定时备份。
- 可以查询备份记录。
- 可以下载备份文件。
- 备份文件具有 SHA256。
- 备份失败能看到错误日志。

### 21.2 Phase 2

目标：完善恢复、安全和告警。

范围：

- 恢复到新实例。
- 原实例恢复强确认。
- 文件上传备份。
- Email/Webhook 告警。
- 审计日志页面。
- 生命周期策略。
- MongoDB 初步支持。
- Celery Worker 改造。

### 21.3 Phase 3

目标：平台化和高级能力。

范围：

- Agent 模式。
- 增量备份。
- 自动恢复验证。
- 多租户。
- 配额限制。
- ClickHouse 支持。
- Restic 去重存储。
- K8S Helm Chart。

---

## 22. 推荐目录结构

```text
dbvault/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── api/
│   │   ├── deps.py
│   │   └── v1/
│   │       ├── auth.py
│   │       ├── users.py
│   │       ├── databases.py
│   │       ├── storages.py
│   │       ├── backups.py
│   │       ├── restores.py
│   │       ├── jobs.py
│   │       └── audit.py
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   ├── encryption.py
│   │   ├── logging.py
│   │   └── errors.py
│   ├── models/
│   ├── schemas/
│   ├── repositories/
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── backup_service.py
│   │   ├── restore_service.py
│   │   ├── storage_service.py
│   │   └── lifecycle_service.py
│   ├── drivers/
│   │   ├── registry.py
│   │   ├── database/
│   │   │   ├── base.py
│   │   │   ├── mysql.py
│   │   │   └── postgresql.py
│   │   ├── storage/
│   │   │   ├── base.py
│   │   │   ├── local.py
│   │   │   └── s3.py
│   │   └── compression/
│   │       ├── base.py
│   │       └── zstd.py
│   ├── scheduler/
│   ├── tasks/
│   └── utils/
├── alembic/
├── frontend/
├── tests/
├── scripts/
├── docker/
├── docs/
├── docker-compose.yml
└── README.md
```

---

## 23. 关键设计决策

| 决策 | 结论 | 原因 |
| --- | --- | --- |
| 架构形态 | 单体模块化优先 | MVP 简单可靠，降低部署复杂度 |
| 调度器 | APScheduler | 满足初期 Cron/Interval/One-shot |
| 任务队列 | Phase 2 引入 Celery | 避免初期过度设计 |
| 元数据库 | PostgreSQL | 稳定、查询能力强、JSONB 适合配置 |
| 默认存储 | MinIO | 私有化部署友好，兼容 S3 |
| 默认压缩 | zstd | 性能和压缩率平衡 |
| 默认校验 | SHA256 | 安全性优于 MD5 |
| 默认备份 | 逻辑备份 | 实现简单，跨环境恢复友好 |
| 凭据加密 | 应用层 AES 加密 | 防止数据库泄露直接暴露凭据 |
| 恢复保护 | 强确认 + 审计 | 降低误恢复风险 |

---

## 24. 风险与应对

| 风险 | 影响 | 应对 |
| --- | --- | --- |
| 大库备份耗时过长 | 任务超时、影响源库 | 设置超时、限流、后续支持增量 |
| mysqldump 对源库有压力 | 业务性能下降 | 建议从只读副本备份，低峰执行 |
| 临时磁盘不足 | 备份失败 | 监控临时目录容量，流式处理 |
| 对象存储上传中断 | 文件不完整 | multipart upload、失败清理 |
| 密码泄露到日志 | 安全事故 | 全链路脱敏和测试 |
| Scheduler 多实例重复触发 | 重复备份 | 分布式锁 |
| 恢复误操作 | 数据损坏 | 强确认、权限、审计、默认禁用原实例恢复 |
| 备份不可恢复 | 灾备失败 | 校验和后续自动恢复验证 |

---

## 25. MVP 验收清单

| 项目 | 标准 |
| --- | --- |
| 登录 | Admin 可登录并获取 Token |
| 权限 | Viewer 无法执行备份和恢复 |
| 实例管理 | 可新增、编辑、删除、测试 MySQL/PostgreSQL 实例 |
| 存储管理 | 可新增、测试 Local FS 和 MinIO |
| 手动备份 | 可对 MySQL/PostgreSQL 发起立即备份 |
| 定时备份 | 可创建 Cron 任务并自动触发 |
| 压缩 | 默认生成 zstd 文件 |
| 校验 | 备份记录保存 SHA256 |
| 下载 | 可下载备份文件 |
| 删除 | 删除备份会删除存储对象并更新状态 |
| 日志 | 失败任务能查看错误摘要 |
| 审计 | 登录、备份、删除等关键操作有审计记录 |
| 部署 | Docker Compose 一键启动核心组件 |

---

## 26. 后续增强方向

后续可围绕以下方向演进：

- 增量备份：MySQL binlog、PostgreSQL WAL、MongoDB oplog。
- Agent 模式：在数据库主机本地执行备份，解决 Redis 文件采集、网络带宽和权限问题。
- 自动恢复验证：周期性恢复到临时实例，执行校验 SQL 后销毁环境。
- 多租户：部门隔离、资源配额、租户级存储配置。
- 高级生命周期：接入 Restic，实现去重、快照、加密和远端复制。
- K8S 部署：Helm Chart、HPA、PodDisruptionBudget。
- 更多数据库：Oracle、SQLServer、TiDB、Elasticsearch。

---

## 27. 总结

DBVault 采用 FastAPI、PostgreSQL、APScheduler、MinIO、zstd 组成轻量且可扩展的数据库备份平台。MVP 聚焦 MySQL/PostgreSQL/MariaDB 的逻辑备份、统一调度、统一存储、校验、权限和可视化管理，优先形成备份闭环。

平台的长期演进方向是将备份、恢复、校验、生命周期和审计统一管理，并通过 Driver 插件化机制扩展更多数据库、存储和高级备份能力。
