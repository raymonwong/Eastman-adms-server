# Eastman ADMS Server

## 1. 项目简介

Eastman ADMS Server 是用于后续接入考勤设备、考勤平台和明道云/HAP 的服务端项目。

Development Task 001.3 只修正中国大陆服务器拉取 Docker 镜像的部署可靠性，不包含任何 ADMS 业务逻辑、数据库表、业务接口或明道云同步。

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
scripts/DT001.3_install_ubuntu.sh
```

安装脚本会自动完成：

- 优先支持 Alibaba Cloud Linux 3，并兼容 Ubuntu / RHEL compatible distributions
- 通过 `/etc/os-release` 检查当前 Linux 发行版是否受支持
- 自动检测 `apt`、`dnf` 或 `yum`
- 安装 Docker 和 Docker Compose
- 检测 Docker Hub 是否可达
- Docker Hub 超时后自动配置 Docker 镜像源
- 自动重试 `docker compose pull`
- 创建 `.env`
- 创建 Docker Volume
- 启动 MySQL 8
- 启动 FastAPI
- 检查 MySQL 和 FastAPI 状态

部署成功后会输出：

```text
==================================
Eastman ADMS Server
Docker ............. OK
MySQL .............. OK
FastAPI ............ OK
Install Completed
==================================
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
│   └── DT001.3_install_ubuntu.sh
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

Docker Volume：

| Volume | 用途 |
| --- | --- |
| `eastman-adms-mysql` | MySQL 数据 |
| `eastman-adms-logs` | 应用日志 |
| `eastman-adms-backup` | 后续备份文件 |

## 6. 后续开发阶段

DT002 预计进行 ZKEcoPro 或 ADMS 连接验证。DT001.3 完成后等待 Review，不进入 DT002。

明确禁止在 DT001.3 中加入：

- ADMS 业务逻辑
- 数据库表
- 业务接口
- 明道云同步
- 考勤同步逻辑

## 7. License

Reserved.
