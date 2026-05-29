# ============================================
# 股票分析与投资决策系统 - Docker 构建文件
# ============================================
# 构建前需先构建前端：
#   cd dev-team/frontend-dev/stock-analysis-frontend
#   npm run build
# ============================================
# 构建方式：
#   docker build -t stock-analysis:latest .
# 运行方式：
#   docker run -d --name stock-analysis -p 8000:8000 \
#     -v /path/to/.env:/app/.env \
#     -v stock-data:/app/data \
#     stock-analysis:latest
# ============================================

FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制后端代码
COPY backend/ ./backend/
COPY requirements.txt ./

# 复制前端静态文件
COPY backend/static/ ./backend/static/

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 创建数据目录
RUN mkdir -p data/cache data/reports data/a_share_cache data/kline_cache logs

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/api/v1/dashboard').status)"

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
