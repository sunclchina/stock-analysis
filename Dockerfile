# ============================================
# 股票分析与投资决策系统 - Docker 构建文件
# ============================================
# 构建方式：
#   docker build -t stock-analysis .
# 运行方式：
#   docker run -d --name stock-analysis \
#     -p 8081:8081 \
#     -v /path/to/.env:/app/.env \
#     stock-analysis
# ============================================

FROM python:3.11-slim

WORKDIR /app

# 安装系统工具（健康检查用）
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl && \
    rm -rf /var/lib/apt/lists/*

# 复制后端源码（含前端静态文件 backend/static/）
COPY dev-team/backend-dev/stock-analysis-backend/ .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 创建运行时目录
RUN mkdir -p data/cache data/reports logs

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8081/api/v1/health || exit 1

EXPOSE 8081

# 通过 python -m 启动，触发 main.py 的 __main__ 块的 SSL 检查逻辑
# 端口和 SSL 配置从 .env（挂载 /app/.env）或环境变量读取
CMD ["python", "-m", "backend.main"]
