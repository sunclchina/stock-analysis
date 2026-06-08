/**
 * 仪表盘页面（设计规范 v2.0）
 * - 顶部状态栏 + 中间核心数据区
 * - 卡片：盘前提示、实时行情监控
 * - CPU/内存快捷操作右侧辅助
 */
import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import ErrorBoundary from '../../components/ErrorBoundary';
import DecisionBoard from '../../components/DecisionBoard';
import { authFetch } from '../../services/auth';
import {
  Card, Tag, Spin, Progress, Table, Typography, Tooltip, Space, Button, Empty, Modal,
} from 'antd';
import {
  FundOutlined, AlertOutlined, RiseOutlined, FallOutlined, MinusOutlined,
  CloudServerOutlined, ReloadOutlined, SettingOutlined, QuestionCircleOutlined,
  EyeOutlined, PlusOutlined, FileAddOutlined, SwapOutlined, StopOutlined, StarOutlined, DashboardOutlined, BarChartOutlined,
} from '@ant-design/icons';
import type { StockSnapshot, SystemStatusInfo } from '../../types/dashboard';

const { Text } = Typography;

// ─── 工具函数 ───

function trendColor(v: number): string {
  if (v > 0) return '#F53F3F';
  if (v < 0) return '#00B42A';
  return '#8c8c8c';
}

function trendIcon(v: number) {
  if (v > 0) return <RiseOutlined style={{ color: '#F53F3F', fontSize: 12 }} />;
  if (v < 0) return <FallOutlined style={{ color: '#00B42A', fontSize: 12 }} />;
  return <MinusOutlined style={{ color: '#8c8c8c', fontSize: 12 }} />;
}

const cardS: React.CSSProperties = { borderRadius: 8, height: '100%', boxShadow: '0 2px 8px rgba(0,0,0,0.08)' };
const cardB: React.CSSProperties = { padding: '14px 16px' };

// ─── 交易时段倒计时组件 ───

function pad2(n: number): string {
  return String(n).padStart(2, '0');
}

function getMinutesOfDay(d: Date): number {
  return d.getHours() * 60 + d.getMinutes();
}

function isWeekday(d: Date): boolean {
  const day = d.getDay();
  return day >= 1 && day <= 5;
}

/** 计算下一交易时段开盘时间 */
function getNextOpenDate(from: Date): Date {
  const next = new Date(from);
  next.setSeconds(0);
  next.setMilliseconds(0);
  const minutes = getMinutesOfDay(from);
  const day = from.getDay();

  if (isWeekday(from)) {
    if (minutes < 540) { // 9:00 之前 → 当天 9:30
      next.setHours(9, 30, 0, 0);
      return next;
    }
    if (minutes >= 690 && minutes < 780) { // 午休 11:30-13:00 → 当天 13:00
      next.setHours(13, 0, 0, 0);
      return next;
    }
    // 15:00 之后 → 下一交易日 9:30
    next.setDate(next.getDate() + 1);
    next.setHours(9, 30, 0, 0);
    while (next.getDay() === 0 || next.getDay() === 6) {
      next.setDate(next.getDate() + 1);
    }
    return next;
  }

  // 周末 → 周一 9:30
  next.setDate(next.getDate() + 1);
  next.setHours(9, 30, 0, 0);
  while (next.getDay() === 0 || next.getDay() === 6) {
    next.setDate(next.getDate() + 1);
  }
  return next;
}


// ─── A股概况卡片 ───

interface AStockOverviewData {
  shanghai: {
    total: number;
    main_board: { count: number; prefixes: string[] };
    star: { count: number; prefixes: string[] };
    b_share: { count: number; prefixes: string[] };
  };
  shenzhen: {
    total: number;
    main_board: { count: number; prefixes: string[] };
    gem: { count: number; prefixes: string[] };
    b_share: { count: number; prefixes: string[] };
  };
  beijing: {
    total: number;
    all: { count: number; prefixes: string[] };
  };
  etf?: {
    shanghai: { count: number; prefixes: string[] };
    shenzhen: { count: number; prefixes: string[] };
    total: number;
  };
  total_stock_count?: number;
  generated_at?: string;
}

