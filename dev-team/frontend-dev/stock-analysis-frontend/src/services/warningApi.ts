import apiClient from './api';
import type { ApiResponse } from '../types';
import type { WarningItem, WarningStats, WarningDetail, WarningFilter, WarningLevel, WarningType } from '../types/warning';

export interface WarningListResponse {
  items: WarningItem[];
  total: number;
  page: number;
  pageSize: number;
}

export interface MonitorItem {
  code: string;
  name: string;
  timestamp: string;
  price_warning: string;
  updown_warning: string;
  trend_warning: string;
  resonance_warning: string;
  finance_warning: string;
  event_warning: string;
  risk_level: string;
  overall: string;
  reason: string;
  changes?: Record<string, string>;
  price_data?: {
    price?: number;
    pre_close?: number;
    change_pct?: number;
    open?: number;
  };
  trend_data?: {
    ma5?: number;
    ma10?: number;
    ma20?: number;
    price?: number;
    data_points?: number;
  };
  resonance_data?: {
    ma_trend?: { score: number; signal: string };
    rsi?: { value: number; score: number; signal: string };
    macd?: { score: number; signal: string };
  };
  risk_data?: {
    score?: number;
    level?: string;
  };
  finance_data?: Record<string, unknown>;
}

export interface MonitorPanelResponse {
  items: MonitorItem[];
  total: number;
  errors: number;
  timestamp: string;
}

/** 获取预警列表 */
export async function getWarningList(params: {
  page?: number;
  pageSize?: number;
  type?: WarningType | 'all';
  level?: WarningLevel | 'all';
  keyword?: string;
  processStatus?: string;
}): Promise<ApiResponse<WarningListResponse>> {
  const query = new URLSearchParams();
  if (params.page) query.set('page', String(params.page));
  if (params.pageSize) query.set('pageSize', String(params.pageSize));
  if (params.type && params.type !== 'all') query.set('type', params.type);
  if (params.level && params.level !== 'all') query.set('level', params.level);
  if (params.keyword) query.set('keyword', params.keyword);
  if (params.processStatus && params.processStatus !== 'all') query.set('processStatus', params.processStatus);
  const qs = query.toString();
  return apiClient.get(`/warning/list${qs ? `?${qs}` : ''}`);
}

/** 获取预警汇总统计 */
export async function getWarningStats(): Promise<ApiResponse<WarningStats>> {
  return apiClient.get('/warning/summary');
}

/** 标记预警已处理 */
export async function acknowledgeWarning(id: string): Promise<ApiResponse<null>> {
  return apiClient.put(`/warning/${id}/ack`);
}

/** 获取单只股票预警详情 */
export async function getWarningDetail(code: string): Promise<ApiResponse<WarningDetail>> {
  return apiClient.get(`/warning/${code}/detail`);
}

/** 获取监控面板（实时7模块颜色） */
export async function getMonitorPanel(forceRefresh?: boolean): Promise<ApiResponse<MonitorPanelResponse>> {
  const qs = forceRefresh ? '?force_refresh=true' : '';
  return apiClient.get(`/warning/monitor${qs}`);
}

/** 获取单只股票实时预警 */
export async function getStockRealtimeWarning(code: string): Promise<ApiResponse<MonitorItem>> {
  return apiClient.get(`/warning/realtime/${code}`);
}
