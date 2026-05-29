// ========== M02 实时行情模块类型 ==========

/** 大盘指数 */
export interface MarketIndex {
  code: string;
  name: string;
  latestPrice: number;
  change: number;
  changePercent: number;
  openPrice: number;
  prevClose: number;
  high: number;
  low: number;
  volume: number;
  amount: number;
  trendColor?: 'red' | 'green' | 'gray';
}

/** 个股行情 */
export interface StockQuote {
  code: string;
  name: string;
  latestPrice: number;
  change: number;
  changePercent: number;
  openPrice: number;
  prevClose: number;
  high: number;
  low: number;
  volume: number;
  amount: number;
  turnoverRate: number;
  amplitude: number;
  trendColor: 'red' | 'green' | 'gray';
  isWatchlist?: boolean;
  market?: string;
  /** 交易异动列表 */
  anomalies?: TradingAnomaly[];
}

/** 交易异动项 */
export interface TradingAnomaly {
  id: string;
  name: string;
  type: 'bullish' | 'bearish' | 'neutral';
}

/** 盘前提示段落 */
export interface PremarketSection {
  title: string;
  content: string;
}

/** 盘前提示（扩展版） */
export interface PremarketTip {
  date: string;
  marketPrediction: string;
  keyLevels: string;
  supportLevel?: number;
  resistanceLevel?: number;
  sectorRecommendations: string[];
  riskTips: string[];
  updatedAt: string;
  dataSource?: string;
  generatedAt?: string;
  /** 五大板块结构化数据 */
  sections?: PremarketSection[];
}

/** K线数据点 */
export interface KLineDataPoint {
  date: string;              // 日期 YYYY-MM-DD
  open: number;
  close: number;
  high: number;
  low: number;
  volume: number;
  amount?: number;
}

/** K线数据响应 */
export interface KLineData {
  code: string;
  name: string;
  period: 'day' | 'week' | 'month';
  dataPoints: KLineDataPoint[];
  ma5?: number[];
  ma10?: number[];
  ma20?: number[];
  ma60?: number[];
}

/** 分时数据点 */
export interface TimeSharePoint {
  time: string;              // HH:mm
  price: number;
  avgPrice: number;
  volume: number;
  amount: number;
}

/** 分时数据 */
export interface TimeShareData {
  code: string;
  name: string;
  date: string;
  points: TimeSharePoint[];
  close: number;
}

/** 技术指标概览 */
export interface TechnicalIndicators {
  code: string;
  name: string;
  ma5: number;
  ma10: number;
  ma20: number;
  ma60: number;
  macd: {
    dif: number;
    dea: number;
    macd: number;
  };
  kdj: {
    k: number;
    d: number;
    j: number;
  };
  rsi: number;
  volumeRatio: number;
}

/** 数据源状态 */
export interface DataSourceState {
  current: string;
  name: string;
  status: 'online' | 'offline' | 'degraded';
  latency: number;
  lastUpdate: string;
  available: { id: string; name: string; status: string; latency: number }[];
}

/** 行情列表筛选条件 */
export interface QuoteFilter {
  keyword: string;
  tag: 'all' | 'watchlist';
  sortField: string;
  sortOrder: 'ascend' | 'descend' | null;
}
