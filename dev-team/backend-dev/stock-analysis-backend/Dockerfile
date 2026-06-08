# =============================================================================
# 股票分析与投资决策系统 — 生产 Dockerfile
#
# 构建步骤:
#   docker build -t stock-analysis:latest .
#
# 运行步骤:
#   前置: Docker 数据目录 D:/docker/stock-analysis/
#         包含 .env, data/, certs/ (如需 HTTPS)
#   docker run -d --name stock-analysis \
#     -p 8081:8081 \
#     --env-file D:/docker/stock-analysis/.env \
#     -v D:/docker/stock-analysis/data:/app/data \
#     -v D:/docker/stock-analysis/certs:/app/certs:ro \
#     stock-analysis:latest
# =============================================================================

FROM python:3.11-slim

WORKDIR /app

# 安装运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码（含前端构建产物 backend/static/）
COPY . .

# 创建运行时数据目录
RUN mkdir -p data/cache data/reports logs

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8081/api/v1/health || exit 1

EXPOSE 8081

CMD ["python", "-m", "backend.main"]
