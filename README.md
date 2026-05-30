# 股票分析与投资决策系统

面向个人投资者的量化分析平台。单端口部署，后端托管前端静态文件，开箱即用。

涵盖实时行情、智能选股、技术分析、七维预警、资产组合管理与决策辅助。

---

## 目录

- [快速启动](#快速启动)
- [环境配置（部署前必读）](#环境配置部署前必读)
- [构建生产版本](#构建生产版本)
- [Docker 部署](#docker-部署)
- [界面导航](#界面导航)
- [目录结构](#目录结构)
- [常见问题](#常见问题)

---

## 快速启动

### 前提条件

| 组件 | 最低版本 |
|------|---------|
| Python | 3.10+ |

### 1. 创建配置文件

```powershell
# 从模板创建
cp .env.example .env
```

### 2. 安装依赖 & 启动

```powershell
pip install -r requirements.txt
python -m backend.main
```

访问 **http://localhost:8000**

---

## 环境配置（部署前必读）

### ⚠️ 必须配置的项

> **不配置就无法安全运行**的项，部署前务必完成设置：

| 优先级 | 配置项 | 说明 | 不配的后果 | 获取方式 |
|--------|--------|------|-----------|---------|
| 🔴 **必须** | `JWT_SECRET` | JWT 签名密钥 | Token 可被伪造，**安全风险** | `python -c "import secrets; print(secrets.token_hex(32))"` 生成 |
| 🟡 **推荐** | `DEEPSEEK_API_KEY` | DeepSeek AI 密钥 | AI 智能分析不可用，核心功能不受影响 | [DeepSeek 开放平台](https://platform.deepseek.com/) |
| 🟡 **推荐** | `DEFAULT_ADMIN_PASSWORD` | 管理员密码 | 默认弱密码 `admin123`，安全风险 | 自行设置 |

> - 编辑 `dev-team/backend-dev/stock-analysis-backend/.env` 文件完成配置
> - 编辑后重启服务生效

---

## 构建生产版本

### 方案一：直接运行（推荐）

后端已包含前端静态文件（`backend/static/`），一个命令启动：

```powershell
cd dev-team\backend-dev\stock-analysis-backend
python -m backend.main
```

访问 `http://localhost:8000`

### 方案二：Docker（推荐）

```bash
# 从仓库根目录构建
docker build -t stock-analysis -f Dockerfile .

# 运行容器（.env 通过挂载注入）
docker run -d --name stock-analysis \
  -p 8000:8000 \
  -v /path/to/your/.env:/app/.env \
  stock-analysis
```

### 方案三：重新构建前端 + 后端打包

如需修改前端代码后重新构建：

```powershell
# 构建前端
cd dev-team\frontend-dev\stock-analysis-frontend
npm install
npm run build

# 复制到后端静态目录
Copy-Item "dist\*" "..\..\backend-dev\stock-analysis-backend\backend\static\" -Recurse -Force

# 启动后端
cd ..\..\backend-dev\stock-analysis-backend
python -m backend.main
```

---

## Docker 部署

### 构建镜像

```bash
docker build -t stock-analysis:latest .
```

### 运行容器

```bash
docker run -d --name stock-analysis \
  -p 8000:8000 \
  -v /path/to/your/.env:/app/.env \
  -v stock-data:/app/data \
  stock-analysis:latest
```

> **注意：** Docker 镜像不包含 `.env` 文件，必须通过挂载卷注入配置。

---

## 界面导航

| 路径 | 模块 |
|------|------|
| `/` | 仪表盘 |
| `/market` | 实时行情 |
| `/warning` | 智能预警（七维预警 + 综合决策矩阵） |
| `/selection` | 智能选股 |
| `/analysis` | 智能分析 |
| `/config` | 系统配置 |

---

## 目录结构

```
stock-analysis/
├── .env.example                  # 配置模板（复制为 .env 后编辑）
├── Dockerfile                    # 多阶段构建（前端 + 后端）
├── requirements.txt              # Python 依赖
├── .gitignore
├── README.md                     # ← 唯一说明文档
│
├── dev-team/
│   ├── backend-dev/
│   │   └── stock-analysis-backend/
│   │       ├── backend/          # Python 源码（FastAPI）
│   │       │   ├── main.py       # 应用入口（含启动配置校验）
│   │       │   ├── api/          # API 路由
│   │       │   ├── config/       # 配置加载
│   │       │   ├── models/       # 数据模型
│   │       │   ├── services/     # 业务逻辑
│   │       │   ├── utils/        # 工具函数
│   │       │   └── static/       # 前端静态文件（生产构建产物）
│   │       ├── deploy/           # 部署脚本
│   │       └── .dockerignore
│   │
│   ├── frontend-dev/
│   │   └── stock-analysis-frontend/   # 前端源码（Vue/React）
│   │       ├── src/
│   │       └── package.json
│   │
│   └── devops/                   # 运维脚本
│       ├── start-all.ps1
│       ├── start-backend.ps1
│       ├── start-frontend.ps1
│       ├── docker-compose.yml
│       └── deploy/
│           ├── nginx.conf
│           └── .env.production
```

---

## 常见问题

### Q: 启动后提示 JWT_SECRET 未设置

编辑 `.env`，用以下命令生成密钥：
```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

### Q: AI 分析功能不可用

`DEEPSEEK_API_KEY` 未配置，不影响行情/预警/选股等核心功能。
如需启用，在 `.env` 中设置有效的 API Key。

### Q: 数据源连接失败

检查 `.env` 中 `PRIMARY_DATA_SOURCE` 和 `FALLBACK_DATA_SOURCE` 配置。

---

**版本：** 1.0.0
