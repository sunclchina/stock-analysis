# 股票分析与投资决策系统 - Windows 部署指南

## 环境要求

| 组件 | 最低版本 | 推荐版本 |
|------|---------|---------|
| Windows | 10 / Server 2019 | 11 / Server 2022 |
| Python | 3.10 | 3.12 |
| Node.js | 18 LTS | 20 LTS |
| 内存 | 4 GB | 8 GB |
| 磁盘 | 500 MB | 2 GB |

## 部署步骤

### 1. 安装依赖

```powershell
# 安装 Python（如未安装）
winget install Python.Python.3.12

# 安装 Node.js（如未安装）
winget install OpenJS.NodeJS.LTS
```

### 2. 初始化后端环境

```powershell
cd dev-team\backend-dev\stock-analysis-backend

# 创建虚拟环境（首次部署）
python -m venv .venv

# 激活虚拟环境
.\.venv\Scripts\Activate.ps1

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置生产环境变量

```powershell
# 复制生产配置
copy .env.production .env

# 编辑 .env 文件，修改以下配置：
# - DEFAULT_ADMIN_PASSWORD=设置一个强密码
# - 如使用通达信本地数据，设置 TDX_DATA_DIR
```

### 4. 构建前端

```powershell
# 构建前端并复制到后端 static 目录
.\deploy\build_prod.ps1
```

### 5. 启动服务

```powershell
# 前台运行（按 Ctrl+C 停止）
.\deploy\start_prod.ps1

# 或直接运行
.\.venv\Scripts\python.exe -m backend.main

# 或后台运行（推荐用于生产）
Start-Process -NoNewWindow -FilePath ".\.venv\Scripts\python.exe" -ArgumentList "-m backend.main"
```

### 6. 访问系统

打开浏览器访问：**http://localhost:8000**

默认管理员账号：
- 用户名：`admin`
- 密码：（见 .env 中设置的密码）

### 7. 注册为 Windows 服务（可选）

使用 NSSM 注册为 Windows 服务：

```powershell
# 下载 NSSM: https://nssm.cc/download
# 注册服务
nssm install StockAnalysis "C:\path\to\.venv\Scripts\python.exe" "-m backend.main"
nssm set StockAnalysis AppDirectory "C:\path\to\stock-analysis-backend"
nssm set StockAnalysis Start SERVICE_AUTO_START
nssm start StockAnalysis
```

### 8. 配置防火墙（可选）

如需远程访问，开放 8000 端口：

```powershell
New-NetFirewallRule -DisplayName "StockAnalysis" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
```

## 目录结构

```
stock-analysis-backend/
├── backend/           # 后端代码
│   ├── main.py
│   ├── static/        # 前端静态文件（由 build_prod.ps1 生成）
│   ├── api/           # API 路由
│   ├── config/        # 配置
│   ├── models/        # 数据模型
│   ├── services/      # 业务逻辑
│   └── utils/         # 工具
├── data/              # 数据目录
│   ├── cache/         # SQLite 数据库
│   └── reports/       # 分析报告
├── logs/              # 日志
├── deploy/            # 部署脚本
└── .env               # 环境配置
```

## 常见问题

### 端口被占用

```powershell
# 查找占用端口的进程
netstat -ano | findstr ":8000"
# 修改 .env 中的 BACKEND_PORT
```

### 数据库损坏

删除 `data/cache/stock.db` 后重启（会重新创建并初始化默认用户）。

### 前端页面空白

确保已执行 `.\deploy\build_prod.ps1`，并且 `backend/static/index.html` 存在。
