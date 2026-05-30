# 部署文档 — 股票分析与投资决策系统

> **版本：** 1.0.0  
> **维护：** 运维工程师  
> **端口：** 前端 8080 / 后端 8000  
> **架构：** 遵循 `dev-team/architect/architecture-plan.md`

---

## 目录

1. [快速启动](#一快速启动)
2. [配置说明](#二配置说明)
3. [端口说明](#三端口说明)
4. [健康检查](#四健康检查)
5. [Docker 部署](#五docker-部署)
6. [目录结构](#六目录结构)
7. [常见问题](#七常见问题)

---

## 一、快速启动

### 1.1 前提条件

| 组件 | 最低版本 | 检查命令 |
|------|---------|---------|
| Python | 3.10+ | `python --version` |
| Node.js | 18+ | `node --version` |
| npm | 9+ | `npm --version` |
| PowerShell | 5.1+ | `$PSVersionTable.PSVersion` |

### 1.2 一键启动（推荐）

```
# 从 dev-team/devops/ 目录执行
.\start-all.ps1
```

脚本将自动：
1. ✅ 检查端口 8000 和 8080 可用性
2. ✅ 关闭可能的残留进程
3. ✅ 启动后端服务（Uvicorn + FastAPI）
4. ✅ 等待后端健康检查通过
5. ✅ 启动前端服务（Vite 开发服务器）
6. ✅ 输出所有访问地址

### 1.3 分别启动

```powershell
# 启动后端（终端1）
.\start-backend.ps1

# 启动前端（终端2）
.\start-frontend.ps1
```

### 1.4 构建 + 启动

```powershell
# 先构建前端产物，再启动
.\start-all.ps1 -Build
```

---

## 二、配置说明

### 2.1 环境变量列表

所有配置项通过 `.env` 文件注入（`dev-team/backend-dev/stock-analysis-backend/.env`）。

| 变量名 | 默认值 | 说明 |
|--------|-------|------|
| `BACKEND_HOST` | `0.0.0.0` | 后端监听地址 |
| `BACKEND_PORT` | `8000` | 后端监听端口 |
| `BACKEND_RELOAD` | `true` | 开发模式热重载（生产设为 false） |
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/cache/stock.db` | 数据库连接地址 |
| `CORS_ORIGINS` | `["http://localhost:8080"]` | 允许跨域的源 |
| `TDX_DATA_DIR` | `./data/tdx` | 通达信本地数据目录 |
| `PRIMARY_DATA_SOURCE` | `tdx_local` | 主力数据源 |
| `FALLBACK_DATA_SOURCE` | `sina` | 备用数据源 |
| `DEEPSEEK_API_KEY` | （空） | DeepSeek API 密钥 |
| `DEEPSEEK_API_URL` | `https://api.deepseek.com/v1/chat/completions` | DeepSeek API 地址 |
| `DEEPSEEK_MODEL` | `deepseek-chat` | DeepSeek 模型名称 |
| `LOG_LEVEL` | `INFO` | 日志级别 |

### 2.2 首次部署：创建配置文件

> ⚠️ **重要：** `.env` 已被 `.gitignore` 排除，不会提交到仓库。
> 第一次部署时请从模板创建，不要直接使用已有的 `.env`。

```powershell
# 从示例模板创建 .env（推荐）
cp dev-team/backend-dev/stock-analysis-backend/.env.example dev-team/backend-dev/stock-analysis-backend/.env

# 或使用生产配置模板
cp dev-team/devops/deploy/.env.production dev-team/backend-dev/stock-analysis-backend/.env
```

然后编辑 `.env`，替换占位符为实际值。

### 2.3 必须配置的变量

| 变量 | 说明 | 获取方式 |
|------|------|---------|
| `DEEPSEEK_API_KEY` | DeepSeek AI 密钥，用于智能分析 | [DeepSeek 开放平台](https://platform.deepseek.com/) |
| `JWT_SECRET` | JWT 签名密钥，用于用户认证 Token | `python -c "import secrets; print(secrets.token_hex(32))"` 生成 |
| `DEFAULT_ADMIN_PASSWORD` | 管理员密码 | 自行设置，**请勿使用默认弱密码** |

> **提示：** `JWT_SECRET` 不设置会导致 Token 签名不安全；`DEEPSEEK_API_KEY` 不设置仅影响 AI 功能。
> 启动时系统会自动检查这些配置并给出提示。

### 2.4 前端环境变量

### 2.3 前端环境变量

| 变量名 | 默认值 | 说明 |
|--------|-------|------|
| `VITE_API_BASE_URL` | `/api/v1` | API 基础路径（开发模式通过 Vite proxy） |
| `VITE_WS_URL` | `ws://localhost:8000/ws` | WebSocket 连接地址 |

> **注意**：开发模式下前端通过 Vite proxy 转发 `/api` 和 `/ws` 到后端 `localhost:8000`。  
> 生产部署（Nginx）时，Nginx 反向代理到 `backend:8000`。

---

## 三、端口说明

| 端口 | 服务 | 协议 | 说明 |
|------|------|------|------|
| **8080** | 前端 | HTTP | **前端展示端口**（原则⑦） |
| **8000** | 后端 API | HTTP/WebSocket | API + 文档 + WebSocket |
| 8000 | 后端 API 文档 | HTTP | Swagger UI: `/docs`，OpenAPI: `/openapi.json` |

**端口冲突处理：**

```powershell
# 查看端口占用
netstat -ano | findstr :8000
netstat -ano | findstr :8080

# 修改后端端口（编辑 .env）
BACKEND_PORT=8001

# 前端端口通过命令行指定
.\start-frontend.ps1 -Port 8081
```

---

## 四、健康检查

### 4.1 后端健康检查

```bash
# 基础健康检查
curl http://localhost:8000/api/v1/health

# 预期返回：
# {"status":"ok","service":"stock-analysis-system","version":"1.0.0"}
```

### 4.2 后端 API 文档

```bash
# Swagger UI
http://localhost:8000/docs

# OpenAPI JSON
http://localhost:8000/openapi.json
```

### 4.3 前端可访问性

```bash
# 主页
http://localhost:8080/

# 各模块页面
http://localhost:8080/          # 仪表盘
http://localhost:8080/market    # 实时行情
http://localhost:8080/warning   # 智能预警
http://localhost:8080/selection # 智能选股
http://localhost:8080/analysis  # 智能分析
http://localhost:8080/config    # 系统配置
```

---

## 五、Docker 部署

### 5.1 构建并启动

```powershell
# 从 dev-team/devops/ 目录执行
docker-compose -f docker-compose.yml up -d --build
```

### 5.2 查看状态

```bash
docker ps --filter "name=stock-"
docker stats stock-backend stock-frontend
```

### 5.3 查看日志

```bash
docker logs -f stock-backend --tail 50
docker logs -f stock-frontend --tail 50
```

### 5.4 停止

```bash
docker-compose -f docker-compose.yml down
```

### 5.5 单独构建镜像

```bash
# 构建后端镜像
docker build -f deploy/Dockerfile.backend -t stock-analysis-backend ../backend-dev/stock-analysis-backend

# 构建前端镜像
docker build -f deploy/Dockerfile.frontend -t stock-analysis-frontend ../frontend-dev/stock-analysis-frontend
```

---

## 六、目录结构

```
dev-team/devops/                          # ← 当前文档所在目录
├── start-backend.ps1                     # 后端启动脚本
├── start-frontend.ps1                    # 前端启动脚本
├── start-all.ps1                         # 一键启动脚本
├── docker-compose.yml                    # Docker 编排文件
├── MONITORING.md                         # 监控配置文档
├── README-DEPLOY.md                      # 本文档
├── deploy/
│   ├── .env.production                   # 生产环境配置模板
│   ├── Dockerfile.backend               # 后端 Dockerfile
│   ├── Dockerfile.frontend              # 前端 Dockerfile
│   └── nginx.conf                        # Nginx 配置
└── IDENTITY.md                           # 运维工程师角色标识
```

---

## 七、常见问题

### Q1: 后端启动报 "address already in use"

**原因：** 端口 8000 被占用。  
**解决：**
```powershell
# 查看占用进程
netstat -ano | findstr :8000
# 终止进程（确认PID后）
Stop-Process -Id <PID> -Force
```

### Q2: 前端页面打开后 API 请求 404

**原因：** Vite proxy 配置的 target 端口错误。  
**解决：** 确认 `vite.config.ts` 中 proxy target 为 `http://localhost:8000`（已修正）。

### Q3: 健康检查通过但页面数据为空

**原因：** 数据源未正确连接或监控池为空。  
**解决：**
1. 检查 `.env` 中 `TDX_DATA_DIR` 路径是否正确
2. 访问 `/config` 页面配置自选股和监控池
3. 查看后端日志 `logs/backend-*.log`

### Q4: WebSocket 无法连接

**原因：** 端口或代理配置问题。  
**解决：**
1. 开发模式：确认 Vite proxy 正确转发 `/ws` 到 `ws://localhost:8000`
2. Docker 模式：确认 Nginx 已配置 WebSocket 升级头
3. 手动测试：`curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" http://localhost:8000/ws`

### Q5: DeepSeek API 调用失败

**原因：** API Key 未配置或 Key 无效。  
**解决：**
1. 在 `.env` 中设置 `DEEPSEEK_API_KEY`
2. 确认 Key 从 [DeepSeek Platform](https://platform.deepseek.com/) 获取
3. 确认账户余额充足

### Q6: Docker 构建失败

**原因：** 路径引用问题。  
**解决：**
```bash
# docker-compose.yml 中 context 路径是相对于 docker-compose.yml 的位置
# 后端：../backend-dev/stock-analysis-backend
# 前端：../frontend-dev/stock-analysis-frontend

# 确认路径存在
ls ../backend-dev/stock-analysis-backend/Dockerfile
```

### Q7: SQLite 数据库损坏

**原因：** 意外断电或并发写入。  
**解决：**
```bash
# 备份旧数据库
cp data/cache/stock.db data/cache/stock.db.bak

# 删除数据库（系统会重新创建清空库）
rm data/cache/stock.db
```

### Q8: 前端页面白屏

**原因：** 路由刷新问题。  
**解决：** 确认 Nginx 配置中 `try_files $uri $uri/ /index.html;` 正确配置（已包含在 `deploy/nginx.conf` 中）。
