"""Debug the pattern analysis 500 error"""
import sys, asyncio
sys.path.insert(0, '.')

async def test():
    code = '600519'
    days = 60
    
    # Step 1: LLM init
    print('Step 1: LLM init...')
    try:
        from backend.services.analysis_engine.llm_client import LLMClient
        llm = LLMClient()
        print(f'  Configured: {llm.is_configured()}')
    except Exception as e:
        print(f'  LLM FAILED: {e}')
        return

    # Step 2: Kline data
    print('Step 2: Kline data...')
    try:
        from backend.api.analysis import _get_kline_data
        klines = await _get_kline_data(code)
        print(f'  Klines: {len(klines)}')
    except Exception as e:
        print(f'  KLINES FAILED: {e}')
        import traceback
        traceback.print_exc()
        return

    # Step 3: Format prompt
    print('Step 3: Format prompt...')
    try:
        from backend.api.analysis import PATTERN_ANALYSIS_PROMPT
        kline_text = '\n'.join([
            f"{k.get('date','')} | {k.get('open',0)} | {k.get('close',0)} | {k.get('high',0)} | {k.get('low',0)} | {k.get('volume',0)} | {k.get('amount',0)}"
            for k in klines[-days:]
        ]) if klines else ''
        prompt = PATTERN_ANALYSIS_PROMPT.format(day_count=min(days, len(klines)), klines=kline_text)
        print(f'  Prompt length: {len(prompt)}')
    except Exception as e:
        print(f'  PROMPT FAILED: {e}')
        import traceback
        traceback.print_exc()
        return

    # Step 4: LLM call
    print('Step 4: LLM call...')
    try:
        if llm.is_configured() and klines:
            result = await llm.chat_with_system_prompt(
                system_prompt="你是资深A股技术分析师",
                user_message=prompt,
            )
            report = result.get("content", "") if isinstance(result, dict) else str(result)
            print(f'  Report length: {len(report)}')
        else:
            print('  Skipped (no klines or no config)')
    except Exception as e:
        print(f'  LLM CALL FAILED: {e}')
        import traceback
        traceback.print_exc()
        return
    
    print('\nALL OK')

asyncio.run(test())
