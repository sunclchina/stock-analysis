<#
.SYNOPSIS
    股票分析与投资决策系统 - 生产构建脚本
.DESCRIPTION
    1. 构建前端静态文件 (npm run build)
    2. 将前端 dist 复制到后端 static 目录
    3. 后端生产模式启动脚本
.NOTES
    版本: 1.0.0
    用法: powershell -ExecutionPolicy Bypass .\deploy\build_prod.ps1
#>

$ErrorActionPreference = "Stop"
$ROOT_DIR = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$FRONTEND_DIR = "$ROOT_DIR\..\..\frontend-dev\stock-analysis-frontend"
$BACKEND_DIR = $ROOT_DIR
$STATIC_DIR = "$BACKEND_DIR\backend\static"
$VENV_DIR = "$BACKEND_DIR\.venv"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  股票分析与投资决策系统 生产构建" -ForegroundColor Cyan
Write-Host "  版本: 1.0.0" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ---- Step 1: 检查依赖 ----
Write-Host "[1/4] 检查依赖..." -ForegroundColor Yellow

if (-not (Test-Path "$FRONTEND_DIR\package.json")) {
    Write-Host "错误: 未找到前端项目 ($FRONTEND_DIR)" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path "$BACKEND_DIR\backend\main.py")) {
    Write-Host "错误: 未找到后端项目 ($BACKEND_DIR)" -ForegroundColor Red
    exit 1
}
Write-Host "  前端: $FRONTEND_DIR" -ForegroundColor Green
Write-Host "  后端: $BACKEND_DIR" -ForegroundColor Green

# ---- Step 2: 构建前端 ----
Write-Host ""
Write-Host "[2/4] 构建前端 (npm run build)..." -ForegroundColor Yellow
Set-Location $FRONTEND_DIR
npm install 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "错误: npm install 失败" -ForegroundColor Red
    exit 1
}
npm run build 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "错误: npm run build 失败" -ForegroundColor Red
    exit 1
}
Write-Host "  前端构建完成: $FRONTEND_DIR\dist" -ForegroundColor Green

# ---- Step 3: 复制静态文件到后端 ----
Write-Host ""
Write-Host "[3/4] 复制静态文件到后端..." -ForegroundColor Yellow

# 清理旧的 static 目录
if (Test-Path $STATIC_DIR) {
    Remove-Item -Recurse -Force "$STATIC_DIR\*" -ErrorAction SilentlyContinue
} else {
    New-Item -ItemType Directory -Force -Path $STATIC_DIR | Out-Null
}

# 复制 dist 内容
Copy-Item -Recurse -Force "$FRONTEND_DIR\dist\*" "$STATIC_DIR\"
Write-Host "  已复制到: $STATIC_DIR" -ForegroundColor Green

# ---- Step 4: 验证后端生产环境 ----
Write-Host ""
Write-Host "[4/4] 验证后端环境..." -ForegroundColor Yellow

# 检查虚拟环境
if (-not (Test-Path "$VENV_DIR\Scripts\python.exe")) {
    Write-Host "  创建 Python 虚拟环境..." -ForegroundColor Yellow
    python -m venv $VENV_DIR
}
Write-Host "  安装后端依赖..." -ForegroundColor Yellow
& "$VENV_DIR\Scripts\pip.exe" install -r "$BACKEND_DIR\requirements.txt" --quiet 2>&1 | Out-Null

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  ✅ 构建完成!" -ForegroundColor Cyan
Write-Host "  启动命令:" -ForegroundColor Cyan
Write-Host "  cd $BACKEND_DIR" -ForegroundColor White
Write-Host "  .\.venv\Scripts\python.exe -m backend.main --no-reload" -ForegroundColor White
Write-Host "  访问: http://localhost:8000" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan
