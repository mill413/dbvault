# 数据库备份平台需求文档（PRD + 技术设计草案）

## 项目名称

建议名称：

* DBVault
* PyBackup
* DataSafeguard
* Polaris Backup
* Atlas Backup

下文统一使用：

```text
DBVault
```

---

# 一、项目背景

部门内部存在大量：

* MySQL
* PostgreSQL
* MongoDB
* Redis
* ClickHouse

等数据库实例。

目前备份方式存在：

* 脚本分散
* 缺少统一管理
* 无备份校验
* 无恢复验证
* 无生命周期管理
* 无权限控制
* 无可视化
* 无统一存储管理

因此需要建设：

> 一个轻量化、Python 技术栈、多数据库支持、可扩展的数据库备份平台。

---

# 二、项目目标

平台需具备：

## 核心能力

### 1. 数据库备份

支持：

* 远程数据库连接备份
* Agentless 备份
* 手动上传备份文件

---

### 2. 多数据库支持

首期支持：

| 数据库        | 备份方式      |
| ---------- | --------- |
| MySQL      | mysqldump |
| PostgreSQL | pg_dump   |
| MongoDB    | mongodump |
| Redis      | RDB/AOF   |
| ClickHouse | BACKUP    |
| MariaDB    | mysqldump |

后续扩展：

* Oracle
* SQLServer
* TiDB
* Elasticsearch

---

### 3. 存储后端

支持：

| 存储     | 类型             |
| ------ | -------------- |
| 本地存储   | filesystem     |
| MinIO  | S3 Compatible  |
| AWS S3 | object storage |
| NFS    | shared storage |

---

### 4. RESTful API

完整 OpenAPI 规范。

支持：

* 用户
* 备份
* 恢复
* 任务
* 存储
* 日志
* 权限

全量 API。

---

### 5. 定时任务

支持：

* Cron
* Interval
* One-shot

---

### 6. 数据恢复

支持：

* 一键恢复
* 恢复到新实例
* 文件下载恢复
* 在线恢复

---

### 7. 数据完整性

备份文件需支持：

* 压缩
* MD5
* SHA256
* 文件校验
* 自动校验

---

---

# 三、技术架构

# 3.1 总体架构

```text
                ┌─────────────────┐
                │     Frontend     │
                │ Vue3 / React     │
                └────────┬────────┘
                         │ REST API
                ┌────────▼────────┐
                │    FastAPI API   │
                └────────┬────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
 ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
 │ Scheduler   │ │ Backup Core │ │ Auth Service │
 │ APScheduler │ │ Driver      │ │ JWT/RBAC     │
 └──────┬──────┘ └──────┬──────┘ └─────────────┘
        │               │
        │       ┌───────▼────────┐
        │       │ Storage Service │
        │       └───────┬────────┘
        │               │
        │    ┌──────────┴──────────┐
        │    │                     │
 ┌──────▼──────┐          ┌────────▼────────┐
 │ Local FS    │          │ MinIO / S3      │
 └─────────────┘          └─────────────────┘
```

---

# 四、技术选型

# 4.1 后端

| 组件                 | 技术                 |
| ------------------ | ------------------ |
| Web Framework      | FastAPI            |
| ORM                | SQLAlchemy 2.0     |
| Migration          | Alembic            |
| Validation         | Pydantic           |
| Auth               | JWT                |
| Task Queue         | APScheduler/Celery |
| Database           | PostgreSQL         |
| Cache              | Redis              |
| Object Storage SDK | boto3/minio        |
| Compression        | zstd               |
| Hash               | hashlib            |

---

# 4.2 前端

推荐：

| 技术           | 说明  |
| ------------ | --- |
| Vue3         | 推荐  |
| Element Plus | UI  |
| Axios        | API |
| ECharts      | 图表  |

---

# 五、核心模块设计

# 5.1 用户系统

---

## 功能

### 用户管理

支持：

* 注册
* 登录
* 修改密码
* Token 刷新
* MFA（后期）

---

### RBAC 权限模型

角色：

| 角色       | 权限   |
| -------- | ---- |
| Admin    | 全部   |
| User     | 自有资源管理 |

---

### JWT

采用：

```text
Access Token + Refresh Token
```

---

# API 示例

## 登录

```http
POST /api/v1/auth/login
```

Request:

```json
{
  "username": "admin",
  "password": "123456"
}
```

