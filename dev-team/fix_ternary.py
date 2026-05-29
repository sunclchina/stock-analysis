"""Fix multi-line ternary at lines 330-335 in FixedSelectionTab.tsx"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\FixedSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()

# Replace the multi-line ternary with a single-line or properly structured version
old = b'''        {!hasRun ? <Empty description="Click the run button to execute the 5-layer stock selection pipeline" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        : <Table columns={columns} dataSource={results} rowKey="code" loading={loading} size="small" scroll={{ x: 1200 }}
            pagination={{ pageSize: 20, showSizeChanger: true, showQuickJumper: true, pageSizeOptions: ['10', '20', '50'],
                showTotal: (total, range) => `${range[0]}-${range[1]} / ${total} total` }}
            locale={{ emptyText: <Empty description='No stocks matched criteria' /> }} />}'''

new = b'''        {!hasRun ? (
          <Empty description="Click the run button to execute the 5-layer stock selection pipeline" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        ) : (
          <Table columns={columns} dataSource={results} rowKey="code" loading={loading} size="small" scroll={{ x: 1200 }}
            pagination={{ pageSize: 20, showSizeChanger: true, showQuickJumper: true, pageSizeOptions: ['10', '20', '50'],
                showTotal: (total, range) => `${range[0]}-${range[1]} / ${total} total` }}
            locale={{ emptyText: <Empty description='No stocks matched criteria' /> }} />
        )}'''

data = data.replace(old, new)

with open(fp, 'wb') as f:
    f.write(data)
print('Fixed ternary structure')
