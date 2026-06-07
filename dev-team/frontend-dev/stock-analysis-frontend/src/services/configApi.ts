import apiClient from './api';
import type {
  ApiResponse,
  SystemSettings,
  SslConfig,
  WatchlistItem,
  MonitorItem,
  DataSourceStatus,
  DataSourceId,
  Template,
  UserPreferences,
  SystemStatus,
  CustomDataSource,
} from '../types';

// ========== 系统设置 ==========
export function fetchSystemConfig(): Promise<ApiResponse<SystemSettings>> {
  return apiClient.get('/config');
}

export function saveSystemConfig(config: SystemSettings): Promise<ApiResponse<SystemSettings>> {
  return apiClient.put('/config', config);
}

// ========== 自选股 ==========
export function fetchWatchlist(): Promise<ApiResponse<WatchlistItem[]>> {
  return apiClient.get('/config/watchlist');
}

export function addWatchlistItem(code: string, name: string): Promise<ApiResponse<WatchlistItem>> {
  return apiClient.post('/config/watchlist', { code, name });
}

export function removeWatchlistItem(code: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/config/watchlist/${code}`);
}

export function batchImportWatchlist(codes: string[]): Promise<ApiResponse<WatchlistItem[]>> {
  return apiClient.post('/config/watchlist/batch', { codes });
}

// ========== 监控池 ==========
export function fetchMonitorPool(): Promise<ApiResponse<MonitorItem[]>> {
  return apiClient.get('/config/monitor');
}

export function addMonitorItem(code: string, name: string): Promise<ApiResponse<MonitorItem>> {
  return apiClient.post('/config/monitor', { code, name });
}

export function removeMonitorItem(code: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/config/monitor/${code}`);
}

export function updateMonitorItem(code: string, data: Partial<{ name: string; is_active: boolean; monitor_type: string }>): Promise<ApiResponse<any>> {
  return apiClient.put(`/config/monitor/${code}`, data);
}

export function syncMonitorPool(items: { code: string; name?: string; monitor_type?: string }[]): Promise<ApiResponse<any>> {
  return apiClient.post('/config/monitor/sync', { items });
}

export function importTdxWatchlist(): Promise<ApiResponse<{ imported: string[]; skipped_duplicates: number; skipped_invalid: number }>> {
  return apiClient.post('/config/watchlist/import-tdx');
}

// ========== 数据源 ==========
export function fetchDataSourceStatus(): Promise<ApiResponse<DataSourceStatus[]>> {
  return apiClient.get('/config/datasource');
}

export function testDataSourceConnection(id: DataSourceId): Promise<ApiResponse<{ latency: number; status: string }>> {
  return apiClient.post(`/config/datasource/test`, { id });
}

export function switchDataSource(id: DataSourceId): Promise<ApiResponse<void>> {
  return apiClient.post('/config/datasource/switch', { id });
}

// ========== 自定义数据源 ==========
export function fetchCustomDataSources(): Promise<ApiResponse<{ sources: CustomDataSource[]; total: number }>> {
  return apiClient.get('/config/custom-datasource');
}

export function addCustomDataSource(data: Partial<CustomDataSource>): Promise<ApiResponse<{ status: string; message: string; data: CustomDataSource }>> {
  return apiClient.post('/config/custom-datasource', data);
}

export function updateCustomDataSource(id: number, data: Partial<CustomDataSource>): Promise<ApiResponse<{ status: string; message: string; data: CustomDataSource }>> {
  return apiClient.put(`/config/custom-datasource/${id}`, data);
}

export function deleteCustomDataSource(id: number): Promise<ApiResponse<{ status: string; message: string }>> {
  return apiClient.delete(`/config/custom-datasource/${id}`);
}

export function testCustomDataSource(api_url: string, api_key: string): Promise<ApiResponse<{ status: string; latency: number; message: string; http_status?: number }>> {
  return apiClient.post('/config/custom-datasource/test', { api_url, api_key });
}

// ========== 模板 ==========
export function fetchTemplates(): Promise<ApiResponse<{ templates: any[]; default: string }>> {
  return apiClient.get('/config/templates');
}

export function fetchTemplateContent(name: string): Promise<ApiResponse<{ name: string; content: string }>> {
  return apiClient.get(`/config/templates/${encodeURIComponent(name)}`);
}

export function saveTemplate(template: { name: string; content: string; overwrite?: boolean }): Promise<ApiResponse<any>> {
  return apiClient.post('/config/templates', template);
}

export function deleteTemplate(id: string): Promise<ApiResponse<void>> {
  return apiClient.delete(`/config/templates/${id}`);
}

export function setDefaultTemplate(id: string, templateType?: string): Promise<ApiResponse<void>> {
  const params = templateType ? `?template_type=${encodeURIComponent(templateType)}` : '';
  return apiClient.put(`/config/templates/${id}/default${params}`);
}

export function exportTemplate(id: string): Promise<Blob> {
  return apiClient.get(`/config/templates/${id}/export`, { responseType: 'blob' });
}

// ========== 用户偏好 ==========
export function fetchUserPreferences(): Promise<ApiResponse<UserPreferences>> {
  return apiClient.get('/config/preferences');
}

export function saveUserPreferences(prefs: UserPreferences): Promise<ApiResponse<UserPreferences>> {
  return apiClient.put('/config/preferences', prefs);
}

// ========== 系统状态 ==========
export function fetchSystemStatus(): Promise<ApiResponse<SystemStatus>> {
  return apiClient.get('/config/system');
}

// ========== HTTPS/SSL 配置 ==========
export function fetchSslConfig(): Promise<ApiResponse<SslConfig>> {
  return apiClient.get('/config/ssl');
}

export function saveSslConfig(config: {
  ssl_enabled?: boolean;
  ssl_cert_file?: string;
  ssl_key_file?: string;
}): Promise<ApiResponse<{ status: string; message: string; requires_restart: boolean }>> {
  return apiClient.put('/config/ssl', config);
}
