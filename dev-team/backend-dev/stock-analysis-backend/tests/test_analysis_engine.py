"""
M05 智能分析引擎测试。
测试大模型客户端（URL/Key配置读取、重试逻辑）、提示词模板加载、报告生成流程。
"""
import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.services.analysis_engine.llm_client import LLMClient, MAX_RETRIES
from backend.services.analysis_engine.prompt_templates import (
    REVIEW_SYSTEM_PROMPT,
    STOCK_ANALYSIS_SYSTEM_PROMPT,
    BATCH_ANALYSIS_SYSTEM_PROMPT,
)


# ============================================================
# 大模型客户端测试
# ============================================================

class TestLLMClientConfiguration:

    def test_default_url_and_model(self):
        """测试默认URL和模型"""
        with patch("backend.services.analysis_engine.llm_client.LLMClient._get_api_key_from_settings", return_value=""):
            with patch("backend.services.analysis_engine.llm_client.LLMClient._get_api_url_from_settings",
                       return_value="https://api.deepseek.com/v1/chat/completions"):
                with patch("backend.services.analysis_engine.llm_client.LLMClient._get_model_from_settings",
                           return_value="deepseek-chat"):
                    client = LLMClient()
                    assert client._api_url == "https://api.deepseek.com/v1/chat/completions"
                    assert client._model == "deepseek-chat"

    def test_is_configured_false(self):
        """测试未配置API Key"""
        with patch("backend.services.analysis_engine.llm_client.LLMClient._get_api_key_from_settings", return_value=""):
            client = LLMClient()
            assert client.is_configured is False

    def test_is_configured_true(self):
        """测试已配置API Key"""
        with patch("backend.services.analysis_engine.llm_client.LLMClient._get_api_key_from_settings",
                   return_value="sk-test-key"):
            client = LLMClient()
            assert client.is_configured is True

    def test_custom_params(self):
        """测试自定义参数"""
        client = LLMClient(
            api_key="custom-key",
            api_url="https://custom.api.com/chat",
            model="custom-model",
        )
        assert client._api_key == "custom-key"
        assert client._api_url == "https://custom.api.com/chat"
        assert client._model == "custom-model"


class TestLLMClientChat:

    @pytest.mark.asyncio
    async def test_chat_no_api_key(self):
        """测试无API Key时返回错误"""
        client = LLMClient(api_key="")
        result = await client.chat([{"role": "user", "content": "test"}])
        assert result["success"] is False
        assert "未配置" in result["error"]
        assert result["content"] is not None

    @pytest.mark.asyncio
    async def test_chat_401_error(self):
        """测试401认证错误"""
        client = LLMClient(api_key="invalid-key")

        mock_response = AsyncMock()
        mock_response.status_code = 401

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.return_value = mock_response
            result = await client.chat([{"role": "user", "content": "test"}])

        assert result["success"] is False
        assert "认证" in result["error"]

    @pytest.mark.asyncio
    async def test_chat_retry_on_429(self):
        """测试429限流重试"""
        client = LLMClient(api_key="test-key")

        mock_429 = AsyncMock()
        mock_429.status_code = 429
        mock_200 = AsyncMock()
        mock_200.status_code = 200
        mock_200.json.return_value = {
            "choices": [{"message": {"content": "test response"}}],
            "usage": {"total_tokens": 10},
        }

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.side_effect = [mock_429, mock_200]
            result = await client.chat([{"role": "user", "content": "test"}])

        assert result["success"] is True
        assert result["content"] == "test response"

    @pytest.mark.asyncio
    async def test_chat_retry_exhausted(self):
        """测试重试耗尽"""
        client = LLMClient(api_key="test-key")

        mock_error = AsyncMock()
        mock_error.status_code = 500

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.return_value = mock_error
            result = await client.chat([{"role": "user", "content": "test"}])

        assert result["success"] is False
        assert "重试" in result["error"]

    @pytest.mark.asyncio
    async def test_chat_timeout(self):
        """测试超时"""
        client = LLMClient(api_key="test-key")

        with patch("httpx.AsyncClient.post") as mock_post:
            from httpx import TimeoutException
            mock_post.side_effect = TimeoutException("timeout")
            result = await client.chat([{"role": "user", "content": "test"}])

        assert result["success"] is False
        assert "超时" in result["error"] or "重试" in result["error"]


# ============================================================
# 提示词模板测试
# ============================================================

class TestPromptTemplates:

    def test_review_system_prompt_loaded(self):
        """测试复盘提示词模板已加载"""
        assert REVIEW_SYSTEM_PROMPT is not None
        assert len(REVIEW_SYSTEM_PROMPT) > 100
        assert "复盘" in REVIEW_SYSTEM_PROMPT or "review" in REVIEW_SYSTEM_PROMPT.lower()

    def test_stock_analysis_system_prompt_loaded(self):
        """测试个股分析提示词模板已加载"""
        assert STOCK_ANALYSIS_SYSTEM_PROMPT is not None
        assert len(STOCK_ANALYSIS_SYSTEM_PROMPT) > 100

    def test_batch_analysis_system_prompt_loaded(self):
        """测试批量分析提示词模板已加载"""
        assert BATCH_ANALYSIS_SYSTEM_PROMPT is not None
        assert len(BATCH_ANALYSIS_SYSTEM_PROMPT) > 100

    def test_review_template_build_prompt(self):
        """测试复盘用户提示词构建"""
        from backend.services.analysis_engine.prompt_templates.review_template import build_review_user_prompt
        prompt = build_review_user_prompt(
            date_str="2026-04-29",
            market_data='{"indices": []}',
            watch_stocks_data='{"quotes": []}',
            warning_summary='{}',
        )
        assert "2026-04-29" in prompt
        assert len(prompt) > 50

    def test_stock_analysis_template_build_prompt(self):
        """测试个股分析用户提示词构建"""
        from backend.services.analysis_engine.prompt_templates.stock_analysis_template import build_stock_analysis_user_prompt
        prompt = build_stock_analysis_user_prompt(
            code="600519",
            name="贵州茅台",
            market_data='{"price": 1680}',
            kline_data='[]',
            finance_data='{"pe": 30}',
            warning_data='{}',
            decision_data='{}',
        )
        assert "600519" in prompt
        assert "贵州茅台" in prompt

    def test_batch_analysis_template_build_prompt(self):
        """测试批量分析用户提示词构建"""
        from backend.services.analysis_engine.prompt_templates.batch_analysis_template import build_batch_analysis_user_prompt
        prompt = build_batch_analysis_user_prompt(
            stocks_data='{"stocks": {}}',
            warning_data='{}',
        )
        assert len(prompt) > 50
