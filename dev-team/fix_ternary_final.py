"""Fix ternary structure properly"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    lines = f.read().split(b'\n')

# Replace lines 1118-1131 with proper structure
new_lines = [
    b'            {!hasRun ? (',
    b'              <Empty description="Configure dimensions and run selection" image={Empty.PRESENTED_IMAGE_SIMPLE} />',
    b'            ) : (',
    b'              <Table',
    b'                columns={columns}',
    b'                dataSource={results}',
    b'                rowKey="code"',
    b'                loading={loading}',
    b'                size="small"',
    b'                scroll={{ x: 1200 }}',
    b'                pagination={{',
    b'                  pageSize: 20, showSizeChanger: true, showQuickJumper: true,',
    b"                  pageSizeOptions: ['10', '20', '50'],",
    b'                  showTotal: (total, range) => `${range[0]}-${range[1]} / ${total} total` },',
    b'                }}',
    b'                locale={{ emptyText: <Empty description="No stocks matched" /> }}',
    b'              />',
    b'            )}',
]

old_lines = [
    b'            {!hasRun ? (',
    b'              <Empty description="Configure dimensions and run selection" image={Empty.PRESENTED_IMAGE_SIMPLE} />',
    b'                loading={loading} ) : (',
    b'              <Table',
    b'                size="small"',
    b'                scroll={{ x: 1200 }}',
    b'                pagination={{',
    b'                  pageSize: 20, showSizeChanger: true, showQuickJumper: true,',
    b"                  pageSizeOptions: ['10', '20', '50'],",
    b'                  showTotal: (total, range) => `${range[0]}-${range[1]} / ${total} total` },',
    b'                }}',
    b'                locale={{ emptyText: <Empty description="No stocks matched" /> }}',
    b'              />',
    b'            )}',
]

# Find the range to replace
start_idx = None
for i in range(len(lines)):
    if lines[i] == old_lines[0]:
        start_idx = i
        break

if start_idx:
    end_idx = start_idx + len(old_lines)
    # Add \r to each line
    new_with_cr = [line + b'\r' for line in new_lines]
    # Last line might not need \r
    new_with_cr[-1] = new_lines[-1] + b'\r' if not new_lines[-1].endswith(b'\r') else new_lines[-1]
    
    lines[start_idx:end_idx] = new_with_cr
    print(f'Replaced lines {start_idx+1} to {end_idx}')
else:
    print('Could not find exact pattern, trying to replace by position')
    # Replace by line number
    lines[1117:1132] = [line + b'\r' if not line.endswith(b'\r') else line for line in new_lines]

with open(fp, 'wb') as f:
    f.write(b'\n'.join(lines))
print('Done')
