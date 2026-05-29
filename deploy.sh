#!/bin/bash
# ==========================================
# 股票分析与投资决策系统 - Docker 部署脚本
# ==========================================
# 用法：
#   chmod +x deploy.sh
#   ./deploy.sh              # 构建并启动
#   ./deploy.sh --build      # 强制重新构建
#   ./deploy.sh --tar        # 构建 + 导出 .tar 文件
#   ./deploy.sh --up         # 仅启动已有容器
#   ./deploy.sh --down       # 停止
#   ./deploy.sh --logs       # 查看日志
# ==========================================

set -e

cd "$(dirname "$0")"

ACTION="${1:-build}"

case "$ACTION" in
  --build|-b)
    echo "=== 构建 Docker 镜像 ==="
    docker compose build --no-cache
    echo "=== 构建完成 ==="
    echo "=== 启动服务 ==="
    docker compose up -d
    echo "=== 服务已启动 ==="
    ;;

  --tar|-t)
    echo "=== 构建 Docker 镜像 ==="
    docker compose build --no-cache
    echo "=== 导出镜像为 .tar ==="
    docker save stock-analysis:1.0.1 | gzip > stock-analysis-1.0.1-docker.tar.gz
    echo "=== 导出完成: stock-analysis-1.0.1-docker.tar.gz ==="
    ;;

  --up|-u)
    echo "=== 启动服务 ==="
    docker compose up -d
    echo "=== 服务已启动 ==="
    ;;

  --down|-d)
    echo "=== 停止服务 ==="
    docker compose down
    echo "=== 服务已停止 ==="
    ;;

  --logs|-l)
    docker compose logs -f
    ;;

  --restart|-r)
    docker compose restart
    ;;

  --status|-s)
    docker compose ps
    ;;

  *)
    echo "用法: $0 [--build|--tar|--up|--down|--logs|--restart|--status]"
    echo ""
    echo "  默认: 构建并启动"
    echo "  --build   强制重新构建并启动"
    echo "  --tar     构建 + 导出 .tar.gz 文件（用于离线部署）"
    echo "  --up      仅启动服务"
    echo "  --down    停止服务"
    echo "  --logs    查看日志"
    echo "  --restart 重启服务"
    echo "  --status  查看状态"
    ;;
esac
