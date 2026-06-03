/**
 * 板块行情 — 行业/概念板块涨跌幅排行，双栏布局
 */
import React from 'react';
import { Typography, Row, Col, Spin, Space, Tooltip } from 'antd';
import { FundOutlined } from '@ant-design/icons';

const { Text } = Typography;

interface SectorItem {
  name: string;
  avg_change_pct: number;
  leading_stock?: string;
  leading_stock_price?: number;
  leading_stock_change?: number;
}

interface SectorRankingProps {
  industries: SectorItem[];
  concepts: SectorItem[];
  loading?: boolean;
}

const SectorList: React.FC<{ items: SectorItem[]; emptyText?: string }> = ({ items, emptyText }) => {
  if (items.length === 0) {
    return <div style={{ padding: '8px 0', textAlign: 'center' }}><Text type="secondary" style={{ fontSize: 11 }}>{emptyText || '暂无数据'}</Text></div>;
  }
  return (
    <div>
      {items.slice(0, 5).map((item, i) => {
        const color = item.avg_change_pct > 0 ? '#cf1322' : item.avg_change_pct < 0 ? '#389e0d' : '#8c8c8c';
        return (
          <Tooltip
            key={i}
            title={
              item.leading_stock
                ? `领涨: ${item.leading_stock} ${(item.leading_stock_change ?? 0) > 0 ? '+' : ''}${(item.leading_stock_change ?? 0).toFixed(2)}%`
                : undefined
            }
          >
            <div style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '2px 4px', borderRadius: 4, fontSize: 12,
              cursor: 'default',
            }}
              onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = '#f5f5f5'; }}
              onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
            >
              <Space size={6}>
                <span style={{
                  width: 14, textAlign: 'center', fontWeight: 700,
                  color: i < 3 ? (item.avg_change_pct > 0 ? '#cf1322' : '#389e0d') : '#bbb',
                  fontSize: 11,
                }}>{i + 1}</span>
                <Text ellipsis style={{ maxWidth: 100, fontSize: 12 }}>{item.name}</Text>
              </Space>
              <span style={{ color, fontWeight: 600, fontSize: 12 }}>
                {item.avg_change_pct > 0 ? '+' : ''}{item.avg_change_pct.toFixed(2)}%
              </span>
            </div>
          </Tooltip>
        );
      })}
    </div>
  );
};

const SectorRanking: React.FC<SectorRankingProps> = ({ industries, concepts, loading }) => {
  if (loading) {
    return <div style={{ textAlign: 'center', padding: 8 }}><Spin size="small" /></div>;
  }

  const hasData = industries.length > 0 || concepts.length > 0;
  if (!hasData) return null;

  return (
    <div style={{ borderTop: '1px solid #f0f0f0', padding: '4px 0 0' }}>
      <Row gutter={16}>
        <Col span={12}>
          <div style={{ fontSize: 11, color: '#999', marginBottom: 2, fontWeight: 600 }}>
            <FundOutlined /> 行业板块 TOP5
          </div>
          <SectorList items={industries} emptyText="暂无行业数据" />
        </Col>
        <Col span={12}>
          <div style={{ fontSize: 11, color: '#999', marginBottom: 2, fontWeight: 600 }}>
            <FundOutlined /> 概念板块 TOP5
          </div>
          <SectorList items={concepts} emptyText="暂无概念数据" />
        </Col>
      </Row>
    </div>
  );
};

export default SectorRanking;