Response:

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "expires_in": 7200
}
```

---

# 5.2 数据库实例管理

---

## 功能

支持管理：

* 主机
* 端口
* 用户
* 密码
* SSL
* 数据库类型

---

## 数据模型

```python
class DatabaseInstance:
    id
    name
    db_type
    host
    port
    username
    password_encrypted
    ssl_enabled
    tags
```

---

## 支持连接测试

```http
POST /api/v1/databases/test
```

---

# 5.3 备份核心模块

---

# 备份类型

## 1. 逻辑备份

| 数据库        | 工具        |
| ---------- | --------- |
| MySQL      | mysqldump |
| PostgreSQL | pg_dump   |
| MongoDB    | mongodump |

---

## 2. 文件上传备份

用户上传：

* `.sql`
* `.dump`
* `.tar.zst`

---

# Backup Driver 抽象

```python
class BackupDriver:

    async def backup():
        pass

    async def restore():
        pass

    async def validate():
        pass
```

---

# MySQL Driver

```python
class MySQLDriver(BackupDriver):
```

内部调用：

```bash
mysqldump
```

---

# PostgreSQL Driver

```python
class PostgreSQLDriver(BackupDriver):
```

内部调用：

```bash
pg_dump
```

---

# 5.4 压缩模块

---

# 压缩算法

推荐：

| 算法   | 推荐   |
| ---- | ---- |
| zstd | 强烈推荐 |
| lz4  | 超高速  |
| gzip | 兼容性  |

默认：

```text
zstd
```

---

# 压缩流程

```text
dump
  ↓
stream compress
  ↓
checksum
  ↓
upload
```

---

# 示例

```bash
mysqldump ... | zstd -T0 > backup.sql.zst
```

---

# 5.5 Checksum 校验

---

# 校验算法

支持：

* md5
* sha256

---

# Metadata

```json
{
  "filename": "backup.sql.zst",
  "size": 123123123,
  "md5": "...",
  "sha256": "...",
  "compressed": true,
  "compression": "zstd"
}
```

---

# 自动校验

支持：

* 上传后校验
* 下载前校验
* 恢复前校验

---

# 5.6 存储系统

---

# Storage Driver 抽象

```python
class StorageDriver:

    async def upload():
        pass

    async def download():
        pass

    async def delete():
        pass
```

---

# Local Storage

目录结构：

```text
/data/backups/
  mysql/
    prod-db/
      2026-05-25/
```

---

# MinIO/S3

Bucket：

```text
dbvault-backups
```

对象路径：

```text
/mysql/prod-db/2026/05/25/
```

---

# 生命周期管理

支持：

* 自动清理
* 保留最近 N 次
* 保留月备份
* 冷归档

---

# 5.7 恢复系统

---

# 支持恢复方式

| 类型    | 支持  |
| ----- | --- |
| 原实例恢复 | YES |
| 新实例恢复 | YES |
| 导出下载  | YES |
| 在线恢复  | YES |

---

# 恢复流程

```text
download
  ↓
checksum verify
  ↓
decompress
  ↓
