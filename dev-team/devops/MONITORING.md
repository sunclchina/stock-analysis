# 监控配置建议 — 股票分析与投资决策系统

> 本文档列出系统需要监控的关键指标、健康检查 URL 以及推荐的监控工具。

---

## 一、健康检查 URL

### 1.1 后端服务

| 端点 | 说明 | 预期响应 |
|------|------|---------|
| `http://localhost:8000/api/v1/health` | 基础健康检查 | `{"status":"ok","service":"stock-analysis-system","version":"1.0.0"}` |
| `http://localhost:8000/docs` | OpenAPI 文档可访问性 | 返回 Swagger UI 页面（200） |
| `http://localhost:8000/openapi.json` | API 规范可访问性 | 返回 OpenAPI JSON（200） |

### 1.2 前端服务

| 端点 | 说明 | 预期响应 |
|------|------|---------|
| `http://localhost:8080/` | 前端主页可访问性 | 返回 HTML（200） |

---

## 二、关键指标

### 2.1 基础设施指标

| 指标 | 告警阈值 | 说明 |
|------|---------|------|
| **CPU 使用率** | > 80% 持续 5 分钟 | 后端服务 CPU 负载 |
| **内存使用率** | > 80% | 后端进程内存占用 |
| **磁盘使用率** | > 85% | 数据目录（SQLite/报告/缓存） |
| **磁盘 I/O** | > 50 MB/s 持续 10 分钟 | 数据源读取/缓存写入 |

### 2.2 后端服务指标

| 指标 | 告警阈值 | 说明 |
|------|---------|------|
| **API 响应时间（P95）** | > 2000ms | 正常应在 500ms 内 |
| **API 错误率** | > 5% | 5xx 错误比例 |
| **WebSocket 连接数** | > 100 | 正常：1~5 个连接 |
| **预警引擎计算耗时** | > 5000ms | 单次全量计算 |
| **数据源请求失败率** | > 10% | 通达信/网络数据源 |
| **DeepSeek API 调用失败率** | > 20% | AI 分析接口 |

### 2.3 业务指标

| 指标 | 说明 | 检查频率 |
|------|------|---------|
| **监控池股票数量** | 预警引擎监控的股票总数 | 每日 |
| **活跃预警数量** | 当前触发的预警数 | 实时 |
| **选股结果数量** | 智能选股输出结果数 | 每次运行 |
| **分析报告生成数** | 今日生成的报告数 | 每日 |
| **行情刷新延迟** | 上次刷新时间距当前 | 实时（应 < 10s） |

### 2.4 数据库指标

| 指标 | 告警阈值 | 说明 |
|------|---------|------|
| SQLite 数据库大小 | > 500MB | 数据缓存文件 |
| 日志文件大小 | > 100MB | 单日日志 |
| 报告存储数量 | > 1000 个 | ./data/reports/ 目录 |

---

## 三、推荐监控方案

### 3.1 极简方案（个人使用）

```powershell
# 定期健康检查脚本（PowerShell）
while ($true) {
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/health" -TimeoutSec 5
        Write-Host "$(Get-Date -Format 'HH:mm:ss') ✓ 后端健康"
    } catch {
        Write-Host "$(Get-Date -Format 'HH:mm:ss') ✗ 后端异常: $_" -ForegroundColor Red
    }
    Start-Sleep -Seconds 30
}
```

### 3.2 专业方案

| 工具 | 用途 | 配置方式 |
|------|------|---------|
| **Prometheus + Grafana** | 指标采集与可视化 | 后端暴露 /metrics 端点后对接 |
| **uptime-kuma** | 简易健康监控 | 配置 HTTP 监控检查 |
| **Watchtower** | Docker 自动更新 | Docker 模式自动拉取新镜像 |
| **Loki + Promtail** | 日志集中管理 | 采集 `logs/*.log` 文件 |

### 3.3 Docker 监控

```bash
# 查看容器状态
docker ps --filter "name=stock-"

# 查看容器资源占用
docker stats stock-backend stock-frontend

# 查看日志
docker logs -f stock-backend --tail 100
docker logs -f stock-frontend --tail 100
```

---

## 四、日志管理

### 4.1 日志位置

| 组件 | 日志路径 |
|------|---------|
| 后端运行时 | `dev-team/backend-dev/stock-analysis-backend/logs/backend-*.log` |
| 后端容器 | `docker logs stock-backend` |
| 前端运行时 | `dev-team/frontend-dev/stock-analysis-frontend/logs/frontend-*.log` |
| 前端容器 | `docker logs stock-frontend` |

### 4.2 日志轮转建议

```powershell
# 每周清理超过7天的日志
Get-ChildItem -Path "logs/*.log" | Where-Object {
    $_.LastWriteTime -lt (Get-Date).AddDays(-7)
} | Remove-Item -Force
```

---

## 五、告警规则

### 5.1 需要立即处理的告警

1. 后端服务无法启动或频繁重启
2. 数据源连续 3 次以上请求失败
3. 预警引擎计算超时（> 10s）
4. 磁盘空间不足（< 1GB 可用空间）
5. DeepSeek API 连续调用失败

### 5.2 可延后处理

1. 单次 API 请求超时
2. 偶发 WebSocket 断开重连
3. 监控池中个别股票数据缺失
4. 前端构建版本滞后

---

## 六、监控检查清单

- [ ] 后端 Health API 返回 200
- [ ] 前端页面可正常访问
- [ ] WebSocket 连接正常
- [ ] 数据源状态正常（通达信/网络）
- [ ] 预警引擎启动正常
- [ ] SQLite 数据库可读写
- [ ] 磁盘空间充足（> 5GB）
- [ ] 报告目录可写入
- [ ] DeepSeek API Key 有效
