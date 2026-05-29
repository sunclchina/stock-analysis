import apiClient from './api';

/** 个股研报 */
export async function fetchStockResearchReport(stockCode: string, days = 365): Promise<any[]> {
  const res: any = await apiClient.get('/market/stock-research-report', { params: { stock_code: stockCode, days } });
  return res;
}

/** 公司公告 */
export async function fetchStockNotice(stockCodes: string, pageSize = 10): Promise<any[]> {
  const res: any = await apiClient.get('/market/stock-notice', { params: { stock_codes: stockCodes, page_size: pageSize } });
  return res;
}

/** 行业研究 */
export async function fetchIndustryResearchReport(industryCode = '', days = 7): Promise<any[]> {
  const res: any = await apiClient.get('/market/industry-research-report', { params: { industryCode, days } });
  return res;
}

/** 指标选股 */
export async function fetchIndicatorSelection(keyword: string): Promise<any> {
  const res: any = await apiClient.post('/market/indicator-selection', { keyword });
  return res;
}

/** 涨停梯队 */
export async function fetchLimitUpTier(): Promise<any[]> {
  const res: any = await apiClient.get('/market/limit-up-tier');
  return res.stocks || res || [];
}

/** 异动监控 */
export async function fetchAnomalyMonitor(): Promise<any[]> {
  const res: any = await apiClient.get('/market/anomaly-monitor');
  return res.stocks || res || [];
}

/** 个股研报详情全文 */
export async function fetchResearchReportDetail(infoCode: string): Promise<any> {
  const res: any = await apiClient.get(`/market/research-report-detail/${infoCode}`);
  return res;
}

/** K线迷你数据（用于悬浮预览） */
export async function fetchKLineMini(code: string, count: number = 60): Promise<any> {
  const res: any = await apiClient.get(`/market/kline/${code}`, { params: { count, period: 'daily' } });
  return res;
}
