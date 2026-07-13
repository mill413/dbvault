# 升级指南

本文适用于通过 `docker/deploy.sh` 或 `docker/docker-compose.yml` 启动的 Docker Compose 部署。

> 默认 Compose 文件使用生产镜像运行，不会挂载仓库源码，也不会启用 API 热重载。升级时应让 Compose/部署脚本、Docker 镜像和 Alembic 迁移保持同一发布版本。

## 升级前检查

1. 后端代码或数据库结构变更时，安排维护窗口。
2. 确认当前服务使用的 Compose 项目名。默认是 `dbvault`；如果部署时用了 `./deploy.sh -p <project>`，升级也要使用同一个项目名。
3. 升级时不要执行 `./deploy.sh -D`。该命令会运行 `docker compose down -v`，删除 PostgreSQL 和 DBVault 数据卷。
4. 保留生产环境密钥，尤其是 `.env` 或运行环境中的 `DBVAULT_JWT_SECRET` 和 `DBVAULT_ENCRYPTION_KEY`。

如果服务部署时使用了自定义项目名，直接执行 `docker compose` 命令前需要先设置：

```bash
export COMPOSE_PROJECT_NAME=<project>
```

## 备份运行数据

除特别说明外，以下命令从仓库根目录执行。

```bash
cd docker
docker compose ps

# 备份元数据库。
docker compose exec postgres pg_dump -U dbvault dbvault > ../dbvault-meta-$(date +%Y%m%d-%H%M%S).sql
```

如果使用本地存储保存备份文件或 kubeconfig，还需要归档 `dbvault-data` 数据卷。若 `COMPOSE_PROJECT_NAME` 不是 `dbvault`，请相应调整卷名。

```bash
docker run --rm \
  -v dbvault_dbvault-data:/data:ro \
  -v "$PWD/..:/backup" \
  busybox tar czf /backup/dbvault-data-$(date +%Y%m%d-%H%M%S).tar.gz -C /data .
```

## 从源码升级

服务器上保留 Git 工作区时使用此方式。

```bash
cd docker
docker compose stop api frontend

cd ..
git fetch --all --tags
git checkout <目标标签或分支>

# 如果目标是跟踪分支，执行此命令更新；固定 tag 跳过。
# git pull --ff-only

# 先构建新镜像，但暂不启动应用容器。
docker build -t dbvault-api:latest -f docker/Dockerfile .
docker build -t dbvault-frontend:latest -f docker/Dockerfile.frontend frontend

cd docker
docker compose up -d postgres redis
docker compose run --rm api alembic upgrade head
docker compose up -d api frontend
```

如果没有后端或迁移变更，纯前端升级可以只执行 `./deploy.sh -b -f`。涉及 API 的升级建议使用上面的完整流程，确保迁移先于新 API 启动。

## 从发布镜像升级

使用 GitHub Releases 中的镜像归档时走此流程。请使用对应发布版本中的 `docker/docker-compose.yml` 和 `docker/deploy.sh`，因为不同版本的部署配置可能变化；应用源码不会挂载进容器。

```bash
git fetch --all --tags
git checkout <匹配的发布标签>

gh release download --repo mill413/dbvault -p '*.tar.gz'
docker load -i dbvault-images-*.tar.gz

cd docker
docker compose stop api frontend
docker compose up -d postgres redis
docker compose run --rm api alembic upgrade head
docker compose up -d api frontend
```

## 升级后验证

```bash
cd docker
docker compose ps
docker compose logs --tail=100 api
docker compose logs --tail=100 frontend
curl -f http://127.0.0.1:8000/docs >/dev/null
```

打开 `http://localhost:5173`，登录后检查仪表盘、数据库列表、备份列表和定时任务。

## 回滚

如果尚未执行数据库迁移，可以切回旧代码或重新导入旧镜像归档，然后重新部署：

```bash
cd docker
./deploy.sh -b
```

如果迁移已经修改元数据库，优先使用升级前导出的数据库备份恢复。执行 `alembic downgrade -1` 前必须先检查对应迁移脚本；并非所有业务变更都能安全回滚。
