# Byte-level check of CustomSelectionTab.tsx lines 378-395

with open(r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx', 'rb') as f:
    data = f.read()
lines = data.split(b'\n')
for i in range(377, 395):
    line = lines[i]
    high = sum(1 for b in line if b > 127)
    ticks = line.count(b'\x60')
    sq = line.count(b'\x27')
    print(f'{i+1:4d}: hb={high:3d} t={ticks} sq={sq} | {line[:150]}')
