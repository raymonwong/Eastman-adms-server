# Deploy

## 支持的部署系统

- Alibaba Cloud Linux 3 (OpenAnolis Edition) - 第一目标平台
- Ubuntu 22.04+ - 兼容平台
- Ubuntu 24.04+ - 兼容平台
- RHEL compatible distributions

从 DT001.2 开始，所有部署脚本优先面向 Alibaba Cloud Linux 3 设计，Ubuntu 作为兼容平台维护。

## Linux 部署

在项目根目录执行：

```bash
scripts/DT001.2_install_ubuntu.sh
```

脚本会自动：

1. 检查当前 Linux 发行版是否受支持，优先支持 Alibaba Cloud Linux 3。
2. 自动检测 `apt`、`dnf` 或 `yum`。
3. 安装 Docker。
4. 安装 Docker Compose。
5. 创建项目目录。
6. 根据 `.env.example` 创建 `.env`。
7. 创建 Docker Volume。
8. 启动 MySQL。
9. 启动 FastAPI。
10. 检查 MySQL 连接。
11. 检查 FastAPI 健康状态。

旧脚本 `scripts/DT001_install_ubuntu.sh` 保留用于历史追溯。DT001.2 起推荐使用 `scripts/DT001.2_install_ubuntu.sh`。

## 验证

```bash
curl http://localhost:8080/health
curl http://localhost:8080/ready
```

预期返回：

```json
{"status":"ok"}
```
