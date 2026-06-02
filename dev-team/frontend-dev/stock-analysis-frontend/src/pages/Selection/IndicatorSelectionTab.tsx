
// KLineChart 组件
const KLineChart: React.FC<{ data: any[] }> = ({ data }) => {
  const chartRef = React.useRef<any>(null);
  const containerRef = React.useRef<HTMLDivElement>(null);
  React.useEffect(() => {
    if (!containerRef.current || data.length === 0) return;
    import('echarts').then(echarts => {
      if (chartRef.current) chartRef.current.dispose();
      const chart = echarts.init(containerRef.current!);
      chartRef.current = chart;
      const kdata = data.map((k: any) => [k.date || k.trade_date || '',
        k.open !== undefined ? Number(k.open) : Number(k.open_price),
        k.close !== undefined ? Number(k.close) : Number(k.close_price),
        k.low !== undefined ? Number(k.low) : Number(k.low_price),
        k.high !== undefined ? Number(k.high) : Number(k.high_price),
        k.volume || 0]);
      const dates = kdata.map((d: any) => d[0]);
      const values = kdata.map((d: any) => [d[1], d[2], d[3], d[4]]);
      const volumes = kdata.map((d: any) => d[5]);
      chart.setOption({
        tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
        grid: [{ left: '8%', right: '5%', top: '5%', height: '65%' }, { left: '8%', right: '5%', top: '78%', height: '15%' }],
        xAxis: [{ type: 'category', data: dates, gridIndex: 0, axisLabel: { rotate: 30, fontSize: 10 } },
                { type: 'category', data: dates, gridIndex: 1, axisLabel: { show: false } }],
        yAxis: [{ type: 'value', gridIndex: 0, scale: true }, { type: 'value', gridIndex: 1 }],
        series: [
          { type: 'candlestick', data: values, xAxisIndex: 0, yAxisIndex: 0,
            itemStyle: { color: '#ef5350', color0: '#26a69a', borderColor: '#ef5350', borderColor0: '#26a69a' } },
          { type: 'bar', data: volumes, xAxisIndex: 1, yAxisIndex: 1,
            itemStyle: { color: (p: any) => Number(data[p.dataIndex]?.close || 0) >= Number(data[p.dataIndex]?.open || 0) ? '#ef5350' : '#26a69a' } },
        ],
      });
      const hr = () => chart.resize();
      window.addEventListener('resize', hr);
      return () => { window.removeEventListener('resize', hr); chart.dispose(); };
    });
  }, [data]);
  return <div ref={containerRef} style={{ width: '100%', height: '100%' }} />;
};

/**
 * M04 智能选股 - 指标选股标签页
 * 双模式：热门策略（标签式紧凑布局）+ 自定义策略
 */
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Table, Input, Button, Space, message, Modal, Form, Radio, Typography, Empty, Tooltip, Tag, Row, Col, Divider, Spin, Descriptions } from 'antd';
import {
  ThunderboltOutlined, PlusOutlined, EditOutlined, DeleteOutlined, SaveOutlined,
  FireOutlined, SearchOutlined, DownOutlined, UpOutlined, StarOutlined, StarFilled,
} from '@ant-design/icons';
import { fetchIndicatorSelection } from '../../services/marketResearchApi';
import { authFetch } from '../../services/auth';
import { useConfigStore } from '../../store/configStore';
import apiClient from '../../services/api';
import StockDetailDrawer from '../Market/StockDetailDrawer';
import type { StockQuote, KLineData, TimeShareData, TechnicalIndicators } from '../../types/market';

const { Text } = Typography;

