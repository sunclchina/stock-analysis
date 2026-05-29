import asyncio, sys, os
sys.path.insert(0, os.getcwd())
os.environ['LOG_LEVEL'] = 'WARNING'

async def test():
    from backend.main import data_source_manager as dsm
    
    codes = ['300850','600666','300207','600501','300456','001337','601678','002134','603660','688393','688128','600570','300833','300440']
    
    print('Priority list:', dsm._priority_list())
    print('Active name:', dsm._active_name)
    print('Primary:', dsm._primary_name, 'Fallback:', dsm._fallback_name)
    
    import time
    t0 = time.time()
    result = await dsm.get_quotes(codes)
    elapsed = time.time() - t0
    print(f'\nget_quotes: {len(result) if result else 0} quotes, {elapsed:.2f}s')
    print('Active name after:', dsm._active_name)
    if result:
        for q in result[:3]:
            print(f'  {q.code} {q.name} {q.price}')

asyncio.run(test())
