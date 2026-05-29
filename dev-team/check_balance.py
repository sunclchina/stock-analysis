"""Check string delimiter balance"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\FixedSelectionTab.tsx'
with open(fp, 'rb') as f:
    lines = f.read().split(b'\n')

total_bt = 0
total_sq = 0
total_dq = 0
limit = 162  # 0-indexed, before line 163

for i in range(limit):
    line = lines[i]
    total_bt += line.count(b'\x60')
    total_sq += line.count(b"'")
    total_dq += line.count(b'"')

print(f'Before line 163 (0-indexed {limit}):')
print(f'  Backticks: {total_bt} (balance: {total_bt % 2})')
print(f'  Single-quotes: {total_sq} (balance: {total_sq % 2})')
print(f'  Double-quotes: {total_dq} (balance: {total_dq % 2})')
