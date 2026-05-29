"""测试个股资金流API"""
import asyncio, json, sys, asyncio

sys.path.insert(0, ".")

async def test():
    try:
        # 直接从数据源层测试
        from backend.services.data_source.fallback import DataSourceManager
        from backend.services.data_source.base import DataSourceStatus
        
        dsm = DataSourceManager()
        dsm.register_default_sources()
        
        # 确保akshare在线
        ak = dsm._sources.get("akshare")
        if ak and ak.status == DataSourceStatus.OFFLINE:
            ak._status = DataSourceStatus.ONLINE
            ak._consecutive_failures = 0
            print("AKShare: 已重置为在线")
        
        src = dsm.get_active_for_module("market_fund_flow")
        print(f"数据源: {src.name} ({type(src).__name__})")
        
        result = await src.get_individual_fund_flow("000001")
        print("✅ 成功:")
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(test())
