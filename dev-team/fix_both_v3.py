"""Fix FixedSelectionTab.tsx - add missing function declaration and fix garbled JSX"""
import os

FP_FIXED = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\FixedSelectionTab.tsx'
FP_CUSTOM = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'

print('=== FixedSelectionTab.tsx ===')
with open(FP_FIXED, 'rb') as f:
    data = f.read()

# Add missing function declaration
data = data.replace(
    b'// K\xe7\xba\xbf\xe6\x95\xb0\xe6\x8d\xae\xe5\x8a\xa0\xe8\xbd\xbd\r\n  const { openHelp } = useHelp();',
    b'const FixedSelectionTab: React.FC = () => {\r\n  const { openHelp } = useHelp();',
)

# Fix garbled layerDescriptions 
old_layer = b'  const layerDescriptions = [\r\n    { name:'
if old_layer in data:
    start = data.find(old_layer)
    end = data.find(b'  ];', start)
    if end > start:
        new_layer = b'''  const layerDescriptions = [
    { name: 'L1', label: 'L1 Base Filter', desc: 'Remove ST/suspended/low-liq/low-price/new stocks' },
    { name: 'L2', label: 'L2 Tech Coarse', desc: '6 light indicators all met' },
    { name: 'L3', label: 'L3 Deep Refine', desc: '3 mandatory + >=2 optional + tech removal' },
    { name: 'L4', label: 'L4 Fin Event', desc: 'Fin safety + no event risk' },
    { name: 'L5', label: 'L5 Composite', desc: 'Score >=85 + capacity control' },
  ];'''
        data = data[:start] + new_layer + data[end+4:]

# Fix garbled message calls
for old, new in [
    (b"message.info('\xe6\x8f\x90\xe7\xa4\xba\xe6\x96\x87\xe6\x9c\xac')", b"message.info('Processing complete')"),
    (b"message.error('\xe6\x8f\x90\xe7\xa4\xba\xe6\x96\x87\xe6\x9c\xac')", b"message.error('Operation failed')"),
    (b"message.warning('\xe6\x8f\x90\xe7\xa4\xba\xe6\x96\x87\xe6\x9c\xac')", b"message.warning('Please check your input')"),
]:
    while new in data:
        pass  # Prevent double-apply
    data = data.replace(old, new)

# Fix JSX issues
for old, new in [
    (b'<Tooltip title="\xe7\x82\xb9\xe5\x87\xbb\xe5\x88\x86\xe9\xa1\xb5\xe8\xa1\xa8\xe6\x8e\x92\xe5\xba\x8f">', b'<Tooltip title="Click to sort column">'),
    (b'\xe5\xaf\xbc\xe5\x87\xbaCSV', b'Export CSV'),
    (b'\xe9\x87\x8d\xe6\x96\xb0\xe9\x80\x89\xe8\x82\xa1', b'Rerun Selection'),
    (b'\xe4\xb8\x80\xe9\x94\xae\xe8\xbf\x90\xe8\xa1\x8c\xe9\x80\x89\xe8\x82\xa1', b'Run Selection'),
    (b'\xe9\x80\x89\xe8\x82\xa1\xe7\xbb\x93\xe6\x9e\x9c', b'Selection Results'),
]:
    while new in data:
        pass
    data = data.replace(old, new)

# Fix broken closing tags
data = data.replace(b'?/Text>', b'</Text>')
data = data.replace(b'?/Tag>', b'</Tag>')

with open(FP_FIXED, 'wb') as f:
    f.write(data)
print(f'Fixed. {len(data)} bytes')

print('\n=== CustomSelectionTab.tsx ===')
with open(FP_CUSTOM, 'rb') as f:
    data = f.read()

# Fix broken closing tags
data = data.replace(b'?/Text>', b'</Text>')
data = data.replace(b'?/Tag>', b'</Tag>')
data = data.replace(b'?/Space>', b'</Space>')

# Fix garbled message calls
for old, new in [
    (b"message.info('\xe6\x8f\x90\xe7\xa4\xba\xe6\x96\x87\xe6\x9c\xac')", b"message.info('Done')"),
    (b"message.error('\xe6\x8f\x90\xe7\xa4\xba\xe6\x96\x87\xe6\x9c\xac')", b"message.error('Error')"),
]:
    data = data.replace(old, new)

# Fix garbled column titles
for garbled, clean in [
    (b'\xe5\x85\xb1\xe6\x8c\xaf\xe7\x8a\xb6\xe6\x80\x81', b'Resonance Status'),
    (b'\xe9\xa3\x8e\xe9\x99\xa9\xe8\xaf\x84\xe5\x88\x86', b'Risk Score'),
    (b'\xe9\xa3\x8e\xe9\x99\xa9\xe7\xad\x9b\xe9\xaa\x87', b'Risk Level'),
    (b'\xe8\xb4\xa2\xe5\x8a\xa1\xe7\xad\x9b\xe9\xaa\x87', b'Finance Grade'),
    (b'\xe7\xbb\xbc\xe5\x90\x88\xe5\xbe\x97\xe5\x88\x86', b'Composite Score'),
]:
    data = data.replace(garbled, clean)

# Fix unclosed placeholder quotes
idx = 0
while True:
    idx = data.find(b'placeholder="', idx)
    if idx < 0:
        break
    next_q = data.find(b'"', idx + 14)
    if next_q < 0 or next_q > idx + 80:
        # Missing closing quote - find the next separator
        for sep in [b' />', b'/>', b' style=', b'}']:
            si = data.find(sep, idx + 14)
            if 0 < si < idx + 60:
                data = data[:si] + b'"' + data[si:]
                break
    idx = idx + 14

with open(FP_CUSTOM, 'wb') as f:
    f.write(data)
print(f'Fixed. {len(data)} bytes')
