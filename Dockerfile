# ==========================================
# 股票分析与投资决策系统 - Docker 多阶段构建
# ==========================================

# ---- Stage 1: 构建前端（本地构建）----
# 使用本地已构建的 dist，避免 Docker 构建缓存不一致

# ---- Stage 2: 运行后端 ----
FROM docker.m.daocloud.io/python:3.11-slim

LABEL maintainer="闲适老翁"
LABEL version="1.0.4"
LABEL description="股票分析与投资决策系统"

WORKDIR /app

ARG BUILD_TIME

# 复制并安装 Python 依赖（使用清华镜像加速）
COPY dev-team/backend-dev/stock-analysis-backend/requirements.txt .
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip install --no-cache-dir -r requirements.txt

# 复制后端代码
COPY dev-team/backend-dev/stock-analysis-backend/ .

# 复制本地已构建的前端产物（确保包含最新修改）
COPY dev-team/frontend-dev/stock-analysis-frontend/dist ./backend/static

# 创建必要目录
RUN mkdir -p data/cache data/reports logs

# 生产环境默认配置
ENV BACKEND_HOST=0.0.0.0
ENV BACKEND_PORT=8000
ENV BACKEND_RELOAD=false
ENV CORS_ORIGINS=["*"]
ENV LOG_LEVEL=INFO
ENV TDX_ENABLED=false
# 数据源：新浪优先（东财HTTPS在此网络不通）
ENV PRIMARY_DATA_SOURCE=sina
ENV FALLBACK_DATA_SOURCE=eastmoney

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; response=urllib.request.urlopen('http://localhost:8000/api/v1/health'); assert response.status == 200" || exit 1

EXPOSE 8000

# 使用 uvicorn 直接启动（信号处理更可靠）
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
