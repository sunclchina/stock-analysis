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
