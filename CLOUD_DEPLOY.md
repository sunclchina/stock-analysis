# 云服务器 Docker 部署实战指南

## 场景

本机 Windows（有完整代码）→ 云服务器 Linux（Docker 部署）

---

## 方式一：本地构建 → 导出镜像 → 上传到服务器 → 导入运行（推荐）

**优点**：服务器上不需要 Node.js / Python，只需 Docker。
**缺点**：镜像文件较大（~800MB），上传需要时间。

### 步骤 1：本机构建 Docker 镜像

```powershell
# 进入 workspace 根目录
cd C:\Users\suncl\.openclaw\workspace

# 构建镜像
docker build -f Dockerfile -t stock-analysis:1.0.0 .
```

### 步骤 2：导出镜像为 tar 文件

```powershell
# 导出（压缩后大概 200-300MB）
docker save stock-analysis:1.0.0 -o stock-analysis-1.0.0.tar
```

### 步骤 3：上传到云服务器

```powershell
# 用 scp 上传（替换成你自己的服务器 IP）
scp .\stock-analysis-1.0.0.tar root@你的服务器IP:/root/
```

### 步骤 4：云服务器上导入并运行

```bash
# SSH 登录云服务器
ssh root@你的服务器IP

# 导入镜像
docker load -i /root/stock-analysis-1.0.0.tar

# 创建数据目录
mkdir -p /opt/stock-analysis/data

# 启动容器
docker run -d \
  --name stock-analysis \
  --restart unless-stopped \
  -p 8000:8000 \
  -v /opt/stock-analysis/data:/app/data \
  -e DEFAULT_ADMIN_PASSWORD=你的安全密码 \
  stock-analysis:1.0.0

# 查看运行状态
docker ps
docker logs stock-analysis --tail 20

# 验证
curl http://localhost:8000/api/v1/health
```

### 步骤 5：配置安全组 / 防火墙

登录云服务商控制台 → 安全组/防火墙 → **放行 8000 端口**（TCP）。

然后浏览器访问：`http://服务器IP:8000`

---

## 方式二：服务器上直接 git clone + docker compose（有 Git 仓库时）

如果你把代码推到了 GitHub/Gitee，服务器上更简单：

```bash
# SSH 登录云服务器

# 1. 安装 Docker（如未安装）
curl -fsSL https://get.docker.com | sh
systemctl enable docker
systemctl start docker

# 2. 安装 Docker Compose（如未安装）
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# 3. 克隆代码
git clone https://github.com/你的仓库/项目.git
cd 项目

# 4. 构建并启动
docker compose build
docker compose up -d

# 5. 验证
curl http://localhost:8000/api/v1/health
```

---

## 方式三：scp 上传源码 → 服务器上构建（无 Git 仓库时）

### 本机操作

```powershell
# 把 workspace 源码打包
# 注意排除不需要的大文件
cd C:\Users\suncl\.openclaw\workspace
tar -czf stock-analysis.tar.gz `
  --exclude="dev-team/backend-dev/stock-analysis-backend/.venv" `
  --exclude="dev-team/backend-dev/stock-analysis-backend/__pycache__" `
  --exclude="dev-team/backend-dev/stock-analysis-backend/**/__pycache__" `
  --exclude="dev-team/backend-dev/stock-analysis-backend/**/*.pyc" `
  --exclude="dev-team/backend-dev/stock-analysis-backend/.pytest_cache" `
  --exclude="dev-team/backend-dev/stock-analysis-backend/logs" `
  --exclude="dev-team/frontend-dev/stock-analysis-frontend/node_modules" `
  --exclude="dev-team/frontend-dev/stock-analysis-frontend/dist" `
  --exclude=".git" `
  --exclude=".venv" `
  VERSION Dockerfile docker-compose.yml .dockerignore `
  dev-team/

# 上传到服务器
scp stock-analysis.tar.gz root@你的服务器IP:/opt/
```

### 服务器操作

```bash
# SSH 登录
ssh root@你的服务器IP

# 解压
cd /opt
tar -xzf stock-analysis.tar.gz

# 构建并启动
cd stock-analysis  # 解压后的目录名，根据实际情况调整
docker compose build
docker compose up -d

# 验证
curl http://localhost:8000/api/v1/health
```

---

## 后续维护

### 查看日志

```bash
docker compose logs -f --tail=50
```

### 更新版本

```bash
# 本机：重新 build + save
docker build -f Dockerfile -t stock-analysis:新版本号 .
docker save stock-analysis:新版本号 -o stock-analysis-新版本号.tar
scp stock-analysis-新版本号.tar root@服务器IP:/root/

# 服务器
docker load -i /root/stock-analysis-新版本号.tar
docker stop stock-analysis
docker rm stock-analysis
# 用新镜像启动（命令同上）
```

### 备份数据

```bash
# 数据库和报告数据在数据卷中
docker run --rm -v stock-analysis-data:/data -v /opt/backup:/backup alpine tar -czf /backup/stock-data-$(date +%Y%m%d).tar.gz -C /data .
```

### 日常运维命令速查

| 操作 | 命令 |
|------|------|
| 查看运行状态 | `docker compose ps` |
| 查看实时日志 | `docker compose logs -f` |
| 重启服务 | `docker compose restart` |
| 停止服务 | `docker compose down` |
| 完全重建（代码更新后） | `docker compose build --no-cache && docker compose up -d` |
| 进入容器排查 | `docker exec -it stock-analysis sh` |
