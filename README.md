# Eastman ADMS Server

## 1. 项目简介

Eastman ADMS Server 是用于后续接入考勤设备、考勤平台和明道云/HAP 的服务端项目。

Development Task 001.4 完成 DT001 部署收口：生产环境以 Alibaba Cloud Linux 3 为第一目标平台，Docker 镜像统一从 `.env` 配置，并默认使用已验证可达的 DaoCloud Proxy 镜像。

本阶段不包含任何 ADMS 业务逻辑、数据库表、业务接口或明道云同步。

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
scripts/DT001.4_install_ubuntu.sh
```

安装脚本会自动完成：

- 创建或补全 `.env`
- 创建 Docker Volume
- 验证 Docker
- 验证 Docker Compose
- 拉取 `.env` 中配置的 Docker 镜像
- 启动 MySQL
- 启动 FastAPI
- 执行 `docker compose ps`
- 执行 `docker ps`
- 检查 MySQL 和 FastAPI 容器运行状态

部署成功后会输出：

```text
Docker Running
MySQL Running
FastAPI Running
Install Completed
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
│   └── DT001.4_install_ubuntu.sh
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
| `api` | Python 3.12 + FastAPI 应用，仅提供健康检查 |

默认 Docker 镜像由 `.env` 维护：

| 配置 | 默认值 |
| --- | --- |
| `MYSQL_IMAGE` | `docker.m.daocloud.io/library/mysql:8.4` |
| `PYTHON_IMAGE` | `docker.m.daocloud.io/library/python:3.12` |
| `API_IMAGE` | `eastman-adms-server:dt001` |

Docker Volume：

| Volume | 用途 |
| --- | --- |
| `eastman-adms-mysql` | MySQL 数据 |
| `eastman-adms-logs` | 应用日志 |
| `eastman-adms-backup` | 后续备份文件 |

## 6. 后续开发阶段

DT002 预计进行 ZKEcoPro 或 ADMS 连接验证。DT001.4 完成后等待 Review，不进入 DT002。

明确禁止在 DT001.4 中加入：

- ADMS 业务逻辑
- 数据库表
- 业务接口
- 明道云同步
- 考勤同步逻辑

## 7. License

Reserved.
