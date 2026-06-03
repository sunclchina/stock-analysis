/**
 * 涨跌分布 — 紧凑横条样式
 * 展示全市场上涨/平盘/下跌家数 + 涨停/跌停，一行内显示。
 */
import React from 'react';
import { Typography, Space, Spin } from 'antd';
import { RiseOutlined, FallOutlined, MinusOutlined } from '@ant-design/icons';

const { Text } = Typography;

interface AdvanceDeclineProps {
  data: {
    up: number;
    down: number;
    flat: number;
    total: number;
    limit_up: number;
    limit_down: number;
  } | null;
  loading?: boolean;
}

const fmt = (n: number) => n.toLocaleString();

const AdvanceDeclineCard: React.FC<AdvanceDeclineProps> = ({ data, loading }) => {
  if (loading) {
    return <div style={{ textAlign: 'center', padding: '6px 0' }}><Spin size="small" /></div>;
  }
  if (!data || data.total === 0) {
    return null;
  }

  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 16,
      padding: '6px 0', flexWrap: 'wrap',
    }}>
      <Space size={4}>
        <RiseOutlined style={{ color: '#cf1322', fontSize: 11 }} />
        <Text style={{ color: '#cf1322', fontWeight: 700, fontSize: 13 }}>上涨 {fmt(data.up)}</Text>
      </Space>

      <Space size={4}>
        <MinusOutlined style={{ color: '#8c8c8c', fontSize: 11 }} />
        <Text style={{ color: '#8c8c8c', fontWeight: 600, fontSize: 13 }}>平盘 {fmt(data.flat)}</Text>
      </Space>

      <Space size={4}>
        <FallOutlined style={{ color: '#389e0d', fontSize: 11 }} />
        <Text style={{ color: '#389e0d', fontWeight: 700, fontSize: 13 }}>下跌 {fmt(data.down)}</Text>
      </Space>

      <div style={{
        width: 1, height: 16, background: '#e8e8e8', margin: '0 4px',
      }} />

      <Space size={4}>
        <span style={{ color: '#cf1322', fontSize: 11 }}>涨停</span>
        <Text style={{ color: '#cf1322', fontWeight: 700, fontSize: 13 }}>{data.limit_up}</Text>
      </Space>

      <Space size={4}>
        <span style={{ color: '#389e0d', fontSize: 11 }}>跌停</span>
        <Text style={{ color: '#389e0d', fontWeight: 700, fontSize: 13 }}>{data.limit_down}</Text>
      </Space>

      <Text type="secondary" style={{ fontSize: 11 }}>
        共 {fmt(data.total)} 只
      </Text>
    </div>
  );
};

export default AdvanceDeclineCard;
