# Eastman ADMS Server

## 1. 项目简介

Eastman ADMS Server 是用于后续接入考勤设备、考勤平台和明道云/HAP 的服务端项目。

Development Task 005 实现 ATTLOG 数据接收与解析：设备通过 `POST /iclock/cdata?table=ATTLOG` 上传考勤记录时，服务器按《考勤 PUSH 通讯协议 V4.3》第 12.2 章解析并保存到 `attendance_event`。

本阶段只保存设备上传的原始考勤事件，不包含排班、迟到、早退、加班、请假、补卡、薪资、统计、用户同步、命令队列、明道云同步或任何 ERP 业务逻辑。

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
scripts/DT005_install_ubuntu.sh
```

安装脚本会自动完成：

- 创建或补全 `.env`
- 验证 Docker
- 验证 Docker Compose
- 拉取 `.env` 中配置的 Docker 镜像
- 执行 `docker compose build --pull`
- 执行 `docker compose up -d`
- 使用 `SHOW TABLES;` 检查数据库表
- 验证 `/api/v1/health`
- 验证初始化握手响应构造
- 验证 `attendance_event` 表和 ATTLOG 解析器
- 失败时输出容器状态和最近 100 行容器日志

部署成功后会输出：

```text
========================================
ATTLOG Parser Ready
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
│   ├── DT002_install_ubuntu.sh
│   ├── DT004_install_ubuntu.sh
│   └── DT005_install_ubuntu.sh
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
| `API_IMAGE` | `eastman-adms-server:latest` |

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
| `attendance_event` | 保存设备上传的原始 ATTLOG 考勤事件 |
| `raw_request` | 保存 ADMS 原始请求和服务器响应快照 |
| `device_event_log` | 保存设备连接事件历史 |
| `sync_log` | 保存后续明道云同步记录 |

DT003 为 `raw_request` 增加 `parsed`、`request_hash`、完整 URL、查询参数、客户端 IP、User-Agent、Content-Type、HTTP 响应内容、HTTP 状态码、请求大小和响应大小等原始请求审计字段。

DT004 为 `device` 增加初始化握手字段：`last_handshake_time`、`push_version`、`device_type`、`language`、`push_options`。

DT005 增加 `attendance_event`，保存设备序列号、PIN、考勤时间、状态、验证方式、工作代码、保留字段、口罩标识、温度、转换温度、接收时间和对应 `raw_request`。

开发环境如需重建数据库，可执行：

```bash
scripts/DT002_install_ubuntu.sh --reset-db
```

正常部署不会删除 Docker Volume 或已有数据。

健康检查接口：

```http
GET /api/v1/health
```

ADMS 设备接入接口：

```http
GET /iclock/cdata
POST /iclock/cdata
```

非初始化握手请求继续返回 `HTTP 200` 和 `OK`，保持 DT003 兼容。

初始化信息交互：

```http
GET /iclock/cdata?SN=<SN>&options=all&pushver=<VERSION>&DeviceType=<TYPE>&language=<LANG>
```

响应内容按官方协议返回 `GET OPTION FROM: <SN>`，并包含 `ATTLOGStamp=9999`、`OPERLOGStamp=9999`、`ATTPHOTOStamp=9999`、`ERRORLOGStamp=9999`、`TimeZone=4`、`Realtime=1`、`Delay=10`、`ErrorDelay=30`、`TransFlag=TransData	AttLog	OpLog	EnrollUser	ChgUser	EnrollFP	ChgFP	FACE	UserPic`、`PushProtVer=2.4.2` 等配置。

ATTLOG 上传：

```http
POST /iclock/cdata?SN=<SN>&table=ATTLOG&Stamp=<STAMP>
```

请求体按官方格式解析为多行记录，最低要求 6 字段 `PIN<TAB>Time<TAB>Status<TAB>Verify<TAB>WorkCode<TAB>Reserved1`，并兼容可选字段 `Reserved2<TAB>MaskFlag<TAB>Temperature<TAB>ConvTemperature`。服务器成功保存后返回 `OK:n`，其中 `n` 是成功解析并保存的记录数。

## 7. 设备配置说明

设备端推荐配置：

| 配置项 | 推荐值 |
| --- | --- |
| Server Address | 服务器公网 IP 或域名 |
| Server Port | `4370` |
| ADMS | 开启 |
| Push | 开启 |
| URL/Path | 如设备支持路径配置，填写 `/iclock/cdata` |

如果设备只支持填写完整地址，使用：

```text
http://<Server Address>:4370/iclock/cdata
```

推荐先使用 HTTP 方式联调。DT003 不直接启用 HTTPS；如设备要求 HTTPS，后续可在服务器前增加 Nginx 或负载均衡并配置证书。

连接成功判断：

- API 容器日志出现 `Device Connected`
- `device` 表新增或更新对应 `SN`
- `raw_request` 表新增完整原始请求
- `device_event_log` 表新增 `Connect` 事件
- 设备请求收到 `HTTP 200` 和 `OK`

常见故障排查：

- 检查云服务器安全组是否放行 TCP `4370`
- 检查服务器防火墙是否放行 TCP `4370`
- 检查设备网络、网关和 DNS 是否正常
- 检查设备 Server Address、Server Port、ADMS、Push 配置是否正确
- 执行 `docker compose ps` 确认容器运行状态
- 执行 `docker logs eastman-adms-api --tail 100` 查看连接日志
- 访问 `http://<Server Address>:4370/api/v1/health` 确认服务正常

## 8. 后续开发阶段

DT006 预计根据真实设备数据继续处理下一类协议数据。DT005 完成后等待 Review，不进入 DT006。

明确禁止在 DT005 中加入：

- 考勤结果计算
- 排班
- 迟到/早退/加班判断
- 请假/补卡
- 薪资
- 统计
- 用户同步
- 设备命令
- Command Queue
- 明道云同步
- 考勤业务逻辑

## 9. License

Reserved.
