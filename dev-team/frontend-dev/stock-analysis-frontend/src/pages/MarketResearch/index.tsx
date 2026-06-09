import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Card, Table, Tag, Typography, Space, Tabs, Input, Button, message, Popover, Modal, Tooltip, Empty, Row, Col } from 'antd';
import { Spin } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined, FileTextOutlined, LinkOutlined, AimOutlined, WarningOutlined, AlertOutlined, EyeOutlined, FileAddOutlined, MinusOutlined } from '@ant-design/icons';
import * as echarts from 'echarts';
import apiClient from '../../services/api';
import {
  fetchStockResearchReport,
  fetchStockNotice,
  fetchIndustryResearchReport,
  fetchLimitUpTier,
  fetchAnomalyMonitor,
  fetchResearchReportDetail,
  fetchKLineMini,
} from '../../services/marketResearchApi';
import { GlobalIndices, IndustryRanking, StockMoneyFlow } from '../MarketExt';

const { Text, Title } = Typography;

function ChangeTag({ v }: { v: any }) {
  const n = Number(v) || 0;
  if (n === 0) return <Tag>0.00%</Tag>;
  const color = n > 0 ? 'red' : 'green';
  const icon = n > 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />;
  return <Tag color={color}>{icon} {n > 0 ? '+' : ''}{n.toFixed(2)}%</Tag>;
}

// ── K线迷你图（ECharts 渲染）──────────────────────────────────────────

const KLineMiniChart: React.FC<{ code: string; name?: string }> = ({ code, name }) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [klines, setKlines] = useState<any[]>([]);
  const [quoteInfo, setQuoteInfo] = useState<any>(null);

  useEffect(() => {
    let destroyed = false;
    const fetchData = async () => {
      try {
        const [klineRes, quoteRes] = await Promise.allSettled([
          fetchKLineMini(code, 60),
          apiClient.get(`/market/quote/${code}`).catch(() => null) as any,
        ]);
        if (destroyed) return;
        if (klineRes.status === 'fulfilled') {
          setKlines(klineRes.value?.klines || []);
        }
        if (quoteRes.status === 'fulfilled') {
          setQuoteInfo(quoteRes.value);
        }
      } catch (e) {
        if (!destroyed) setError('数据加载失败');
      } finally {
        if (!destroyed) setLoading(false);
      }
    };
    fetchData();
    return () => { destroyed = true; };
  }, [code]);

  useEffect(() => {
    if (!chartRef.current || klines.length === 0) return;
    const chart = echarts.init(chartRef.current, null, { renderer: 'canvas' });
    const dates = klines.map(k => k.date?.substring(5) || '');
    const closePrices = klines.map(k => k.close);
    const volumes = klines.map(k => k.volume || 0);
    const maxV = Math.max(...volumes, 1);

    const option = {
      animation: false,
      grid: [{ left: 8, right: 8, top: 12, bottom: 18 }, { left: 8, right: 8, top: 50, bottom: 18, height: 30 }],
      xAxis: [{ type: 'category', data: dates, show: false }, { type: 'category', data: dates, show: false, gridIndex: 1 }],
      yAxis: [{ type: 'value', show: false, scale: true }, { type: 'value', show: false, gridIndex: 1 }],
      series: [
        {
          type: 'line', data: closePrices, smooth: true, showSymbol: false, lineStyle: { width: 2 },
          areaStyle: { opacity: 0.15 },
          itemStyle: { color: closePrices[0] <= closePrices[closePrices.length - 1] ? '#f5222d' : '#52c41a' },
        },
        {
          type: 'bar', data: volumes.map(v => v / maxV * 100), barWidth: '60%', xAxisIndex: 1, yAxisIndex: 1,
          itemStyle: { color: (p: any) => {
            const cls = klines[p.dataIndex]?.close || 0;
            const opn = klines[p.dataIndex]?.open || 0;
            return cls >= opn ? 'rgba(245,34,45,0.3)' : 'rgba(82,196,26,0.3)';
          }},
        },
      ],
    };
    chart.setOption(option);
    return () => chart.dispose();
  }, [klines]);

  if (loading) return <div style={{ width: 340, height: 120, display: 'flex', alignItems: 'center', justifyContent: 'center' }}><Spin size="small" /></div>;
  if (error || klines.length === 0) return <div style={{ width: 340, height: 120, display: 'flex', alignItems: 'center', justifyContent: 'center' }}><Text type="secondary" style={{ fontSize: 12 }}>暂无K线数据</Text></div>;

  const lastClose = klines[klines.length - 1]?.close;
  const firstClose = klines[0]?.close;
  const change = lastClose && firstClose ? ((lastClose - firstClose) / firstClose * 100).toFixed(2) : '-';
  const isUp = Number(change) >= 0;

  return (
    <div style={{ width: 340 }}>
      <div style={{ padding: '4px 8px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #f0f0f0' }}>
        <Text strong style={{ fontSize: 13 }}>
          {name || code}
          {quoteInfo?.price != null && (
            <Text style={{ marginLeft: 8, fontSize: 13, color: isUp ? '#f5222d' : '#52c41a' }}>
              {quoteInfo.price.toFixed(2)} {isUp ? '+' : ''}{quoteInfo.change_pct?.toFixed(2)}%
            </Text>
          )}
        </Text>
        <Text style={{ fontSize: 11 }} type="secondary">60日K线</Text>
      </div>
      <div ref={chartRef} style={{ width: 340, height: 90 }} />
    </div>
  );
};

