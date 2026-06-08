import sqlite3
conn = sqlite3.connect(r'C:\Users\suncl\.openclaw\workspace\dev-team\backend-dev\stock-analysis-backend\data\cache\stock.db')
cur = conn.cursor()
tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print('Tables:', [t[0] for t in tables])
for t in tables:
    tn = t[0]
    cols = cur.execute(f"PRAGMA table_info({tn})").fetchall()
    print(f'{tn}: {[(c[1],c[2]) for c in cols]}')
    if 'cache' in tn.lower() or 'generic' in tn.lower():
        rows = cur.execute(f"SELECT * FROM {tn}").fetchall()
        for r in rows:
            print(r)
conn.close()
