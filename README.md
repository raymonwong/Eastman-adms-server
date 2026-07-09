# Eastman ADMS Server

## 1. 项目简介

Eastman ADMS Server 是用于后续接入考勤设备、考勤平台和明道云/HAP 的服务端项目。

Development Task 001.1 只修正 DT001 初始化质量，不包含任何 ADMS 业务逻辑、数据库表、业务接口或明道云同步。

## 2. 系统要求

- Ubuntu Server
- Docker
- Docker Compose
- Python 3.12
- FastAPI
- SQLAlchemy
- MySQL 8

## 3. 快速部署

在项目根目录执行：

```bash
scripts/DT001_install_ubuntu.sh
```

安装脚本会自动完成：

- 检查 Ubuntu 系统
- 安装 Docker 和 Docker Compose
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
│   └── DT001_install_ubuntu.sh
├── docs/
│   ├── Architecture.md
│   └── Deploy.md
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

DT002 预计进行 ZKEcoPro 或 ADMS 连接验证。DT001.1 完成后等待 Review，不进入 DT002。

明确禁止在 DT001.1 中加入：

- ADMS 业务逻辑
- 数据库表
- 业务接口
- 明道云同步
- 考勤同步逻辑

## 7. License

Reserved.
