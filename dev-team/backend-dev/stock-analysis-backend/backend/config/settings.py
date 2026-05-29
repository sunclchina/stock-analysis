"""
系统配置：Pydantic Settings，所有配置从环境变量读取。
遵循原则②：禁止硬编码，所有配置项通过 .env 或系统环境变量注入。
"""

from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field, model_validator
import json


def _parse_cors(raw: str) -> List[str]:
    """解析 CORS_ORIGINS 环境变量：兼容 JSON 数组、逗号分隔、单字符串"""
    if not raw or not raw.strip():
        return ["http://localhost:8080"]
    v = raw.strip()
    # 尝试 JSON 解析
    if v.startswith("["):
        try:
            parsed = json.loads(v)
            if isinstance(parsed, list):
                return [str(x) for x in parsed]
        except json.JSONDecodeError:
            # JSON 解析失败（如 Docker 吞掉引号后变成 [*]）
            # 提取括号内的内容，按逗号分隔
            inner = v.strip("[]")
            if not inner.strip():
                return []
            items = [x.strip().strip("\"'") for x in inner.split(",") if x.strip()]
            if items:
                return items
    # 逗号分隔（不带括号）
    if "," in v:
        return [x.strip() for x in v.split(",") if x.strip()]
    # 单个值
    return [v]


class Settings(BaseSettings):
    """应用配置，从环境变量加载"""

    # 后端服务
    backend_host: str = Field(default="0.0.0.0", alias="BACKEND_HOST")
    backend_port: int = Field(default=8000, alias="BACKEND_PORT")
    backend_reload: bool = Field(default=True, alias="BACKEND_RELOAD")

    # 数据库
    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/cache/stock.db",
        alias="DATABASE_URL",
    )

    # CORS（兼容 JSON 数组、逗号分隔、单字符串）
    cors_origins_str: str = Field(
        default='["http://localhost:8080"]',
        alias="CORS_ORIGINS",
    )

    @property
    def cors_origins(self) -> List[str]:
        return _parse_cors(self.cors_origins_str)

    # 数据源
    tdx_enabled: bool = Field(default=True, alias="TDX_ENABLED")
    tdx_data_dir: str = Field(default="./data/tdx", alias="TDX_DATA_DIR")
    tdx_api_url: str = Field(default="http://49.232.145.222:8080", alias="TDX_API_URL")
    primary_data_source: str = Field(default="tdx_api", alias="PRIMARY_DATA_SOURCE")
    fallback_data_source: str = Field(default="eastmoney", alias="FALLBACK_DATA_SOURCE")

    # 东方财富 API 配置（可配置URL，不硬编码）
    eastmoney_batch_quote_url: str = Field(
        default="https://push2.eastmoney.com/api/qt/ulist.np/get",
        alias="EASTMONEY_BATCH_QUOTE_URL",
    )
    eastmoney_single_quote_url: str = Field(
        default="https://push2.eastmoney.com/api/qt/stock/get",
        alias="EASTMONEY_SINGLE_QUOTE_URL",
    )
    eastmoney_kline_url: str = Field(
        default="https://push2his.eastmoney.com/api/qt/stock/kline/get",
        alias="EASTMONEY_KLINE_URL",
    )
    eastmoney_timeout: int = Field(default=10, alias="EASTMONEY_TIMEOUT")

    # DeepSeek AI配置
    deepseek_api_key: str = Field(default="", alias="DEEPSEEK_API_KEY")
    deepseek_api_url: str = Field(
        default="https://api.deepseek.com/v1/chat/completions",
        alias="DEEPSEEK_API_URL",
    )
    deepseek_model: str = Field(default="deepseek-chat", alias="DEEPSEEK_MODEL")

    # 用户认证
    jwt_secret: str = Field(default="", alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_hours: int = Field(default=8, alias="ACCESS_TOKEN_EXPIRE_HOURS")

    # 默认管理员账号
    default_admin_username: str = Field(default="admin", alias="DEFAULT_ADMIN_USERNAME")
    default_admin_password: str = Field(default="admin123", alias="DEFAULT_ADMIN_PASSWORD")
    default_admin_nickname: str = Field(default="系统管理员", alias="DEFAULT_ADMIN_NICKNAME")
    force_change_password: bool = Field(default=True, alias="FORCE_CHANGE_PASSWORD_ON_FIRST_LOGIN")
    enable_demo_user: bool = Field(default=True, alias="ENABLE_DEMO_USER")
    demo_username: str = Field(default="demo", alias="DEMO_USERNAME")
    demo_password: str = Field(default="demo123", alias="DEMO_PASSWORD")
    demo_nickname: str = Field(default="演示用户", alias="DEMO_NICKNAME")

    # 回测默认标的
    default_backtest_stock: str = Field(default="000001", alias="DEFAULT_BACKTEST_STOCK")

    # 日志
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    model_config = {"env_file": __file__.rsplit("backend", 1)[0] + ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


# 全局单例
settings = Settings()
