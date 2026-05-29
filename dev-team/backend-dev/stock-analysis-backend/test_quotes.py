import asyncio, httpx

async def test():
    codes = ['300850', '600666', '300207', '600501', '300456', '001337', '601678', '002134', '603660', '688393', '688128', '600570', '300833', '300440']
    
    # Test sina batch
    client = httpx.AsyncClient(timeout=5.0, headers={'Referer': 'https://finance.sina.com.cn'})
    
    prefixes = {'6': 'sh', '5': 'sh', '9': 'bj', '0': 'sz', '3': 'sz', '4': 'sz', '8': 'bj'}
    sina_list = ','.join([f'{prefixes.get(c[0],"sh")}{c}' for c in codes])
    url = f'https://hq.sinajs.cn/list={sina_list}'
    r = await client.get(url)
    print(f'Sina status: {r.status_code}, text length: {len(r.text)}')
    lines = r.text.strip().split('\n')
    for line in lines[:5]:
        print(line[:200])
    print(f'Total lines: {len(lines)}')
    
    # Now test dsm.get_quotes via the API  
    r2 = httpx.get('http://127.0.0.1:8000/api/v1/market/quotes/' + ','.join(codes[:3]), timeout=10)
    d = r2.json()
    print(f'\nBatch quotes: count={d["count"]}, active_source={d["active_data_source"]}')
    for q in d['quotes']:
        print(f'  {q["code"]} {q["name"]} {q["price"]}')
    
    await client.aclose()

asyncio.run(test())
