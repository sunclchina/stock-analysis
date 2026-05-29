"""Remove NewsCard and AnnounceCard from Dashboard.tsx"""
import re

path = 'C:/Users/suncl/.openclaw/workspace/dev-team/frontend-dev/stock-analysis-frontend/src/pages/Dashboard/index.tsx'
with open(path, 'r', encoding='utf-8-sig') as f:
    content = f.read()

# Find section boundaries
s1 = content.find('// --- ')  # Skip intro
# Find NewsCard and AnnounceCard
news_start = content.find('const NewsCard:')
news_end = content.find('\n// --- ', news_start)
if news_end < 0:
    news_end = content.find('\n// ', news_start)

ann_start = content.find('const AnnounceCard:')
ann_end = content.find('\n// --- ', ann_start)
if ann_end < 0:
    ann_end = content.find('\n// ', ann_start)
    if ann_end < 0:
        ann_end = len(content)

# Remove NewsCard and AnnounceCard definitions
# Work backwards to avoid index shifting
# First, remove the comment lines before each
news_comment = content.rfind('// ', 0, news_start)
ann_comment = content.rfind('// ', 0, ann_start)

# Process: replace the comment+def with a short placeholder
lines = content.split('\n')
new_lines = []
skip_until = -1
for i, line in enumerate(lines):
    # Check if this is the start of NewsCard or AnnounceCard
    if line.startswith('const NewsCard:') or line.startswith('const AnnounceCard:'):
        skip_until = 1  # Skip this line
        # Skip the comment before it
        if new_lines and new_lines[-1].startswith('// --- 财经新闻') or new_lines and new_lines[-1].startswith('// --- 巨潮公告'):
            new_lines.pop()
        continue
    if skip_until > 0:
        # Count braces to know when the component ends
        # Simple approach: skip until we hit a line that starts with '//' at indent 0
        stripped = line.strip()
        if stripped.startswith('// ---') or stripped.startswith('const ') or stripped.startswith('interface ') or stripped.startswith('}'):
            skip_until = 0
            new_lines.append(line)
            continue
        continue
    new_lines.append(line)

content2 = '\n'.join(new_lines)

# Remove state vars
content2 = content2.replace(
    '  const [newsItems, setNewsItems] = useState<any[]>([]);',
    ''
)
content2 = content2.replace(
    '  const [announcements, setAnnouncements] = useState<any[]>([]);',
    ''
)

# Remove JSX usage (find the NewsCard/AnnounceCard usage lines)
# They appear as: <NewsCard items={newsItems} /> ...
lines = content2.split('\n')
new_lines = []
for line in lines:
    if '<NewsCard items={newsItems}' in line:
        continue
    if '<AnnounceCard items={announcements}' in line:
        continue
    new_lines.append(line)
content2 = '\n'.join(new_lines)

# Remove fetch calls
content2 = content2.replace(
    "fetch('/api/v1/market/news').then(r => r.json()).then(d => setNewsItems(d.items || [])).catch(() => {}),\nfetch('/api/v1/market/announcements').then(r => r.json()).then(d => setAnnouncements(d.items || [])).catch(() => {}),",
    ''
)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content2)

print('Done')
