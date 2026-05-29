// Theme
export type ThemeMode = 'light' | 'dark';
export type LayoutDensity = 'compact' | 'default' | 'loose';
export type ExportFormat = 'txt' | 'markdown' | 'pdf';

// Navigation
export interface NavItem {
  key: string;
  label: string;
  path: string;
  icon: string;
}

// API response
export interface ApiResponse<T = unknown> {
  code: number;
  message: string;
  data: T;
}

// ========== M06 系统配置 ==========

// 系统设置 - 环境变量分组
export interface EnvVarGroup {
  key: string;
  title: string;
  fields: EnvVarField[];
}

export interface EnvVarField {
  key: string;
  label: string;
  type: 'text' | 'number' | 'select' | 'password' | 'boolean';
  placeholder?: string;
  options?: { label: string; value: string }[];
  defaultValue?: string;
  description?: string;
  requiresRestart?: boolean;
}

export interface SystemSettings {
  port: number;
  environment: 'development' | 'production';
  logPath: string;
  cacheTime: number;
  apiBaseUrl: string;
  apiPrefix: string;
  apiTimeout: number;
  aiModel: string;
  aiApiKey: string;
  aiApiUrl: string;
  aiTemperature: number;
  aiMaxTokens: number;
  [key: string]: unknown;
}

// 自选股
export interface WatchlistItem {
  code: string;
  name: string;
  addedAt: string;
  industry?: string;
  market?: string;
}

// 监控池
export interface MonitorItem {
  code: string;
  name: string;
  status: 'active' | 'paused' | 'error' | 'suspended';
  addedAt: string;
  industry?: string;
  market?: string;
}

// 数据源
export interface DataSourceStatus {
  id: string;
  name: string;
  type: 'primary' | 'backup' | 'fallback';
  status: 'online' | 'offline' | 'degraded';
  lastCheck: string;
  latency: number;
  description: string;
}

export type DataSourceId = 'tdx' | 'sina' | 'eastmoney' | 'baostock' | 'akshare';

// 自定义数据源（付费第三方）
export interface CustomDataSource {
  id?: number;
  name: string;
  api_url: string;
  api_key: string;
  description?: string;
  enabled: boolean;
  created_at?: string;
  updated_at?: string;
}

// 模板
export interface Template {
  id: string;
  name: string;
  type: 'selection' | 'premarket' | 'analysis';
  content: string;
  isDefault: boolean;
  updatedAt: string;
}

// 用户偏好
export interface UserPreferences {
  theme: ThemeMode | 'auto';
  fontSize: number;
  layout: LayoutDensity;
  alertHighlight: boolean;
  alertSound: boolean;
  autoRefreshInterval: number;
  defaultExportFormat: ExportFormat;
}

// 系统状态
export interface SystemStatus {
  cpu: number;
  memory: number;
  disk: number;
  uptime: string;
  services: ServiceStatus[];
  version: string;
  buildTime: string;
}

export interface ServiceStatus {
  name: string;
  status: 'running' | 'stopped' | 'error';
  uptime: string;
  port?: number;
}

// Re-export dashboard and warning types
export * from './dashboard';
export * from './warning';
