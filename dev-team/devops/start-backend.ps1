<#
.SYNOPSIS
    后端服务启动脚本 — 股票分析与投资决策系统
.DESCRIPTION
    安装Python依赖并启动FastAPI后端服务（Uvicorn）。
    端口从 .env 读取（默认8000）。
    包含日志重定向和健康检查等待。
.NOTES
    遵循原则②：配置从环境变量读取，不硬编码
    遵循原则⑤：文件放 dev-team/devops/
#>

param(
    [string]$ProjectRoot = (Resolve-Path "$PSScriptRoot\..\backend-dev\stock-analysis-backend"),
    [int]$Port = $null,
    [int]$HealthCheckTimeoutSeconds = 30
)

$ErrorActionPreference = "Stop"
$logDir = Join-Path $ProjectRoot "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$logFile = Join-Path $logDir "backend-$timestamp.log"
$pidFile = Join-Path $logDir "backend.pid"

Write-Host "╔══════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  股票分析系统 — 后端服务启动                  ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# 1. 检查Python环境
Write-Host "→ 检查Python环境..." -ForegroundColor Yellow
$python = Get-Command python3 -ErrorAction SilentlyContinue
if (-not $python) {
    $python = Get-Command python -ErrorAction SilentlyContinue
}
if (-not $python) {
    Write-Host "✗ 错误：未找到Python，请安装Python 3.10+" -ForegroundColor Red
    exit 1
}
Write-Host "  ✓ Python: $($python.Source)" -ForegroundColor Green
python --version 2>&1 | ForEach-Object { Write-Host "     $_" }

# 2. 检查 .env 文件
$envFile = Join-Path $ProjectRoot ".env"
if (-not (Test-Path $envFile)) {
    Write-Host "✗ 错误：未找到 .env 文件 ($envFile)" -ForegroundColor Red
    Write-Host "  提示：如有需要，从 dev-team/devops/deploy/.env.production 复制" -ForegroundColor Yellow
    exit 1
}
Write-Host "  ✓ .env 配置文件已找到" -ForegroundColor Green

# 3. 安装Python依赖
Write-Host "→ 安装Python依赖..." -ForegroundColor Yellow
Push-Location $ProjectRoot
try {
    pip install -r requirements.txt 2>&1 | ForEach-Object {
        if ($_ -match "^(ERROR|WARNING)") {
            Write-Host "  $_" -ForegroundColor Yellow
        }
    }
    Write-Host "  ✓ Python依赖安装完成" -ForegroundColor Green
} catch {
    Write-Host "✗ 依赖安装失败: $_" -ForegroundColor Red
    Pop-Location
    exit 1
}
Pop-Location

# 4. 创建必要的数据目录
$dataDirs = @(
    (Join-Path $ProjectRoot "data"),
    (Join-Path $ProjectRoot "data\cache"),
    (Join-Path $ProjectRoot "data\reports"),
    (Join-Path $ProjectRoot "data\templates")
)
foreach ($dir in $dataDirs) {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
}

# 5. 解析端口
$backendPort = $Port
if (-not $backendPort) {
    # 从 .env 读端口
    $envContent = Get-Content -Path $envFile -Raw
    if ($envContent -match 'BACKEND_PORT\s*=\s*(\d+)') {
        $backendPort = [int]$Matches[1]
    } else {
        $backendPort = 8000
    }
}
Write-Host "  ✓ 后端端口: $backendPort" -ForegroundColor Green

# 6. 检查端口占用
$portCheck = netstat -an 2>$null | Select-String ":$backendPort " | Select-String "LISTEN"
if ($portCheck) {
    Write-Host "✗ 错误：端口 $backendPort 已被占用" -ForegroundColor Red
    netstat -ano | Select-String ":$backendPort " | Select-String "LISTEN" | ForEach-Object {
        $parts = $_ -split '\s+'
        $pid = $parts[-1]
        $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
        Write-Host "  占用进程: $($proc.ProcessName) (PID: $pid)" -ForegroundColor Red
    }
    exit 1
}
Write-Host "  ✓ 端口 $backendPort 可用" -ForegroundColor Green

# 7. 启动Uvicorn后端
Write-Host "→ 启动后端服务 (端口 $backendPort)..." -ForegroundColor Yellow
Write-Host "  日志文件: $logFile" -ForegroundColor Gray

# 在后台启动uvicorn
$startCmd = @"
cd "$ProjectRoot"
`$env:LOG_LEVEL = "INFO"
uvicorn backend.main:app --host 0.0.0.0 --port $backendPort --log-level info
"@

# 使用Start-Process启动，重定向日志
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = "powershell"
$psi.Arguments = "-NoProfile -Command `"$startCmd`""
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$psi.UseShellExecute = $false
$psi.WorkingDirectory = $ProjectRoot
$proc = [System.Diagnostics.Process]::Start($psi)

# 保存PID
$proc.Id | Out-File -FilePath $pidFile -Encoding utf8
Write-Host "  ✓ 后端进程PID: $($proc.Id)" -ForegroundColor Green

# 8. 等待健康检查
Write-Host "→ 等待后端服务就绪 (超时: ${HealthCheckTimeoutSeconds}s)..." -ForegroundColor Yellow
$healthUrl = "http://localhost:$backendPort/api/v1/health"
$startTime = Get-Date
$ready = $false

while (((Get-Date) - $startTime).TotalSeconds -lt $HealthCheckTimeoutSeconds) {
    try {
        $response = Invoke-WebRequest -Uri $healthUrl -TimeoutSec 3 -ErrorAction SilentlyContinue
        $content = $response.Content | ConvertFrom-Json
        if ($content.status -eq "ok") {
            $ready = $true
            break
        }
    } catch {
        # 服务尚未就绪，继续等待
    }
    Start-Sleep -Milliseconds 500
    Write-Host "  ." -NoNewline -ForegroundColor Gray
}
Write-Host ""

if ($ready) {
    Write-Host "  ✓ 后端服务就绪!" -ForegroundColor Green
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  后端服务已启动" -ForegroundColor Cyan
    Write-Host "  API地址: http://localhost:$backendPort" -ForegroundColor White
    Write-Host "  健康检查: http://localhost:$backendPort/api/v1/health" -ForegroundColor White
    Write-Host "  API文档: http://localhost:$backendPort/docs" -ForegroundColor White
    Write-Host "  日志文件: $logFile" -ForegroundColor Gray
    Write-Host "═══════════════════════════════════════════════" -ForegroundColor Cyan
} else {
    Write-Host ""
    Write-Host "✗ 错误：后端服务启动超时，请检查日志" -ForegroundColor Red
    Write-Host "  日志文件: $logFile" -ForegroundColor Yellow
    exit 1
}
