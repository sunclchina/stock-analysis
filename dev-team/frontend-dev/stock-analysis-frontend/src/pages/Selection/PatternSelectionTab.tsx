/**
 * M04 智能选股 - 形态选股标签页
 * 从股票池中扫描符合K线形态的股票。
 * 支持多种形态：均线多头排列、金叉、放量突破、回踩支撑等。
 */
import React, { useState } from 'react';
import { Table, Button, Space, message, Card, Tag, Select, Radio, Typography, Row, Col } from 'antd';
import { BranchesOutlined, SearchOutlined } from '@ant-design/icons';
import apiClient from '../../services/api';
// 简单名称单元格（带K线悬浮，直接复用MarketResearch同名组件逻辑）
const StockNameCell: React.FC<{ name: string; code: string; children?: React.ReactNode }> = ({ name, code, children }) => (
  <span style={{ cursor: 'pointer', borderBottom: '1px dashed #d9d9d9' }}>{children || `${name}(${code})`}</span>
);

const { Text } = Typography;

const PATTERN_OPTIONS = [
  { value: 'ma_bullish', label: '均线多头排列', desc: 'MA5 > MA10 > MA20 > MA60' },
  { value: 'golden_cross', label: '均线金叉', desc: 'MA5上穿MA10或MA10上穿MA20' },
  { value: 'volume_breakout', label: '放量突破', desc: '量>5日均量1.5倍+涨幅>3%' },
  { value: 'pullback', label: '回踩支撑', desc: '股价回踩MA20/MA60附近' },
  { value: 'macd_golden', label: 'MACD金叉', desc: 'DIF上穿DEA' },
  { value: 'death_cross', label: '均线死叉', desc: 'MA5下穿MA10（空头）' },
];

const SOURCE_OPTIONS = [
  { value: 'monitor', label: '监控池' },
  { value: 'watchlist', label: '自选股' },
  { value: 'all', label: '全市场' },
];

const PatternSelectionTab: React.FC = () => {
  const [pattern, setPattern] = useState('ma_bullish');
  const [source, setSource] = useState('monitor');
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<any[]>([]);
  const [scanInfo, setScanInfo] = useState<{ pattern: string; source: string; count: number } | null>(null);

  const scan = async () => {
    setLoading(true);
    setData([]);
    setScanInfo(null);
    try {
      const res: any = await apiClient.post('/analysis/pattern', {
        source,
        pattern,
        max: 50,
      });
      if (res?.status === 'ok') {
        const stocks = res.stocks || [];
        setData(stocks);
        setScanInfo({ pattern: res.pattern_name || pattern, source, count: res.count });
        if (stocks.length === 0) {
          message.info('未找到符合形态的股票');
        } else {
          message.success(`找到 ${stocks.length} 只`);
        }
      } else {
        message.error(res?.error || '扫描失败');
      }
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '请求失败');
    }
    setLoading(false);
  };

  const cols = [
    { title: '序号', key: 'rank', width: 50, render: (_: any, __: any, i?: number) => (i ?? 0) + 1 },
    { title: '代码', dataIndex: 'code', width: 90 },
    {
      title: '名称', dataIndex: 'name', width: 100,
      render: (v: string, r: any) => <StockNameCell name={v} code={r.code}>{v}</StockNameCell>,
    },
    { title: '最新价', dataIndex: 'price', width: 80, render: (v: any) => Number(v)?.toFixed(2) },
    { title: '涨幅', dataIndex: 'change_pct', width: 80, render: (v: any) => {
      if (v == null) return '-';
      const color = v >= 0 ? '#f5222d' : '#52c41a';
      return <span style={{ color, fontWeight: 600 }}>{v > 0 ? '+' : ''}{v.toFixed(2)}%</span>;
    }},
    { title: '形态描述', dataIndex: 'pattern_detail', render: (v: string) => (
      <Text style={{ fontSize: 12 }} ellipsis>{v || '-'}</Text>
    )},
  ];

  return (
    <div>
      {/* 配置区 */}
      <Card size="small" style={{ marginBottom: 12 }}>
        <Row gutter={[16, 12]} align="middle">
          <Col xs={24} sm={8}>
            <div>
              <Text strong style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>形态类型</Text>
              <Select
                value={pattern}
                onChange={setPattern}
                style={{ width: '100%' }}
                options={PATTERN_OPTIONS.map(o => ({
                  value: o.value,
                  label: <Space><span>{o.label}</span><Text type="secondary" style={{ fontSize: 11 }}>{o.desc}</Text></Space>,
                }))}
              />
            </div>
          </Col>
          <Col xs={12} sm={6}>
            <div>
              <Text strong style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>扫描范围</Text>
              <Radio.Group value={source} onChange={e => setSource(e.target.value)} optionType="button" size="small">
                {SOURCE_OPTIONS.map(o => <Radio.Button key={o.value} value={o.value}>{o.label}</Radio.Button>)}
              </Radio.Group>
            </div>
          </Col>
          <Col xs={12} sm={4}>
            <Button type="primary" icon={<SearchOutlined />} onClick={scan} loading={loading} style={{ marginTop: 18 }}>
              扫描形态
            </Button>
          </Col>
        </Row>
      </Card>

      {/* 扫描信息 */}
      {scanInfo && (
        <div style={{ marginBottom: 8, padding: '4px 0' }}>
          <Space>
            <Tag icon={<BranchesOutlined />} color="blue">{scanInfo.pattern}</Tag>
            <Tag>范围: {scanInfo.source === 'all' ? '全市场' : scanInfo.source === 'watchlist' ? '自选股' : '监控池'}</Tag>
            <Text type="secondary">匹配 {scanInfo.count} 只</Text>
          </Space>
        </div>
      )}

      {/* 结果表格 */}
      {data.length > 0 ? (
        <Table
          dataSource={data}
          columns={cols}
          rowKey="code"
          loading={loading}
          size="small"
          pagination={{ pageSize: 20 }}
          scroll={{ x: 550 }}
        />
      ) : !loading ? (
        <div style={{ textAlign: 'center', padding: 48, color: '#999' }}>
          <BranchesOutlined style={{ fontSize: 36, marginBottom: 8 }} />
          <div>选择形态类型和扫描范围，点击"扫描形态"</div>
          <div style={{ fontSize: 12, marginTop: 4 }}>
            从股票池中自动筛选符合K线形态的股票
          </div>
        </div>
      ) : null}
    </div>
  );
};

export default PatternSelectionTab;
