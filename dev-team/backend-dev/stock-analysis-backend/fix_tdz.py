"""Fix RiskMonitorTab TDZ issue by moving tabs before MarketResearchPage"""
import re

path = 'C:/Users/suncl/.openclaw/workspace/dev-team/frontend-dev/stock-analysis-frontend/src/pages/MarketResearch/index.tsx'
with open(path, 'r', encoding='utf-8-sig') as f:
    content = f.read()

# Find positions
page_start = content.find('\nconst MarketResearchPage:')
news_start = content.find('\nconst NewsAndAnnounceTab:')
risk_start = content.find('\nconst RiskMonitorTab:')
items_start = content.find('\n  const items = [')

print(f'marketPage: {page_start}')
print(f'newsAndAnn: {news_start}')
print(f'riskMon: {risk_start}')
print(f'items: {items_start}')

# Find end of RiskMonitorTab (next const after it)
# Find all const declaration positions after risk_start
const_positions = []
search_from = risk_start + 1
while True:
    pos = content.find('\nconst ', search_from)
    if pos < 0:
        break
    const_positions.append(pos)
    search_from = pos + 1

# Also find end of file
print('Const positions after risk:', const_positions)
