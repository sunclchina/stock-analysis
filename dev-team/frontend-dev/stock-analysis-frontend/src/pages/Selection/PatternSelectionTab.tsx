/**
 * M04 智能选股 - 形态选股标签页
 * 从股票池中扫描符合K线形态的股票。
 * 支持多种形态：均线多头排列、金叉、放量突破、回踩支撑等。
 */
import React, { useState, useCallback, useMemo, useEffect } from 'react';
import { Table, Button, Space, message, Card, Tag, Select, Radio, Typography, Row, Col, Modal, Descriptions, Divider, Spin, Tooltip } from 'antd';
import { BranchesOutlined, SearchOutlined, StarOutlined, StarFilled, ReloadOutlined } from '@ant-design/icons';
import { authFetch } from '../../services/auth';
import { useConfigStore } from '../../store/configStore';
import apiClient from '../../services/api';
import StockDetailDrawer from '../Market/StockDetailDrawer';
import type { StockQuote, KLineData, TimeShareData, TechnicalIndicators } from '../../types/market';

const { Text } = Typography;

// ── K线图组件（可复用） ──
const KLineChart: React.FC<{ data: any[] }> = ({ data }) => {
  const chartRef = React.useRef<any>(null);
  const containerRef = React.useRef<HTMLDivElement>(null);
  React.useEffect(() => {
    if (!containerRef.current || data.length === 0) return;
    import('echarts').then(echarts => {
      if (chartRef.current) chartRef.current.dispose();
      const chart = echarts.init(containerRef.current!);
      chartRef.current = chart;
      const kdata = data.map((k: any) => [
        k.date || k.trade_date || '',
        k.open !== undefined ? Number(k.open) : Number(k.open_price),
        k.close !== undefined ? Number(k.close) : Number(k.close_price),
        k.low !== undefined ? Number(k.low) : Number(k.low_price),
        k.high !== undefined ? Number(k.high) : Number(k.high_price),
        k.volume || 0,
      ]);
      const dates = kdata.map((d: any) => d[0]);
      const values = kdata.map((d: any) => [d[1], d[2], d[3], d[4]]);
      const volumes = kdata.map((d: any) => d[5]);
      chart.setOption({
        tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
        grid: [
          { left: '8%', right: '5%', top: '5%', height: '65%' },
          { left: '8%', right: '5%', top: '78%', height: '15%' },
        ],
        xAxis: [
          { type: 'category', data: dates, gridIndex: 0, axisLabel: { rotate: 30, fontSize: 10 } },
          { type: 'category', data: dates, gridIndex: 1, axisLabel: { show: false } },
        ],
        yAxis: [
          { type: 'value', gridIndex: 0, scale: true, splitNumber: 5 },
          { type: 'value', gridIndex: 1, splitNumber: 3 },
        ],
        series: [
          { type: 'candlestick', data: values, xAxisIndex: 0, yAxisIndex: 0,
            itemStyle: { color: '#ef5350', color0: '#26a69a', borderColor: '#ef5350', borderColor0: '#26a69a' } },
          { type: 'bar', data: volumes, xAxisIndex: 1, yAxisIndex: 1,
            itemStyle: { color: (params: any) => {
              const idx = params.dataIndex;
              const close = Number(data[idx]?.close || 0);
              const open = Number(data[idx]?.open || 0);
              return close >= open ? '#ef5350' : '#26a69a';
            }}},
        ],
      });
      const handleResize = () => chart.resize();
      window.addEventListener('resize', handleResize);
      return () => {
        window.removeEventListener('resize', handleResize);
        chart.dispose();
      };
    });
  }, [data]);
  return <div ref={containerRef} style={{ width: '100%', height: '100%' }} />;
};

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
  // 详情弹窗
  const [detailStock, setDetailStock] = useState<any>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailQuote, setDetailQuote] = useState<StockQuote | null>(null);
  const [detailKline, setDetailKline] = useState<KLineData | null>(null);
  const [detailTimeshare, setDetailTimeshare] = useState<TimeShareData | null>(null);
  const [detailIndicators, setDetailIndicators] = useState<TechnicalIndicators | null>(null);

  // 详情弹窗数据加载
  useEffect(() => {
    if (!detailStock) { setDetailLoading(false); return; }
    setDetailLoading(true);
    const code = detailStock.code || '';
    Promise.all([
      fetch(`/api/v1/market/kline/${code}?count=60`).then(r => r.json()),
      fetch(`/api/v1/market/quote/${code}`).then(r => r.json()).catch(() => null),
    ]).then(([klineRes, quoteRes]) => {
      setDetailKline(klineRes?.klines ? { dataPoints: klineRes.klines, ma5: klineRes.ma5, ma10: klineRes.ma10, ma20: klineRes.ma20 } : null);
      if (quoteRes) {
        setDetailQuote(quoteRes);
        setDetailTimeshare(quoteRes.timeshare || null);
        setDetailIndicators(quoteRes.indicators || null);
      } else {
        setDetailQuote(detailStock);
      }
    }).catch(() => {}).finally(() => setDetailLoading(false));
  }, [detailStock]);

  // 自选股
  const { watchlist, addWatchlistItem, removeWatchlistItem } = useConfigStore();
  const watchlistCodes = useMemo(() => new Set(watchlist.map((w) => w.code)), [watchlist]);

  const handleWatchlistToggle = useCallback(
    async (item: any) => {
      const inWatchlist = watchlistCodes.has(item.code);
      if (inWatchlist) {
        try {
          await authFetch(`/api/v1/config/watchlist/${item.code}`, { method: 'DELETE' });
          removeWatchlistItem(item.code);
          setData((prev) => prev.map((r) => r.code === item.code ? { ...r, addedToWatchlist: false } : r));
          message.success(`已将 ${item.name} 移出自选股`);
        } catch { message.error('操作失败'); }
      } else {
        try {
          await authFetch('/api/v1/config/watchlist', {
            method: 'POST',
            body: JSON.stringify({ code: item.code, name: item.name }),
          });
          addWatchlistItem({ code: item.code, name: item.name, addedAt: new Date().toISOString() });
          setData((prev) => prev.map((r) => r.code === item.code ? { ...r, addedToWatchlist: true } : r));
          message.success(`已将 ${item.name} 加入自选股`);
        } catch { message.error('操作失败'); }
      }
    },
    [watchlistCodes, addWatchlistItem, removeWatchlistItem]
  );

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
    { title: '代码', dataIndex: 'code', width: 90,
      render: (code: string, r: any) => <a onClick={() => setDetailStock(r)} style={{ fontWeight: 700, fontSize: 13 }}>{code}</a> },
    { title: '名称', dataIndex: 'name', width: 100,
      render: (v: string, r: any) => <a onClick={() => setDetailStock(r)} style={{ fontWeight: 600 }}>{v}</a> },
    { title: '最新价', dataIndex: 'price', width: 80, render: (v: any) => Number(v)?.toFixed(2) },
    { title: '涨幅', dataIndex: 'change_pct', width: 80, render: (v: any) => {
      if (v == null) return '-';
      const color = v >= 0 ? '#f5222d' : '#52c41a';
      return <span style={{ color, fontWeight: 600 }}>{v > 0 ? '+' : ''}{v.toFixed(2)}%</span>;
    }},
    { title: '形态描述', dataIndex: 'pattern_detail', render: (v: string) => (
      <Text style={{ fontSize: 12 }} ellipsis>{v || '-'}</Text>
    )},
    { title: '操作', key: 'action', width: 70, fixed: 'right' as const,
      render: (_: any, r: any) => {
        const inWl = watchlistCodes.has(r.code);
        return (
          <Tooltip title={inWl ? '移出自选股' : '加入自选股'}>
            <Button type="text" size="small" icon={inWl ? <StarFilled style={{ color: '#faad14' }} /> : <StarOutlined />}
              onClick={() => handleWatchlistToggle(r)} />
          </Tooltip>
        );
      }},
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

      {/* 详情弹窗（复用行情页StockDetailDrawer） */}
      <StockDetailDrawer
        open={!!detailStock}
        loading={detailLoading}
        quote={detailQuote}
        kline={detailKline}
        timeshare={detailTimeshare}
        indicators={detailIndicators}
        onClose={() => { setDetailStock(null); setDetailQuote(null); setDetailKline(null); setDetailTimeshare(null); setDetailIndicators(null); }}
        onRefresh={() => {}}
      />
    </div>
  );
};

export default PatternSelectionTab;