// ── 名称单元格（带K线悬浮）──────────────────────────────────────────────

const StockNameCell: React.FC<{ name: string; code: string; children?: React.ReactNode }> = ({ name, code, children }) => (
  <Popover
    trigger="hover"
    placement="right"
    mouseEnterDelay={0.4}
    mouseLeaveDelay={0.1}
    content={<KLineMiniChart code={code} name={name} />}
  >
    <span style={{ cursor: 'pointer', borderBottom: '1px dashed #d9d9d9' }}>{children || `${name}(${code})`}</span>
  </Popover>
);

// ── 研报全文弹窗 ──────────────────────────────────────────────────────

const ReportDetailModal: React.FC<{
  visible: boolean;
  onClose: () => void;
  infoCode: string;
  title: string;
  stockName?: string;
}> = ({ visible, onClose, infoCode, title, stockName }) => {
  const [loading, setLoading] = useState(false);
  const [detail, setDetail] = useState<any>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!visible || !infoCode) return;
    setLoading(true);
    setDetail(null);
    setError('');
    fetchResearchReportDetail(infoCode)
      .then(res => {
        if (res?.title || res?.content) setDetail(res);
        else setDetail({ ...res, empty: true });
      })
      .catch(() => setError('加载失败'))
      .finally(() => setLoading(false));
  }, [visible, infoCode]);

  const openPdf = () => {
    if (detail?.pdf_url) window.open(detail.pdf_url, '_blank');
  };

  return (
    <Modal
      title={
        <Space>
          <FileTextOutlined />
          <span>{stockName ? `【${stockName}】` : ''}{title?.substring(0, 60)}</span>
        </Space>
      }
      open={visible}
      onCancel={onClose}
      footer={null}
      width={720}
      style={{ top: 20 }}
      styles={{ body: { maxHeight: '70vh', overflow: 'auto' } }}
    >
      {loading ? (
        <div style={{ textAlign: 'center', padding: 40 }}><Spin size="large" tip="加载研报全文..." /></div>
      ) : error ? (
        <Empty description="加载失败" />
      ) : detail?.empty || (!detail?.title && !detail?.content) ? (
        <div style={{ textAlign: 'center', padding: 24 }}>
          <Empty description={
            <span>
              {detail?.note || '暂未获取到全文内容'}<br />
              {detail?.pdf_url && (
                <Button type="link" icon={<LinkOutlined />} onClick={openPdf}>
                  在新窗口打开PDF原文
                </Button>
              )}
            </span>
          } />
        </div>
      ) : (
        <div>
          {detail?.title && (
            <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 16, color: '#333' }}>
              {detail.title.split('-').slice(0, -1).join('-')}
            </div>
          )}
          <div style={{ whiteSpace: 'pre-wrap', fontSize: 14, lineHeight: 1.8, color: '#555' }}>
            {detail?.content || '暂无内容'}
          </div>
          {detail?.pdf_url && (
            <div style={{ textAlign: 'center', marginTop: 16, paddingTop: 12, borderTop: '1px solid #f0f0f0' }}>
              <Button type="primary" ghost icon={<LinkOutlined />} onClick={openPdf}>
                查看PDF原文
              </Button>
            </div>
          )}
        </div>
      )}
    </Modal>
  );
};

// ========== 1. 个股研报 ==========
const ratingChangeMap: Record<string, string> = { '1': '上调', '2': '首次', '3': '维持', '4': '下调', '5': '空' };

