# Eastman ADMS Server

## 1. 项目简介

Eastman ADMS Server 是用于后续接入考勤设备、考勤平台和明道云/HAP 的服务端项目。

Development Task 010.14 增加 ADMS Users Console：通过 `/users` 只读查看 ADMS `device_user` 中的用户，并按部门分组展示员工工号、打卡机 PIN、姓名、同步状态和最后更新时间。

本阶段不修改 ADMS 协议、HTTP 返回格式、ATTLOG/OPLOG/USER Parser、考勤上传逻辑、明道云考勤同步或任何 ERP 业务逻辑。

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
scripts/DT010.14_install_ubuntu.sh
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
- 验证 Console V2 设备筛选和 Device Summary 数据结构
- 验证 Console V2 布局、Lucide 图标、紧凑表格和 Device Summary 列
- 验证 Console V2 数据集成、最多 7 条 ATTLOG、最多 10 条实时事件和设备筛选数据结构
- 验证 Console P0 设备唯一显示、加载/失败状态和筛选数据结构
- 验证 Device Management 加载/失败状态和英文主信息、中文辅助信息展示结构
- 验证 Realtime Event Log 的事件筛选、暂停刷新、技术详情、最新事件置顶和清空当前日志说明
- 验证 Device Management 的未保存提示、保存中状态和开关影响说明
- 验证 Console P2 Operation Monitor 导航、异常优先视图和 Device Summary 筛选/搜索/排序控件
- 验证 `package.json` 中声明官方 `lucide` 依赖
- 验证 `device` 设备管理配置字段
- 验证 `/dms` 页面
- 验证 `/api/devices` 数据
- 验证 Device Management 优化 UI
- 验证 `device_user` Mingdao 用户字段
- 验证 `device_user_sync` 表
- 验证 `POST /api/v1/users`
- 验证 `POST /api/v1/users/batch`
- 验证 `GET /api/v1/users/{employee_id}`
- 验证 `employee_id` 与 `pin` 分开保存
- 验证重复 `pin` 返回 `409 Conflict`
- 验证 `/users` 用户页面
- 验证 `/api/adms-users` 用户读取接口
- 失败时输出容器状态和最近 100 行容器日志

部署成功后会输出：

