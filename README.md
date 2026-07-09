# Eastman ADMS Server

## 1. 项目简介

Eastman ADMS Server 是用于后续接入考勤设备、考勤平台和明道云/HAP 的服务端项目。

Development Task 002 建立数据库基础架构：应用启动时检查 MySQL 连接，并通过 SQLAlchemy ORM 自动创建初始化数据表。

本阶段不包含 ADMS 协议、考勤解析、明道云同步或考勤业务逻辑。

## 2. 系统要求

- Alibaba Cloud Linux 3 (OpenAnolis Edition) - primary target
- Ubuntu 22.04+ - compatibility target
- Ubuntu 24.04+ - compatibility target
- RHEL compatible distributions
- Docker
- Docker Compose
- Python 3.12
- FastAPI
- SQLAlchemy
- MySQL 8

## 3. 快速部署

在项目根目录执行：

```bash
scripts/DT002_install_ubuntu.sh
```

安装脚本会自动完成：

- 创建或补全 `.env`
- 验证 Docker
- 验证 Docker Compose
- 拉取 `.env` 中配置的 Docker 镜像
- 重建并重启容器
- 检查数据库连接
- 验证 `/api/v1/health`

部署成功后会输出：

```text
========================================
Database Ready
Application Ready
========================================
```

## 4. 项目目录结构

```text
eastman-adms-server/
├── app/
├── config/
├── logs/
├── backup/
├── mysql/
├── scripts/
│   ├── DT001_install_ubuntu.sh
│   ├── DT001.2_install_ubuntu.sh
│   ├── DT001.3_install_ubuntu.sh
│   ├── DT001.4_install_ubuntu.sh
│   └── DT002_install_ubuntu.sh
├── docs/
│   ├── Architecture.md
│   ├── Deploy.md
│   └── PROJECT_STATUS.md
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── README.md
├── CHANGELOG.md
└── .gitignore
```

## 5. Docker 服务说明

| 服务 | 说明 |
| --- | --- |
| `mysql` | MySQL 8 数据库，仅用于初始化阶段连接检查 |
| `api` | Python 3.12 + FastAPI 应用，负责数据库初始化和健康检查 |

默认 Docker 镜像由 `.env` 维护：

| 配置 | 默认值 |
| --- | --- |
| `MYSQL_IMAGE` | `docker.m.daocloud.io/library/mysql:8.4` |
| `PYTHON_IMAGE` | `docker.m.daocloud.io/library/python:3.12` |
| `API_IMAGE` | `eastman-adms-server:dt002` |

Docker Volume：

| Volume | 用途 |
| --- | --- |
| `eastman-adms-mysql` | MySQL 数据 |
| `eastman-adms-logs` | 应用日志 |
| `eastman-adms-backup` | 后续备份文件 |

## 6. 数据库表

DT002 自动创建以下基础表：

| 表名 | 用途 |
| --- | --- |
| `device` | 保存考勤设备信息 |
| `attendance` | 保存后续解析后的考勤记录 |
| `raw_request` | 保存后续 ADMS 原始请求 |
| `sync_log` | 保存后续明道云同步记录 |

全新数据库部署时，SQLAlchemy 会自动创建 DT002 定义的唯一约束和索引，不需要手动执行 SQL。

健康检查接口：

```http
GET /api/v1/health
```

## 7. 后续开发阶段

DT003 预计进入 ADMS 请求接收或设备连接验证。DT002 完成后等待 Review，不进入 DT003。

明确禁止在 DT002 中加入：

- ADMS 协议实现
- 考勤解析
- 明道云同步
- 考勤业务逻辑

## 8. License

Reserved.
