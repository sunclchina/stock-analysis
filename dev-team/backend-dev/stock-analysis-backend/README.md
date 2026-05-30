# 股票分析与投资决策系统

个人股票分析与投资决策系统后端，基于 FastAPI 构建。

> **推荐直接使用一键启动脚本：** `..\..\devops\start-all.ps1`

---

## 目录

- [快速开始](#快速开始)
- [环境配置（部署前必读）](#环境配置部署前必读)
- [启动服务](#启动服务)
- [Docker 部署](#docker-部署)
- [API 文档](#api-文档)
- [目录结构](#目录结构)
- [常见问题](#常见问题)

---

## 快速开始

### 前提条件

| 组件 | 最低版本 |
|------|---------|
| Python | 3.10+ |
| Node.js | 18+（构建前端时需要） |

### 一键启动

```powershell
# 从 dev-team/devops/ 目录执行
.\start-all.ps1
```

### 分别启动

```powershell
# 终端 1：启动后端
cd dev-team\backend-dev\stock-analysis-backend
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python.exe -m backend.main

# 终端 2：启动前端（开发模式）
cd dev-team\frontend-dev\stock-analysis-frontend
npm install
npm run dev
```

---

## 环境配置（部署前必读）

### 1. 创建配置文件

```powershell
# 从模板创建 .env（已有 .env 则跳过）
cd dev-team\backend-dev\stock-analysis-backend
cp .env.example .env
```

### 2. ⚠️ 必须配置的项

> **不配置就无法安全运行**的项，部署前务必完成设置：

| 优先级 | 配置项 | 说明 | 不配的后果 | 获取方式 |
|--------|--------|------|-----------|---------|
| 🔴 **必须** | `JWT_SECRET` | JWT 签名密钥 | Token 可被伪造，**安全风险** | `python -c "import secrets; print(secrets.token_hex(32))"` 生成 |
| 🟡 **推荐** | `DEEPSEEK_API_KEY` | DeepSeek AI 密钥 | AI 智能分析不可用，核心功能不受影响 | [DeepSeek 开放平台](https://platform.deepseek.com/) |
| 🟡 **推荐** | `DEFAULT_ADMIN_PASSWORD` | 管理员密码 | 默认弱密码 `admin123`，安全风险 | 自行设置 |

```
# 快速配置示例
JWT_SECRET="$(python -c 'import secrets; print(secrets.token_hex(32))')"
DEEPSEEK_API_KEY=sk-你的实际密钥
```

### 3. 配置验证

启动时系统会自动检查配置完整性：
- JWT_SECRET 缺失 → 打印警告
- DEEPSEEK_API_KEY 为空 → 打印提示
- 默认密码未修改 → 建议修改

### 4. 安全说明

- `.env` 文件已被 `.gitignore` 排除，不会提交到代码仓库
- 所有 API Key、密码、密钥仅存在于本地 `.env` 文件中
- Docker 构建时 `.env` 不会被打包到镜像中（见 `.dockerignore`）
- 生产部署时通过挂载外部卷注入配置

---

## 启动服务

### 开发模式

```powershell
cd dev-team\backend-dev\stock-analysis-backend
.\.venv\Scripts\python.exe -m backend.main
```

### 生产模式

```powershell
# 先构建前端静态文件
cd dev-team\devops
.\deploy\build_prod.ps1

# 启动后端（默认 8000 端口）
cd dev-team\backend-dev\stock-analysis-backend
.\deploy\start_prod.ps1
```

访问 `http://localhost:8000` 查看系统。

---

## Docker 部署

### 构建镜像

```bash
cd dev-team/devops
docker-compose -f docker-compose.yml up -d --build
```

### 使用挂载卷注入配置

```bash
docker run -d --name stock-analysis \
  -p 8000:8000 \
  -v /path/to/your/.env:/app/.env \
  stock-analysis:latest
```

> **注意：** Docker 镜像不包含 `.env` 文件，必须通过挂载卷注入配置。

---

## API 文档

| 地址 | 说明 |
|------|------|
| `http://localhost:8000/docs` | Swagger UI |
| `http://localhost:8000/openapi.json` | OpenAPI JSON |

---

## 目录结构

```
stock-analysis-backend/
├── backend/              # 后端 Python 源码
│   ├── main.py          # FastAPI 应用入口（含启动配置校验）
│   ├── api/             # API 路由
│   ├── config/          # 配置（settings.py 从 .env 加载）
│   ├── models/          # 数据模型
│   ├── services/        # 业务服务层
│   ├── utils/           # 工具函数
│   └── static/          # 前端静态文件（构建后生成）
├── deploy/              # 部署脚本
│   ├── build_prod.ps1   # 生产构建脚本
│   └── start_prod.ps1   # 生产启动脚本（含配置预检）
├── data/                # 运行时数据
├── tests/               # 测试用例
├── .env                 # 本地配置（已 gitignore）
├── .env.example         # 配置模板
├── .gitignore           # Git 忽略规则
├── .dockerignore        # Docker 构建忽略规则
├── Dockerfile           # Docker 构建文件
├── requirements.txt     # Python 依赖
└── README.md            # 本文件
```

---

## 常见问题

### Q: 启动后提示 JWT_SECRET 未设置

**原因：** JWT 签名密钥未配置，Token 签名不安全。

**解决：** 编辑 `.env`，设置 `JWT_SECRET`：
```powershell
python -c "import secrets; print(secrets.token_hex(32))"
# 输出复制到 .env 的 JWT_SECRET= 后面
```

### Q: AI 分析功能不可用

**原因：** `DEEPSEEK_API_KEY` 未配置。

**解决：** 在 `.env` 中设置有效的 DeepSeek API Key。

### Q: 数据源连接失败

**原因：** 数据源配置或网络问题。

**解决：** 检查 `.env` 中 `PRIMARY_DATA_SOURCE` 和 `FALLBACK_DATA_SOURCE` 配置。

---

**版本：** 1.0.0 — [文档首页](../../devops/README-DEPLOY.md)
