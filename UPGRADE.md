# 升级指南

## 版本迭代流程

### 1. 代码更新

```bash
# 拉取最新代码
git pull origin main

# 查看版本变更
git log --oneline --no-merges HEAD...@{1}
```

### 2. 后端依赖更新

```bash
cd dev-team/backend-dev/stock-analysis-backend
.\.venv\Scripts\pip.exe install -r requirements.txt --upgrade
```

### 3. 前端依赖更新

```bash
cd dev-team/frontend-dev/stock-analysis-frontend
npm install
```

### 4. 数据库迁移

默认使用 SQLite，升级版本会自动创建缺少的字段（SQLAlchemy ORM）。
如需迁移到 MySQL：

```sql
-- 使用 Alembic 或在目标数据库手动建表
-- 表结构见 backend/models/ 下各模块
```

### 5. 重新构建

**Windows 部署：**
```powershell
.\deploy\build_prod.ps1
.\deploy\start_prod.ps1
```

**Docker 部署：**
```bash
docker compose build --no-cache stock-analysis
docker compose up -d
```

### 6. 版本号更新

1. 修改 `VERSION` 文件
2. 修改 `frontend/package.json` 中的 `version` 字段
3. 修改 `backend/main.py` 中 `FastAPI(version="...")` 
4. 更新 `CHANGELOG.md`

## 回滚

```bash
git revert HEAD  # 或回退到特定版本
# Windows: 重新构建部署
# Docker: docker compose up -d (使用上一个镜像)
```
