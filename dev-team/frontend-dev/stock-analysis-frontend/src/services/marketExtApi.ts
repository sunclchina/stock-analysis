import apiClient from './api';

/** 全球指数接口 */
export async function fetchGlobalIndices(): Promise<{ groups: { name: string; items: any[] }[]; count: number }> {
  const res = await apiClient.get('/market/global-indices');
  return res; // apiClient 拦截器已返回 response.data
}

/** 行业排名接口 */
export async function fetchIndustryRanking(sort = '0', count = 20): Promise<any[]> {
  const res = await apiClient.get('/market/industry-ranking', { params: { sort, count } });
  return res;
}

/** 行业资金流向接口 */
export async function fetchIndustryMoneyFlow(sort = 'netamount', fenlei = '0'): Promise<any[]> {
  const res = await apiClient.get('/market/industry-money-flow', { params: { sort, fenlei } });
  return res;
}

/** 个股资金流向接口 */
export async function fetchStockMoneyFlow(sort = 'netamount'): Promise<any[]> {
  const res = await apiClient.get('/market/stock-money-flow', { params: { sort } });
  return res;
}