const StockResearchReportTab: React.FC = () => {
  const [code, setCode] = useState('600519');
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [detailModal, setDetailModal] = useState<{ visible: boolean; infoCode: string; title: string; stockName: string }>({ visible: false, infoCode: '', title: '', stockName: '' });

  const search = () => {
    setLoading(true);
    fetchStockResearchReport(code).then(d => setData(d || [])).catch(() => setData([])).finally(() => setLoading(false));
  };
  useEffect(() => { search(); }, []);

  const showDetail = (infoCode: string, title: string, stockName: string) => {
    setDetailModal({ visible: true, infoCode, title, stockName });
  };

  const cols = [
    {
      title: '名称', dataIndex: 'stockName', width: 100,
      render: (v: string, r: any) => (
        <StockNameCell name={v} code={r.stockCode}>
          {v}({r.stockCode})
        </StockNameCell>
      ),
    },
    { title: '行业', dataIndex: 'indvInduName', width: 100 },
    {
      title: '标题', dataIndex: 'title',
      render: (v: string, r: any) => (
        <Tooltip title="点击查看全文">
          <Text
            style={{ fontSize: 13, cursor: 'pointer', color: '#1677ff' }}
            onClick={() => showDetail(r.infoCode, v, r.stockName)}
            ellipsis
          >
            {v}
          </Text>
        </Tooltip>
      ),
    },
    { title: '东财评级', dataIndex: 'emRatingName', width: 80, render: (v: string) => <Tag color={v?.includes('买入') ? 'red' : v?.includes('增持') ? 'blue' : 'default'}>{v}</Tag> },
    { title: '评级变动', dataIndex: 'ratingChange', width: 80, render: (v: any) => <Tag>{ratingChangeMap[String(v)] || '-'}</Tag> },
    { title: '机构评级', dataIndex: 'sRatingName', width: 80, render: (v: string) => <Tag>{v}</Tag> },
    { title: '分析师', dataIndex: 'researcher', width: 120 },
    { title: '机构', dataIndex: 'orgSName', width: 100 },
    { title: '日期', dataIndex: 'publishDate', width: 100, render: (v: string) => v?.substring(0, 10) },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 12 }}>
        <Input.Search value={code} onChange={e => setCode(e.target.value)} onSearch={search} placeholder="输入股票代码" enterButton="查询" style={{ width: 280 }} />
      </Space>
      <Table dataSource={data} columns={cols} rowKey={(r: any, i?: number) => r.infoCode || String(i)} loading={loading} size="small" pagination={{ pageSize: 20 }} scroll={{ x: 1000 }} />
      <ReportDetailModal
        visible={detailModal.visible}
        onClose={() => setDetailModal(p => ({ ...p, visible: false }))}
        infoCode={detailModal.infoCode}
        title={detailModal.title}
        stockName={detailModal.stockName}
      />
    </div>
  );
};

// ========== 2. 公司公告 ==========
const StockNoticeTab: React.FC = () => {
  const [codes, setCodes] = useState('600519,000001');
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const search = () => {
    setLoading(true);
    fetchStockNotice(codes).then(d => setData(d || [])).catch(() => setData([])).finally(() => setLoading(false));
  };
  useEffect(() => { search(); }, []);

  const openPdf = (artCode: string) => {
    if (artCode) window.open(`https://pdf.dfcfw.com/pdf/H2_${artCode}_1.pdf`, '_blank');
  };

  const cols = [
    {
      title: '股票代码', key: 'stockCode', width: 90,
      render: (_: any, r: any) => r.codes?.[0]?.stock_code || '-',
    },
    {
      title: '股票名称', key: 'stockName', width: 100,
      render: (_: any, r: any) => {
        const sc = r.codes?.[0]?.stock_code || '';
        const name = r.codes?.[0]?.short_name || r.title?.split(':')[0] || '-';
        return sc ? (
          <StockNameCell name={name} code={sc}>{name}</StockNameCell>
        ) : (
          <Text>{name}</Text>
        );
      },
    },
    {
      title: '公告标题', dataIndex: 'title',
      render: (v: string, r: any) => (
        <a style={{ fontSize: 13, cursor: 'pointer', color: '#1677ff' }} onClick={() => openPdf(r.art_code)}>
          {v}
        </a>
      ),
    },
    { title: '公告类型', key: 'annType', width: 120, render: (_: any, r: any) => r.columns?.[0]?.column_name || '-' },
    { title: '公告日期', dataIndex: 'notice_date', width: 100, render: (v: string) => v?.substring(0, 10) },
    { title: '数据更新时间', dataIndex: 'display_time', width: 160, render: (v: string) => v?.substring(0, 19)?.replace(/-/g, '/') },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 12 }}>
        <Input.Search value={codes} onChange={e => setCodes(e.target.value)} onSearch={search} placeholder="股票代码,逗号分隔" enterButton="查询" style={{ width: 340 }} />
      </Space>
      <Table dataSource={data} columns={cols} rowKey={(r: any, i?: number) => r.art_code || String(i)} loading={loading} size="small" pagination={{ pageSize: 20 }} scroll={{ x: 900 }} />
    </div>
  );
};

