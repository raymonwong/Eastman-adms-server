# Architecture

## 初始化版本

DT001.1 只建立 Eastman ADMS Server 的基础运行环境。

```text
Client / Operator
        |
        v
FastAPI container
        |
        v
MySQL 8 container
```

## 当前组件

- `api`: FastAPI 应用，仅用于健康检查和 MySQL 连接检查。
- `mysql`: MySQL 8 数据库，仅用于初始化环境验证。
- Docker Volumes: 保存 MySQL 数据、日志目录和备份目录。

## 当前不包含

- ADMS 协议
- 设备接入
- 数据库表
- 明道云同步
- 业务接口

