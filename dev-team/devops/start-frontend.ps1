<#
.SYNOPSIS
    前端服务启动脚本 — 股票分析与投资决策系统
.DESCRIPTION
    安装npm依赖并启动Vite开发服务器（端口8080）。
    包含等待服务就绪逻辑。
.NOTES
    遵循原则⑤：文件放 dev-team/devops/
    遵循原则⑦：前端端口8080
#>

param(
    [string]$ProjectRoot = (Resolve-Path "$PSScriptRoot\..\frontend-dev\stock-analysis-frontend"),
    [int]$Port = 8080,
    [int]$HealthCheckTimeoutSeconds = 30
)

$ErrorActionPreference = "Stop"
$logDir = Join-Path $ProjectRoot "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$logFile = Join-Path $logDir "frontend-$timestamp.log"
$pidFile = Join-Path $logDir "frontend.pid"

Write-Host "╔══════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  股票分析系统 — 前端服务启动                  ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# 1. 检查Node.js环境
Write-Host "→ 检查Node.js环境..." -ForegroundColor Yellow
$node = Get-Command node -ErrorAction SilentlyContinue
if (-not $node) {
    Write-Host "✗ 错误：未找到Node.js，请安装Node.js 18+" -ForegroundColor Red
    exit 1
}
Write-Host "  ✓ Node.js: $($node.Source)" -ForegroundColor Green
node --version 2>&1 | ForEach-Object { Write-Host "     $_" }

$npm = Get-Command npm -ErrorAction SilentlyContinue
if (-not $npm) {
    Write-Host "✗ 错误：未找到npm" -ForegroundColor Red
    exit 1
}
npm --version 2>&1 | ForEach-Object { Write-Host "     npm $_" }

# 2. 检查端口占用（原则⑦：端口8080）
Write-Host "→ 检查端口 ${Port}..." -ForegroundColor Yellow
$portCheck = netstat -an 2>$null | Select-String ":$Port " | Select-String "LISTEN"
if ($portCheck) {
    Write-Host "✗ 错误：端口 $Port 已被占用" -ForegroundColor Red
    netstat -ano | Select-String ":$Port " | Select-String "LISTEN" | ForEach-Object {
        $parts = $_ -split '\s+'
        $pid = $parts[-1]
        $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
        Write-Host "  占用进程: $($proc.ProcessName) (PID: $pid)" -ForegroundColor Red
    }
    exit 1
}
Write-Host "  ✓ 端口 $Port 可用" -ForegroundColor Green

# 3. 安装npm依赖
Push-Location $ProjectRoot
try {
    # 检查 node_modules 是否存在
    if (-not (Test-Path "node_modules\.package-lock.json")) {
        Write-Host "→ 安装npm依赖..." -ForegroundColor Yellow
        npm install 2>&1 | ForEach-Object {
            if ($_ -match "^(ERR|WARN)") {
                Write-Host "  $_" -ForegroundColor Yellow
            }
        }
        Write-Host "  ✓ npm依赖安装完成" -ForegroundColor Green
    } else {
        Write-Host "  ✓ node_modules 已存在，跳过安装" -ForegroundColor Green
    }
} catch {
    Write-Host "✗ npm安装失败: $_" -ForegroundColor Red
    Pop-Location
    exit 1
}

# 4. 启动Vite开发服务器
Write-Host "→ 启动前端服务 (端口 ${Port})..." -ForegroundColor Yellow
Write-Host "  日志文件: $logFile" -ForegroundColor Gray

# 启动Vite开发服务器
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = "npx"
$psi.Arguments = "vite --port $Port --host"
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$psi.UseShellExecute = $false
$psi.WorkingDirectory = $ProjectRoot

$proc = [System.Diagnostics.Process]::Start($psi)

# 保存PID
$proc.Id | Out-File -FilePath $pidFile -Encoding utf8
Pop-Location
Write-Host "  ✓ 前端进程PID: $($proc.Id)" -ForegroundColor Green

# 5. 等待服务就绪
Write-Host "→ 等待前端服务就绪 (超时: ${HealthCheckTimeoutSeconds}s)..." -ForegroundColor Yellow
$startTime = Get-Date
$ready = $false

while (((Get-Date) - $startTime).TotalSeconds -lt $HealthCheckTimeoutSeconds) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$Port/" -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            $ready = $true
            break
        }
    } catch {
        # 服务尚未就绪
    }
    Start-Sleep -Milliseconds 500
    Write-Host "  ." -NoNewline -ForegroundColor Gray
}
Write-Host ""

if ($ready) {
    Write-Host "  ✓ 前端服务就绪!" -ForegroundColor Green
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  前端服务已启动" -ForegroundColor Cyan
    Write-Host "  访问地址: http://localhost:$Port" -ForegroundColor White
    Write-Host "  日志文件: $logFile" -ForegroundColor Gray
    Write-Host "═══════════════════════════════════════════════" -ForegroundColor Cyan
} else {
    Write-Host ""
    Write-Host "✗ 错误：前端服务启动超时，请检查日志" -ForegroundColor Red
    Write-Host "  日志文件: $logFile" -ForegroundColor Yellow
    exit 1
}
