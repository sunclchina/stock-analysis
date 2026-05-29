import apiClient from './api';
import type { ApiResponse } from '../types';
import type {
  MarketIndex,
  StockQuote,
  PremarketTip,
  KLineData,
  TimeShareData,
  TechnicalIndicators,
  DataSourceState,
  TradingAnomaly,
} from '../types/market';

/** 将后端大盘指数字段映射为前端 MarketIndex 格式 */
function mapIndex(raw: any): MarketIndex {
  if (!raw) return null as any;
  const change = raw.change ?? 0;
  return {
    code: raw.code || '',
    name: raw.name || '',
    latestPrice: raw.price ?? raw.latestPrice ?? 0,
    change: change,
    changePercent: raw.change_pct ?? raw.changePercent ?? 0,
    openPrice: raw.open ?? raw.openPrice ?? 0,
    prevClose: raw.pre_close ?? raw.prevClose ?? 0,
    high: raw.high ?? 0,
    low: raw.low ?? 0,
    volume: raw.volume ?? 0,
    amount: raw.amount ?? 0,
    trendColor: change > 0 ? 'red' : change < 0 ? 'green' : 'gray',
  };
}

/** 获取大盘概览（7大指数） */
export async function getMarketOverview(): Promise<ApiResponse<MarketIndex[]>> {
  return apiClient.get('/market/overview').then((res: any) => {
    const rawList = res.items ?? [];
    return { ...res, data: Array.isArray(rawList) ? rawList.map(mapIndex) : [] };
  });
}

/** 将后端行情字段映射为前端 StockQuote 格式 */
function mapQuote(raw: any): StockQuote {
  if (!raw) return null as any;
  const change = raw.change ?? 0;
  const preClose = raw.pre_close ?? raw.prevClose ?? 0;
  return {
    code: raw.code || '',
    name: raw.name || '',
    latestPrice: raw.price ?? raw.latestPrice ?? 0,
    change: change,
    changePercent: raw.change_pct ?? raw.changePercent ?? 0,
    openPrice: raw.open ?? raw.openPrice ?? 0,
    prevClose: preClose,
    high: raw.high ?? 0,
    low: raw.low ?? 0,
    volume: raw.volume ?? 0,
    amount: raw.amount ?? 0,
    turnoverRate: raw.turnover_rate ?? raw.turnoverRate ?? 0,
    amplitude: raw.amplitude ?? 0,
    trendColor: change > 0 ? 'red' : change < 0 ? 'green' : 'gray',
    isWatchlist: raw.isWatchlist ?? false,
    market: raw.market ?? '',
  };
}

/** 批量查询行情 */
export async function getBatchQuotes(codes?: string): Promise<ApiResponse<StockQuote[]>> {
  const path = codes ? `/market/quotes/${codes}` : '/market/quotes';
  return apiClient.get(path).then((res: any) => {
    // 后端返回 {quotes: [...]} 或 {items: [...]}
    const rawList = res.quotes ?? res.items ?? [];
    if (!Array.isArray(rawList)) return { ...res, data: [] };
    return { ...res, data: rawList.map(mapQuote) };
  });
}

/** 查询单只行情 */
export async function getQuote(code: string): Promise<ApiResponse<StockQuote>> {
  return apiClient.get(`/market/quote/${code}`).then((res: any) => ({
    ...res,
    data: mapQuote(res.data ?? res),
  }));
}

/** 获取盘前提示 */
export async function getPremarketTip(): Promise<ApiResponse<PremarketTip>> {
  return apiClient.get('/market/premarket').then((res: any) => ({
    ...res,
    data: res.tip ?? res.data ?? res,
  }));
}

/** 生成盘前提示 */
export async function generatePremarketTip(): Promise<ApiResponse<PremarketTip>> {
  return apiClient.post('/market/premarket/generate').then((res: any) => ({
    ...res,
    data: res.tip ?? res.data?.tip ?? res,
  }));
}

/** 获取K线数据 */
export async function getKlineData(code: string, period: string = 'daily'): Promise<ApiResponse<KLineData>> {
  return apiClient.get(`/market/kline/${code}`, { params: { period } }).then((res: any) => ({
    ...res,
    data: {
      code: res.code || code,
      name: res.name || '',
      period: res.period || period,
      dataPoints: (res.klines || []).map((k: any) => ({
        date: k.date || '',
        open: k.open ?? 0,
        close: k.close ?? 0,
        high: k.high ?? 0,
        low: k.low ?? 0,
        volume: k.volume ?? 0,
        amount: k.amount ?? 0,
      })),
      ma5: res.ma5,
      ma10: res.ma10,
      ma20: res.ma20,
      ma60: res.ma60,
    } as KLineData,
  }));
}

/** 获取分时数据 */
export async function getTimeShareData(code: string): Promise<ApiResponse<TimeShareData>> {
  return apiClient.get(`/market/timeshare/${code}`).then((res: any) => ({
    ...res,
    data: {
      code: res.code || code,
      name: res.name || '',
      date: res.date || '',
      close: res.close ?? 0,
      points: (res.items || []).map((p: any) => ({
        time: p.time || '',
        price: p.price ?? 0,
        avgPrice: p.avg_price ?? p.avgPrice ?? 0,
        volume: p.volume ?? 0,
        amount: p.amount ?? 0,
      })),
    } as TimeShareData,
  }));
}

/** 获取技术指标 */
export async function getTechnicalIndicators(code: string): Promise<ApiResponse<TechnicalIndicators>> {
  return apiClient.get(`/market/indicators/${code}`).then((res: any) => {
    // 后端返回 { ma: { ma5, ma10, ... }, macd: {...}, kdj: {...}, rsi: {...} }
    // 前端需要 { ma5, ma10, ..., macd: {...}, kdj: {...}, rsi, volumeRatio }
    const ma = res.ma || {};
    const macd = res.macd || {};
    const kdj = res.kdj || {};
    const rsi = res.rsi || {};
    const mapped: TechnicalIndicators = {
      code: res.code || code,
      name: res.name || '',
      ma5: ma.ma5 ?? 0,
      ma10: ma.ma10 ?? 0,
      ma20: ma.ma20 ?? 0,
      ma60: ma.ma60 ?? 0,
      macd: {
        dif: macd.dif ?? 0,
        dea: macd.dea ?? 0,
        macd: macd.macd ?? 0,
      },
      kdj: {
        k: kdj.k ?? 0,
        d: kdj.d ?? 0,
        j: kdj.j ?? 0,
      },
      rsi: rsi.rsi6 ?? 0,
      volumeRatio: 0,
    };
    return { ...res, data: mapped };
  });
}

/** 获取数据源状态 */
export async function getDataSourceState(): Promise<ApiResponse<DataSourceState>> {
  return apiClient.get('/config/datasource');
}

/** 批量查询交易异动 */
export async function getAnomalies(codes: string[]): Promise<Record<string, TradingAnomaly[]>> {
  if (!codes.length) return {};
  try {
    const res = await apiClient.get('/market/anomalies', { params: { codes: codes.join(',') } });
    return res.anomalies ?? {};
  } catch {
    return {};
  }
}
