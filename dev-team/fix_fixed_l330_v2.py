"""Replace entire line 330 with clean content"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\FixedSelectionTab.tsx'
with open(fp, 'rb') as f:
    lines = f.read().split(b'\n')

# Line 330 (0-indexed 329)
old_line = lines[329]
print(f'Line 330 was: {repr(old_line[:60])}')

# Replace the ENTIRE line with clean content
lines[329] = b'        {!hasRun ? <Empty description="Click Run to execute the 5-layer stock selection pipeline" image={Empty.PRESENTED_IMAGE_SIMPLE} />'

new_data = b'\n'.join(lines)
with open(fp, 'wb') as f:
    f.write(new_data)
print(f'Line 330 now: {repr(lines[329][:60])}')
print('Fixed!')
