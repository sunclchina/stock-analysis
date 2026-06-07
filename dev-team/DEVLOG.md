
## 2026-06-05 13:58:14 — 开发环境启动

**操作人：** 青崖（开发总监）

**操作：** 开启开发环境（前后端）

**状态：**
| 服务 | 端口 | PID | 状态 |
|------|------|-----|------|
| 后端 (FastAPI) | 8000 | 11224 | ✅ 运行中 |
| 前端 (Vite) | 8080 | — | ✅ 运行中 |

**健康检查：** 后端 /api/v1/health → 200 OK

## 2026-06-07 10:07 — HTTPS/SSL 证书配置功能

**操作人：** 青崖（开发总监）

**需求：** 在系统设置中增加 HTTPS 证书配置功能

**修改文件：**

| 文件 | 操作 |
|------|------|
| `backend/config/settings.py` | 新增 `ssl_enabled`, `ssl_cert_file`, `ssl_key_file` 字段 |
| `backend/main.py` | `__main__` 启动时检测 SSL 配置，传给 uvicorn |
| `backend/api/config_api.py` | GET /config 返回 SSL 配置；新增 GET/PUT /config/ssl 读写 .env |
| `frontend/src/types/index.ts` | 新增 `SslConfig` 接口，`SystemSettings` 加 SSL 字段 |
| `frontend/src/services/configApi.ts` | 新增 `fetchSslConfig`, `saveSslConfig` API 调用 |
| `frontend/src/pages/Config/SettingsTab.tsx` | 新增 HTTPS/SSL 证书配置卡片组件 |
| `.env` / `.env.example` | 新增 SSL 配置注释模板 |

**使用方式：**
1. 打开系统设置 → 系统状态下方可见 HTTPS/SSL 证书配置卡片
2. 填入证书文件路径，开启 HTTPS，保存
3. 重启后端服务生效

## 2026-06-07 10:41 — Docker compose 调整

**改动：**
- `env_file` 从 `D:/docker/stock-analysis/.env.vars` 改为指向本地 `./.env`
  - 前端保存 SSL 配置后重启容器即可生效，不需要手动维护两份 .env
- 新增 `certs` 卷挂载 `D:/docker/stock-analysis/certs:/app/certs:ro`
- 端口映射改为 `8081:8000`（与 ddns-go 域名一致）

