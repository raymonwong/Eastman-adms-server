# Eastman ADMS Server

## 1. 项目简介

Eastman ADMS Server 是用于后续接入考勤设备、考勤平台和明道云/HAP 的服务端项目。

Development Task 009.5 增加 ADMS Server Console：开发人员打开 `/console` 后，无需 SSH、MySQL、tcpdump 或 docker logs，即可查看服务器状态、设备 Online/Offline、Last Seen、Last Heartbeat、Last Data Upload、Last Raw Request、Last Request、实时事件和今日统计。Console 采用中英文双语和紧凑高信息密度界面，以最近一次设备通信 Last Seen 判断在线状态，60 秒内为 Online，超过 60 秒为 Offline。

本阶段不修改数据库结构、ADMS 协议、HTTP 返回、Parser 行为或任何 ERP 业务逻辑。

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
scripts/DT009.5_install_ubuntu.sh
```

安装脚本会自动完成：

- 创建或补全 `.env`
- 验证 Docker
- 验证 Docker Compose
- 拉取 `.env` 中配置的 Docker 镜像
- 镜像源临时超时时，如本地已有缓存镜像则继续部署
- 执行 `docker compose build --pull`
- 执行 `docker compose up -d --force-recreate api`，确保 API 容器运行最新构建代码
- 使用 `SHOW TABLES;` 检查数据库表
- 验证 `/api/v1/health`
- 验证初始化握手响应构造
- 验证 `attendance_event` 表和 ATTLOG 解析器
- 验证 `operation_event` 表和 OPERLOG 解析器
- 验证 `device_sync_state` 表和同步状态更新逻辑
- 验证 `device_user` 表和 USER 解析器
- 验证 ADMS debug log helper 可用
- 验证 `/console` 页面
- 验证 `/console?format=json` 数据
- 失败时输出容器状态和最近 100 行容器日志

部署成功后会输出：

```text
========================================
ADMS Server Console Ready
Console URL: http://SERVER_IP:4370/console
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
│   ├── DT005_install_ubuntu.sh
│   ├── DT006_install_ubuntu.sh
│   ├── DT007_install_ubuntu.sh
│   ├── DT008_install_ubuntu.sh
│   ├── DT009_install_ubuntu.sh
│   └── DT009.5_install_ubuntu.sh
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
| `operation_event` | 保存设备上传的原始 OPERLOG 操作事件 |
| `device_sync_state` | 保存每台设备每类数据的同步状态 |
| `device_user` | 保存设备在 OPERLOG Body 中上传的 USER 用户资料 |
| `raw_request` | 保存 ADMS 原始请求和服务器响应快照 |
| `device_event_log` | 保存设备连接事件历史 |
| `sync_log` | 保存后续明道云同步记录 |

DT003 为 `raw_request` 增加 `parsed`、`request_hash`、完整 URL、查询参数、客户端 IP、User-Agent、Content-Type、HTTP 响应内容、HTTP 状态码、请求大小和响应大小等原始请求审计字段。

DT004 为 `device` 增加初始化握手字段：`last_handshake_time`、`push_version`、`device_type`、`language`、`push_options`。

DT005 增加 `attendance_event`，保存设备序列号、PIN、考勤时间、状态、验证方式、工作代码、保留字段、口罩标识、温度、转换温度、接收时间和对应 `raw_request`。

DT006 增加 `operation_event`，保存设备序列号、操作代码、操作名称、操作人、操作时间、操作对象、Value1、Value2、Value3、接收时间和对应 `raw_request`。

DT007 增加 `device_sync_state`，保存设备序列号、数据类型、设备 Stamp、最后成功时间和最后原始请求 ID。本阶段只记录状态，不改变初始化握手返回的固定 Stamp。

DT008 增加 `device_user`，保存设备序列号、PIN、姓名、权限、密码、卡号、组号、时区、验证方式、副卡、开始时间、结束时间、接收时间和对应 `raw_request`。同一设备同一 PIN 再次上传时执行更新。

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

DT005 已通过真实设备 `UCE6262000016` 验证：`raw_request.parsed=1`、服务器响应 `OK:1`、`attendance_event` 正常生成并关联 `raw_request_id`。

OPERLOG 上传：

```http
POST /iclock/cdata?SN=<SN>&table=OPERLOG&Stamp=<STAMP>
```

请求体按第一列分发解析：

- `OPLOG` 保存到 `operation_event`，兼容官方 tab 格式和真实设备空格格式，例如 `OPLOG 4 0 2026-07-10 19:32:34 0 0 0 0`。
- `USER` 保存到 `device_user`，例如 `USER PIN=1 Name=raymon Pri=0 Passwd= Card= Grp=1 TZ=0000000100000000 Verify=1 ViceCard= StartDatetime=0 EndDatetime=0`。

服务器成功保存后返回 `OK:n`，其中 `n` 是成功解析并保存的记录数。

开发调试日志：

```bash
docker logs -f eastman-adms-api
```

DT009 输出统一格式日志，覆盖：

- `HANDSHAKE`
- `HEARTBEAT`
- `ATTLOG RECEIVED`
- `ATTLOG SAVED`
- `OPERLOG RECEIVED`
- `OPERLOG SAVED`
- `USER RECEIVED`
- `USER SAVED`
- `ERROR`

DT009 只增强日志，不改变 ADMS 返回内容、数据库结构、Parser 规则或业务逻辑。

ADMS Server Console:

```http
GET /console
```

Console 是开发阶段唯一控制台入口，包含：

- Server Status / 服务器状态
- Device Status / 设备状态
- Realtime Event Log / 实时事件日志
- Statistics / 今日统计
- Latest Activity / 最近活动

Device Status 使用 Last Seen 判断在线状态。Last Seen 表示设备最近一次通信时间，包括 HANDSHAKE、GETREQUEST、ATTLOG、OPERLOG、USER 或其它已保存的设备请求。60 秒内显示 Online，超过 60 秒显示 Offline。页面同时显示 Last Data Upload、Last Raw Request ID 和 Last Request Type，便于快速判断是否有新的请求进入服务器。

页面每 2 秒自动刷新。桌面端使用紧凑运维控制台排版，Current State 为响应式信息网格，Device Status 在宽屏下按三列显示，Realtime Event Log 在面板内部滚动。页面内数据通过同一路径 `GET /console?format=json` 读取，不新增 `/monitor`、`/dashboard`、`/status`、`/events` 或 `/statistics` 页面。

设备同步状态：

```text
device_sync_state
```

ATTLOG 或 OPERLOG 成功解析并保存后，服务器会按 `device_sn + data_type` 更新同步状态，记录设备请求中的 `Stamp`、最后成功时间和 `raw_request_id`。DT007 不把该状态用于动态初始化回复，`ATTLOGStamp=9999` 和 `OPERLOGStamp=9999` 保持不变。

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

DT010 预计根据真实设备数据继续处理下一类协议数据。DT009.5 完成后等待 Review，不进入 DT010。

明确禁止在 DT009.5 中加入：

- 考勤结果计算
- 排班
- 迟到/早退/加班判断
- 请假/补卡
- 薪资
- 统计
- 用户下发
- 人员同步
- 设备命令
- Command Queue
- 动态 ATTLOGStamp
- 动态 OPERLOGStamp
- FACE
- FINGER
- BIODATA
- 明道云同步
- 考勤业务逻辑

## 9. License

Reserved.
