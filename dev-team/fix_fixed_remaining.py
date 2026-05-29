# -*- coding: utf-8 -*-
"""Fix remaining JSX issues in FixedSelectionTab.tsx"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\FixedSelectionTab.tsx'

with open(fp, 'rb') as f:
    data = f.read()

lines = data.split(b'\n')
changes = 0

for i in range(len(lines)):
    line = lines[i]
    
    # Fix broken closing tags
    if b'?/Text>' in line:
        lines[i] = line.replace(b'?/Text>', b'</Text>')
        changes += 1
    if b'?/Tag>' in line:
        lines[i] = line.replace(b'?/Tag>', b'</Tag>')
        changes += 1
    if b'?/Space>' in line:
        lines[i] = line.replace(b'?/Space>', b'</Space>')
        changes += 1
    
    # Fix L0 tag with garbled Chinese
    if b'L0:' in line and b'totalStockCount' in line:
        for j, b in enumerate(line):
            if b > 127:
                idx_start = line.find(b'L0:')
                if idx_start >= 0:
                    after_l0 = line[idx_start+3:]
                    tmpl_start = after_l0.find(b'totalStockCount')
                    if tmpl_start >= 0:
                        lines[i] = line[:idx_start+3] + b'All A-shares ' + after_l0[tmpl_start:]
                        changes += 1
                break
    
    # Fix garbled Descriptions labels
    if b'<Descriptions.Item label=' in line:
        qt = line.find(b'label=')
        dqt = line.find(b'"', qt+6)
        if dqt > qt:
            label = line[qt+7:dqt]
            if any(b > 127 for b in label):
                lines[i] = line[:qt+7] + b'Item\x00'[:4] + line[dqt:]
                changes += 1

new_data = b'\n'.join(lines)
with open(fp, 'wb') as f:
    f.write(new_data)
print(f'Fixed {changes} issues. {len(data)} -> {len(new_data)} bytes')
