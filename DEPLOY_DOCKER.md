# 股票分析与投资决策系统 - Docker 部署指南

## 环境要求

| 组件 | 版本 |
|------|------|
| Docker Engine | 24+ |
| Docker Compose | 2.20+ |
| 内存 | 至少 1 GB（分配） |
| 磁盘 | 2 GB |

## 快速部署

### 1. 构建并启动

```bash
# 从项目根目录执行（包含 Dockerfile 的目录）
cd /path/to/workspace

# 构建镜像并启动
docker compose up -d

# 查看启动日志
docker compose logs -f stock-analysis
```

### 2. 访问系统

浏览器打开：**http://服务器IP:8000**

### 3. 停止服务

```bash
docker compose down
# 如需同时删除数据卷
docker compose down -v
```

## 自定义配置

### 环境变量

通过 `docker-compose.yml` 的 `environment` 配置：

```yaml
environment:
  # 管理员密码（首次启动前修改！）
  - DEFAULT_ADMIN_PASSWORD=your_secure_password
  
  # 可选：MySQL 替代 SQLite
  - DATABASE_URL=mysql+aiomysql://user:pass@mysql-host:3306/stock_db
  
  # 可选：DeepSeek AI（用于智能分析）
  - DEEPSEEK_API_KEY=sk-xxx
  
  # 可选：通达信本地数据挂载路径
  - TDX_DATA_DIR=/data/tdx
```

### 数据持久化

```yaml
volumes:
  - stock_data:/app/data              # 数据库和报告持久化
  - /path/to/tdx:/data/tdx:ro         # 可选：通达信数据挂载
```

### 修改端口

```yaml
ports:
  - "8080:8000"  # 将宿主机 8080 映射到容器 8000
```

## 使用外部数据库（MySQL）

1. 在 `docker-compose.yml` 中添加 MySQL 服务：

```yaml
services:
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: rootpass
      MYSQL_DATABASE: stock_db
      MYSQL_USER: stock
      MYSQL_PASSWORD: stockpass
    volumes:
      - mysql_data:/var/lib/mysql
    healthcheck:
      test: ["CMD", "mysqladmin", "ping"]
      
  stock-analysis:
    depends_on:
      mysql:
        condition: service_healthy
    environment:
      - DATABASE_URL=mysql+aiomysql://stock:stockpass@mysql:3306/stock_db

volumes:
  mysql_data:
```

2. 重启：
```bash
docker compose up -d
```

## 健康检查

```bash
# 服务健康状态
docker compose ps

# API 健康检查
curl http://localhost:8000/api/v1/health

# 预期返回
{"status":"ok","service":"stock-analysis-system","version":"1.0.0"}
```

## 镜像管理

```bash
# 重新构建（更新代码后）
docker compose build --no-cache stock-analysis

# 查看镜像
docker images stock-analysis

# 导出镜像用于离线部署
docker save stock-analysis:1.0.0 -o stock-analysis-1.0.0.tar

# 导入镜像
docker load -i stock-analysis-1.0.0.tar

# 推送到私有仓库
docker tag stock-analysis:1.0.0 registry.example.com/stock-analysis:1.0.0
docker push registry.example.com/stock-analysis:1.0.0
```

## 生产环境安全建议

1. **修改默认密码**：首次启动前务必修改 `DEFAULT_ADMIN_PASSWORD`
2. **限制访问**：配置防火墙只允许可信 IP 访问 8000 端口
3. **使用 HTTPS**：前置 Nginx 反向代理配置 SSL
4. **定期备份**：备份 `stock_data` 卷中的数据
5. **日志轮转**：Docker 默认日志驱动建议配置 max-size

## 常见问题

### 端口冲突

```bash
# 修改 docker-compose.yml 中 ports 映射
ports:
  - "8080:8000"  # 改为其他端口
```

### 数据库权限

Docker 容器内运行的用户是 `root`，如需指定用户运行：

```yaml
services:
  stock-analysis:
    user: "1000:1000"
    volumes:
      - stock_data:/app/data
```

### 日志查看

```bash
# 实时日志
docker compose logs -f

# 最近100行
docker compose logs --tail=100
```