const DEFAULT_STRATEGIES = [
  '收盘价大于10日均线总市值小于200亿;非ST股票;成交量大于前一日成交量的2.5倍;非北交所股票;收盘价大于5日均线;非科创板股票;当日涨幅大于等于3%;上市时间大于1年;归属母公司股东的净利润大于0;',
  '成交量大于10日均量的1.5倍;收盘价站上10日均线;今日涨幅大于3%;沪深A股',
  '非北交所股票;非退市股;近7个交易日涨幅排名前700;上市时间 > 180天;非ST股;收盘价 > 5日均线;无大股东减持计划',
  '全部A股;振幅大于等于2%小于等于6%;成交量较5日均量大于等于150%;涨幅大于等于2%小于等于5%',
  '成交量/过去5日平均成交量≥1.2;机器人/氟化工/芯片概念;流通市值>50亿;股价>10日均线涨幅2%-6%;非ST;非新股;',
  '近5日涨幅大于0;70%筹码集中度小于15%;收盘价大于20日均线',
  '成交量较5日均量放大1.5-3倍;流通市值20-100亿涨跌幅-3%至3%;深市或沪市;',
  '涨跌幅-5%~0%;扣非净利润同比增长率>0;非退市股主营业务收入增长率>0;非ST股;总市值>100亿;沪深主板;',
  '180个交易日内有涨停板次数≥2次或者30日内有涨停板;5个交易日交易额大于8亿;20日换手率不低于30%;近三年内未被证监会立案调查;A股主板;收入大于4亿元或者非两年连续亏损非ST;总市值小于800亿;',
  '昨日开盘涨幅<5%;昨日股吧人气排名前200;非未来三个月解禁股;非北交所股票;非ST股票;昨日换手率从大到小排序;昨日非涨停;非科创板股票;非退市股;非三个月内有大股东减持计划股昨日成交额>5亿元;',
  '净利润同比增长率大于等于1%;非[北京证券交易所];非[ST股票];4月15日到5月6日连续上涨天数大于等于5天;营业利润同比增长率大于等于1%;非[近三月监管函类型匹配监管函出现次数大于等于1 或 近三月监管函类型匹配监管工作函出现次数大于等于1];2025年8月1日到2026年4月14日区间振幅小于等于20%;市净率大于等于0倍小于等于10倍;非[退市股];非[新规风险]主营业务收入同比增长率大于等于1%;',
  '总市值介于100亿~1200亿;股吧人气排名介于1名~2000名;非[退市股];上市日期小于2025-05-16;非[ST股票];非[北京证券交易所]成交额介于20亿~180亿;',
  '6天区间涨跌幅小于0;近6天区间振幅大于15%;上市板块匹配主板或深交所创业板;成交量从大到小排名收盘价大于20日均线;总市值小于450亿;30日区间涨跌幅大于0%;',
  '每股净资产>0;每股现金流量净额>0.1;营业利润同比增长率大于等于7%小于等于50%净利润同比增长率大于等于7%小于等于500%;市净率大于等于1倍小于等于8倍;营业收入大于等于5亿小于等于100亿;',
  '上市日期大于等于2021-05-16;营业利润率介于30%~100%;总市值小于80亿;净利润3年复合增长率介于0%~80%;',
  '营业利润率介于15%~75%;扣除非经常性损益后归属于母公司股东的净利润>15亿归属母公司股东的净利润>15亿;净资产收益率3年复合>5%;营业收入增长率3年复合>5%;',
  '近5天最高价等于涨停价开盘5分钟K线为阴线;盘中5分钟线周期成交量大于前5分钟均值且为阳线;换手率大于5%;',
  '股价大于等于10元小于等于100元日线周期MACD金叉;流通市值大于等于50亿小于等于200亿;非[ST股票];非[上交所科创板];涨跌幅介于-1%~0%;非[退市股];非[深交所创业板]总市值介于50亿~200亿;量比大于1.5;',
];

// 从策略文本中提取简短摘要（第一条条件）
function getBrief(text: string): string {
  const parts = text.split(';').filter(Boolean);
  return parts.length > 0 ? parts[0] : text;
}

// 策略颜色
const TAG_COLORS = ['magenta', 'red', 'volcano', 'orange', 'gold', 'lime', 'green', 'cyan', 'blue', 'geekblue', 'purple'];

