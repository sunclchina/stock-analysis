import asyncio
import aiosqlite

async def check():
    async with aiosqlite.connect('/app/data/cache/stock.db') as db:
        cur = await db.execute("SELECT COUNT(*) FROM trading_notes")
        cnt = (await cur.fetchone())[0]
        print('Total rows in trading_notes:', cnt)
        cur2 = await db.execute("SELECT id, title FROM trading_notes ORDER BY id")
        rows = await cur2.fetchall()
        for r in rows:
            print('  [%d] %s' % r)

asyncio.run(check())