// ========== 3. 行业研究 ==========
const IndustryResearchTab: React.FC = () => {
  const [code, setCode] = useState('');
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [detailModal, setDetailModal] = useState<{ visible: boolean; infoCode: string; title: string }>({ visible: false, infoCode: '', title: '' });

  const search = () => {
    setLoading(true);
    fetchIndustryResearchReport(code).then(d => setData(d || [])).catch(() => setData([])).finally(() => setLoading(false));
  };
  useEffect(() => { search(); }, []);

  const showDetail = (infoCode: string, title: string) => {
    setDetailModal({ visible: true, infoCode, title });
  };

  const cols = [
    { title: '行业', dataIndex: 'industryName', width: 100 },
    {
      title: '标题', dataIndex: 'title',
      render: (v: string, r: any) => (
        <Tooltip title="点击查看全文">
          <Text
            style={{ fontSize: 13, cursor: 'pointer', color: '#1677ff' }}
            onClick={() => showDetail(r.infoCode, v)}
            ellipsis
          >
            {v}
          </Text>
        </Tooltip>
      ),
    },
    { title: '东财评级', dataIndex: 'emRatingName', width: 80, render: (v: string) => v ? <Tag>{v}</Tag> : '-' },
    { title: '评级变动', dataIndex: 'ratingChange', width: 80, render: (v: any) => v ? <Tag>{ratingChangeMap[String(v)] || '-'}</Tag> : '-' },
    { title: '机构评级', dataIndex: 'sRatingName', width: 80, render: (v: string) => v ? <Tag>{v}</Tag> : '-' },
    { title: '分析师', dataIndex: 'researcher', width: 120 },
    { title: '机构', dataIndex: 'orgSName', width: 100 },
    { title: '日期', dataIndex: 'publishDate', width: 100, render: (v: string) => v?.substring(0, 10) },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 12 }}>
        <Input.Search value={code} onChange={e => setCode(e.target.value)} onSearch={search} placeholder="行业代码（空=全部）" enterButton="查询" style={{ width: 280 }} />
      </Space>
      <Table dataSource={data} columns={cols} rowKey={(r: any, i?: number) => r.infoCode || String(i)} loading={loading} size="small" pagination={{ pageSize: 20 }} scroll={{ x: 900 }} />
      <ReportDetailModal
        visible={detailModal.visible}
        onClose={() => setDetailModal(p => ({ ...p, visible: false }))}
        infoCode={detailModal.infoCode}
        title={detailModal.title}
      />
    </div>
  );
};

// ========== 4. 涨停梯队 ==========
const LimitUpTierTab: React.FC = () => {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => { fetchLimitUpTier().then(d => setData(d || [])).catch(() => setData([])).finally(() => setLoading(false)); }, []);
  const cols = [
    { title: '排名', key: 'rank', width: 50, render: (_: any, __: any, i?: number) => (i ?? 0) + 1 },
    { title: '代码', dataIndex: 'code', width: 90 },
    {
      title: '名称', dataIndex: 'name', width: 100,
      render: (v: string, r: any) => <StockNameCell name={v} code={r.code}>{v}</StockNameCell>,
    },
    { title: '最新价', dataIndex: 'price', width: 80, render: (v: any) => Number(v)?.toFixed(2) },
    { title: '涨幅', dataIndex: 'change_pct', width: 80, render: (v: any) => <ChangeTag v={v} /> },
    { title: '连板', dataIndex: 'limit_up_times', width: 60, render: (v: any) => v && v !== '0' && v !== '首板' ? <Tag color="red">{v}板</Tag> : <Tag>{v || '-'}</Tag> },
    { title: '涨停原因', dataIndex: 'limit_up_reason', width: 150, render: (v: any) => v ? <Text style={{ fontSize: 12 }} ellipsis>{v}</Text> : '-' },
    { title: '换手率', dataIndex: 'turnover_rate', width: 70, render: (v: any) => v ? v + '%' : '-' },
    { title: '振幅', dataIndex: 'amplitude', width: 70, render: (v: any) => v ? v + '%' : '-' },
  ];
  return (
    <div>
      {data.length === 0 && !loading ? (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Text type="secondary">非交易时段暂无涨停数据</Text>
        </div>
      ) : (
        <Table dataSource={data} columns={cols} rowKey={(r: any, i?: number) => r.code || String(i)} loading={loading} size="small" pagination={{ pageSize: 20 }} scroll={{ x: 800 }} />
      )}
    </div>
  );
};

