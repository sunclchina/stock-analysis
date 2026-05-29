import React, { useState, useMemo, useCallback } from 'react';
import {
  Card,
  Table,
  Input,
  Select,
  Tag,
  Typography,
  Space,
  Tooltip,
  Button,
  Empty,
  Row,
  Col,
  Spin,
} from 'antd';
import {
  ArrowUpOutlined,
  ArrowDownOutlined,
  MinusOutlined,
  SearchOutlined,
  StarOutlined,
  FilterOutlined,
  ReloadOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import type { ColumnsType, TablePaginationConfig } from 'antd/es/table';
import type { StockQuote, TradingAnomaly } from '../../types/market';

const { Text } = Typography;

interface StockQuoteTableProps {
  quotes: StockQuote[];
  loading: boolean;
  filter: { keyword: string; tag: string };
  onFilterChange: (filter: { keyword: string; tag: string }) => void;
  onRefresh: () => void;
  onOpenDetail: (code: string) => void;
}

/** Color helpers */
function changeColor(changePercent: number): string {
  if (changePercent > 0) return '#cf1322';
  if (changePercent < 0) return '#389e0d';
  return '#8c8c8c';
}

function changeBg(changePercent: number): string {
  if (changePercent > 0) return '#fff1f0';
  if (changePercent < 0) return '#f6ffed';
  return '#f5f5f5';
}

function changeIcon(changePercent: number) {
  if (changePercent > 0) return <ArrowUpOutlined style={{ color: '#cf1322' }} />;
  if (changePercent < 0) return <ArrowDownOutlined style={{ color: '#389e0d' }} />;
  return <MinusOutlined style={{ color: '#8c8c8c' }} />;
}

/** 格式化大数字 */
function formatVolume(v: number): string {
  if (v >= 100000000) return (v / 100000000).toFixed(2) + '亿';
  if (v >= 10000) return (v / 10000).toFixed(2) + '万';
  return v.toFixed(0);
}

function formatAmount(v: number): string {
  if (v >= 100000000) return (v / 100000000).toFixed(2) + '亿';
  if (v >= 10000) return (v / 10000).toFixed(0) + '万';
  return v.toFixed(0);
}

/** 实时行情表格 */
const StockQuoteTable: React.FC<StockQuoteTableProps> = ({
  quotes,
  loading,
  filter,
  onFilterChange,
  onRefresh,
  onOpenDetail,
}) => {
  const [searchValue, setSearchValue] = useState(filter.keyword);

  // Filtered data（排序交由 Ant Design Table 内部处理，先按 code 去重）
  const filteredData = useMemo(() => {
    const seen = new Set<string>();
    let data = [...quotes].filter((q) => {
      if (!q?.code || seen.has(q.code)) return false;
      seen.add(q.code);
      return true;
    });

    if (filter.keyword) {
      const kw = filter.keyword.toLowerCase();
      data = data.filter(
        (q) =>
          (q.code || '').toLowerCase().includes(kw) ||
          (q.name || '').toLowerCase().includes(kw)
      );
    }

    return data;
  }, [quotes, filter]);

  // Search handler
  const handleSearch = useCallback((value: string) => {
    setSearchValue(value);
    onFilterChange({ ...filter, keyword: value });
  }, [filter, onFilterChange]);

  // Tag change handler
  const handleTagChange = useCallback((value: string) => {
    onFilterChange({ ...filter, tag: value });
  }, [filter, onFilterChange]);

  // ========== Columns ==========
  const columns: ColumnsType<StockQuote> = [
    {
      title: '代码',
      dataIndex: 'code',
      key: 'code',
      width: 90,
      sorter: (a: StockQuote, b: StockQuote) => (a.code ?? '').localeCompare(b.code ?? ''),
      render: (code: string) => (
        <Text code style={{ fontSize: 15, fontWeight: 700 }}>{code}</Text>
      ),
    },
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      width: 100,
      sorter: (a: StockQuote, b: StockQuote) => (a.name ?? '').localeCompare(b.name ?? ''),
      render: (name: string) => (
        <Text style={{ fontSize: 13, fontWeight: 500 }}>{name}</Text>
      ),
    },
    {
      title: '最新价',
      dataIndex: 'latestPrice',
      key: 'price',
      width: 100,
      sorter: (a: StockQuote, b: StockQuote) => (a.latestPrice ?? 0) - (b.latestPrice ?? 0),
      align: 'right',
      render: (price: number, record: StockQuote) => (
        <Text
          style={{
            fontSize: 14,
            fontWeight: 600,
            color: changeColor(record.changePercent),
          }}
        >
          {price.toFixed(2)}
        </Text>
      ),
    },
    {
      title: '涨跌幅',
      dataIndex: 'changePercent',
      key: 'changePercent',
      width: 100,
      sorter: (a: StockQuote, b: StockQuote) => (a.changePercent ?? 0) - (b.changePercent ?? 0),
      align: 'right',
      render: (percent: number, record: StockQuote) => (
        <Tag
          color={percent > 0 ? 'red' : percent < 0 ? 'green' : 'default'}
          style={{
            fontSize: 12,
            fontWeight: 600,
            padding: '0 6px',
            lineHeight: '22px',
            minWidth: 60,
            textAlign: 'center',
          }}
        >
          {changeIcon(percent)}
          {' '}
          {percent > 0 ? '+' : ''}{percent.toFixed(2)}%
        </Tag>
      ),
    },
    {
      title: '涨跌额',
      dataIndex: 'change',
      key: 'change',
      width: 80,
      sorter: (a: StockQuote, b: StockQuote) => (a.change ?? 0) - (b.change ?? 0),
      align: 'right',
      render: (change: number) => (
        <Text style={{ fontSize: 12, color: changeColor(change) }}>
          {change > 0 ? '+' : ''}{change.toFixed(2)}
        </Text>
      ),
    },
    {
      title: '成交量',
      dataIndex: 'volume',
      key: 'volume',
      width: 100,
      sorter: (a: StockQuote, b: StockQuote) => (a.volume ?? 0) - (b.volume ?? 0),
      align: 'right',
      render: (vol: number) => (
        <Text style={{ fontSize: 12 }}>{formatVolume(vol)}</Text>
      ),
    },
    {
      title: '成交额',
      dataIndex: 'amount',
      key: 'amount',
      width: 100,
      sorter: (a: StockQuote, b: StockQuote) => (a.amount ?? 0) - (b.amount ?? 0),
      align: 'right',
      render: (amt: number) => (
        <Text style={{ fontSize: 12 }}>{formatAmount(amt)}</Text>
      ),
    },
    {
      title: '换手率',
      dataIndex: 'turnoverRate',
      key: 'turnoverRate',
      width: 80,
      sorter: (a: StockQuote, b: StockQuote) => (a.turnoverRate ?? 0) - (b.turnoverRate ?? 0),
      align: 'right',
      render: (rate: number) => (
        <Text style={{ fontSize: 12 }}>
          {rate && rate > 0 ? rate.toFixed(2) + '%' : '-'}
        </Text>
      ),
    },
    {
      title: '趋势',
      key: 'trend',
      width: 50,
      align: 'center',
      render: (_: unknown, record: StockQuote) => {
        const color = record.trendColor === 'red' ? '#cf1322' : record.trendColor === 'green' ? '#389e0d' : '#8c8c8c';
        const icon = record.trendColor === 'red' ? <ArrowUpOutlined /> : record.trendColor === 'green' ? <ArrowDownOutlined /> : <MinusOutlined />;
        return <span style={{ color, fontSize: 16 }}>{icon}</span>;
      },
    },
    {
      title: '交易异动',
      key: 'anomalies',
      width: 140,
      align: 'left',
      render: (_: unknown, record: StockQuote) => {
        const anomalies = record.anomalies;
        if (!anomalies || anomalies.length === 0) return null;
        // 最多显示3个异动，优先显示利好
        const sorted = [...anomalies].sort((a, b) => {
          const order = { bullish: 0, neutral: 1, bearish: 2 };
          return (order[a.type] ?? 1) - (order[b.type] ?? 1);
        });
        const display = sorted.slice(0, 3);
        return (
          <Space size={2} wrap>
            {display.map((a) => {
              const isBullish = a.type === 'bullish';
              const isBearish = a.type === 'bearish';
              return (
                <Tag
                  key={a.id}
                  color={isBullish ? 'green' : isBearish ? 'red' : 'default'}
                  style={{
                    fontSize: 11,
                    lineHeight: '18px',
                    padding: '0 4px',
                    margin: 0,
                    borderRadius: 3,
                  }}
                >
                  {a.name}
                </Tag>
              );
            })}
            {anomalies.length > 3 && (
              <Text type="secondary" style={{ fontSize: 10 }}>+{anomalies.length - 3}</Text>
            )}
          </Space>
        );
      },
    },
    {
      title: '操作',
      key: 'action',
      width: 60,
      align: 'center',
      fixed: 'right',
      render: (_: unknown, record: StockQuote) => (
        <Tooltip title="查看详情">
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={(e) => { e.stopPropagation(); onOpenDetail(record.code); }}
          />
        </Tooltip>
      ),
    },
  ];

  return (
    <Card
      size="small"
      style={{ borderRadius: 8 }}
      bodyStyle={{ padding: 0 }}
      title={
        <Space>
          <EyeOutlined style={{ color: '#1677ff', fontSize: 16 }} />
          <span style={{ fontSize: 16, fontWeight: 700, color: '#262626' }}>实时行情</span>
          <Tag>{filteredData.length} 只</Tag>
          {loading && <Spin size="small" style={{ marginLeft: 4 }} />}
        </Space>
      }
      extra={
        <Button size="small" shape="round" icon={<ReloadOutlined />} onClick={onRefresh} type="primary" ghost>
          刷新
        </Button>
      }
    >
      {/* Filter bar */}
      <div style={{ padding: '8px 12px', borderBottom: '1px solid var(--border-color, #f0f0f0)' }}>
        <Row gutter={[12, 8]} align="middle">
          <Col xs={24} sm={12} md={8}>
            <Space>

            </Space>
          </Col>
          <Col xs={24} sm={12} md={8}>
            <Input.Search
              placeholder="搜索代码/名称..."
              value={searchValue}
              onChange={(e) => setSearchValue(e.target.value)}
              onSearch={handleSearch}
              enterButton={<SearchOutlined />}
              size="small"
              allowClear
              onClear={() => handleSearch('')}
            />
          </Col>
          <Col xs={24} sm={12} md={8}>
            <Space>
              <StarOutlined style={{ color: '#faad14' }} />
              <Text type="secondary" style={{ fontSize: 12 }}>
                点击名称查看个股详情
              </Text>
            </Space>
          </Col>
        </Row>
      </div>

      {/* Table — 不使用 loading 遮罩避免闪烁，改用标题栏 Spin 提示 */}
      <Table<StockQuote>
        columns={columns}
        dataSource={filteredData}
        rowKey="code"
        loading={false}
        size="small"
        scroll={{ x: 800 }}
        pagination={{
          pageSize: 30,
          showSizeChanger: true,
          pageSizeOptions: ['20', '30', '50', '100'],
          showTotal: (total, range) => `${range[0]}-${range[1]} / 共 ${total} 只`,
          size: 'small',
        }}
        locale={{
          emptyText: <Empty description="暂无行情数据" />,
        }}
        onRow={(record) => ({
          onClick: () => onOpenDetail(record.code),
          style: {
            cursor: 'pointer',
            transition: 'background 0.2s',
          },
          onMouseEnter: (e) => {
            (e.currentTarget as HTMLElement).style.background = 'rgba(0,0,0,0.02)';
          },
          onMouseLeave: (e) => {
            (e.currentTarget as HTMLElement).style.background = '';
          },
        })}
      />
    </Card>
  );
};

export default StockQuoteTable;
