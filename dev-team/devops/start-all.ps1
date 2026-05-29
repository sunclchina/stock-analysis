<#
.SYNOPSIS
    一键启动脚本 — 股票分析与投资决策系统
.DESCRIPTION
    按顺序启动后端→前端，检查端口占用，输出访问地址。
    支持 "--build" 参数先构建前端。
.NOTES
    遵循原则②：配置从 .env 读取
    遵循原则⑦：前端端口8080
#>

param(
    [switch]$Build = $false,
    [switch]$NoWait = $false
)

$ErrorActionPreference = "Stop"
$scriptPath = $PSScriptRoot

Write-Host @"

╔═══════════════════════════════════════════════════════╗
║     股票分析与投资决策系统 — 一键启动                   ║
║                                                       ║
║  前端：http://localhost:8080                           ║
║  后端：http://localhost:8000                           ║
║  后端文档：http://localhost:8000/docs                   ║
╚═══════════════════════════════════════════════════════╝

"@ -ForegroundColor Cyan

# 1. 检查端口占用
Write-Host "→ 检查端口占用..." -ForegroundColor Yellow
$ports = @(8000, 8080)
$occupied = @()
foreach ($port in $ports) {
    $check = netstat -an 2>$null | Select-String ":$port " | Select-String "LISTEN"
    if ($check) {
        $occupied += $port
    }
}
if ($occupied.Count -gt 0) {
    Write-Host "✗ 以下端口被占用: $($occupied -join ', ')" -ForegroundColor Red
    foreach ($port in $occupied) {
        netstat -ano | Select-String ":$port " | Select-String "LISTEN" | ForEach-Object {
            $parts = $_ -split '\s+'
            $pid = $parts[-1]
            $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
            Write-Host "  端口 $port : $($proc.ProcessName) (PID: $pid)" -ForegroundColor Red
        }
    }
    Write-Host "  请关闭占用进程后重试，或用 'netstat -ano | findstr :$port' 查看" -ForegroundColor Yellow
    exit 1
}
Write-Host "  ✓ 端口 8000, 8080 均可用" -ForegroundColor Green

# 2. 关闭之前可能残留的进程
$prevPidDir = Join-Path (Resolve-Path "$scriptPath\..\backend-dev\stock-analysis-backend") "logs"
$prevFrontPidDir = Join-Path (Resolve-Path "$scriptPath\..\frontend-dev\stock-analysis-frontend") "logs"

$pidFiles = @(
    (Join-Path $prevPidDir "backend.pid"),
    (Join-Path $prevFrontPidDir "frontend.pid")
)

foreach ($pf in $pidFiles) {
    if (Test-Path $pf) {
        $oldPid = Get-Content $pf -Raw -ErrorAction SilentlyContinue
        if ($oldPid) {
            $oldPid = $oldPid.Trim()
            $oldProc = Get-Process -Id $oldPid -ErrorAction SilentlyContinue
            if ($oldProc) {
                Write-Host "  → 关闭残留进程: $($oldProc.ProcessName) (PID: $oldPid)" -ForegroundColor Yellow
                Stop-Process -Id $oldPid -Force -ErrorAction SilentlyContinue
            }
        }
    }
}

# 3. 可选：构建前端
if ($Build) {
    Write-Host "→ 构建前端..." -ForegroundColor Yellow
    Push-Location "$scriptPath\..\frontend-dev\stock-analysis-frontend"
    try {
        npm run build 2>&1 | ForEach-Object { Write-Host "  $_" }
        Write-Host "  ✓ 前端构建完成" -ForegroundColor Green
    } catch {
        Write-Host "✗ 前端构建失败: $_" -ForegroundColor Red
    }
    Pop-Location
}

# 4. 启动后端
Write-Host ""
Write-Host "────────────────── 启动后端服务 ──────────────────" -ForegroundColor Cyan
$backendJob = Start-Job -ScriptBlock {
    param($ScriptPath)
    & (Join-Path $ScriptPath "start-backend.ps1")
} -ArgumentList $scriptPath

# 5. 等待后端就绪
Write-Host "→ 等待后端就绪..." -ForegroundColor Yellow
$backendReady = $false
$backendTimeout = 45
$elapsed = 0
$backProj = Resolve-Path "$scriptPath\..\backend-dev\stock-analysis-backend"

while ($elapsed -lt $backendTimeout) {
    $jobState = $backendJob | Receive-Job -ErrorAction SilentlyContinue
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/health" -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($r.StatusCode -eq 200) {
            $backendReady = $true
            break
        }
    } catch {}
    Start-Sleep -Seconds 1
    $elapsed++
    Write-Host "  ." -NoNewline -ForegroundColor Gray
}
Write-Host ""

if (-not $backendReady) {
    Write-Host "✗ 后端启动超时，请手动检查日志" -ForegroundColor Red
    # 仍然尝试启动前端
}

# 6. 启动前端
Write-Host ""
Write-Host "────────────────── 启动前端服务 ──────────────────" -ForegroundColor Cyan
& "$scriptPath\start-frontend.ps1"

# 7. 输出最终访问信息
Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                   系统已成功启动！                      ║" -ForegroundColor Cyan
Write-Host "╠═══════════════════════════════════════════════════════╣" -ForegroundColor Cyan
Write-Host "║                                                       ║" -ForegroundColor Cyan
Write-Host "║  前端界面:  http://localhost:8080                      ║" -ForegroundColor White
Write-Host "║  后端API:   http://localhost:8000                      ║" -ForegroundColor White
Write-Host "║  API文档:   http://localhost:8000/docs                 ║" -ForegroundColor White
Write-Host "║  健康检查:  http://localhost:8000/api/v1/health       ║" -ForegroundColor White
Write-Host "║                                                       ║" -ForegroundColor Cyan
Write-Host "║  停止方式:  Stop-Process -Id (Get-Content logs/backend.pid) ║" -ForegroundColor Gray
Write-Host "║             Stop-Process -Id (Get-Content logs/frontend.pid) ║" -ForegroundColor Gray
Write-Host "╚═══════════════════════════════════════════════════════╝" -ForegroundColor Cyan
