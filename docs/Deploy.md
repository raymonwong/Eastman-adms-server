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
scripts/DT001.3_install_ubuntu.sh
```

脚本会自动：

1. 通过 `/etc/os-release` 检查当前 Linux 发行版是否受支持，优先支持 Alibaba Cloud Linux 3。
2. 自动检测 `apt`、`dnf` 或 `yum`。
3. Ubuntu 使用 Docker 官方 Ubuntu 仓库安装 Docker。
4. Alibaba Cloud Linux 3 / RHEL compatible distributions 使用 Docker CE CentOS/RHEL 兼容仓库安装 Docker。
5. 安装 Docker Compose plugin。
6. 检查 Docker Hub 是否可达。
7. Docker Hub 超时后自动配置 Docker 镜像源。
8. 自动重启 Docker。
9. 自动重试 `docker compose pull` 至少 3 次。
10. 创建项目目录。
11. 根据 `.env.example` 创建 `.env`。
12. 创建 Docker Volume。
13. 启动 MySQL。
14. 启动 FastAPI。
15. 检查 MySQL 连接。
16. 检查 FastAPI 健康状态。

旧脚本 `scripts/DT001_install_ubuntu.sh` 和 `scripts/DT001.2_install_ubuntu.sh` 保留用于历史追溯。DT001.3 起推荐使用 `scripts/DT001.3_install_ubuntu.sh`。

## Docker 镜像源

DT001.3 会先检测 Docker Hub 是否可达。如果不可达，会尝试内置中国大陆镜像源候选：

- Aliyun Mirror
- Docker Official China Mirror if available
- Tencent Mirror
- USTC Mirror

如需指定镜像源，可在 `.env` 中设置：

```dotenv
DOCKER_REGISTRY_MIRROR=https://your-mirror.example.com
```

如果 `/etc/docker/daemon.json` 已经存在 `registry-mirrors`，脚本不会覆盖现有镜像配置。

## 验证

```bash
curl http://localhost:8080/health
curl http://localhost:8080/ready
```

预期返回：

```json
{"status":"ok"}
```
