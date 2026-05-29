"""Test the pattern analysis endpoint directly"""
import sys, asyncio, json
sys.path.insert(0, '.')

from backend.api.analysis import _get_kline_data, PATTERN_ANALYSIS_PROMPT
from backend.services.analysis_engine.llm_client import LLMClient

async def test():
    print("Testing kline data...")
    klines = await _get_kline_data('600519')
    print(f"Klines: {len(klines)}")
    if not klines:
        print("Kline data empty (weekend)")
    
    print("\nTesting LLMClient...")
    llm = LLMClient()
    print(f"Configured: {llm.is_configured()}")
    print(f"API Key: {'set' if llm._api_key else 'NOT SET'}")
    
    if llm.is_configured():
        print("\nTesting pattern analysis prompt...")
        header = "日期 | 开盘 | 收盘 | 最高 | 最低 | 成交量 | 成交额"
        kline_text = "\n".join([
            f"{k['date']} | {k['open']} | {k['close']} | {k['high']} | {k['low']} | {k['volume']} | {k['amount']}"
            for k in klines[-120:]
        ])
        prompt = PATTERN_ANALYSIS_PROMPT.format(day_count=min(120, len(klines)), klines=kline_text)
        print(f"Prompt length: {len(prompt)}")
        
        result = await llm.chat_with_system_prompt(
            system_prompt="你是资深A股技术分析师",
            user_message=prompt,
        )
        report = result.get("content", "") if isinstance(result, dict) else str(result)
        print(f"Report length: {len(report)}")
        print(f"Report preview: {report[:200]}...")

asyncio.run(test())