const AStockOverviewCard: React.FC<{ data: AStockOverviewData | null }> = ({ data }) => {
  if (!data) return null;
  const s = (v: number) => v.toLocaleString();
  return (
    <Card size="small" title={<Space><FundOutlined style={{ color: '#165DFF' }} />A股概况</Space>}
      style={{ ...cardS, height: 'auto' }} styles={{ body: { padding: '6px 12px' } }}>
      <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap' }}>
        {/* 沪市 */}
        <div style={{ minWidth: 170, flex: 1 }}>
          <div style={{ fontSize: 14, fontWeight: 700, color: '#165DFF', marginBottom: 2, borderBottom: '1px solid #165DFF', paddingBottom: 2 }}>
            沪市 {s(data.shanghai.total)}
          </div>
          <div style={{ fontSize: 13, lineHeight: 1.7 }}>
            <div>主板（600/601/603/605）<span style={{ float: 'right', fontWeight: 600 }}>{s(data.shanghai.main_board.count)}</span></div>
            <div>科创板（688）<span style={{ float: 'right', fontWeight: 600 }}>{s(data.shanghai.star.count)}</span></div>
            <div>沪市B股（900）<span style={{ float: 'right', fontWeight: 600 }}>{s(data.shanghai.b_share.count)}</span></div>
          </div>
        </div>
        {/* 深市 */}
        <div style={{ minWidth: 170, flex: 1 }}>
          <div style={{ fontSize: 14, fontWeight: 700, color: '#165DFF', marginBottom: 2, borderBottom: '1px solid #165DFF', paddingBottom: 2 }}>
            深市 {s(data.shenzhen.total)}
          </div>
          <div style={{ fontSize: 13, lineHeight: 1.7 }}>
            <div>主板（000/001/002/003/004）<span style={{ float: 'right', fontWeight: 600 }}>{s(data.shenzhen.main_board.count)}</span></div>
            <div>创业板（300/301）<span style={{ float: 'right', fontWeight: 600 }}>{s(data.shenzhen.gem.count)}</span></div>
            <div>深市B股（200）<span style={{ float: 'right', fontWeight: 600 }}>{s(data.shenzhen.b_share.count)}</span></div>
          </div>
        </div>
        {/* 北交所 */}
        <div style={{ minWidth: 140, flex: 1 }}>
          <div style={{ fontSize: 14, fontWeight: 700, color: '#165DFF', marginBottom: 2, borderBottom: '1px solid #165DFF', paddingBottom: 2 }}>
            北交所（920）{s(data.beijing.total)}
          </div>
          <div style={{ fontSize: 13, lineHeight: 1.7 }}>
            <div>全部<span style={{ float: 'right', fontWeight: 600 }}>{s(data.beijing.all.count)}</span></div>
          </div>
          <div style={{ fontSize: 13, marginTop: 4, color: '#666' }}>
            <div style={{ fontWeight: 600, marginBottom: 1 }}>ETF</div>
            <div>沪市（51/52/56/58）<span style={{ float: 'right', fontWeight: 600, color: '#165DFF' }}>{s(data.etf?.shanghai.count ?? 0)}</span></div>
            <div>深市（159）<span style={{ float: 'right', fontWeight: 600, color: '#165DFF' }}>{s(data.etf?.shenzhen.count ?? 0)}</span></div>
          </div>
        </div>
      </div>
    </Card>
  );
};

// ─── 盘前提示卡片 ───

function renderPremarketContent(text: string): React.ReactNode {
  return <div style={{ fontSize: 13, lineHeight: 1.9, whiteSpace: 'pre-wrap', color: 'var(--content-text, #333)' }}>{text}</div>;
}

const PremarketCard: React.FC<{ tip: any }> = ({ tip }) => {
  const [expanded, setExpanded] = useState(false);
  if (!tip) return null;
  const sections = tip.sections || [];
  const preview = sections.length > 0
    ? (sections[0]?.content || '').slice(0, 50).replace(/[\n【]+/g, ' ') + '…'
    : (tip.marketPrediction || '').slice(0, 50) || '暂无盘前提示';
  return (
    <Card size="small" title={<Space><DashboardOutlined style={{ color: '#165DFF' }} />盘前提示</Space>}
      extra={<Button type="link" size="small" onClick={() => setExpanded(!expanded)}>{expanded ? '收起' : '展开'}</Button>}
      style={cardS} styles={{ body: { ...cardB, padding: expanded ? '14px 16px' : '8px 16px' } }}>
      {!expanded ? <Text style={{ fontSize: 13 }}>📌 {preview}</Text> : (
        <div style={{ maxHeight: 400, overflowY: 'auto', paddingRight: 4 }}>
          {sections.length > 0 ? sections.map((sec: any, idx: number) => (
            <div key={idx} style={{ marginBottom: 16 }}>
              <div style={{
                fontSize: 14, fontWeight: 700, color: '#165DFF',
                padding: '6px 0', marginBottom: 6,
                borderBottom: '2px solid #165DFF',
              }}>{sec.title}</div>
              {renderPremarketContent(sec.content)}
            </div>
          )) : (
            <div style={{ fontSize: 13, lineHeight: 1.9, whiteSpace: 'pre-wrap' }}>
              {tip.marketPrediction || '暂无盘前提示数据'}
            </div>
          )}
          <div style={{ fontSize: 11, color: '#999', textAlign: 'right', marginTop: 8 }}>
            更新于: {tip.updatedAt || tip.generatedAt || '-'} | 数据源: {tip.dataSource || tip.source || '-'}
          </div>
        </div>
      )}
    </Card>
  );
};

