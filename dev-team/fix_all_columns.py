"""Fix ALL remaining garbled column titles in FixedSelectionTab.tsx"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\FixedSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()
lines = data.split(b'\n')

# Fix ALL garbled column titles - match by dataIndex
title_fixes = [
    (b"'Rank', dataIndex: 'rank'", b"'Rank', dataIndex: 'rank'"),
    (b"'Code', dataIndex: 'code'", b"'Code', dataIndex: 'code'"),
    (b"'Name', dataIndex: 'name'", b"'Name', dataIndex: 'name'"),
    (b"'Industry', dataIndex: 'industry'", b"'Industry', dataIndex: 'industry'"),
    (b"'Trend', dataIndex: 'trendColor'", b"'Trend', dataIndex: 'trendColor'"),
    (b"'Resonance', dataIndex: 'resonanceStatus'", b"'Resonance', dataIndex: 'resonanceStatus'"),
    (b"'Strength', dataIndex: 'trendStrength'", b"'Strength', dataIndex: 'trendStrength'"),
    (b"'Risk Score', dataIndex: 'riskScore'", b"'Risk Score', dataIndex: 'riskScore'"),
    (b"'Risk Level', dataIndex: 'riskLevel'", b"'Risk Level', dataIndex: 'riskLevel'"),
    (b"'Finance Grade', dataIndex: 'financeGrade'", b"'Finance Grade', dataIndex: 'financeGrade'"),
    (b"'Score', dataIndex: 'compositeScore'", b"'Score', dataIndex: 'compositeScore'"),
    (b"'Advice', dataIndex: 'operationAdvice'", b"'Advice', dataIndex: 'operationAdvice'"),
    (b"'Watchlist', dataIndex: 'action'", b"'Watchlist', dataIndex: 'action'"),
]

for i, line in enumerate(lines):
    # Check if line has a column title with garbled text
    if b"dataIndex: '" in line and b"title: '" in line:
        # Extract the dataIndex value
        di_start = line.find(b"dataIndex: '")
        if di_start > 0:
            di_end = line.find(b"'", di_start + 12)
            if di_end > di_start:
                data_idx = line[di_start+12:di_end]
                # Find matching clean title
                for title, _ in title_fixes:
                    if data_idx in title:
                        # Replace the title value
                        t_start = line.find(b"title: '")
                        t_end = line.find(b"'", t_start + 8)
                        if t_start > 0 and t_end > t_start:
                            clean_title = title[:title.find(b"', dataIndex")]
                            lines[i] = line[:t_start+8] + clean_title[1:] + line[t_end:]
                        break

# Also fix column title for line 251
for i, line in enumerate(lines):
    if b"dataIndex: 'action'" in line and b"title:" in line:
        # This is the Action column
        t_start = line.find(b"title: '")
        t_end = line.find(b"'", t_start + 8)
        if t_start > 0 and t_end > t_start:
            lines[i] = line[:t_start+8] + b"Watchlist" + line[t_end:]
        # Also fix trailing comma-quote
        if b"as const,'" in line:
            lines[i] = lines[i].replace(b"as const,'", b"as const,")

new_data = b'\n'.join(lines)
with open(fp, 'wb') as f:
    f.write(new_data)
print('Fixed all garbled column titles')