restore command
```

---

# MySQL Restore

```bash
mysql db1 < backup.sql
```

---

# PostgreSQL Restore

```bash
psql db1 < backup.sql
```

---

# 恢复安全机制

恢复前：

* 二次确认
* Dry-run
* 权限校验

---

# 5.8 定时任务系统

---

# Scheduler

首期：

```text
APScheduler
```

后期：

```text
Celery + Redis
```

---

# 支持任务类型

| 类型       | 示例     |
| -------- | ------ |
| Cron     | 每天 1 点 |
| Interval | 每 6 小时 |
| One-time | 立即执行   |

---

# API

```http
POST /api/v1/jobs
```

---

# 示例

```json
{
  "database_id": 1,
  "cron": "0 1 * * *",
  "retention_days": 30
}
```

---

# 5.9 日志系统

---

# 日志内容

记录：

* 备份开始
* 备份结束
* 文件大小
* 压缩耗时
* 上传耗时
* 恢复日志
* 错误日志

---

# 支持：

* Elasticsearch（后期）
* Loki（后期）

---

# 六、RESTful API 设计

# Auth

| Method | Path          |
| ------ | ------------- |
| POST   | /auth/login   |
| POST   | /auth/refresh |
| POST   | /auth/logout  |

---

# Users

| Method | Path        |
| ------ | ----------- |
| GET    | /users      |
| POST   | /users      |
| PUT    | /users/{id} |
| DELETE | /users/{id} |

---

# Databases

| Method | Path            |
| ------ | --------------- |
| GET    | /databases      |
| POST   | /databases      |
| POST   | /databases/test |
| DELETE | /databases/{id} |

---

# Backups

| Method | Path          |
| ------ | ------------- |
| POST   | /backups/run  |
| GET    | /backups      |
| GET    | /backups/{id} |
| DELETE | /backups/{id} |

---

# Restore

| Method | Path              |
| ------ | ----------------- |
| POST   | /restore/run      |
| POST   | /restore/validate |

---

# Storage

| Method | Path           |
| ------ | -------------- |
| GET    | /storages      |
| POST   | /storages      |
| DELETE | /storages/{id} |

---

# Jobs

| Method | Path       |
| ------ | ---------- |
| GET    | /jobs      |
| POST   | /jobs      |
| DELETE | /jobs/{id} |

---

# 七、数据库设计（核心表）

---

# users

```sql
id
username
password_hash
role
created_at
```

---

# databases

```sql
id
name
db_type
host
port
username
password_encrypted
```

---

# backups

```sql
id
database_id
status
file_path
storage_type
size
compressed
md5
sha256
created_at
```

---

# restore_tasks

```sql
id
backup_id
target_database
status
started_at
ended_at
```

---

# jobs

```sql
id
database_id
cron_expr
enabled
last_run
next_run
```

---

# 八、安全设计

---

# 密码存储

采用：

```text
AES-256 加密
```

数据库密码不能明文。

---

# HTTPS

必须支持：

* HTTPS
* TLS

---

# API 安全

支持：

* JWT
* RBAC
* Rate Limit
* Audit Log

---

# 审计日志

记录：

* 登录
* 删除备份
* 恢复操作
* 权限修改

---

# 九、监控与告警

---

# 告警渠道

支持：

* 企业微信
* 邮件
* Slack
* Webhook

---

# 告警场景

| 场景   | 告警  |
| ---- | --- |
| 备份失败 | YES |
| 校验失败 | YES |
| 存储异常 | YES |
| 恢复失败 | YES |

---

# 十、扩展性设计

---

# 插件化 Driver

支持：

* 新数据库
* 新存储
* 新压缩算法

---

# Driver Registry

```python
registry.register("mysql", MySQLDriver)
```

---

# 十一、部署方案

---

# Docker Compose（推荐）

组件：

* API
* PostgreSQL
* Redis
* MinIO

---

# K8S（后期）

支持：

* Horizontal Scaling
* HA

---

# 十二、未来增强方向

---

# 增量备份

支持：

* binlog
* WAL

---

# Agent 模式

目标机本地 dump。

---

# 自动恢复验证

自动：

```text
恢复 → 校验 → 删除
```

---

# 多租户

支持：

* 部门隔离
* 配额限制

---

# 十三、非功能性需求

| 指标     | 要求     |
| ------ | ------ |
| API 响应 | <200ms |
| 并发任务   | ≥100   |
| 单文件    | ≥5TB   |
| 可用性    | 99.9%  |

---

# 十四、推荐目录结构

```text
dbvault/
├── app/
│   ├── api/
│   ├── core/
│   ├── models/
│   ├── drivers/
│   │   ├── database/
│   │   ├── storage/
│   │   └── compression/
│   ├── scheduler/
│   ├── services/
│   ├── tasks/
│   └── utils/
├── tests/
├── scripts/
├── docker/
└── docs/
```

---

# 十五、推荐开发阶段

---

# Phase 1（MVP）

支持：

* MySQL
* PostgreSQL
* Local Storage
* MinIO
* 手动备份
* 定时任务
* REST API

---

# Phase 2

支持：

* 恢复
* RBAC
* 告警
* 文件上传

---

# Phase 3

支持：

* Agent
* 增量备份
* 自动恢复校验
* 多租户

---

# 十六、最终推荐技术路线（核心）

推荐最终采用：

```text
FastAPI
 + SQLAlchemy
 + APScheduler
 + PostgreSQL
 + Redis
 + MinIO
 + zstd
 + Restic（可选）
```

其中：

* Restic 用于高级生命周期与去重
* 平台负责调度与管理
* Driver 负责数据库适配

这是目前：

> “轻量、现代、可维护”

且非常适合部门内部平台的方案。
