"""Remove NewsCard and AnnounceCard from Dashboard.tsx"""
import re

path = 'C:/Users/suncl/.openclaw/workspace/dev-team/frontend-dev/stock-analysis-frontend/src/pages/Dashboard/index.tsx'
with open(path, 'r', encoding='utf-8-sig') as f:
    content = f.read()

# Remove NewsCard component definition
# From "const NewsCard:" up to "// --- A股概况卡片 ---"
content = re.sub(
    r'(?s)// ─── 财经新闻卡片 ───\n\nconst NewsCard: React\.FC.*?(?=\n// ─── )',
    '',
    content
)

# Remove AnnounceCard component definition
content = re.sub(
    r'(?s)// ─── 巨潮公告卡片 ───\n\nconst AnnounceCard: React\.FC.*?(?=\n// ─── )',
    '',
    content
)

# Remove JSX usage
content = content.replace(
    '<NewsCard items={newsItems} />\n            </div>\n            <div style={{ flex: 1, minWidth: 0 }}>\n              <AnnounceCard items={announcements} />',
    ''
)

# Remove state vars
content = content.replace(
    '  const [newsItems, setNewsItems] = useState<any[]>([]);\n  const [announcements, setAnnouncements] = useState<any[]>([]);\n',
    ''
)

# Remove fetch calls
content = content.replace(
    "        fetch('/api/v1/market/news').then(r => r.json()).then(d => setNewsItems(d.items || [])).catch(() => {}),\n        fetch('/api/v1/market/announcements').then(r => r.json()).then(d => setAnnouncements(d.items || [])).catch(() => {}),\n",
    ''
)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Done')
