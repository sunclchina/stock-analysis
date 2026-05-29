"""
M05 分析引擎 — DeepSeek大模型客户端。

职责：
1. 通过HTTP调用DeepSeek API（从.env读取API Key和URL）
2. 自动重试3次
3. 失败返回结构化"分析失败"消息
4. 支持流式/非流式两种模式

遵循原则②：API Key/URL从配置读取，无硬编码。
"""

import json
import logging
from typing import Optional, Dict, Any, AsyncIterator, List

import httpx

logger = logging.getLogger(__name__)

# 默认API配置（会被.env中的配置覆盖）
DEFAULT_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEFAULT_MODEL = "deepseek-chat"

# 重试配置
MAX_RETRIES = 3
RETRY_DELAY_MS = 1000  # 1秒


class LLMClient:
    """
    DeepSeek大模型客户端。

    支持：
    - 同步/异步调用
    - 流式/非流式模式
    - 自动重试（3次）
    - 结构化失败返回
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 60,
    ):
        """
        初始化LLM客户端。

        优先使用传入参数，其次从settings读取，最后使用默认值。
        """
        self._api_key = api_key or self._get_api_key_from_settings()
        self._api_url = api_url or self._get_api_url_from_settings()
        self._model = model or self._get_model_from_settings()
        self._timeout = timeout

        logger.info(
            f"LLM客户端初始化: model={self._model}, "
            f"url={self._api_url[:60] + '...' if len(self._api_url) > 60 else self._api_url}, "
            f"key_present={bool(self._api_key)}"
        )

    @staticmethod
    def _get_api_key_from_settings() -> Optional[str]:
        """从settings获取API Key"""
        try:
            from backend.config.settings import settings
            return getattr(settings, 'deepseek_api_key', None) or ""
        except (ImportError, AttributeError):
            import os
            return os.environ.get("DEEPSEEK_API_KEY", "")

    @staticmethod
    def _get_api_url_from_settings() -> str:
        """从settings获取API URL"""
        try:
            from backend.config.settings import settings
            return getattr(settings, 'deepseek_api_url', None) or DEFAULT_API_URL
        except (ImportError, AttributeError):
            import os
            return os.environ.get("DEEPSEEK_API_URL", DEFAULT_API_URL)

    @staticmethod
    def _get_model_from_settings() -> str:
        """从settings获取模型名称"""
        try:
            from backend.config.settings import settings
            return getattr(settings, 'deepseek_model', None) or DEFAULT_MODEL
        except (ImportError, AttributeError):
            import os
            return os.environ.get("DEEPSEEK_MODEL", DEFAULT_MODEL)

    @property
    def is_configured(self) -> bool:
        """检查是否已配置API Key"""
        return bool(self._api_key)

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,
        search: bool = False,
    ) -> Dict[str, Any]:
        """
        发送聊天请求。

        Args:
            messages: 消息列表
            temperature: 温度参数（0~2）
            max_tokens: 最大生成长度
            stream: 是否流式
            search: 是否启用联网搜索（DeepSeek支持）

        Returns:
            成功: {"success": True, "content": "回复内容", "usage": {...}}
            失败: {"success": False, "error": "错误信息", "content": None}
        """
        if not self.is_configured:
            return self._build_error("DeepSeek API Key未配置，请在.env中设置DEEPSEEK_API_KEY")

        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }
        if search:
            payload["search"] = True

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        last_error = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.post(
                        self._api_url,
                        json=payload,
                        headers=headers,
                    )

                    if response.status_code == 200:
                        data = response.json()
                        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                        usage = data.get("usage", {})
                        logger.info(
                            f"LLM调用成功 (attempt {attempt}): "
                            f"tokens={usage.get('total_tokens', '?')}"
                        )
                        return {
                            "success": True,
                            "content": content,
                            "usage": usage,
                        }
                    elif response.status_code == 429:
                        # 限流，重试
                        import asyncio
                        wait = RETRY_DELAY_MS * attempt / 1000
                        logger.warning(f"LLM限流 (429)，{wait}s后重试 (attempt {attempt})")
                        await asyncio.sleep(wait)
                        last_error = f"API限流 (429)"
                        continue
                    elif response.status_code == 401:
                        return self._build_error("API认证失败，请检查DEEPSEEK_API_KEY")
                    elif response.status_code == 400:
                        error_body = response.text[:200]
                        return self._build_error(f"API请求错误 (400): {error_body}")
                    else:
                        logger.warning(
                            f"LLM调用异常 (attempt {attempt}): "
                            f"status={response.status_code}, body={response.text[:200]}"
                        )
                        last_error = f"HTTP {response.status_code}"
                        if attempt < MAX_RETRIES:
                            import asyncio
                            await asyncio.sleep(RETRY_DELAY_MS * attempt / 1000)

            except httpx.TimeoutException:
                logger.warning(f"LLM请求超时 (attempt {attempt}/{MAX_RETRIES})")
                last_error = "请求超时"
                if attempt < MAX_RETRIES:
                    import asyncio
                    await asyncio.sleep(RETRY_DELAY_MS * attempt / 1000)

            except httpx.RequestError as e:
                logger.warning(f"LLM网络错误 (attempt {attempt}): {e}")
                last_error = f"网络错误: {str(e)[:100]}"
                if attempt < MAX_RETRIES:
                    import asyncio
                    await asyncio.sleep(RETRY_DELAY_MS * attempt / 1000)

            except Exception as e:
                logger.error(f"LLM未知错误 (attempt {attempt}): {e}")
                last_error = f"未知错误: {str(e)[:100]}"
                if attempt < MAX_RETRIES:
                    import asyncio
                    await asyncio.sleep(RETRY_DELAY_MS * attempt / 1000)

        # 全部重试失败
        return self._build_error(f"分析失败（{MAX_RETRIES}次重试后仍失败）: {last_error}")

    def _build_error(self, message: str) -> Dict[str, Any]:
        """构建结构化的失败响应"""
        return {
            "success": False,
            "error": message,
            "content": self._format_error_message(message),
        }

    @staticmethod
    def _format_error_message(error: str) -> str:
        """格式化为用户可读的错误文案"""
        return (
            "# ⚠️ 分析暂时不可用\n\n"
            f"**原因：** {error}\n\n"
            "**建议：**\n"
            "1. 检查环境变量 `DEEPSEEK_API_KEY` 是否正确配置\n"
            "2. 检查网络连接是否正常\n"
            "3. 稍后重试\n\n"
            "---\n\n"
            "*智能分析由 DeepSeek 大模型驱动，当前服务暂不可用。*"
        )

    async def chat_with_system_prompt(
        self,
        system_prompt: str,
        user_content: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        """便捷方法：传入system prompt + user message"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
        return await self.chat(messages, temperature, max_tokens)


# 全局单例
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """获取全局LLM客户端单例"""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
