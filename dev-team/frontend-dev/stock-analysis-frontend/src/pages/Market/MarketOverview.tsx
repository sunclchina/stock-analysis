/**
 * 大盘概览卡片（左侧） — 指数预览 + 涨跌分布
 */
import React from 'react';
import { Card, Spin, Typography, Tooltip } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined, MinusOutlined } from '@ant-design/icons';
import type { MarketIndex } from '../../types/market';

const { Text } = Typography;

interface MarketOverviewProps {
  indices: MarketIndex[];
  loading: boolean;
  advDecl: {
    up: number; down: number; flat: number; total: number;
    limit_up: number; limit_down: number;
  } | null;
}

const sf = (v: number | null | undefined, d = 2) => v != null ? v.toFixed(d) : '—';
const fmt = (n: number) => (n ?? 0).toLocaleString();
const pctColor = (v: number) => v > 0 ? '#cf1322' : v < 0 ? '#389e0d' : '#8c8c8c';

const MarketOverview: React.FC<MarketOverviewProps> = ({ indices, loading, advDecl }) => {
  if (loading && indices.length === 0) {
    return <Card size="small" style={{ borderRadius: 8, height: '100%' }}>
      <div style={{ textAlign: 'center', padding: 20 }}><Spin /></div>
    </Card>;
  }

  return (
    <Card size="small" style={{ borderRadius: 8, height: '100%' }}
      title={<span style={{ fontSize: 14, fontWeight: 700 }}>大盘概览</span>}
    >
      {/* 指数预览 */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {indices.map((idx) => {
          const color = pctColor(idx.changePercent);
          return (
            <Tooltip key={idx.code} title={
              <div style={{ fontSize: 12, lineHeight: 1.8 }}>
                开 {sf(idx.openPrice)} 高 {sf(idx.high)} 低 {sf(idx.low)}<br />
                昨收 {sf(idx.prevClose)} 量 {sf(idx.volume / 1e8, 0)}亿 额 {sf(idx.amount / 1e8, 0)}亿
              </div>
            }>
              <div style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '5px 8px', borderRadius: 4, cursor: 'default',
                background: idx.changePercent > 0 ? '#fff1f0' : idx.changePercent < 0 ? '#f6ffed' : '#fafafa',
              }}>
                <div style={{ fontSize: 12, color: '#666', minWidth: 50 }}>{idx.name}</div>
                <div style={{ fontSize: 14, fontWeight: 700, color, minWidth: 70, textAlign: 'right' }}>{sf(idx.latestPrice)}</div>
                <div style={{ fontSize: 12, color, minWidth: 60, textAlign: 'right' }}>
                  {idx.changePercent > 0 ? <ArrowUpOutlined /> : idx.changePercent < 0 ? <ArrowDownOutlined /> : <MinusOutlined />}
                  {' '}{idx.changePercent > 0 ? '+' : ''}{sf(idx.changePercent)}%
                </div>
              </div>
            </Tooltip>
          );
        })}
      </div>

      {/* 涨跌分布 */}
      {advDecl && advDecl.total > 0 && (
        <div style={{
          borderTop: '1px solid #f0f0f0', marginTop: 8, paddingTop: 6,
          display: 'flex', flexWrap: 'wrap', gap: '4px 8px', justifyContent: 'center',
          fontSize: 12,
        }}>
          <span><span style={{ color: '#cf1322', fontWeight: 700 }}>↑</span> 上涨 <b style={{ color: '#cf1322' }}>{fmt(advDecl.up)}</b></span>
          <span style={{ color: '#d9d9d9' }}>|</span>
          <span><span style={{ color: '#8c8c8c', fontWeight: 700 }}>—</span> 平盘 <b>{fmt(advDecl.flat)}</b></span>
          <span style={{ color: '#d9d9d9' }}>|</span>
          <span><span style={{ color: '#389e0d', fontWeight: 700 }}>↓</span> 下跌 <b style={{ color: '#389e0d' }}>{fmt(advDecl.down)}</b></span>
          <span style={{ color: '#d9d9d9' }}>|</span>
          <span>涨停 <b style={{ color: '#cf1322' }}>{advDecl.limit_up}</b></span>
          <span>跌停 <b style={{ color: '#389e0d' }}>{advDecl.limit_down}</b></span>
        </div>
      )}
    </Card>
  );
};

export default MarketOverview;