// ─── 实时行情监控汇总卡片 ───

const MarketMonitorCard: React.FC<{ quotes: StockSnapshot[]; onRefresh: () => void }> = ({ quotes, onRefresh }) => {
  const total = quotes.length;
  const up = quotes.filter(q => q.changePercent > 0).length;
  const down = quotes.filter(q => q.changePercent < 0).length;
  return (
    <Card size="small" title={<Space><FundOutlined style={{ color: '#165DFF' }} />实时行情监控</Space>}
      extra={<Button type="link" size="small" icon={<ReloadOutlined />} onClick={onRefresh} />}
      style={cardS} styles={{ body: { padding: '24px 16px' } }}>
      <div style={{ display: 'flex', justifyContent: 'space-around', textAlign: 'center' }}>
        <div>
          <Text style={{ fontSize: 32, fontWeight: 700, color: '#165DFF' }}>{total}</Text>
          <div><Text type="secondary" style={{ fontSize: 13 }}>监控股票</Text></div>
        </div>
        <div>
          <Text style={{ fontSize: 32, fontWeight: 700, color: '#F53F3F' }}>{up}</Text>
          <div><Text type="secondary" style={{ fontSize: 13 }}>价格上涨</Text></div>
        </div>
        <div>
          <Text style={{ fontSize: 32, fontWeight: 700, color: '#00B42A' }}>{down}</Text>
          <div><Text type="secondary" style={{ fontSize: 13 }}>价格下跌</Text></div>
        </div>
      </div>
    </Card>
  );
};

// ─── 右侧辅助区 ───

