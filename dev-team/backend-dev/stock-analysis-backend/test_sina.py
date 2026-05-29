import asyncio, sys, os
sys.path.insert(0, os.getcwd())
os.environ['LOG_LEVEL'] = 'WARNING'

async def test():
    from backend.services.data_source.sina import SinaDataSource
    
    codes = ['300850','600666','300207','600501','300456','001337','601678','002134','603660','688393','688128','600570','300833','300440']
    
    s = SinaDataSource()
    quotes = await s.get_quotes(codes)
    print(f'Sina get_quotes returned: {len(quotes)} quotes')
    for q in quotes:
        print(f'  {q.code} {q.name} {q.price}')

asyncio.run(test())
