"""Fix ALL remaining garbled content in FixedSelectionTab.tsx"""
import os

fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\FixedSelectionTab.tsx'

with open(fp, 'rb') as f:
    data = f.read()

lines = data.split(b'\n')

fixes_applied = []

for i, line in enumerate(lines):
    # Fix 1: <Empty description="garbled" /> (line ~330)
    if b'<Empty description="' in line and sum(1 for b in line if b > 127) > 5:
        lines[i] = b'        {!hasRun ? <Empty description="Click the run button to execute the 5-layer stock selection pipeline" image={Empty.PRESENTED_IMAGE_SIMPLE} />'
        fixes_applied.append(f'Line {i+1}: Empty description')
    
    # Fix 2: showTotal with garbled text (line ~333)
    if b'showTotal:' in line and b'\x24{' in line and sum(1 for b in line if b > 127) > 0:
        lines[i] = b"                showTotal: (total, range) => `${range[0]}-${range[1]} / ${total} total`"
        fixes_applied.append(f'Line {i+1}: showTotal')
    
    # Fix 3: garbled tooltip title
    if b"<Tooltip title=\"" in line and sum(1 for b in line if b > 127) > 5:
        # Replace garbled in tooltip
        in_val = line.find(b'<Tooltip title="')
        if in_val >= 0:
            after_title = line[in_val+16:]
            quote_end = after_title.find(b'"')
            if quote_end >= 0:
                orig_title = after_title[:quote_end].decode('ascii', errors='replace')
                new_title = 'Click to sort'
                lines[i] = line[:in_val] + b'<Tooltip title="' + new_title.encode() + after_title[quote_end:]
                fixes_applied.append(f'Line {i+1}: Tooltip title')
    
    # Fix 4: garbled Button text
    if b'>' in line and b'\xe5\xaf\xbc' in line and b'<Button' in line:
        # This is "导出CSV" button
        lines[i] = line.replace(b'\xe5\xaf\xbc\xe5\x87\xbaCSV', b'Export CSV')
        fixes_applied.append(f'Line {i+1}: Button text export')
    
    # Fix 5: garbled "重新选股" button
    if b'\xe9\x87\x8d\xe6\x96\xb0\xe9\x80\x89\xe8\x82\xa1' in line:
        lines[i] = line.replace(b'\xe9\x87\x8d\xe6\x96\xb0\xe9\x80\x89\xe8\x82\xa1', b'Rerun Selection')
        fixes_applied.append(f'Line {i+1}: Reload button text')
    
    # Fix 6: garbled locale emptyText
    if b'locale={{ emptyText:' in line and sum(1 for b in line if b > 127) > 5:
        lines[i] = b'            locale={{ emptyText: <Empty description="No stocks matched current criteria" /> }}'
        fixes_applied.append(f'Line {i+1}: locale emptyText')
    
    # Fix 7: garbled in Descriptions labels (lines around ~340)
    if b'<Descriptions' in line or b'<Descriptions.Item' in line:
        for label in [b'\xe4\xbb\xb7\xe9\x94\x8b\xe6\x9d\xb8', b'\xe6\xb6\xa8\xe8\xb5\xb0\xe5\xb9\xbb', 
                       b'\xe7\xbb\xbc\xe5\xbe\x97\xe6\xad\xa3\xe5\x88\x86', b'\xe9\xa3\x8e\xe9\x99\xa9\xe8\x93\x9d\xe6\xad\xa3']:
            if label in line:
                bt_label = {b'\xe4\xbb\xb7\xe9\x94\x8b\xe6\x9d\xb8': b'Price', 
                           b'\xe6\xb6\xa8\xe8\xb5\xb0\xe5\xb9\xbb': b'Change', 
                           b'\xe7\xbb\xbc\xe5\xbe\x97\xe6\xad\xa3\xe5\x88\x86': b'Composite', 
                           b'\xe9\xa3\x8e\xe9\x99\xa9\xe8\x93\x9d\xe6\xad\xa3': b'Risk Score'}.get(label, b'')
                if bt_label:
                    lines[i] = line.replace(label, bt_label)
                    fixes_applied.append(f'Line {i+1}: Descriptions label')
    
    # Fix 8: garbled column titles in columns array
    # Check for garbled text inside column title strings
    for garbled, clean in [
        (b'\xe9\x8f\x8f\xe6\x8e\x92\xe5\x90\x8d', b'Rank'),
        (b'\xe4\xbb\xb7\xe4\xb6\x9d\xe7\x92\xb2', b'Code'),
        (b'\xe5\x90\x8e\xe7\xbd\xae\xe2\x84\x83', b'Name'),
        (b'\xe6\xb7\xb1\xe4\xb8\x9a', b'Industry'),
        (b'\xe7\x93\xa1\xe5\x8a\xbf', b'Trend'),
        (b'\xe5\x85\xb1\xe6\x8c\xaf\xe7\x8a\xb6\xe6\x80\x81\xe7\x9b\x98', b'Resonance'),
        (b'\xe7\x93\xa1\xe5\x8a\xbf\xe5\x93\x84\xe5\xae\xb3', b'Strength'),
        (b'\xe9\xa3\x8e\xe9\x99\xa9\xe8\xaf\x84\xe5\x88\x86', b'Risk Score'),
        (b'\xe9\xa3\x8e\xe9\x99\xa9\xe7\xad\x9b\xe9\xaa\x9b', b'Risk Lvl'),
        (b'\xe8\xb4\xa2\xe5\x8a\xa1\xe7\xad\x9b\xe9\xaa\x9b', b'Fin Grade'),
        (b'\xe7\xbb\xbc\xe5\x90\x88\xe5\xbe\x97\xe5\x88\x86', b'Composite'),
        (b'\xe6\x93\x8d\xe4\xbd\x9c\xe5\xbb\xba\xe8\xae\xae', b'Advice'),
        (b'\xe5\x8a\xa0\xe5\x85\xa5\xe8\x87\xaa\xe9\x80\x89', b'Watchlist'),
        (b'\xe6\x8a\x80\xe9\x97\x84\xe9\x9d\xa2', b'Trend'),
        (b'\xe4\xbb\xb7\xe6\xa0\xbc\xe4\xbd\x8d\xe7\xbd\xae', b'Price Pos'),
    ]:
        if garbled in line and b'title:' in line:
            lines[i] = line.replace(garbled, clean)
            # Check if we haven't already logged this
            found = False
            for f in fixes_applied:
                if f'{i+1}' in f and 'column' in f:
                    found = True
                    break
            if not found:
                fixes_applied.append(f'Line {i+1}: column title')
    
    # Fix 9: garbled in "请选择策略" / help section
    if b'\xe9\x80\x89\xe8\x82\xa1\xe7\xad\x9b\xe6\x9e\xb7' in line:
        lines[i] = line.replace(b'\xe9\x80\x89\xe8\x82\xa1\xe7\xad\x9b\xe6\x9e\xb7', b'Selection Strategy')
        fixes_applied.append(f'Line {i+1}: strategy label')
    
    # Fix 10: garbled L0 tag text
    if b'L0:' in line and sum(1 for b in line if b > 127) > 0:
        if b'\xe5\x85\xa8' in line:  # contains "全" garbled variant
            # Find the L0: text area
            tag_start = line.find(b'L0:')
            if tag_start >= 0:
                # Replace after L0: 
                after_l0 = line[tag_start:]
                # Check for template literal
                if b'\x60' in after_l0:
                    # Template literal with totalStockCount
                    pass  # This should be fine as is
                else:
                    fixed = b'L0: All A-shares' + b'}' if b'}' in after_l0 else b'L0: All A-shares'
                    lines[i] = line[:tag_start] + fixed + line[tag_start + len(after_l0):]
                    fixes_applied.append(f'Line {i+1}: L0 tag')
    
    # Fix 11: garbled in modal button text
    if b'\xe6\x9f\xa5\xe7\x9c\x8b\xe5\xb8\xae\xe5\x8a\xa9' in line:
        lines[i] = line.replace(b'\xe6\x9f\xa5\xe7\x9c\x8b\xe5\xb8\xae\xe5\x8a\xa9', b'View Help')
        fixes_applied.append(f'Line {i+1}: help button')
    
    # Fix 12: garbled message.success calls
    if b'message.success' in line and b'\x60' in line and sum(1 for b in line if b > 127) > 0:
        # Has template literal with garbled content
        first_tick = line.find(b'\x60')
        last_tick = line.rfind(b'\x60')
        if first_tick >= 0 and last_tick > first_tick:
            # The content between backticks is garbled, replace it
            content = line[first_tick:last_tick+1]
            new_content = b'"Selection complete"' 
            lines[i] = line[:first_tick] + new_content + line[last_tick+1:]
            fixes_applied.append(f'Line {i+1}: message.success')
    
    # Fix 13: garbled message.info calls  
    if b'message.info' in line and b"'" in line and sum(1 for b in line if b > 127) > 0:
        if b'\xe6\x8f\x90\xe7\xa4\xba\xe6\x96\x87\xe6\x9c\xac' in line:
            lines[i] = b"        message.info('No results found')"
            fixes_applied.append(f'Line {i+1}: message.info')
    
    # Fix 14: garbled message.error calls
    if b'message.error' in line and b"'" in line and sum(1 for b in line if b > 127) > 0:
        lines[i] = b"      message.error('Selection failed')"
        fixes_applied.append(f'Line {i+1}: message.error')
    
    # Fix 15: garbled text in description sections
    if b'<Text type=\"secondary\"' in line and sum(1 for b in line if b > 127) > 0:
        if b'\xe6\x9a\xab\xe6\x97\xa0' in line:
            lines[i] = line.replace(b'\xe6\x9a\xab\xe6\x97\xa0\xe7\x9b\x98\xe5\x89\x8d\xe6\x8f\x90\xe7\xa4\xba\xe6\x95\xb0\xe6\x8d\xae', b'No data')
            fixes_applied.append(f'Line {i+1}: no data text')

# Write back
new_data = b'\n'.join(lines)
with open(fp, 'wb') as f:
    f.write(new_data)
print(f'Written: {len(data)} -> {len(new_data)} bytes')
print(f'Fixes applied:')
for f in fixes_applied:
    print(f'  {f}')