// ========== 5. 异动监控 ==========
const AnomalyMonitorTab: React.FC = () => {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => { fetchAnomalyMonitor().then(d => setData(d || [])).catch(() => setData([])).finally(() => setLoading(false)); }, []);
  const anomalyColor: Record<string, string> = { '急速拉升': 'red', '大幅下跌': 'green', '放量异动': 'orange', '剧烈波动': 'purple' };
  const cols = [
    { title: '排名', key: 'rank', width: 50, render: (_: any, __: any, i: number) => i + 1 },
    { title: '代码', dataIndex: 'code', width: 90 },
    {
      title: '名称', dataIndex: 'name', width: 100,
      render: (v: string, r: any) => <StockNameCell name={v} code={r.code}>{v}</StockNameCell>,
    },
    { title: '最新价', dataIndex: 'price', render: (v: any) => Number(v)?.toFixed(2) },
    { title: '涨幅', dataIndex: 'change_pct', render: (v: any) => <ChangeTag v={v} /> },
    { title: '异动类型', dataIndex: 'anomaly_type', render: (v: string) => <Tag color={anomalyColor[v] || 'default'}>{v}</Tag> },
    { title: '换手率', dataIndex: 'turnover_rate', render: (v: any) => v ? v + '%' : '-' },
    { title: '振幅', dataIndex: 'amplitude', render: (v: any) => v ? v + '%' : '-' },
  ];
  return <Table dataSource={data} columns={cols} rowKey={(r: any, i?: number) => r.code || String(i)} loading={loading} size="small" pagination={{ pageSize: 20 }} scroll={{ x: 700 }} />;
};

