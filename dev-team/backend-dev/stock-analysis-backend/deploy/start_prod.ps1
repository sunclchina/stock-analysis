<#
.SYNOPSIS
    股票分析与投资决策系统 - 生产启动脚本
.DESCRIPTION
    以生产模式启动后端服务（无热重载，加载前端静态文件）
    前提：已执行 deploy\build_prod.ps1 完成前端构建
.NOTES
    版本: 1.0.0
    用法: powershell -ExecutionPolicy Bypass .\deploy\start_prod.ps1
#>

$ErrorActionPreference = "Stop"
$BACKEND_DIR = Split-Path -Parent (Split-Path -Parent $PSCommandPath)

# 切换到生产配置
if (Test-Path "$BACKEND_DIR\.env.production") {
    Copy-Item "$BACKEND_DIR\.env.production" "$BACKEND_DIR\.env" -Force
    Write-Host "已加载生产环境配置" -ForegroundColor Green
}

# ---- 部署前配置检查 ----
Write-Host ""
Write-Host "[检查] 验证配置完整性..." -ForegroundColor Yellow

$envFile = "$BACKEND_DIR\.env"
if (-not (Test-Path $envFile)) {
    Write-Host "错误: 未找到 .env 配置文件！" -ForegroundColor Red
    Write-Host "请先执行: cp .env.example .env" -ForegroundColor Cyan
    Write-Host "然后编辑 .env 填入必要配置项。" -ForegroundColor Cyan
    exit 1
}

# 读取 .env 并检查关键配置
$envContent = Get-Content $envFile -Raw

if ($envContent -match 'DEEPSEEK_API_KEY=your_deepseek_api_key_here') {
    Write-Host "  ⚠️  DEEPSEEK_API_KEY 未配置（AI分析功能不可用）" -ForegroundColor Yellow
}

if ($envContent -match 'JWT_SECRET=your_jwt_secret_here') {
    Write-Host "  ⚠️  JWT_SECRET 未配置（Token签名不安全！）" -ForegroundColor Yellow
    Write-Host "  建议生成随机密钥: python -c "import secrets; print(secrets.token_hex(32))"" -ForegroundColor Gray
}

if ($envContent -match 'DEFAULT_ADMIN_PASSWORD=admin123') {
    Write-Host "  ⚠️  默认管理员密码为弱密码（admin123）" -ForegroundColor Yellow
}

Write-Host "  ✅ 配置检查完成" -ForegroundColor Green

# 验证静态文件
$STATIC_DIR = "$BACKEND_DIR\backend\static"
if (-not (Test-Path "$STATIC_DIR\index.html")) {
    Write-Host "警告: 未找到前端静态文件！" -ForegroundColor Yellow
    Write-Host "请先运行: deploy\build_prod.ps1" -ForegroundColor Cyan
    exit 1
}

$VENV_DIR = "$BACKEND_DIR\.venv"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  股票分析与投资决策系统 v1.0.0" -ForegroundColor Cyan
Write-Host "  生产模式启动中..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 确保日志目录存在
New-Item -ItemType Directory -Force -Path "$BACKEND_DIR\logs" | Out-Null
New-Item -ItemType Directory -Force -Path "$BACKEND_DIR\data\cache" | Out-Null
New-Item -ItemType Directory -Force -Path "$BACKEND_DIR\data\reports" | Out-Null

Set-Location $BACKEND_DIR

# 启动后端（前台运行，按 Ctrl+C 停止）
Write-Host "启动后端服务: http://0.0.0.0:8000" -ForegroundColor Green
Write-Host "访问: http://localhost:8000" -ForegroundColor White
Write-Host "按 Ctrl+C 停止服务" -ForegroundColor Yellow
Write-Host ""

& "$VENV_DIR\Scripts\python.exe" -m backend.main
