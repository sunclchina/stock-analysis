// @ts-nocheck
﻿/**
 * 固定规则选股鏍囩项? *
 * 3澶х瓥鐣ユā条匡紙璁捐鏂标。搂6夛細
 * 1. steady_trend 鈥?稳健趋势型鈫?鈮?0取? * 2. reversal_breakout 鈥?反转突破型鈫?鈮?5取? * 3. short_term_strong 鈥?短线哄势型?鈫?鈮?0取? *
 * 5灞傝繃婊ゆ祦姘寸嚎堣璁℃枃妗Ｂ?.1夛細
 * 度曞眰杩标护鈫掓妧术矖筛涒啋娣卞害绮剧筛鈫掕储鍔′簨价垛啋缁煎评分
 *
 * 杈撳嚭瀛楁堣璁℃枃妗Ｂ?.3夛細
 * 鎺掑悕/价ｇ爜/后置О/琛笟/瓒势额滆壊/共振状态盘?瓒势哄害/
 * 风险评分/风险筛骇/财务筛骇/缁煎寰楀垎/鎿嶄綔寤鸿/鏄惁鍦ㄨ嚜选? */
import React, { useState, useCallback, useMemo, useEffect } from 'react';
import {
  Card, Radio, Button, Table, Tag, Space, Tooltip, message, Typography,
  Row, Col, Empty, Slider, InputNumber, Modal, Descriptions, Divider, Spin,
} from 'antd';
import {
  PlayCircleOutlined, ReloadOutlined, SortAscendingOutlined,
  StarOutlined, StarFilled, DownloadOutlined, SettingOutlined,
  QuestionCircleOutlined,
} from '@ant-design/icons';
import type { ColumnsType, SortOrder } from 'antd/es/table/interface';
import { authFetch, getCurrentUser } from '../../services/auth';
import { useConfigStore } from '../../store/configStore';
import type { SelectionResultItem, SelectionResponse } from '../../services/selectionApi';
import { fixedSelection } from '../../services/selectionApi';
import { useHelp } from '../../services/help';

const { Text, Title } = Typography;

// ========== Strategy Definitions ==========

interface StrategyDef {
  key: string;
  label: string;
  description: string;
  highlightColor: string;
}

const strategies: Record<string, StrategyDef> = {
  steady_trend: {
    key: 'steady_trend',
    label: '稳健趋势型',
    description: '上涨趋势+共振+风险<40+价位30-55%+财务安全，中长期稳步上涨，适合保守型投资者',
    highlightColor: '#1677ff',
  },
  reversal_breakout: {
    key: 'reversal_breakout',
    label: '反转突破型',
    description: '上涨/反转+价位<40%+放量1.5倍以上，底部盘整后放量突破，适合左侧交易者',
    highlightColor: '#cf1322',
  },
  short_term_strong: {
    key: 'short_term_strong',
    label: '短线强势型',
    description: '趋势强度<80+共振+量比>=1.5，短期强势上涨捕捉主升浪，适合短线交易者',
    highlightColor: '#52c41a',
  },
};

const LAYER_CONDITIONS: Record<string, { label: string; conditions: string[] }> = {
  L1: { label: '底层过滤', conditions: ['非ST/*ST/退市', '非停牌', '成交额/流通市值>0.5%', '股价>=1元', '上市>=20日'] },
  L2: { label: "财务/事件", conditions: ['现价>MA20且MA20向上', 'MA5>MA10>MA20', '近3日涨幅>=2%', '60日价位30%-70%', '今日涨幅>=-2%', '成交量>=5日均量'] },
  L3: { label: '深度精筛', conditions: ['趋势=上涨/反转', '多头共振>=4项', '风险评分<=40', '附加条件>=2项', '5项剔除检查'] },
  L4: { label: '财务事件', conditions: ['财务等级(绿)', '异常指标=0', '扣非净利润>0(稳健)/不为负(其他)', '现金流>0', '负债率<=60%(稳健)/<=75%(其他)', '事件风险检查'] },
  L5: { label: '综合评分', conditions: ['趋势共振45分', '价量健康20分', '财务安全25分', '事件风险10分', '总评分>=85分'] },
};

interface StockDetail extends SelectionResultItem {
  price?: number;
  changePct?: number;
}