```text
========================================
DT010.14 ADMS Users Console Ready
Page: /users
API: /api/adms-users
Grouped by Department
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
│   ├── DT009.5_install_ubuntu.sh
│   ├── DT009.6_install_ubuntu.sh
│   ├── DT009.7_install_ubuntu.sh
│   ├── DT009.8_install_ubuntu.sh
│   ├── DT009.81_install_ubuntu.sh
│   ├── DT009.82_install_ubuntu.sh
│   ├── DT009.83_install_ubuntu.sh
│   ├── DT010.1_install_ubuntu.sh
│   ├── DT010.11_install_ubuntu.sh
│   ├── DT010.13_install_ubuntu.sh
│   └── DT010.14_install_ubuntu.sh
├── docs/
│   ├── Architecture.md
│   ├── Deploy.md
│   └── PROJECT_STATUS.md
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── package.json
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
| `device_user` | 保存设备上传 USER 用户资料和 Mingdao 用户主数据 |
| `device_user_sync` | 保存 Mingdao 用户到每台设备的同步状态 |
| `raw_request` | 保存 ADMS 原始请求和服务器响应快照 |
| `device_event_log` | 保存设备连接事件历史 |
| `sync_log` | 保存后续明道云同步记录 |

DT003 为 `raw_request` 增加 `parsed`、`request_hash`、完整 URL、查询参数、客户端 IP、User-Agent、Content-Type、HTTP 响应内容、HTTP 状态码、请求大小和响应大小等原始请求审计字段。

DT004 为 `device` 增加初始化握手字段：`last_handshake_time`、`push_version`、`device_type`、`language`、`push_options`。

DT005 增加 `attendance_event`，保存设备序列号、PIN、考勤时间、状态、验证方式、工作代码、保留字段、口罩标识、温度、转换温度、接收时间和对应 `raw_request`。

DT006 增加 `operation_event`，保存设备序列号、操作代码、操作名称、操作人、操作时间、操作对象、Value1、Value2、Value3、接收时间和对应 `raw_request`。

DT007 增加 `device_sync_state`，保存设备序列号、数据类型、设备 Stamp、最后成功时间和最后原始请求 ID。本阶段只记录状态，不改变初始化握手返回的固定 Stamp。

DT008 增加 `device_user`，保存设备序列号、PIN、姓名、权限、密码、卡号、组号、时区、验证方式、副卡、开始时间、结束时间、接收时间和对应 `raw_request`。同一设备同一 PIN 再次上传时执行更新。

DT009.6 为 `device` 增加设备管理配置字段：`location`、`record_attendance`、`show_in_console`。设备仍然通过 ADMS 请求自动发现，不提供手动新增和删除。DT009.7 将新设备默认名称优化为 `New Machine (Device SN)`，并将布尔字段在 UI 中显示为 `ON / 开启` 或 `OFF / 关闭`。

DT009.8 将 Console 升级为多设备监控中心。Console 只显示 `show_in_console = true` 的设备，并在监控视图中优先显示 Device Name。DT009.82 将设备筛选收敛为所有设备或单台可显示设备。DT009.83 完成 Console P0/P1/P2 体验优化，统一筛选作用域、设备唯一显示、加载/失败状态、ATTLOG 主日志去重、事件日志操作控件、异常优先视图和设备状态总览筛选/搜索/排序。

DT010.1 扩展 `device_user`，新增 `employee_id`、`department`、`card_no`、`enabled` 等 Mingdao 用户字段，并新增 `device_user_sync`。Mingdao 用户以 `employee_id` 作为唯一业务键；重复提交相同数据不会产生重复用户，也不会重复触发同步。DT011 完成员工同步闭环：用户新增或变更后，系统会为所有已登记设备创建或更新 `PENDING` 同步记录；设备访问 `/iclock/getrequest` 时服务器返回 `DATA UPDATE USERINFO` 命令；设备通过 `/iclock/devicecmd` 回传执行结果后，`device_user_sync` 更新为 `SYNCED` 或 `FAILED`。

DT010.1 Review Fix 增加 Mingdao API Token 鉴权。部署前必须在 `.env` 中配置：

```env
MINGDAO_API_TOKEN=replace-with-a-secure-token
USER_SYNC_MAX_RETRY=3
USER_SYNC_ACK_TIMEOUT_SECONDS=120
```

调用 Mingdao 用户 API 时支持以下任意一种方式：

```http
Authorization: Bearer replace-with-a-secure-token
X-API-Key: replace-with-a-secure-token
```

`device_user` 是系统唯一员工主表，Mingdao 是唯一员工主数据来源。设备端 USER 上传只允许更新设备侧元数据，例如最后上传设备、最后上传时间和最后原始请求 ID；不得覆盖 Mingdao 下发的员工姓名、部门、启用状态、权限等主数据。`device_user_sync.sync_status` 仅允许 `PENDING`、`SYNCING`、`SYNCED`、`FAILED`。批量同步每次最多 500 个用户。

DT010.11 在现有 Communication Console 中增加 System Settings Integration 页面：

```text
http://<Server Address>:4370/settings/integration
```

该页面用于 Mingdao 集成配置、API Token 查看/复制/生成/保存、运行时状态查看、Health Check、管理员集成指南和自动生成 cURL 示例。页面只用于集成配置和调试，不改变 ATTLOG、OPERLOG、USER Parser、GETREQUEST、设备同步状态或 Mingdao 用户同步逻辑。永久文档见：

```text
docs/Mingdao_API_Integration.md
```

DT010.12 增强现有 Integration 页面，不改变布局和既有 Console 功能。API Token 默认全掩码显示，只有点击 Show 才显示完整令牌；API Base URL 继续根据当前访问 Host 动态生成；页面新增 Mingdao Configuration Guide、Copy Mingdao Configuration、API Test、Last API Response Code、Total API Requests 和 Open Integration Documentation。

DT010.13 增加 Mingdao 用户 `pin` 字段支持。`employee_id` 仅作为 Mingdao/ERP 工号参考和人员关联字段保留在数据表中；`pin` 是未来下发/更新打卡机用户时使用的设备用户编号。不同 `employee_id` 不允许使用相同 `pin`，重复时接口返回 `409 Conflict`。旧请求如果未传 `pin`，系统仍兼容使用 `employee_id` 作为默认 PIN。

DT010.14 增加只读 ADMS Users Console：

```text
http://<Server Address>:4370/users
```

该页面从 `device_user` 读取用户，按部门分组展示，并显示 `employee_id`、`pin`、姓名、来源、权限、启用状态、每台设备同步状态、最后设备上传和更新时间。页面只用于查看，不修改用户、不改变 Mingdao API 或数据库结构。

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

Console 是开发阶段唯一控制台入口，DT009.83 后按固定监控布局展示真实数据库数据：

- Server Status / 服务器状态
- Device Filter / 设备筛选
- Dashboard / 仪表盘
- Exception Priority / 异常优先
- Latest Activity / 最近活动
- Device Summary / 设备状态总览
- Realtime Event Log / 实时事件日志

Console 只显示 Device Management 中 `show_in_console = true` 的设备。全局 Device Filter 位于服务器状态卡片下方、业务统计卡片上方，可按所有设备或单台设备筛选；Dashboard、Latest Activity、Realtime Event Log 和 Device Summary 会同步跟随筛选条件。所有筛选请求使用 `device_sn`，不使用设备名称作为筛选依据。

在线状态使用最近 Heartbeat 判断：60 秒内显示 Online，超过 60 秒显示 Offline。Console 统一显示 `设备名称 · 设备 SN · 所属位置`，所属位置为空时显示 `设备名称 · 设备 SN`，无法匹配设备时显示 `Unknown Device`。Latest Activity 从 `attendance_event` 读取最新 7 条 ATTLOG，按 `attendance_time DESC` 排序；员工编号在页面显示为 5 位，不修改数据库原始 PIN；考勤时间完整显示。Realtime Event Log 从现有 raw request、ATTLOG、USER、OPLOG 记录生成当前筛选条件下的最新 10 条事件，前端和后端均按事件时间倒序显示，确保最新事件在最上方；已保存的 ATTLOG 不再重复显示对应 raw ATTLOG 主日志。心跳默认折叠为 Heartbeat Summary，不逐条占用主日志；主日志默认突出考勤、设备上线/离线、操作、用户同步和异常事件。新到达的 Latest Activity 和 Realtime Event Log 记录会短暂红色底色闪动，用于提示有新记录进入，闪动结束后恢复正常底色。事件日志支持事件类型筛选、关键字搜索、暂停/继续实时刷新、自动滚动开关、清除筛选条件，以及技术详情折叠和复制。Device Summary 支持按状态筛选、按设备名称/SN/位置搜索，并支持按最后心跳、最后考勤和今日考勤排序；异常优先视图可快速筛选离线或超时未心跳设备。协议代码在主界面转换为业务语言，例如 `Attendance Event`、`Device Operation`、`Device Heartbeat`，原始类型和详情保留在 Technical Details。页面首次加载和切换设备筛选时显示加载状态，接口失败显示失败原因和重新加载按钮，接口成功且结果为空时才显示无数据状态。页面统一使用英文作为主信息、中文作为辅助信息。页面统一使用官方 Lucide Icons，`package.json` 声明 `lucide` 依赖；非 React 页面通过 Lucide 官方 UMD 构建渲染图标。不使用 Wi-Fi、Signal 或 Radio 图标表示设备在线。页面每 2 秒自动刷新，切换设备筛选时通过 `GET /console?format=json&device_filter=<value>` Ajax 刷新，不新增 `/monitor`、`/dashboard`、`/status`、`/events` 或 `/statistics` 页面。

Device Management / 设备管理:

```http
GET /dms
```

Device Management 是独立配置模块，不属于 Console。页面提供设备搜索和编辑，不提供新增和删除。设备由 ADMS 请求自动注册，默认值为：

- `device_name = New Machine (Device SN)`
- `record_attendance = TRUE`
- `show_in_console = TRUE`

设备管理页按 `updated_at DESC` 排序，搜索支持设备名称、设备 SN 和所属位置。页面首次加载显示加载状态，接口失败显示失败原因和重新加载按钮，接口成功且结果为空时才显示无数据状态。存在同名设备时页面会显示提示，编辑保存成功提示会同时显示设备名称和 SN。编辑弹窗在内容未变化时禁用 Save，保存过程中显示 Saving 并防止重复点击，存在未保存修改时关闭会提示确认，保存失败会保留用户输入并显示失败原因。Record Attendance 和 Show in Console 均显示影响说明，关闭 Record Attendance 时仍会询问是否同时关闭 Console 显示。

REST API:

```http
GET /api/devices
GET /api/device/{sn}
PUT /api/device/{sn}
```

`PUT /api/device/{sn}` 仅允许更新 `device_name`、`location`、`record_attendance`、`show_in_console`。当 `record_attendance = FALSE` 时，服务器继续接收设备请求并正常返回，但跳过 ATTLOG 入库和考勤事件处理，适合测试设备使用。在 `/dms` 页面关闭 Record Attendance 时，会提示是否同时关闭 Show in Console。本阶段只保存 `show_in_console` 字段，不改变 Console 显示过滤。

Mingdao User Synchronization API:

```http
POST /api/v1/users
POST /api/v1/users/batch
GET /api/v1/users
GET /api/v1/users/{employee_id}
```

单个用户同步请求示例：

```json
{
  "employee_id": "ESM0001",
  "pin": "1",
  "name": "Raymon",
  "department": "IT",
  "card_no": "",
  "privilege": 0,
  "enabled": true
}
```

`employee_id` 保存 Mingdao/ERP 工号，例如 `ESM0001`；`pin` 保存打卡机用户编号，例如 `1`。`POST /api/v1/users` 使用 UPSERT 逻辑。如果 `employee_id` 已存在则更新，否则新增；如果字段没有变化，则返回成功但不重置 `device_user_sync`。如果其它员工已使用相同 `pin`，接口返回 `409 Conflict`，避免不同员工绑定同一个打卡机编号。`POST /api/v1/users/batch` 会逐条处理，单条失败不会影响后续用户。新增或变更用户后，系统会为每台 `record_attendance = TRUE` 的已登记设备维护一条 `device_user_sync` 记录并设置为 `PENDING`；`record_attendance = FALSE` 的设备不参与用户同步。设备后续访问 `/iclock/getrequest` 时会收到 `C:<sync_id>:DATA UPDATE USERINFO ...` 命令；如果打卡机已经存在相同 `PIN`，设备按 `DATA UPDATE USERINFO` 更新/覆盖该用户信息。设备执行后通过 `/iclock/devicecmd` 回传 `ID=<sync_id>&Return=0` 时，同步记录更新为 `SYNCED`。失败回执会记录为 `FAILED`，并按 `USER_SYNC_MAX_RETRY` 限制重试。

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

DT011 完成后等待 Review，不进入指纹、人脸、照片或 Command Queue 开发。

明确禁止在 DT011 中加入：

- 考勤结果计算
- 排班
- 迟到/早退/加班判断
- 请假/补卡
- 薪资
- 统计
- Command Queue
- 动态 ATTLOGStamp
- 动态 OPERLOGStamp
- FACE
- FINGER
- BIODATA
- 指纹同步
- 人脸同步
- 照片同步
- 考勤同步到明道云
- 考勤业务逻辑

## 9. License

Reserved.
