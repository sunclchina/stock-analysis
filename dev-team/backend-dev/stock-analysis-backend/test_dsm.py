import asyncio, time, sys, os
os.environ['LOG_LEVEL'] = 'WARNING'
sys.path.insert(0, os.getcwd())
from backend.services.data_source.fallback import DataSourceManager

async def test():
    dsm = DataSourceManager()
    dsm.register_default_sources()
    t0 = time.time()
    s = dsm.get_status_summary()
    t1 = time.time()
    for src in s:
        print(f'{src["name"]:20s} status={src["status"]:10s} failures={src["consecutive_failures"]}')
    print(f'get_status_summary: {(t1-t0)*1000:.0f}ms')

asyncio.run(test())