const FixedSelectionTab: React.FC = () => {
  const { openHelp } = useHelp();
  // 价庣紦瀛樻仮澶嶄笂娆′娇鐢ㄧ殑筛栫暐
  const lastStrategy = localStorage.getItem('selection_last_strategy') || 'steady_trend';
  const [selectedStrategy, setSelectedStrategy] = useState<string>(lastStrategy);
  const [loading, setLoading] = useState(false);
  // K线数据加载
  const cachedKey = `selection_fixed_${getCurrentUser()?.id || '0'}_${selectedStrategy}`;
  const cachedRaw = localStorage.getItem(cachedKey);
  const cachedResults: SelectionResultItem[] = cachedRaw ? (() => {
    try { return JSON.parse(cachedRaw).items || []; } catch { return []; }
  })() : [];
  const [results, setResults] = useState<SelectionResultItem[]>(cachedResults);
  const [hasRun, setHasRun] = useState(cachedResults.length > 0);
  const [capacityLimit, setCapacityLimit] = useState<number>(20);
  const [detailStock, setDetailStock] = useState<StockDetail | null>(null);
  const [filterModal, setFilterModal] = useState<string | null>(null);
  const [klineData, setKlineData] = useState<any[]>([]);
  const [klineLoading, setKlineLoading] = useState(false);
  const [layerCounts, setLayerCounts] = useState<Record<string, number> | null>(null);
  const [tradingSession, setTradingSession] = useState<{ label: string; note: string; timestamp: string } | null>(null);
  const [totalStockCount, setTotalStockCount] = useState<number>(0);

  // K线数据加载
  useEffect(() => {
    if (!detailStock) { setKlineData([]); return; }
    setKlineLoading(true);
    fetch(`/api/v1/market/kline/${detailStock.code}?count=60`)
      .then(r => r.json())
      .then(d => setKlineData(d?.klines || []))
      .catch(() => setKlineData([]))
      .finally(() => setKlineLoading(false));
  }, [detailStock]);

  const { watchlist, addWatchlistItem, removeWatchlistItem } = useConfigStore();
  const watchlistCodes = useMemo(() => new Set(watchlist.map((w) => w.code)), [watchlist]);

  const handleRun = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fixedSelection(selectedStrategy, capacityLimit);
      const rawItems: any[] = res?.items || [];
      const items: SelectionResultItem[] = rawItems.map((item) => ({
        rank: item.rank,
        code: item.code,
        name: item.name,
        industry: item.industry || '',
        trendColor: item.trendColor || item.trend_color,
        resonanceStatus: item.resonanceStatus || item.resonance_status,
        trendStrength: item.trendStrength ?? item.trend_strength,
        riskScore: item.riskScore ?? item.risk_score,
        riskLevel: item.riskLevel || item.risk_level,
        financeGrade: item.financeGrade || item.finance_grade,
        compositeScore: item.compositeScore ?? item.total_score,
        operationAdvice: item.operationAdvice || item.trade_advice,
        addedToWatchlist: watchlistCodes.has(item.code),
        price: item.price,
        changePct: item.changePct ?? item.change_pct,
      }));
      setResults(items);
      // K线数据加载
  const cacheKey = `selection_fixed_${getCurrentUser()?.id || '0'}_${selectedStrategy}`;
      localStorage.setItem(cacheKey, JSON.stringify({
        strategy: selectedStrategy, items, layer_counts: res?.layer_counts,
        trading_session: res?.trading_session, total_count: res?.total_count,
      }));
      setLayerCounts(res?.layer_counts || null);
      setHasRun(true);
      setTradingSession(res?.trading_session || null);
      setTotalStockCount(res?.total_count || 0);
      if (items.length === 0) {
        message.info('Processing complete')
      } else {
        message.success('Selection complete');
      }
    } catch (err) {
      console.error('固定规则选股澶辫触:', err);
      message.error('Operation failed')
      setResults([]);
      setHasRun(true);
    } finally {
      setLoading(false);
    }
  }, [selectedStrategy, capacityLimit, watchlistCodes]);

  const handleWatchlistToggle = useCallback(
    async (item: SelectionResultItem) => {
      if (item.addedToWatchlist) {
        try {
          await authFetch(`/api/v1/config/watchlist/${item.code}`, { method: 'DELETE' });
          removeWatchlistItem(item.code);
          setResults((prev) => prev.map((r) => r.code === item.code ? { ...r, addedToWatchlist: false } : r));
          message.success('宸插皢 ${item.name} Watched');
        } catch { message.error('Watched澶辫触'); }
      } else {
        try {
          await authFetch('/api/v1/config/watchlist', {
            method: 'POST',
            body: JSON.stringify({ code: item.code, name: item.name }),
          });
          addWatchlistItem({ code: item.code, name: item.name, addedAt: new Date().toISOString() });
          setResults((prev) => prev.map((r) => r.code === item.code ? { ...r, addedToWatchlist: true } : r));
          message.success('宸插皢 ${item.name} Action股');
        } catch { message.error('Action股澶辫触'); }
      }
    },
    [addWatchlistItem, removeWatchlistItem]
  );

  const handleExport = useCallback(() => {
    if (results.length === 0) { message.warning('No data'); return; }
      const headers = ['Rank', 'Code', 'Name', 'Industry', 'Trend', 'Resonance', 'Strength', 'Risk Score', 'Risk Level', 'Fin Grade', 'Composite', 'Advice'];;
    const rows = results.map((r) => [r.rank, r.code, r.name, r.industry, r.trendColor, r.resonanceStatus || '-', r.trendStrength, r.riskScore, r.riskLevel, r.financeGrade, r.compositeScore, r.operationAdvice, r.addedToWatchlist ? 'Yes' : 'No']);
    const csv = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `selection_${strategies[selectedStrategy]?.label || 'fixed'}_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    message.success('Export successful');
  }, [results, selectedStrategy]);
  const columns: ColumnsType<SelectionResultItem> = [
    { title: '排名', dataIndex: 'rank', key: 'rank', width: 60,
      sorter: (a, b) => a.rank - b.rank,
      render: (rank: number) => <Text strong style={{ color: rank <= 3 ? '#ff4d4f' : undefined }}>{rank}</Text> },
    { title: '代码', dataIndex: 'code', key: 'code', width: 100,
      render: (code: string, record: SelectionResultItem) => (
        <a onClick={() => setDetailStock(record as StockDetail)} style={{ fontSize: 14, fontWeight: 700 }}>{code}</a>) },
    { title: '名称', dataIndex: 'name', key: 'name', width: 110,
      render: (name: string, record: SelectionResultItem) => (
        <a onClick={() => setDetailStock(record as StockDetail)} style={{ fontWeight: 600, fontSize: 13 }}>{name}</a>) },
    { title: '行业', dataIndex: 'industry', key: 'industry', width: 100,
      render: (industry: string) => {
        if (!industry) return <Text type="secondary" style={{ fontSize: 11 }}>-</Text>;
        return <Tag style={{ fontSize: 12, padding: '1px 6px' }}>{industry}</Tag>;
      }},
    { title: '趋势', dataIndex: 'trendColor', key: 'trendColor', width: 55,
      render: (color: string) => {
        const cm: Record<string, string> = { 'key': '#52c41a', 'normal': '#1677ff', 'light': '#faad14', 'skip': '#8c8c8c' };
        return <Tooltip title={{ red: '\u4e0a\u6da8', green: '\u6b63\u5e38', blue: '\u53cd\u8f6c', yellow: '\u9884\u8b66', gray: '\u65e0\u6570\u636e' }[color] || color}>
          <div style={{ width: 14, height: 14, borderRadius: '50%', background: cm[color] || '#8c8c8c', display: 'inline-block' }} />
        </Tooltip>;
      }},
    { title: '共振', dataIndex: 'resonanceStatus', key: 'resonanceStatus', width: 90,
      render: (status: string) => {
        if (!status) return <Text type="secondary">-</Text>;
        return <Tag color={status.includes('Up') ? 'green' : status.includes('Down') ? 'red' : 'default'} style={{ fontSize: 11 }}>{status}</Tag>;
      }},
    { title: '强度', dataIndex: 'trendStrength', key: 'trendStrength', width: 85,
      sorter: (a, b) => a.trendStrength - b.trendStrength,
      render: (val: number) => <Text style={{ color: val >= 70 ? '#52c41a' : val >= 50 ? '#faad14' : '#8c8c8c' }}>{val}</Text> },
    { title: '风险评分', dataIndex: 'riskScore', key: 'riskScore', width: 85,
      sorter: (a, b) => a.riskScore - b.riskScore,
      render: (val: number) => <Text style={{ color: val <= 30 ? '#52c41a' : val <= 60 ? '#faad14' : '#ff4d4f' }}>{val}</Text> },
    { title: '风险等级', dataIndex: 'riskLevel', key: 'riskLevel', width: 75,
      render: (level: string) => {
        const lm: Record<string, string> = { low: '#52c41a', medium: '#faad14', high: '#ff4d4f' };
        const ll: Record<string, string> = { low: '低', medium: '中', high: '高' };
        return <Tag color={lm[level]} style={{ fontSize: 11 }}>{ll[level]}</Tag>;
      }},
    { title: '财务等级', dataIndex: 'financeGrade', key: 'financeGrade', width: 75,
      sorter: (a, b) => a.financeGrade.localeCompare(b.financeGrade),
      render: (grade: string) => {
        const cm: Record<string, string> = { 'key': '#52c41a', 'normal': '#1677ff', 'light': '#faad14', 'skip': '#8c8c8c' };
        return <Tag color={cm[grade]}>{grade}</Tag>;
      }},
    { title: '综合得分', dataIndex: 'compositeScore', key: 'compositeScore', width: 90,
      sorter: (a, b) => a.compositeScore - b.compositeScore,
      defaultSortOrder: 'descend' as SortOrder,
      render: (val: number) => <Text strong style={{ color: val >= 90 ? '#52c41a' : val >= 85 ? '#1677ff' : val >= 70 ? '#faad14' : '#8c8c8c' }}>{val}</Text> },
    { title: '建议', dataIndex: 'operationAdvice', key: 'operationAdvice', width: 100,
      render: (advice: string) => {
        const cm: Record<string, string> = { 'key': '#52c41a', 'normal': '#1677ff', 'light': '#faad14', 'skip': '#8c8c8c' };
        return <span style={{ color: cm[advice] || 'inherit', fontSize: 12 }}>{advice}</span>;
      }},
    { title: '操作', dataIndex: 'action', key: 'action', width: 70, fixed: 'right' as const,
      render: (_: unknown, record: SelectionResultItem) => (
        <Tooltip title={record.addedToWatchlist ? '移出自选股' : '加入自选股'}>
          <Button type="text" size="small" icon={record.addedToWatchlist ? <StarFilled style={{ color: '#faad14' }} /> : <StarOutlined />}
            onClick={() => handleWatchlistToggle(record)} />
        </Tooltip>
      )},
  ];

  const layerDescriptions = [ { name: "L1", label: "底层过滤", desc: "底层过滤" }, { name: "L2", label: "财务/事件", desc: "财务/事件" }, { name: "L3", label: "流动性过滤", desc: "流动性过滤" }, { name: "L4", label: "基础技术", desc: "基础技术" }, { name: "L5", label: "深度精筛", desc: "深度精筛" }, { name: "L6", label: "综合评分", desc: "综合评分" }, ];

  return (
    <div style={{ padding: '16px 0' }}>
      <Card size="small" style={{ marginBottom: 16, borderRadius: 8 }}>
        <div style={{ marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
          <Text strong style={{ fontSize: 14 }}>选股策略</Text>
          <Tooltip title="查看帮助文档">
            <Button type="text" size="small" icon={<QuestionCircleOutlined style={{ fontSize: 16, color: '#1677ff' }} />}
              onClick={() => openHelp('fixed-selection')} />
          </Tooltip>
        </div>
        <Radio.Group value={selectedStrategy} onChange={(e) => { setSelectedStrategy(e.target.value); localStorage.setItem('selection_last_strategy', e.target.value); }} optionType="button" buttonStyle="solid" size="middle">
          {Object.values(strategies).map((s) => (
            <Radio.Button key={s.key} value={s.key} style={{ padding: '4px 20px', fontSize: 14 }}>{s.label}</Radio.Button>
          ))}
        </Radio.Group>
        <div style={{ marginTop: 12, color: 'var(--content-text)', opacity: 0.65, fontSize: 13 }}>
          {strategies[selectedStrategy]?.description}
        </div>
        <div style={{ marginTop: 12, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          <Tag style={{ fontSize: 12, padding: '2px 8px', background: '#f0f0f0', border: '1px solid #d9d9d9' }}>
            L0: 全A股池 {totalStockCount ? ` (${totalStockCount.toLocaleString()})` : ''}
          </Tag>
          {layerDescriptions.map((layer, idx) => {
            const layerKey = idx < 5 ? `layer${idx + 1}` : "layer6_scored";
            const cnt = layerCounts?.[layerKey];
            return (
            <Tag key={layer.name} onClick={() => setFilterModal(layer.name)}
              style={{ fontSize: 12, cursor: 'pointer', padding: '2px 8px', background: idx < 3 ? '#e6f4ff' : '#f6ffed', border: '1px solid ' + (idx < 3 ? '#91caff' : '#b7eb8f') }}>
              {layer.name}: {layer.label}{cnt != null ? ` (${cnt.toLocaleString()})` : ''}
            </Tag>
          );
          })}
        </div>
        {tradingSession && (
          <div style={{ marginTop: 12, display: 'flex', gap: 8, alignItems: 'center' }}>
            <Tag color={tradingSession.label === '盘樹中实时' ? 'green' : 'default'} style={{ fontSize: 11 }}>
              {tradingSession.label}
            </Tag>
            <Text type="secondary" style={{ fontSize: 12 }}>{tradingSession.note}</Text>
            <Text type="secondary" style={{ fontSize: 11, fontFamily: 'monospace' }}>{tradingSession.timestamp}</Text>
          </div>
        )}
        <div style={{ marginTop: 16, display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <Space><SettingOutlined style={{ opacity: 0.5 }} /><Text style={{ fontSize: 13 }}>杈撳嚭一婇檺</Text></Space>
          <Slider style={{ width: 160 }} min={1} max={100} value={capacityLimit} onChange={setCapacityLimit} />
          <InputNumber size="small" min={1} max={100} value={capacityLimit} onChange={(v) => setCapacityLimit(v ?? 20)} style={{ width: 60 }} />
          <Text type="secondary" style={{ fontSize: 12 }}>取</Text>
          <div style={{ marginLeft: 'auto' }}>
            <Button type="primary" icon={<PlayCircleOutlined />} onClick={handleRun} loading={loading} size="middle" style={{ minWidth: 140 }}>一键选股</Button>
          </div>
        </div>
      </Card>

      <Divider style={{ margin: '12px 0' }} />

      <Card size="small" style={{ borderRadius: 8 }} bodyStyle={{ padding: hasRun ? 0 : '24px' }}
        title={<Space><span>选股结果</span>{hasRun && <><Tag color="blue">{results.length} 取</Tag></>}</Space>}
        extra={hasRun ? <Space>
          <Tooltip title="鐐瑰嚮分楄〃鎺掑簭"><SortAscendingOutlined style={{ opacity: 0.45, fontSize: 14 }} /></Tooltip>
          <Button size="small" icon={<DownloadOutlined />} onClick={handleExport}>导出CSV</Button>
          <Button size="small" icon={<ReloadOutlined />} onClick={handleRun} loading={loading}>重新选股</Button>
        </Space> : null}>
        {!hasRun ? <Empty description="点击“一键选股”执行5层漏斗选股" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        : <Table columns={columns} dataSource={results} rowKey="code" loading={loading} size="small" scroll={{ x: 1200 }}
            pagination={{ pageSize: 20, showSizeChanger: true, showQuickJumper: true, pageSizeOptions: ['10', '20', '50'],
                showTotal: (total, range) => `${range[0]}-${range[1]} / ${total} total` }}
            locale={{ emptyText: <Empty description='No stocks matched criteria' /> }} />}
      </Card>

      <Modal title={detailStock ? `${detailStock.code} ${detailStock.name}` : ''} open={!!detailStock} onCancel={() => { setDetailStock(null); setKlineData([]); }} footer={null} width={700} style={{ top: 20, maxWidth: 'calc(100vw - 32px)' }}>
        {detailStock && <>
          <div style={{ overflowX: 'auto', width: '100%' }}>
          <Descriptions column={{ xs: 1, sm: 2 }} size="small" bordered style={{ marginBottom: 16 }}>
            <Descriptions.Item label="Price">{(detailStock as any).price || '-'}</Descriptions.Item>
            <Descriptions.Item label="Change">{(detailStock as any).changePct != null ? `${(detailStock as any).changePct}%` : '-'}</Descriptions.Item>
            <Descriptions.Item label="Composite">{detailStock.compositeScore}</Descriptions.Item>
            <Descriptions.Item label="Risk Score">{detailStock.riskScore}</Descriptions.Item>
            <Descriptions.Item label="Risk Level">{detailStock.riskLevel}</Descriptions.Item>
            <Descriptions.Item label="Trend">{detailStock.trendStrength}</Descriptions.Item>
            <Descriptions.Item label="Resonance">{detailStock.resonanceStatus || '-'}</Descriptions.Item>
            <Descriptions.Item label="Fin Grade">{detailStock.financeGrade}</Descriptions.Item>
            <Descriptions.Item label="Advice" span={2}>
              <Text strong style={{ color: detailStock.compositeScore >= 85 ? '#52c41a' : '#faad14' }}>{detailStock.operationAdvice}</Text>
            </Descriptions.Item>
          </Descriptions>
          </div>
          <Divider style={{ margin: '8px 0', fontSize: 13 }}>K-Line</Divider>
          <div style={{ width: '100%', height: 320 }}>
            {klineLoading ? <div style={{ textAlign: 'center', paddingTop: 120 }}><Spin /></div>
            : klineData.length > 0 ? <KLineChart data={klineData} />
            : <Text type="secondary" style={{ display: 'block', textAlign: 'center', paddingTop: 120 }}>No K-line data</Text>}
          </div>
        </>}
      </Modal>

      <Modal title={filterModal ? `${filterModal}: ${LAYER_CONDITIONS[filterModal]?.label || ''}` : ''} open={!!filterModal} onCancel={() => setFilterModal(null)} footer={null} width={400} style={{ top: 20, maxWidth: 'calc(100vw - 32px)' }}>
        {filterModal && LAYER_CONDITIONS[filterModal] && <div>
          <Text type="secondary" style={{ marginBottom: 12, display: 'block' }}>
            {filterModal === 'L1' ? 'L1: 底层过滤' : filterModal === 'L5' ? 'L5: 综合评分>=85' : 'View conditions'}
          </Text>
          {LAYER_CONDITIONS[filterModal].conditions.map((c: string, i: number) => (
            <div key={i} style={{ padding: '4px 0', fontSize: 13 }}>
              <Tag color={filterModal === 'L1' ? 'red' : filterModal === 'L5' ? 'blue' : 'green'} style={{ marginRight: 8, fontSize: 11 }}>{i + 1}</Tag>
              {c}
            </div>
          ))}
        </div>}
      </Modal>
    </div>
  );
};

// K线数据加载
  const KLineChart: React.FC<{ data: any[] }> = ({ data }) => {
  const chartRef = React.useRef<any>(null);
  const containerRef = React.useRef<HTMLDivElement>(null);
  React.useEffect(() => {
    if (!containerRef.current || data.length === 0) return;

    // 鍔ㄦ盘佸鍏charts
    import('echarts').then(echarts => {
      if (chartRef.current) chartRef.current.dispose();
      const chart = echarts.init(containerRef.current!);
      chartRef.current = chart;

      // K线数据加载
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
        tooltip: {
          trigger: 'axis',
          axisPointer: { type: 'cross' },
        },
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
          {
            type: 'candlestick',
            data: values,
            xAxisIndex: 0, yAxisIndex: 0,
            itemStyle: {
              color: '#ef5350', color0: '#26a69a',
              borderColor: '#ef5350', borderColor0: '#26a69a',
            },
          },
          {
            type: 'bar',
            data: volumes,
            xAxisIndex: 1, yAxisIndex: 1,
            itemStyle: {
              color: (params: any) => {
                const idx = params.dataIndex;
                const close = Number(data[idx]?.close || 0);
                const open = Number(data[idx]?.open || 0);
                return close >= open ? '#ef5350' : '#26a69a';
              },
            },
          },
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

export default FixedSelectionTab;