const SidePanel: React.FC<{
  resources: SystemStatusInfo | null;
  quotes: StockSnapshot[];
  watchlistQuotes?: StockSnapshot[];
  portfolioSummary?: any;
}> = ({ resources, quotes, watchlistQuotes, portfolioSummary }) => {
  const navigate = useNavigate();
  const total = quotes.length;
  const up = quotes.filter(q => q.changePercent > 0).length;
  const down = quotes.filter(q => q.changePercent < 0).length;
  const wlTotal = watchlistQuotes?.length ?? 0;
  const wlUp = (watchlistQuotes ?? []).filter(q => q.changePercent > 0).length;
  const wlDown = (watchlistQuotes ?? []).filter(q => q.changePercent < 0).length;
  const cpu = resources?.resources?.cpu ?? 32;
  const mem = resources?.resources?.memory ?? 55;
  const uptime = resources?.resources?.uptime ?? '7天 3小时';
  const pf = portfolioSummary || {};
  const fmt = (v: number) => {
    if (v >= 10000) return (v / 10000).toFixed(2) + '万元';
    return v.toFixed(2) + '元';
  };
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {/* 实时行情监控汇总（小卡片） */}
      <Card size="small" title={<Space><FundOutlined style={{ color: '#165DFF' }} />实时行情</Space>}
        style={cardS} styles={{ body: { padding: '12px 8px' } }}>
        <div style={{ display: 'flex', justifyContent: 'space-around', textAlign: 'center' }}>
          <div>
            <Text style={{ fontSize: 22, fontWeight: 700, color: '#165DFF' }}>{total}</Text>
            <div><Text type="secondary" style={{ fontSize: 11 }}>监控</Text></div>
          </div>
          <div>
            <Text style={{ fontSize: 22, fontWeight: 700, color: '#F53F3F' }}>{up}</Text>
            <div><Text type="secondary" style={{ fontSize: 11 }}>上涨</Text></div>
          </div>
          <div>
            <Text style={{ fontSize: 22, fontWeight: 700, color: '#00B42A' }}>{down}</Text>
            <div><Text type="secondary" style={{ fontSize: 11 }}>下跌</Text></div>
          </div>
        </div>
      </Card>

      {/* 自选股卡片 */}
      <Card size="small" title={<Space><StarOutlined style={{ color: '#F59E0B' }} />自选股</Space>}
        extra={<Button type="link" size="small" onClick={() => navigate('/config')}>管理</Button>}
        style={cardS} styles={{ body: { padding: '12px 8px' } }}>
        <div style={{ display: 'flex', justifyContent: 'space-around', textAlign: 'center' }}>
          <div>
            <Text style={{ fontSize: 22, fontWeight: 700, color: '#165DFF' }}>{wlTotal}</Text>
            <div><Text type="secondary" style={{ fontSize: 11 }}>自选股</Text></div>
          </div>
          <div>
            <Text style={{ fontSize: 22, fontWeight: 700, color: '#F53F3F' }}>{wlUp}</Text>
            <div><Text type="secondary" style={{ fontSize: 11 }}>上涨</Text></div>
          </div>
          <div>
            <Text style={{ fontSize: 22, fontWeight: 700, color: '#00B42A' }}>{wlDown}</Text>
            <div><Text type="secondary" style={{ fontSize: 11 }}>下跌</Text></div>
          </div>
        </div>
      </Card>

      {/* 资产管理卡片 */}
      <Card size="small" title={<Space><FundOutlined style={{ color: '#52C41A' }} />资产管理</Space>}
        extra={<Button type="link" size="small" onClick={() => navigate('/portfolio')}>管理</Button>}
        style={cardS} styles={{ body: { padding: '12px 14px' } }}>
        <div style={{ fontSize: 13, lineHeight: 2 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <Text type="secondary">总资产</Text>
            <Text style={{ fontWeight: 600 }}>{pf.total_assets != null ? fmt(pf.total_assets) : '—'}</Text>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <Text type="secondary">可用资金</Text>
            <Text>{pf.total_cash != null ? fmt(pf.total_cash) : '—'}</Text>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <Text type="secondary">仓位</Text>
            <Text style={{ color: (pf.position_ratio || 0) > 70 ? '#F53F3F' : '#52C41A' }}>{pf.position_ratio != null ? pf.position_ratio.toFixed(1) + '%' : '—'}</Text>
          </div>
          <div style={{ borderTop: '1px solid #f0f0f0', margin: '4px 0' }} />
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <Text type="secondary">总收益</Text>
            <Text style={{ color: (pf.total_profit || 0) >= 0 ? '#F53F3F' : '#00B42A', fontWeight: 600 }}>{pf.total_profit != null ? fmt(pf.total_profit) : '—'}</Text>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <Text type="secondary">收益率</Text>
            <Text style={{ color: (pf.total_profit_rate || 0) >= 0 ? '#F53F3F' : '#00B42A' }}>{pf.total_profit_rate != null ? (pf.total_profit_rate >= 0 ? '+' : '') + pf.total_profit_rate.toFixed(2) + '%' : '—'}</Text>
          </div>
          <div style={{ borderTop: '1px solid #f0f0f0', margin: '4px 0' }} />
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <Text type="secondary">持股数</Text>
            <Text>{pf.position_count != null ? pf.position_count + ' 只' : '—'}</Text>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <Text type="secondary">清仓股票</Text>
            <Text>{pf.close_position_count != null ? pf.close_position_count + ' 只' : '—'}</Text>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <Text type="secondary">虚拟账户</Text>
            <Text>{pf.account_count != null ? pf.account_count + ' 个' : '—'}</Text>
          </div>
        </div>
      </Card>

      {/* 系统资源监控 */}
      <Card size="small" title={<Space><CloudServerOutlined style={{ color: '#165DFF' }} />系统资源</Space>} style={cardS} styles={{ body: cardB }}>
        <div style={{ marginBottom: 8 }}>
          <Space style={{ justifyContent: 'space-between', width: '100%' }}><Text style={{ fontSize: 12 }}>CPU</Text><Text style={{ fontSize: 12, fontWeight: 600, color: cpu > 80 ? '#FF4D4F' : undefined }}>{cpu}%</Text></Space>
          <Progress percent={cpu} size="small" showInfo={false} strokeColor={cpu > 80 ? '#FF4D4F' : '#165DFF'} />
        </div>
        <div style={{ marginBottom: 8 }}>
          <Space style={{ justifyContent: 'space-between', width: '100%' }}><Text style={{ fontSize: 12 }}>内存</Text><Text style={{ fontSize: 12, fontWeight: 600, color: mem > 90 ? '#FF4D4F' : undefined }}>{mem}%</Text></Space>
          <Progress percent={mem} size="small" showInfo={false} strokeColor={mem > 90 ? '#FF4D4F' : '#165DFF'} />
        </div>
        <Text type="secondary" style={{ fontSize: 11 }}>运行时长: {uptime}</Text>
      </Card>

    </div>
  );
};

// ─── ST股票列表卡片 + 突发事件卡片（已移至研究中心） ───

// ─── 主页面 ───

const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const pad = (n: number) => String(n).padStart(2, '0');
  const d0 = new Date();
  const [marketQuotes, setMarketQuotes] = useState<StockSnapshot[]>([]);
  const [watchlistQuotes, setWatchlistQuotes] = useState<StockSnapshot[]>([]);
  const [systemStatus, setSystemStatus] = useState<SystemStatusInfo | null>(null);
  const [aStockOverview, setAStockOverview] = useState<AStockOverviewData | null>(null);

  const [portfolioSummary, setPortfolioSummary] = useState<any>(null);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      await Promise.all([
        authFetch('/api/v1/market/quotes').then(r => r.json()).then(d => setMarketQuotes((d.quotes || d.items || []).map((q: any) => ({ code: q.code, name: q.name, price: q.price || q.latestPrice, changePercent: q.change_pct || q.changePercent, trendColor: (q.change_pct || 0) > 0 ? 'red' : (q.change_pct || 0) < 0 ? 'green' : 'gray' })))).catch(() => {}),
        fetch('/api/v1/system/status').then(r => r.json()).then(d => setSystemStatus(d)).catch(() => {}),
        fetch('/api/v1/dashboard/a-share-overview').then(r => r.json()).then(d => setAStockOverview(d)).catch(() => {}),
        authFetch('/api/v1/market/watchlist-quotes').then(r => r.json()).then(d => setWatchlistQuotes((d.quotes || []).map((q: any) => ({ code: q.code, name: q.name, price: q.price || q.latestPrice, changePercent: q.change_pct || q.changePercent, trendColor: (q.change_pct || 0) > 0 ? 'red' : (q.change_pct || 0) < 0 ? 'green' : 'gray' })))).catch(() => {}),

        authFetch('/api/v1/portfolio/dashboard').then(r => r.json()).then(d => setPortfolioSummary(d)).catch(() => {}),
      ]);
    } finally { setLoading(false); }
  }, []);

  // 响应式：检测视口宽度
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);
  useEffect(() => {
    const onResize = () => setIsMobile(window.innerWidth < 768);
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  useEffect(() => {
    fetchAll();
    const refreshInterval = setInterval(fetchAll, 30000);
    return () => { clearInterval(refreshInterval); };
  }, [fetchAll]);

  const colStack = { flexDirection: 'column' as const, gap: 12, flex: 1, minWidth: 0 };
  const colRow = { display: 'flex', gap: 12 };
  const colRowMobile = { display: 'flex', flexDirection: 'column' as const, gap: 12 };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: isMobile ? 8 : 12, flex: 1 }}>
      {isMobile ? (
        /* 移动端：全部纵向堆叠，不分主栏/侧栏 */
        <>
          <AStockOverviewCard data={aStockOverview} />
          <DecisionBoard />
          <SidePanel resources={systemStatus} quotes={marketQuotes} watchlistQuotes={watchlistQuotes} portfolioSummary={portfolioSummary} />
        </>
      ) : (
        /* 桌面端：主栏+侧栏 */
        <>
          <div className="dashboard-main-row" style={{ display: 'flex', gap: 12, flex: 1, minHeight: 0 }}>
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 12, overflow: 'auto', minWidth: 0 }}>
              <AStockOverviewCard data={aStockOverview} />
              <div className="dashboard-col-row" style={{ display: 'flex', gap: 12 }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <DecisionBoard />
                </div>
              </div>
            </div>
            <div className="dashboard-sidepanel" style={{ width: 280, flexShrink: 0 }}>
              <SidePanel resources={systemStatus} quotes={marketQuotes} watchlistQuotes={watchlistQuotes} portfolioSummary={portfolioSummary} />
            </div>
          </div>
        </>
      )}
    </div>
  );
};

const Wrapped: React.FC = () => (
  <ErrorBoundary title="仪表盘异常" description="仪表盘模块发生异常，请重试。"><DashboardPage /></ErrorBoundary>
);
export default Wrapped;
