import React from 'react';
import { Row, Col, Spin, Typography, Tooltip } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined, MinusOutlined } from '@ant-design/icons';
import type { MarketIndex } from '../../types/market';

const { Text } = Typography;

interface MarketOverviewProps {
  indices: MarketIndex[];
  loading: boolean;
}

function changeColor(v: number): string {
  if (v > 0) return '#cf1322';
  if (v < 0) return '#389e0d';
  return '#8c8c8c';
}

function changeIcon(v: number) {
  if (v > 0) return <ArrowUpOutlined style={{ color: '#cf1322', fontSize: 10 }} />;
  if (v < 0) return <ArrowDownOutlined style={{ color: '#389e0d', fontSize: 10 }} />;
  return <MinusOutlined style={{ color: '#8c8c8c', fontSize: 10 }} />;
}

const MarketOverview: React.FC<MarketOverviewProps> = ({ indices, loading }) => {
  if (loading && indices.length === 0) {
    return <div style={{ textAlign: 'center', padding: 16 }}><Spin size="small" /></div>;
  }
  if (indices.length === 0) {
    return <div style={{ textAlign: 'center', padding: 16 }}><Text type="secondary">暂无大盘指数数据</Text></div>;
  }

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fill, minmax(170px, 1fr))',
      gap: 8,
    }}>
      {indices.map((idx) => {
        const color = changeColor(idx.changePercent);
        return (
          <Tooltip
            key={idx.code}
            title={
              <div style={{ fontSize: 12, lineHeight: 1.8 }}>
                <div>开盘 {idx.openPrice.toFixed(2)}</div>
                <div>最高 {idx.high.toFixed(2)}</div>
                <div>最低 {idx.low.toFixed(2)}</div>
                <div>昨收 {idx.prevClose.toFixed(2)}</div>
                <div>成交量 {(idx.volume / 1e8).toFixed(2)}亿</div>
                <div>成交额 {(idx.amount / 1e8).toFixed(2)}亿</div>
              </div>
            }
            placement="bottom"
          >
            <div style={{
              background: idx.changePercent > 0 ? '#fff1f0' : idx.changePercent < 0 ? '#f6ffed' : '#fafafa',
              borderRadius: 6,
              padding: '8px 12px',
              borderLeft: `3px solid ${color}`,
              cursor: 'pointer',
              transition: 'all 0.15s',
            }}
              onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.boxShadow = '0 1px 4px rgba(0,0,0,0.08)'; }}
              onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.boxShadow = 'none'; }}
            >
              <div style={{ fontSize: 12, color: '#666', marginBottom: 2 }}>{idx.name}</div>
              <div style={{ fontSize: 18, fontWeight: 700, color, lineHeight: 1.3 }}>{idx.latestPrice.toFixed(2)}</div>
              <div style={{ fontSize: 11, color, display: 'flex', gap: 6, alignItems: 'center' }}>
                {changeIcon(idx.changePercent)}
                <span>{idx.change > 0 ? '+' : ''}{idx.change.toFixed(2)}</span>
                <span>{idx.changePercent > 0 ? '+' : ''}{idx.changePercent.toFixed(2)}%</span>
              </div>
            </div>
          </Tooltip>
        );
      })}
    </div>
  );
};

export default MarketOverview;
