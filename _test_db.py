import sqlite3
conn = sqlite3.connect(r'C:\Users\suncl\.openclaw\workspace\dev-team\backend-dev\stock-analysis-backend\data\cache\stock.db')
cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
for t in tables:
    print(t[0])
