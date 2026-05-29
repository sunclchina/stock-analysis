import { create } from 'zustand';
import type {
  ThemeMode,
  LayoutDensity,
  ExportFormat,
  SystemSettings,
  WatchlistItem,
  MonitorItem,
  DataSourceStatus,
  Template,
  UserPreferences,
  SystemStatus,
  DataSourceId,
} from '../types';

interface ConfigState {
  // General
  theme: ThemeMode;
  sidebarCollapsed: boolean;
  refreshInterval: number;

  // System Settings
  systemSettings: SystemSettings;
  setSystemSettings: (settings: Partial<SystemSettings>) => void;

  // Watchlist
  watchlist: WatchlistItem[];
  setWatchlist: (list: WatchlistItem[]) => void;
  addWatchlistItem: (item: WatchlistItem) => void;
  removeWatchlistItem: (code: string) => void;
  clearWatchlist: () => void;
  batchRemoveWatchlist: (codes: string[]) => void;

  // Monitor Pool
  monitorPool: MonitorItem[];
  setMonitorPool: (list: MonitorItem[]) => void;
  addMonitorItem: (item: MonitorItem) => void;
  removeMonitorItem: (code: string) => void;
  updateMonitorStatus: (code: string, status: MonitorItem['status']) => void;
  clearMonitorPool: () => void;
  batchRemoveMonitor: (codes: string[]) => void;

  // Data Sources
  dataSources: DataSourceStatus[];
  setDataSources: (sources: DataSourceStatus[]) => void;
  updateDataSourceStatus: (id: string, status: DataSourceStatus['status'], latency: number) => void;

  // Templates
  templates: Template[];
  setTemplates: (templates: Template[]) => void;
  addTemplate: (template: Template) => void;
  updateTemplate: (id: string, data: Partial<Template>) => void;
  removeTemplate: (id: string) => void;

  // User Preferences
  userPreferences: UserPreferences;
  setUserPreferences: (prefs: Partial<UserPreferences>) => void;

  // System Status
  systemStatus: SystemStatus | null;
  setSystemStatus: (status: SystemStatus) => void;

  // Actions
  setTheme: (theme: ThemeMode) => void;
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  setRefreshInterval: (interval: number) => void;
}

const defaultSystemSettings: SystemSettings = {
  port: 8080,
  environment: 'development',
  logPath: './logs',
  cacheTime: 300,
  apiBaseUrl: '/api/v1',
  apiPrefix: '/api/v1',
  apiTimeout: 10000,
  aiModel: 'deepseek-chat',
  aiApiKey: '',
  aiApiUrl: 'https://api.deepseek.com',
  aiTemperature: 0.7,
  aiMaxTokens: 4096,
};

const defaultUserPreferences: UserPreferences = {
  theme: 'auto',
  fontSize: 14,
  layout: 'default',
  alertHighlight: true,
  alertSound: true,
  autoRefreshInterval: 5000,
  defaultExportFormat: 'markdown',
};

export const useConfigStore = create<ConfigState>((set) => ({
  // General
  theme: 'light',
  sidebarCollapsed: window.innerWidth < 768,
  refreshInterval: 5000,

  // System Settings
  systemSettings: { ...defaultSystemSettings },
  setSystemSettings: (settings) =>
    set((state) => ({
      systemSettings: { ...state.systemSettings, ...settings },
    })),

  // Watchlist
  watchlist: [],
  setWatchlist: (list) => set({ watchlist: list }),
  addWatchlistItem: (item) =>
    set((state) => ({
      watchlist: [...state.watchlist, item],
    })),
  removeWatchlistItem: (code) =>
    set((state) => ({
      watchlist: state.watchlist.filter((i) => i.code !== code),
    })),
  clearWatchlist: () => set({ watchlist: [] }),
  batchRemoveWatchlist: (codes) =>
    set((state) => ({
      watchlist: state.watchlist.filter((i) => !codes.includes(i.code)),
    })),

  // Monitor Pool
  monitorPool: [],
  setMonitorPool: (list) => set({ monitorPool: list }),
  addMonitorItem: (item) =>
    set((state) => ({
      monitorPool: [...state.monitorPool, item],
    })),
  removeMonitorItem: (code) =>
    set((state) => ({
      monitorPool: state.monitorPool.filter((i) => i.code !== code),
    })),
  clearMonitorPool: () => set({ monitorPool: [] }),
  batchRemoveMonitor: (codes) =>
    set((state) => ({
      monitorPool: state.monitorPool.filter((i) => !codes.includes(i.code)),
    })),
  updateMonitorStatus: (code, status) =>
    set((state) => ({
      monitorPool: state.monitorPool.map((i) =>
        i.code === code ? { ...i, status } : i
      ),
    })),

  // Data Sources
  dataSources: [],
  setDataSources: (sources) => set({ dataSources: sources }),
  updateDataSourceStatus: (id, status, latency) =>
    set((state) => ({
      dataSources: state.dataSources.map((s) =>
        s.id === id ? { ...s, status, latency, lastCheck: new Date().toISOString() } : s
      ),
    })),

  // Templates
  templates: [],
  setTemplates: (templates) => set({ templates }),
  addTemplate: (template) =>
    set((state) => ({
      templates: [...state.templates, template],
    })),
  updateTemplate: (id, data) =>
    set((state) => ({
      templates: state.templates.map((t) =>
        t.id === id ? { ...t, ...data } : t
      ),
    })),
  removeTemplate: (id) =>
    set((state) => ({
      templates: state.templates.filter((t) => t.id !== id),
    })),

  // User Preferences
  userPreferences: { ...defaultUserPreferences },
  setUserPreferences: (prefs) =>
    set((state) => ({
      userPreferences: { ...state.userPreferences, ...prefs },
    })),

  // System Status
  systemStatus: null,
  setSystemStatus: (status) => set({ systemStatus: status }),

  // Actions
  setTheme: (theme) => set({ theme }),
  toggleSidebar: () =>
    set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
  setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
  setRefreshInterval: (interval) => set({ refreshInterval: interval }),
}));
