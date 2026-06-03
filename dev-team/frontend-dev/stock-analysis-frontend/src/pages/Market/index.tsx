import React, { useEffect, useCallback, useRef, useState } from 'react';
import ErrorBoundary from '../../components/ErrorBoundary';
import { Row, Col, Card, Tag, Spin, Typography, Space, Button, Switch, Divider } from 'antd';
import {
  StockOutlined,
  ReloadOutlined,
  SyncOutlined,
  PauseCircleOutlined,
  PlayCircleOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import { useMarketStore } from '../../store/marketStore';
import { subscribe } from '../../services/websocket';
import { getAnomalies } from '../../services/marketApi';
import type { StockSnapshot } from '../../types/dashboard';
import type { StockQuote, TradingAnomaly } from '../../types/market';

import MarketOverview from './MarketOverview';
import StockQuoteTable from './StockQuoteTable';
import StockDetailDrawer from './StockDetailDrawer';
import DataSourceIndicator from './DataSourceIndicator';
import SectorCard from '../../components/SectorCard';


const { Text } = Typography;

/** 将 StockSnapshot 转为 StockQuote（WebSocket数据融合） */
function snapshotToQuote(snapshot: StockSnapshot): Partial<StockQuote> {
  return {
    code: snapshot.code,
    name: snapshot.name,
    latestPrice: snapshot.price,
    changePercent: snapshot.changePercent,
    trendColor: snapshot.trendColor,
  };
}

const MarketPage: React.FC = () => {
  const {
    // State
    marketIndices, indicesLoading,
    stockQuotes, quotesLoading, quoteFilter,
    dataSourceState,
    detailOpen, detailQuote, detailKline, detailTimeshare, detailIndicators, detailLoading,
    refreshInterval, autoRefreshEnabled,

    // Actions
    fetchMarketIndices, fetchStockQuotes, fetchDataSourceState,
    setQuoteFilter, setRefreshInterval, setAutoRefresh,
    openDetail, closeDetail, refreshDetail, applyQuoteUpdate,
  } = useMarketStore();

  // ── 涨跌分布 & 板块排行 ──
  const [advDecl, setAdvDecl] = useState<{ up: number; down: number; flat: number; total: number; limit_up: number; limit_down: number } | null>(null);
  const [industries, setIndustries] = useState<any[]>([]);
  const [concepts, setConcepts] = useState<any[]>([]);
  const [sectorsLoading, setSectorsLoading] = useState(false);

  const fetchAdvDecl = useCallback(async () => {
    try {
      const res = await fetch('/api/v1/market/advance-decline').then(r => r.json());
      if (res && res.total > 0) setAdvDecl(res);
    } catch { /* ignore */ }
  }, []);

  const fetchSectors = useCallback(async () => {
    setSectorsLoading(true);
    try {
      const [indRes, conRes] = await Promise.all([
        fetch('/api/v1/market/industry-ranking?count=10').then(r => r.json()).catch(() => []),
        fetch('/api/v1/market/concept-sectors').then(r => r.json()).catch(() => []),
      ]);
      if (Array.isArray(indRes)) setIndustries(indRes);
      if (Array.isArray(conRes)) setConcepts(conRes);
    } catch { /* ignore */ }
    setSectorsLoading(false);
  }, []);

  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ========== Fetch anomalies alongside quotes ==========
  const fetchQuotesWithAnomalies = useCallback(async (codes?: string, silent?: boolean) => {
    await fetchStockQuotes(codes, silent);
    // 从 store 获取当前 quotes 的代码列表用于异动检测
    const { stockQuotes: currentQuotes } = useMarketStore.getState();
    const currentCodes = currentQuotes.map(q => q.code).filter(Boolean);
    if (currentCodes.length > 0) {
      try {
        const anomalies = await getAnomalies(currentCodes);
        if (Object.keys(anomalies).length > 0) {
          // 将异动合并到stockQuotes
          useMarketStore.setState((state) => ({
            stockQuotes: state.stockQuotes.map((q) => ({
              ...q,
              anomalies: anomalies[q.code] || q.anomalies,
            })),
          }));
        }
      } catch { /* ignore */ }
    }
  }, [fetchStockQuotes]);

  // ========== Initial load ==========
  useEffect(() => {
    fetchMarketIndices(true);
    fetchQuotesWithAnomalies();
    fetchDataSourceState();
    fetchAdvDecl();
    fetchSectors();
  }, [fetchMarketIndices, fetchQuotesWithAnomalies, fetchDataSourceState, fetchAdvDecl, fetchSectors]);

  // ========== Auto refresh timer ==========
  useEffect(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }

    if (autoRefreshEnabled && refreshInterval > 0) {
      timerRef.current = setInterval(() => {
        // 自动刷新：silent=true，不触发 loading 状态，避免页面闪烁
        fetchQuotesWithAnomalies(undefined, true);
        fetchMarketIndices(true);
      }, refreshInterval);
    }

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [autoRefreshEnabled, refreshInterval, fetchStockQuotes, fetchMarketIndices]);

  // ========== WebSocket subscription (use ref to avoid re-subscribe on every data update) ==========
  const stockQuotesRef = useRef(stockQuotes);
  stockQuotesRef.current = stockQuotes;

  useEffect(() => {
    const unsubMarket = subscribe('market:update', (data: unknown) => {
      const snapshots = data as StockSnapshot[];
      if (Array.isArray(snapshots) && snapshots.length > 0) {
        const currentQuotes = stockQuotesRef.current;
        const updates = snapshots.map((s) => {
          const partial = snapshotToQuote(s);
          const existing = currentQuotes.find((q) => q.code === partial.code);
          return {
            ...(existing || { volume: 0, amount: 0, turnoverRate: 0, amplitude: 0, trendColor: 'gray' as const }),
            ...partial,
          } as StockQuote;
        });
        applyQuoteUpdate(updates);
      }
    });

    return () => {
      unsubMarket();
    };
  }, [applyQuoteUpdate]);

  // ========== Refresh handlers（手动刷新=显示loading，自动刷新=silent=true）==========
  const handleRefreshAll = useCallback(() => {
    fetchMarketIndices();
    fetchStockQuotes();
    fetchDataSourceState();
    fetchAdvDecl();
    fetchSectors();
  }, [fetchMarketIndices, fetchStockQuotes, fetchDataSourceState, fetchAdvDecl, fetchSectors]);

  const handleQuoteRefresh = useCallback(() => {
    fetchStockQuotes();
  }, [fetchStockQuotes]);

  const handleOpenDetail = useCallback((code: string) => {
    openDetail(code);
  }, [openDetail]);

  const handleCloseDetail = useCallback(() => {
    closeDetail();
  }, [closeDetail]);

  const handleRefreshDetail = useCallback(() => {
    refreshDetail();
  }, [refreshDetail]);

  const handleFilterChange = useCallback((filter: { keyword: string; tag: string }) => {
    setQuoteFilter({ keyword: filter.keyword, tag: filter.tag as 'all' | 'watchlist' });
  }, [setQuoteFilter]);

  // ========== Render ==========
  return (
    <div>
      {/* 操作工具栏 */}
      <div
        style={{
          marginBottom: 12,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 8,
        }}
      >
        <DataSourceIndicator dataSource={dataSourceState} />
        <Space size={10} wrap align="center">
          {/* Auto refresh toggle */}
          <Space size={4} style={{ background: '#f5f5f5', borderRadius: 6, padding: '2px 8px' }}>
            {autoRefreshEnabled ? (
              <SyncOutlined style={{ color: '#52c41a', fontSize: 12 }} />
            ) : (
              <PauseCircleOutlined style={{ color: '#8c8c8c', fontSize: 12 }} />
            )}
            <Text type="secondary" style={{ fontSize: 12 }}>
              {refreshInterval / 1000}s
            </Text>
            <Switch
              size="small"
              checked={autoRefreshEnabled}
              onChange={setAutoRefresh}
              style={{ backgroundColor: autoRefreshEnabled ? '#52c41a' : '#d9d9d9' }}
            />
          </Space>

          {/* Refresh interval quick select */}
          <Button
            size="small"
            onClick={() => setRefreshInterval(refreshInterval === 5000 ? 10000 : 5000)}
            icon={<SettingOutlined />}
            shape="round"
            style={{ borderColor: '#1677ff', color: '#1677ff' }}
          >
            {refreshInterval / 1000}s
          </Button>

          {/* Manual refresh */}
          <Button
            size="small"
            icon={<ReloadOutlined />}
            onClick={handleRefreshAll}
            shape="round"
            type="primary"
            ghost
          >
            刷新
          </Button>
        </Space>
      </div>

      {/* 三卡片：大盘概览 | 行业TOP5 | 概念TOP5 */}
      <Row gutter={12} style={{ marginBottom: 12 }}>
        <Col xs={24} sm={24} md={8}>
          <MarketOverview
            indices={marketIndices}
            loading={indicesLoading}
            advDecl={advDecl}
          />
        </Col>
        <Col xs={24} sm={12} md={8}>
          <SectorCard title="行业TOP10" items={industries} loading={sectorsLoading} emptyText="暂无行业数据" />
        </Col>
        <Col xs={24} sm={12} md={8}>
          <SectorCard title="概念TOP10" items={concepts} loading={sectorsLoading} emptyText="暂无概念数据" />
        </Col>
      </Row>

      {/* Stock quote table */}
      <StockQuoteTable
        quotes={stockQuotes}
        loading={quotesLoading}
        filter={{ keyword: quoteFilter.keyword, tag: quoteFilter.tag }}
        onFilterChange={handleFilterChange}
        onRefresh={handleQuoteRefresh}
        onOpenDetail={handleOpenDetail}
      />

      {/* Stock detail drawer */}
      <ErrorBoundary title="个股详情异常" description="详情模块发生异常，请关闭后重试。">
        <StockDetailDrawer
          open={detailOpen}
          loading={detailLoading}
          quote={detailQuote}
          kline={detailKline}
          timeshare={detailTimeshare}
          indicators={detailIndicators}
          onClose={handleCloseDetail}
          onRefresh={handleRefreshDetail}
        />
      </ErrorBoundary>
    </div>
  );
};

export default MarketPage;
