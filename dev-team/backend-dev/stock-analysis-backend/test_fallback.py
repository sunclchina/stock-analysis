import asyncio, sys, os
sys.path.insert(0, os.getcwd())
os.environ['LOG_LEVEL'] = 'WARNING'

async def test():
    from backend.services.data_source.fallback import DataSourceManager
    from backend.services.data_source.sina import SinaDataSource
    
    dsm = DataSourceManager()
    dsm.register_default_sources()
    
    codes = ['300850','600666','300207','600501','300456','001337','601678','002134','603660','688393','688128','600570','300833','300440']
    
    print('Priority list:', dsm._priority_list())
    print('Active name:', dsm._active_name)
    print('Primary:', dsm._primary_name)
    print('Fallback:', dsm._fallback_name)
    
    result = await dsm.get_quotes(codes)
    print(f'\nget_quotes result: {len(result) if result else 0} quotes')
    print('Active name after:', dsm._active_name)
    if result:
        for q in result[:3]:
            print(f'  {q.code} {q.name} {q.price}')

asyncio.run(test())
