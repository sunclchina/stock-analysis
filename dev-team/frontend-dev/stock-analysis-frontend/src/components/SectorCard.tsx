/**
 * 板块排行卡片 — 完全匹配大盘概览风格
 */
import React from 'react';
import { Card, Spin, Typography, Tooltip, Empty } from 'antd';

const { Text } = Typography;

interface SectorItem {
  name: string;
  avg_change_pct: number;
  leading_stock?: string;
  leading_stock_change?: number;
}

interface SectorCardProps {
  title: string;
  items: SectorItem[];
  loading?: boolean;
  emptyText?: string;
}

const pctColor = (v: number | undefined | null) => v == null ? '#8c8c8c' : v > 0 ? '#cf1322' : v < 0 ? '#389e0d' : '#8c8c8c';

const SectorCard: React.FC<SectorCardProps> = ({ title, items, loading, emptyText }) => {
  if (loading) {
    return (
      <Card size="small" style={{ borderRadius: 8, height: '100%' }}
        title={<span style={{ fontSize: 14, fontWeight: 700 }}>{title}</span>}
      >
        <div style={{ textAlign: 'center', padding: 20 }}><Spin size="small" /></div>
      </Card>
    );
  }

  return (
    <Card size="small" style={{ borderRadius: 8, height: '100%' }}
      title={<span style={{ fontSize: 14, fontWeight: 700 }}>{title}</span>}
    >
      {items.length === 0 ? (
        <div style={{ padding: '16px 0' }}>
          <Empty description={emptyText || '暂无数据'} image={Empty.PRESENTED_IMAGE_SIMPLE} />
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {items.slice(0, 10).map((item, i) => {
            const color = pctColor(item.avg_change_pct);
            return (
              <Tooltip key={i} title={
                item.leading_stock
                  ? `领涨: ${item.leading_stock} ${(item.leading_stock_change ?? 0) > 0 ? '+' : ''}${(item.leading_stock_change ?? 0).toFixed(2)}%`
                  : undefined
              }>
                <div style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '5px 8px', borderRadius: 4, cursor: 'default',
                  background: item.avg_change_pct > 0 ? '#fff1f0' : item.avg_change_pct < 0 ? '#f6ffed' : '#fafafa',
                }}>
                  <span>
                    <span style={{ color: i < 3 ? color : '#bbb', fontWeight: 700, marginRight: 6, fontSize: 12 }}>{i + 1}</span>
                    <span style={{ fontSize: 12, color: '#666' }}>{item.name}</span>
                  </span>
                  <span style={{ fontSize: 12, color, fontWeight: 700 }}>
                    {item.avg_change_pct != null ? (item.avg_change_pct > 0 ? '+' : '') + item.avg_change_pct.toFixed(2) + '%' : '—'}
                  </span>
                </div>
              </Tooltip>
            );
          })}
        </div>
      )}
    </Card>
  );
};

export default SectorCard;