const IndicatorSelectionTab: React.FC = () => {
  const [mode, setMode] = useState<'hot' | 'custom'>('hot');
  const [strategies, setStrategies] = useState<string[]>([]);
  const [keyword, setKeyword] = useState('');
  const [searchFilter, setSearchFilter] = useState('');
  const [data, setData] = useState<any[]>([]);
  const [cols, setCols] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editForm] = Form.useForm();
  // K线详情弹窗
  const [detailStock, setDetailStock] = useState<any>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailQuote, setDetailQuote] = useState<StockQuote | null>(null);
  const [detailKline, setDetailKline] = useState<KLineData | null>(null);
  const [detailTimeshare, setDetailTimeshare] = useState<TimeShareData | null>(null);
  const [detailIndicators, setDetailIndicators] = useState<TechnicalIndicators | null>(null);
  // 自选股
  const { watchlist, addWatchlistItem, removeWatchlistItem } = useConfigStore();
  const watchlistCodes = useMemo(() => new Set(watchlist.map((w) => w.code)), [watchlist]);

  // 详情弹窗数据加载
  useEffect(() => {
    if (!detailStock) { setDetailLoading(false); return; }
    setDetailLoading(true);
    const code = detailStock.SECURITY_CODE || detailStock.code || '';
    const mapQuote = (raw: any) => raw ? {
      code: raw.code || raw.SECURITY_CODE || code,
      name: raw.name || raw.SECURITY_SHORT_NAME || '',
      latestPrice: raw.price ?? raw.latestPrice ?? raw.NEWEST_PRICE,
      changePercent: raw.change_pct ?? raw.changePercent ?? raw.CHG,
      change: raw.change ?? raw.change_amount,
      openPrice: raw.open_price ?? raw.openPrice ?? raw.open,
      prevClose: raw.pre_close ?? raw.prevClose,
      high: raw.high_price ?? raw.highPrice ?? raw.high,
      low: raw.low_price ?? raw.lowPrice ?? raw.low,
      volume: raw.volume ?? 0,
      amount: raw.amount ?? 0,
      turnoverRate: raw.turnover_rate ?? raw.turnoverRate,
      amplitude: raw.amplitude ?? 0,
    } : null;
    Promise.all([
      fetch(`/api/v1/market/kline/${code}?count=60`).then(r => r.json()),
      fetch(`/api/v1/market/quote/${code}`).then(r => r.json()).catch(() => null),
    ]).then(([klineRes, quoteRes]) => {
      setDetailKline(klineRes?.klines ? { dataPoints: klineRes.klines, ma5: klineRes.ma5, ma10: klineRes.ma10, ma20: klineRes.ma20 } : null);
      setDetailQuote(mapQuote(quoteRes) || mapQuote(detailStock));
      if (quoteRes) {
        setDetailTimeshare(quoteRes.timeshare || null);
        setDetailIndicators(quoteRes.indicators || null);
      }
    }).catch(() => {}).finally(() => setDetailLoading(false));
  }, [detailStock]);

  const handleWatchlistToggle = useCallback(async (item: any) => {
    const code = item.SECURITY_CODE || item.code || '';
    const name = item.SECURITY_SHORT_NAME || item.name || '';
    const inWl = watchlistCodes.has(code);
    if (inWl) {
      try {
        await authFetch(`/api/v1/config/watchlist/${code}`, { method: 'DELETE' });
        removeWatchlistItem(code);
        message.success(`已移出自选股: ${name}`);
      } catch { message.error('操作失败'); }
    } else {
      try {
        await authFetch('/api/v1/config/watchlist', {
          method: 'POST', body: JSON.stringify({ code, name }),
        });
        addWatchlistItem({ code, name, addedAt: new Date().toISOString() });
        message.success(`已加入自选股: ${name}`);
      } catch { message.error('操作失败'); }
    }
  }, [watchlistCodes, addWatchlistItem, removeWatchlistItem]);

  useEffect(() => {
    apiClient.get('/config/preferences/hot_strategies').then((res: any) => {
      if (res?.value) {
        try {
          const parsed = JSON.parse(res.value);
          if (Array.isArray(parsed) && parsed.length > 0) { setStrategies(parsed); return; }
        } catch {}
      }
      setStrategies(DEFAULT_STRATEGIES);
      apiClient.put('/config/preferences', { hot_strategies: JSON.stringify(DEFAULT_STRATEGIES) }).catch(() => {});
    }).catch(() => setStrategies(DEFAULT_STRATEGIES));
  }, []);

  const saveStrategies = (list: string[]) => {
    setStrategies(list);
    apiClient.put('/config/preferences', { hot_strategies: JSON.stringify(list) }).catch(() => {});
  };

  const search = async (kw?: string) => {
    const text = kw ?? keyword;
    if (!text.trim()) return message.warning('请选择或输入选股条件');
    setLoading(true);
    try {
      const res = await fetchIndicatorSelection(text);
      const result = res?.data?.result;
      if (result?.dataList) {
        const colDefs = (result.columns || []).map((c: any) => ({
          title: c.title || c.key, dataIndex: c.key, width: 100,
          render: (v: any, record: any) => {
            // 代码列：可点击弹详情
            if (c.key === 'SECURITY_CODE') {
              return <a onClick={() => setDetailStock(record)} style={{ cursor: 'pointer', color: '#1677ff', textDecoration: 'underline', fontWeight: 700 }}>{v}</a>;
            }
            // 名称列：可点击弹详情
            if (c.key === 'SECURITY_SHORT_NAME') {
              return <a onClick={() => setDetailStock(record)} style={{ cursor: 'pointer', color: '#1677ff', textDecoration: 'underline' }}>{v}</a>;
            }
            // 涨跌幅列：红绿色
            if (c.key === 'CHG' || (c.title || '').includes('涨幅')) {
              const num = Number(v);
              if (isNaN(num)) return String(v || '');
              return <span style={{ color: num >= 0 ? '#cf1322' : '#389e0d', fontWeight: 600 }}>{num > 0 ? '+' : ''}{num.toFixed(2)}%</span>;
            }
            return typeof v === 'number' ? (v > 100 ? v.toFixed(0) : v.toFixed(2)) : String(v || '');
          },
        }));
        // 追加操作列
        colDefs.push({
          title: '操作', key: 'action', width: 70, fixed: 'right' as const,
          render: (_: any, record: any) => {
            const code = record.SECURITY_CODE || '';
            const inWl = watchlistCodes.has(code);
            return (
              <Tooltip title={inWl ? '移出自选股' : '加入自选股'}>
                <Button type="text" size="small" icon={inWl ? <StarFilled style={{ color: '#faad14' }} /> : <StarOutlined />}
                  onClick={(e) => { e.stopPropagation(); handleWatchlistToggle(record); }} />
              </Tooltip>
            );
          },
        });
        setCols([{ title: '排名', key: 'rank', width: 50, render: (_: any, __: any, i?: number) => i! + 1 }, ...colDefs]);
        setData(result.dataList);
      } else {
        setData([]);
        message.info('无匹配结果');
      }
    } catch (e) {
      setData([]);
      message.error('选股接口调用失败');
    }
    setLoading(false);
  };

  const openEditModal = (index: number | null) => {
    setEditingIndex(index);
    editForm.resetFields();
    if (index !== null && strategies[index]) editForm.setFieldsValue({ content: strategies[index] });
    setModalOpen(true);
  };

  const saveEditStrategy = () => {
    const content = editForm.getFieldValue('content')?.trim();
    if (!content) return message.warning('请输入策略内容');
    const list = [...strategies];
    if (editingIndex !== null) list[editingIndex] = content;
    else list.push(content);
    saveStrategies(list);
    setModalOpen(false);
    message.success(editingIndex !== null ? '策略已更新' : '策略已添加');
  };

  const deleteStrategy = (index: number) => {
    saveStrategies(strategies.filter((_, i) => i !== index));
    message.success('已删除');
  };

  const saveAsHot = () => {
    if (!keyword.trim()) return message.warning('请先输入选股条件');
    saveStrategies([...strategies, keyword.trim()]);
    setMode('hot');
    message.success('已保存为热门策略');
  };

  const activeFilter = searchFilter.toLowerCase();
  const filtered = strategies.filter(s => s.toLowerCase().includes(activeFilter));

  return (
    <div>
      {/* 模式切换 */}
      <Radio.Group value={mode} onChange={(e) => setMode(e.target.value)} style={{ marginBottom: 8 }}
        optionType="button" buttonStyle="solid" size="small">
        <Radio.Button value="hot"><FireOutlined /> 热门策略</Radio.Button>
        <Radio.Button value="custom"><EditOutlined /> 自定义策略</Radio.Button>
      </Radio.Group>

      {mode === 'hot' ? (
        /* ══════ 热门策略 ══════ */
        <div>
          {/* 顶部操作栏：搜索 + 折叠 + 新增 */}
          <Row gutter={8} align="middle" style={{ marginBottom: 6 }}>
            <Col flex="auto">
              <Input
                size="small"
                placeholder="搜索策略..."
                prefix={<SearchOutlined />}
                value={searchFilter}
                onChange={e => setSearchFilter(e.target.value)}
                allowClear
              />
            </Col>
            <Col>
              <Button size="small" type="text" icon={expanded ? <UpOutlined /> : <DownOutlined />}
                onClick={() => setExpanded(!expanded)} />
            </Col>
            <Col>
              <Button size="small" type="primary" ghost icon={<PlusOutlined />} onClick={() => openEditModal(null)}>
                新增
              </Button>
            </Col>
          </Row>

          {/* 策略标签列表 */}
          {expanded && (
            <div style={{ marginBottom: 8, minHeight: 40 }}>
              {filtered.length === 0 ? (
                <Text type="secondary" style={{ fontSize: 12 }}>无匹配策略</Text>
              ) : (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                  {filtered.map((s, i) => (
                    <Tooltip key={i} title={
                      <div style={{ maxWidth: 400, fontSize: 12, lineHeight: 1.6 }}>
                        <div style={{ fontWeight: 600, marginBottom: 4 }}>策略 {(strategies.indexOf(s) + 1)}</div>
                        {s.split(';').filter(Boolean).map((part, pi) => (
                          <div key={pi}>· {part}</div>
                        ))}
                      </div>
                    }>
                      <Tag
                        color={TAG_COLORS[i % TAG_COLORS.length]}
                        style={{ cursor: 'pointer', margin: 1, fontSize: 12, padding: '0 6px', lineHeight: '22px' }}
                        onClick={() => { setKeyword(s); search(s); }}
                        closable
                        onClose={(e) => { e.preventDefault(); Modal.confirm({
                          title: '删除此策略？', content: getBrief(s), okText: '删除', okType: 'danger',
                          onOk: () => deleteStrategy(strategies.indexOf(s)),
                        })}}
                      >
                        #{i + 1} {getBrief(s).substring(0, 20)}{getBrief(s).length > 20 ? '…' : ''}
                      </Tag>
                    </Tooltip>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* 选中的策略显示区 */}
          {keyword && (
            <div style={{
              background: '#f6f8fa', borderRadius: 6, padding: '8px 12px', marginBottom: 8,
              border: '1px solid #e8e8e8',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div style={{ flex: 1 }}>
                  <Text type="secondary" style={{ fontSize: 11, fontWeight: 600 }}>当前策略</Text>
                  <div style={{ fontSize: 12, color: '#333', marginTop: 2, lineHeight: 1.6 }}>
                    {keyword.split(';').filter(Boolean).map((p, pi) => (
                      <Tag key={pi} style={{ fontSize: 11, marginBottom: 2 }}>{p}</Tag>
                    ))}
                  </div>
                </div>
                <Button type="primary" size="small" icon={<ThunderboltOutlined />}
                  onClick={() => search()} loading={loading} style={{ flexShrink: 0, marginLeft: 8 }}>
                  选股
                </Button>
              </div>
            </div>
          )}
        </div>
      ) : (
        /* ══════ 自定义策略 ══════ */
        <div>
          <Input.TextArea
            value={keyword}
            onChange={e => setKeyword(e.target.value)}
            placeholder="输入选股条件，多个条件用;分隔&#10;例如：量比大于2，基本面优秀，主力连续3日净流入，非ST"
            rows={2}
            style={{ marginBottom: 8 }}
          />
          <Space>
            <Button type="primary" icon={<ThunderboltOutlined />} onClick={() => search()} loading={loading}>
              开始选股
            </Button>
            <Button icon={<SaveOutlined />} onClick={saveAsHot} disabled={!keyword.trim()}>
              保存为热门
            </Button>
          </Space>
        </div>
      )}

      <Divider style={{ margin: '8px 0' }} />

      {/* 选股结果 */}
      {data.length > 0 ? (
        <Table
          dataSource={data}
          columns={cols}
          rowKey={(r: any, i?: number) => r.code || String(i)}
          loading={loading}
          size="small"
          pagination={{ pageSize: 20 }}
          scroll={{ x: cols.length * 120 }}
        />
      ) : (
        !loading && <Text type="secondary" style={{ fontSize: 13, display: 'block', textAlign: 'center', padding: 24 }}>
          选择一个策略或输入条件开始选股
        </Text>
      )}

      {/* 新增/编辑弹窗 */}
      <Modal title={editingIndex !== null ? '编辑策略' : '新增策略'} open={modalOpen}
        onOk={saveEditStrategy} onCancel={() => setModalOpen(false)} okText="保存" cancelText="取消" width={600}>
        <Form form={editForm} layout="vertical">
          <Form.Item name="content" label={<Text strong>选股条件</Text>}
            rules={[{ required: true, message: '请输入选股条件' }]}
            help="多个条件用英文分号(;)分隔">
            <Input.TextArea rows={5} placeholder="输入选股条件，多个条件用;分隔" />
          </Form.Item>
        </Form>
      </Modal>

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

export default IndicatorSelectionTab;
