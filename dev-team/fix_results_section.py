"""Restructure the entire table section to avoid brace issues"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()
lines = data.split(b'\n')

# Find the results section and replace it with a simpler version
# Lines 1115-1135
new_section = [
    b'              ) : null',
    b'            }',
    b'          >',
    b'            {!hasRun ? <Empty description="Configure dimensions and run selection" image={Empty.PRESENTED_IMAGE_SIMPLE} />',
    b'            : <Table',
    b'                columns={columns}',
    b'                dataSource={results}',
    b'                rowKey="code"',
    b'                loading={loading}',
    b'                size="small"',
    b'                scroll={{ x: 1200 }}',
    b'                pagination={{pageSize: 20, showSizeChanger: true, showQuickJumper: true, pageSizeOptions: ["10", "20", "50"], showTotal: (total, range) => BACKTICK{range[0]}-{range[1]} / {total} totalBACKTICK}}',
    b'                locale={{emptyText: <Empty description="No stocks matched" />}}',
    b'              />}',
]

# Add \r to each line, replace BACKTICK with actual backtick
new_section_bytes = []
for line in new_section:
    line = line.replace(b'BACKTICK', b'\x60')
    if not line.endswith(b'\r'):
        # Check if it should end with \r
        new_section_bytes.append(line + b'\r')
    else:
        new_section_bytes.append(line)
# Don't add \r to the last line if it would create issues
new_section_bytes[-1] = new_section_bytes[-1].rstrip(b'\r')

# Replace lines 1115-1135 (0-indexed 1114-1134)
start = 1114
end = 1135  # exclusive
if end <= len(lines):
    lines[start:end] = new_section_bytes
    new_data = b'\n'.join(lines)
    with open(fp, 'wb') as f:
        f.write(new_data)
    print(f'Replaced lines {start+1} to {end} with simplified version')
else:
    print(f'Cannot replace: file has {len(lines)} lines, need up to {end}')
