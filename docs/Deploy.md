# Deploy

## 支持的部署系统

- Alibaba Cloud Linux 3 (OpenAnolis Edition) - 第一目标平台
- Ubuntu 22.04+ - 兼容平台
- Ubuntu 24.04+ - 兼容平台
- RHEL compatible distributions

从 DT001.2 开始，所有部署脚本优先面向 Alibaba Cloud Linux 3 设计，Ubuntu 作为兼容平台维护。DT001.4 起，生产部署默认使用已验证可达的 DaoCloud Proxy 镜像，不再由安装脚本配置 Docker Registry Mirror。

## Linux 部署

在项目根目录执行：

```bash
scripts/DT002_install_ubuntu.sh
```

脚本会自动：

1. 根据 `.env.example` 创建或补全 `.env`。
2. 验证 Docker 已安装并可访问。
3. 验证 Docker Compose plugin 已安装并可访问。
4. 拉取 `.env` 中配置的 MySQL 镜像。
5. 拉取 `.env` 中配置的 Python 基础镜像。
6. 执行 `docker compose build --pull`。
7. 执行 `docker compose up -d`。
8. 等待 MySQL 健康。
9. 验证 `/api/v1/health`。
10. 执行 `SHOW TABLES;` 并确认 `device`、`attendance`、`raw_request`、`sync_log` 存在。
11. 如部署失败，输出 `docker compose ps`、`docker ps`、MySQL 最近 100 行日志和 API 最近 100 行日志。

全新数据库部署时，应用启动会自动创建 DT002 表结构、唯一约束和索引，不需要手动执行 SQL。DT002 未引入 Alembic，已存在的旧数据库结构变更需在后续 Review Fix 或迁移任务中明确处理。

旧脚本 `scripts/DT001_install_ubuntu.sh`、`scripts/DT001.2_install_ubuntu.sh`、`scripts/DT001.3_install_ubuntu.sh` 和 `scripts/DT001.4_install_ubuntu.sh` 保留用于历史追溯。DT002 起推荐使用 `scripts/DT002_install_ubuntu.sh`。

## Docker 镜像

DT001.4 不再自动配置 Docker Registry Mirror。所有镜像均通过 `.env` 管理。

默认镜像：

```dotenv
MYSQL_IMAGE=docker.m.daocloud.io/library/mysql:8.4
PYTHON_IMAGE=docker.m.daocloud.io/library/python:3.12
API_IMAGE=eastman-adms-server:latest
```

如需更换镜像源，只修改 `.env` 中对应变量，不修改 `docker-compose.yml`。

## 密码要求

DT002 当前用于开发部署。如果 `.env` 中的 `MYSQL_PASSWORD` 仍使用默认占位密码，例如 `PLEASE_CHANGE_ME`、`changeme`、`password` 或 `123456`，安装脚本会输出警告并继续执行：

```text
[DT002] WARNING: MYSQL_PASSWORD uses a default development placeholder. Please modify MYSQL_PASSWORD before production deployment.
```

## 开发重置模式

仅开发环境可使用：

```bash
scripts/DT002_install_ubuntu.sh --reset-db
```

该模式会执行 `docker compose down` 并删除 `eastman-adms-mysql` Volume，然后重新创建数据库。正常部署不会删除数据。

## 验证

```bash
curl http://localhost:8080/health
curl http://localhost:8080/ready
curl http://localhost:8080/api/v1/health
```

`/health` 和 `/ready` 预期返回：

```json
{"status":"ok"}
```

`/api/v1/health` 预期返回：

```json
{
  "project": "eastman-adms-server",
  "version": "0.0.2",
  "status": "running",
  "database": "connected",
  "time": "..."
}
```
