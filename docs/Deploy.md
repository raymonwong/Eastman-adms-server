# Deploy

## Ubuntu 部署

在项目根目录执行：

```bash
scripts/DT001_install_ubuntu.sh
```

脚本会自动：

1. 检查 Ubuntu 系统。
2. 安装 Docker。
3. 安装 Docker Compose。
4. 创建项目目录。
5. 根据 `.env.example` 创建 `.env`。
6. 创建 Docker Volume。
7. 启动 MySQL。
8. 启动 FastAPI。
9. 检查 MySQL 连接。
10. 检查 FastAPI 健康状态。

## 验证

```bash
curl http://localhost:8080/health
curl http://localhost:8080/ready
```

预期返回：

```json
{"status":"ok"}
```