// ========== 主页面 ==========
// ========== 盘前提示（从实时行情模块移入） ==========
const PremarketTipSection: React.FC = () => {
  const [tip, setTip] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);

  const loadTip = useCallback(async () => {
    setLoading(true);
    try {
      const { getPremarketTip } = await import('../../services/marketApi');
      const r = await getPremarketTip();
      setTip(r.data);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadTip(); }, []);

  const handleRefresh = useCallback(async () => {
    setLoading(true);
    try {
      const { getPremarketTip } = await import('../../services/marketApi');
      const r = await getPremarketTip();
      setTip(r.data);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleGenerate = useCallback(async () => {
    setGenerating(true);
    try {
      const { generatePremarketTip } = await import('../../services/marketApi');
      const r = await generatePremarketTip();
      setTip(r.data);
    } finally {
      setGenerating(false);
    }
  }, []);

  return (
    <div>
      <Row gutter={12}>
        <Col xs={24} lg={14} xl={15}>
          {(() => {
            const PremarketTipCard = React.lazy(() => import('../Market/PremarketTipCard'));
            return (
              <React.Suspense fallback={<Spin style={{ display: 'block', margin: '40px auto' }} />}>
                <PremarketTipCard
                  tip={tip}
                  loading={loading}
                  generating={generating}
                  onRefresh={handleRefresh}
                  onGenerate={handleGenerate}
                />
              </React.Suspense>
            );
          })()}
        </Col>
        <Col xs={24} lg={10} xl={9}>
          {tip && tip.sectorRecommendations && tip.sectorRecommendations.length > 0 && (
            <Card size="small" style={{ borderRadius: 8, marginBottom: 12 }}
              styles={{ body: { padding: '10px 14px' } }}
              title={<Space><AimOutlined style={{ color: '#1677ff', fontSize: 18 }} /><span style={{ fontSize: 16, fontWeight: 700, color: '#1677ff' }}>关注板块</span></Space>}
            >
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {(tip.sectorRecommendations as string[]).map((s: string) => (
                  <Tag key={s} color="blue" style={{ fontSize: 12, padding: '0 8px', margin: 0 }}>{s}</Tag>
                ))}
              </div>
            </Card>
          )}
          {tip && tip.riskTips && tip.riskTips.length > 0 && (
            <Card size="small" style={{ borderRadius: 8, marginBottom: 12 }}
              styles={{ body: { padding: '10px 14px' } }}
              title={<Space><WarningOutlined style={{ color: '#faad14', fontSize: 18 }} /><span style={{ fontSize: 16, fontWeight: 700, color: '#d48806' }}>风险提示</span></Space>}
            >
              {(tip.riskTips as string[]).map((risk: string, i: number) => (
                <div key={i} style={{ fontSize: 12, color: '#d48806', lineHeight: 1.8 }}>
                  • {risk}
                </div>
              ))}
            </Card>
          )}
        </Col>
      </Row>
    </div>
  );
};



const NewsAndAnnounceTab: React.FC = () => {
  const [newsItems, setNewsItems] = useState<any[]>([]);
  const [announceItems, setAnnounceItems] = useState<any[]>([]);

  useEffect(() => {
    fetch('/api/v1/market/news').then(r => r.json()).then(d => setNewsItems(d.items || [])).catch(() => {});
    fetch('/api/v1/market/announcements').then(r => r.json()).then(d => setAnnounceItems(d.items || [])).catch(() => {});
  }, []);

  const cardS: React.CSSProperties = { borderRadius: 8, marginBottom: 12 };

  // ── 新闻卡片 ──
  const NewsCard: React.FC<{ items: any[] }> = ({ items }) => {
    const [expanded, setExpanded] = useState(false);
    const [detail, setDetail] = useState<any>(null);
    const limit = expanded ? items.length : 5;
    return (
      <>
      <Card size="small" title={<Space><AlertOutlined style={{ color: '#165DFF' }} />财经新闻（财联社）</Space>}
        extra={<Button type="link" size="small" onClick={() => setExpanded(!expanded)}>{expanded ? '收起' : '全部'}</Button>}
        style={cardS} styles={{ body: { padding: '6px 10px', maxHeight: expanded ? 500 : 180, overflowY: 'auto' } }}>
        {items.length === 0 ? <Text type="secondary" style={{ fontSize: 13 }}>暂无新闻</Text> :
          items.slice(0, limit).map((item, i) => (
            <div key={i} style={{ padding: '6px 0', borderBottom: i < items.length - 1 ? '1px solid #f0f0f0' : 'none', cursor: 'pointer' }}
              onClick={() => setDetail(item)}>
              <Text style={{ fontSize: 13, fontWeight: 500, lineHeight: 1.4, color: 'var(--content-text, #333)' }}>{item.title || '无标题'}</Text>
              <div style={{ display: 'flex', gap: 8, marginTop: 2 }}>
                <Text type="secondary" style={{ fontSize: 11 }}>{item.time || item.date || ''}</Text>
              </div>
            </div>
          ))}
      </Card>
      <Modal title={detail?.title || '新闻详情'} open={!!detail} onCancel={() => setDetail(null)} footer={null} width={700}>
        {detail && (
          <div>
            <Space style={{ marginBottom: 12 }}><Text type="secondary" style={{ fontSize: 12 }}>{detail.date} {detail.time}</Text></Space>
            <div style={{ fontSize: 14, lineHeight: 1.8, whiteSpace: 'pre-wrap' }}>{detail.content || '暂无详细内容'}</div>
          </div>
        )}
      </Modal>
      </>
    );
  };

  // ── 公告卡片 ──
  const AnnounceCard: React.FC<{ items: any[] }> = ({ items }) => {
    const [expanded, setExpanded] = useState(false);
    const [detail, setDetail] = useState<any>(null);
    const limit = expanded ? items.length : 5;
    return (
      <>
      <Card size="small" title={<Space><FileAddOutlined style={{ color: '#165DFF' }} />巨潮公告</Space>}
        extra={<Button type="link" size="small" onClick={() => setExpanded(!expanded)}>{expanded ? '收起' : '全部'}</Button>}
        style={cardS} styles={{ body: { padding: '6px 10px', maxHeight: expanded ? 500 : 180, overflowY: 'auto' } }}>
        {items.length === 0 ? <Text type="secondary" style={{ fontSize: 13 }}>暂无公告</Text> :
          items.slice(0, limit).map((item, i) => (
            <div key={i} style={{ padding: '6px 0', borderBottom: i < items.length - 1 ? '1px solid #f0f0f0' : 'none', cursor: 'pointer' }}
              onClick={() => setDetail(item)}>
              <Text style={{ fontSize: 13, fontWeight: 500, lineHeight: 1.4, color: 'var(--content-text, #333)' }}>{item.title || '无标题'}</Text>
              <div style={{ display: 'flex', gap: 8, marginTop: 2 }}>
                <Tag style={{ fontSize: 10, margin: 0 }}>{item.code}</Tag>
                <Text type="secondary" style={{ fontSize: 11 }}>{item.date || ''}</Text>
              </div>
            </div>
          ))}
      </Card>
      <Modal title={detail?.title || '公告详情'} open={!!detail} onCancel={() => setDetail(null)} footer={null} width={700}>
        {detail && (
          <div>
            <Space style={{ marginBottom: 12 }}>
              <Tag color="blue">{detail.code} {detail.name}</Tag>
              <Text type="secondary" style={{ fontSize: 12 }}>{detail.date}</Text>
            </Space>
            <div style={{ fontSize: 14, lineHeight: 1.8 }}>{detail.title}</div>
            {detail.adjunct_url && (
              <div style={{ marginTop: 16 }}>
                <Button type="primary" icon={<EyeOutlined />}
                  onClick={() => window.open('https://www.cninfo.com.cn/new/disclosure/detail?announcementId=' + detail.announcement_id, '_blank')}>
                  查看原文PDF
                </Button>
              </div>
            )}
          </div>
        )}
      </Modal>
      </>
    );
  };

  return (
    <Row gutter={12}>
      <Col xs={24} lg={12}>
        <NewsCard items={newsItems} />
      </Col>
      <Col xs={24} lg={12}>
        <AnnounceCard items={announceItems} />
      </Col>
    </Row>
  );
};


// ========== 风险监控（ST股票 + 突发事件，从仪表盘移入）==========
const RiskMonitorTab: React.FC = () => {
  const [stData, setStData] = useState<any>(null);
  const [eventData, setEventData] = useState<any>(null);
  const [stDetail, setStDetail] = useState<any>(null);
  const [stModalOpen, setStModalOpen] = useState(false);
  const [eventDetail, setEventDetail] = useState<any>(null);
  const [eventModalOpen, setEventModalOpen] = useState(false);

  useEffect(() => {
    fetch('/api/v1/dashboard/st-list').then(r => r.json()).then(setStData).catch(() => {});
    fetch('/api/v1/dashboard/event-stocks').then(r => r.json()).then(setEventData).catch(() => {});
  }, []);

  const cardS: React.CSSProperties = { borderRadius: 8, marginBottom: 12 };

  const stColumns = [
    { title: '代码', dataIndex: 'code', key: 'code', width: 80,
      render: (v: string) => <Text style={{ fontFamily: 'monospace', fontSize: 11 }}>{v}</Text> },
    { title: '名称', dataIndex: 'name', key: 'name', width: 100,
      render: (v: string, r: any) => (
        <span>
          <Tag color={r.st_type === '*ST' ? 'red' : 'orange'} style={{ fontSize: 10, marginRight: 4 }}>{r.st_type}</Tag>
          <Text style={{ fontSize: 12 }}>{v.replace(/^[*SST]+/, '')}</Text>
        </span>
      )
    },
    { title: '最新价', dataIndex: 'price', key: 'price', width: 60,
      render: (v: any) => v && v !== '-' ? <Text style={{ fontSize: 11 }}>{v}</Text> : null },
    { title: '涨跌幅', dataIndex: 'change_pct', key: 'change_pct', width: 60,
      render: (v: any) => v && v !== '-' ? <Text style={{ fontSize: 11, color: Number(v) > 0 ? '#F53F3F' : '#00B42A' }}>{v}%</Text> : null },
    { title: 'ST日期', dataIndex: 'st_date', key: 'st_date', width: 80,
      render: (v: string) => v ? <Text type="secondary" style={{ fontSize: 11 }}>{v}</Text> : null },
  ];

  const eventColumns = [
    { title: '代码', dataIndex: 'code', key: 'code', width: 80,
      render: (v: string) => <Text style={{ fontFamily: 'monospace', fontSize: 11 }}>{v}</Text> },
    { title: '名称', dataIndex: 'name', key: 'name', width: 80,
      render: (v: string) => <Text style={{ fontSize: 11 }}>{v}</Text> },
    { title: '事件', dataIndex: 'events', key: 'events',
      render: (events: any[]) => (
        <div style={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
          {events.slice(0, 2).map((e: any, i: number) => (
            <Tag key={i} color={e.label.includes('财务造假') || e.label.includes('否定') ? 'red' : 'orange'} style={{ fontSize: 9, margin: 0 }}>{e.label.slice(0, 8)}</Tag>
          ))}
          {events.length > 2 && <Text type="secondary" style={{ fontSize: 9 }}>+{events.length - 2}</Text>}
        </div>
      )
    },
    { title: '发生日期', dataIndex: 'latest_date', key: 'latest_date', width: 80,
      render: (v: string) => v ? <Text type="secondary" style={{ fontSize: 11 }}>{v}</Text> : null },
  ];

  const openStDetail = async (code: string) => {
    try {
      const r = await fetch('/api/v1/dashboard/st-detail/' + code);
      const d = await r.json();
      setStDetail(d);
      setStModalOpen(true);
    } catch {}
  };

  const openEventDetail = (item: any) => {
    setEventDetail(item);
    setEventModalOpen(true);
  };

  return (
    <div>
      <Row gutter={12}>
        <Col xs={24} lg={12}>
          <Card size="small" title={<Space><AlertOutlined style={{ color: '#F53F3F' }} />ST股票列表（共{(stData?.items || []).length}只）</Space>}
            style={cardS} styles={{ body: { padding: 0, maxHeight: 350, overflowY: 'auto' } }}>
            <Table dataSource={stData?.items || []} columns={stColumns} rowKey="code" size="small" pagination={false}
              onRow={(record) => ({ onClick: () => openStDetail(record.code), style: { cursor: 'pointer', fontSize: 12 } })}
              scroll={{ x: 380 }} locale={{ emptyText: <Empty description="暂无数据" /> }} />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card size="small" title={<Space><AlertOutlined style={{ color: '#F53F3F' }} />突发事件（共{(eventData?.items || []).length}只）</Space>}
            style={cardS} styles={{ body: { padding: 0, maxHeight: 350, overflowY: 'auto' } }}>
            <Table dataSource={eventData?.items || []} columns={eventColumns} rowKey="code" size="small" pagination={false}
              onRow={(record) => ({ onClick: () => openEventDetail(record), style: { cursor: 'pointer', fontSize: 12 } })}
              scroll={{ x: 280 }} locale={{ emptyText: <Empty description="暂无数据" /> }} />
          </Card>
        </Col>
      </Row>

      {/* ST详情弹窗 */}
      <Modal title={stDetail?.code ? `ST原因 - ${stDetail.code}` : 'ST股票详情'}
        open={stModalOpen} onCancel={() => setStModalOpen(false)} footer={null} width={650}>
        {stDetail?.st_reasons?.length > 0 ? (
          <div>
            {stDetail.st_reasons.map((r: any, i: number) => (
              <div key={i} style={{ padding: '12px 0', borderBottom: i < stDetail.st_reasons.length - 1 ? '1px solid #f0f0f0' : 'none' }}>
                <Space style={{ marginBottom: 6 }}>
                  <Tag color={r.reason?.includes('净资产') ? 'red' : r.reason ? 'orange' : 'default'}>{r.reason || 'ST相关'}</Tag>
                  <Text type="secondary" style={{ fontSize: 11 }}>{r.date}</Text>
                  {r.url && (
                    <Button type="link" size="small" icon={<EyeOutlined />} style={{ padding: 0, height: 'auto', fontSize: 11 }}
                      onClick={() => window.open(r.url, '_blank')}>查看公告</Button>
                  )}
                </Space>
                <div style={{ fontSize: 13, lineHeight: 1.5 }}>{r.title}</div>
              </div>
            ))}
          </div>
        ) : (
          <Text type="secondary">{stDetail?.note || '未找到ST相关公告'}</Text>
        )}
      </Modal>

      {/* 突发事件详情弹窗 */}
      <Modal title={eventDetail ? `${eventDetail.code} ${eventDetail.name} - 突发事件详情` : '突发事件详情'}
        open={eventModalOpen} onCancel={() => setEventModalOpen(false)} footer={null} width={650}>
        {eventDetail?.events?.length > 0 ? (
          <div>
            {eventDetail.events.map((e: any, i: number) => (
              <div key={i} style={{ padding: '12px 0', borderBottom: i < eventDetail.events.length - 1 ? '1px solid #f0f0f0' : 'none' }}>
                <Space style={{ marginBottom: 6 }}>
                  <Tag color={e.label.includes('财务造假') || e.label.includes('否定') ? 'red' : e.label.includes('谴责') || e.label.includes('处罚') ? 'orange' : 'blue'}>{e.label}</Tag>
                  <Text type="secondary" style={{ fontSize: 11 }}>{e.date}</Text>
                </Space>
                <div style={{ fontSize: 13, lineHeight: 1.5 }}>{e.title || '无标题'}</div>
                {e.url && (
                  <Button type="link" size="small" icon={<EyeOutlined />} style={{ padding: 0, marginTop: 4 }}
                    onClick={() => window.open(e.url, '_blank')}>查看原文</Button>
                )}
              </div>
            ))}
          </div>
        ) : (
          <Text type="secondary">暂无事件数据</Text>
        )}
      </Modal>
    </div>
  );
};


const MarketResearchPage: React.FC = () => {
  const [tab, setTab] = useState('research');
  const items = [
    { key: 'indices', label: '全球指数', children: <GlobalIndices /> },
    { key: 'industry', label: '行业排名', children: <IndustryRanking /> },
    { key: 'moneyflow', label: '个股资金流向', children: <StockMoneyFlow /> },
    { key: 'research', label: '个股研报', children: <StockResearchReportTab /> },
    { key: 'notice', label: '公司公告', children: <StockNoticeTab /> },
    { key: 'industry_research', label: '行业研究', children: <IndustryResearchTab /> },
    { key: 'premarket', label: '盘前提示', children: <PremarketTipSection /> },
    { key: 'limitup', label: '涨停梯队', children: <LimitUpTierTab /> },
    { key: 'stocks_risk', label: '风险监控', children: <RiskMonitorTab /> },
    { key: 'news', label: '快讯公告', children: <NewsAndAnnounceTab /> },
  ];

  return (
    <div>
      <Card style={{ borderRadius: 8, marginBottom: 12 }} styles={{ body: { padding: "12px 16px" } }}>
        <Space>
          <Title level={5} style={{ margin: 0 }}>🔬 研究中心</Title>
          <Text type="secondary">数据来源：东方财富 / 腾讯财经</Text>
        </Space>
      </Card>
      <Card style={{ borderRadius: 8 }} styles={{ body: { padding: "12px 16px" } }}>
        <Tabs activeKey={tab} onChange={setTab} items={items} />
      </Card>
    </div>
  );
  };



// ========== 快讯公告（财联社快讯 + 巨潮公告，从仪表盘移入）==========

export default MarketResearchPage;
 