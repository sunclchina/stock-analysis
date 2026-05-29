import apiClient from './api';
import type { CoreAnalysis, PremarketTip, StockSnapshot, WarningSummaryItem, PoolSummary, SystemStatusInfo } from '../types/dashboard';
import type { ApiResponse } from '../types';

/** 获取仪表盘全部聚合数据 */
export async function getDashboard(): Promise<ApiResponse<{
  coreAnalysis: CoreAnalysis | null;
  premarketTip: PremarketTip | null;
  marketQuotes: StockSnapshot[];
  warningSummary: WarningSummaryItem[];
  poolSummary: PoolSummary | null;
  systemStatus: SystemStatusInfo | null;
}>> {
  return apiClient.get('/dashboard');
}

/** 获取核心分析结论 */
export async function getCoreAnalysis(): Promise<ApiResponse<CoreAnalysis | null>> {
  return apiClient.get('/dashboard/core-analysis');
}

/** 获取盘前提示 */
export async function getPremarketTip(): Promise<ApiResponse<PremarketTip | null>> {
  return apiClient.get('/market/premarket');
}

/** 获取行情快照 */
export async function getMarketQuotes(codes?: string): Promise<ApiResponse<StockSnapshot[]>> {
  const params = codes ? `?codes=${codes}` : '';
  return apiClient.get(`/market/quotes${params}`);
}

/** 获取预警汇总 */
export async function getWarningSummary(): Promise<ApiResponse<WarningSummaryItem[]>> {
  return apiClient.get('/warning/summary');
}

/** 决策仪表盘 */
export async function getDecisionBoard(): Promise<ApiResponse<{
  stocks: DecisionStock[];
  stats: { bullish: number; bearish: number; neutral: number; avg_score: number; total: number };
}>> {
  return apiClient.get('/dashboard/decision-board');
}

export interface DecisionStock {
  code: string;
  name: string;
  price: number;
  change_pct: number;
  total_score: number;
  signal_type: 'bullish' | 'bearish' | 'neutral';
  action: string;
  scores: { trend: number; momentum: number; volume: number; risk: number };
  details: {
    trend: string;
    ma5: number | null;
    ma10: number | null;
    ma20: number | null;
    anomalies: string[];
  };
}
