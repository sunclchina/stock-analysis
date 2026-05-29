import { create } from 'zustand';
import type { WarningItem, WarningStats, WarningDetail, WarningFilter, WarningLevel, WarningType } from '../types/warning';
import * as warningApi from '../services/warningApi';

interface WarningState {
  // 预警列表
  warningList: WarningItem[];
  total: number;
  currentPage: number;
  pageSize: number;
  loading: boolean;

  // 统计
  stats: WarningStats | null;
  statsLoading: boolean;

  // 筛选
  filter: WarningFilter;

  // 详情弹窗
  detailModalVisible: boolean;
  detailStock: WarningDetail | null;
  detailLoading: boolean;

  // Actions
  setFilter: (filter: Partial<WarningFilter>) => void;
  fetchWarningList: () => Promise<void>;
  fetchStats: () => Promise<void>;
  acknowledgeWarning: (id: string) => Promise<void>;
  openDetail: (code: string) => Promise<void>;
  closeDetail: () => void;
  setPage: (page: number) => void;
  setPageSize: (size: number) => void;
  addWarningItem: (item: WarningItem) => void;
  removeWarningItem: (id: string) => void;
  updateWarningStatus: (id: string, status: string) => void;
}

const defaultFilter: WarningFilter = {
  type: 'all',
  level: 'all',
  keyword: '',
  processStatus: 'all',
};

export const useWarningStore = create<WarningState>((set, get) => ({
  warningList: [],
  total: 0,
  currentPage: 1,
  pageSize: 20,
  loading: false,
  stats: null,
  statsLoading: false,
  filter: { ...defaultFilter },
  detailModalVisible: false,
  detailStock: null,
  detailLoading: false,

  setFilter: (partial) => {
    set((state) => ({
      filter: { ...state.filter, ...partial },
      currentPage: 1, // reset to page 1 on filter change
    }));
    get().fetchWarningList();
  },

  fetchWarningList: async () => {
    const { filter, currentPage, pageSize } = get();
    set({ loading: true });
    try {
      const res = await warningApi.getWarningList({
        page: currentPage,
        pageSize,
        type: filter.type,
        level: filter.level,
        keyword: filter.keyword,
        processStatus: filter.processStatus,
      });
      set({
        warningList: res.data.items,
        total: res.data.total,
        loading: false,
      });
    } catch {
      set({ loading: false });
    }
  },

  fetchStats: async () => {
    set({ statsLoading: true });
    try {
      const res = await warningApi.getWarningStats();
      set({ stats: res.data, statsLoading: false });
    } catch {
      set({ statsLoading: false });
    }
  },

  acknowledgeWarning: async (id: string) => {
    try {
      await warningApi.acknowledgeWarning(id);
      // Update local state
      set((state) => ({
        warningList: state.warningList.map((item) =>
          item.id === id ? { ...item, processStatus: 'acknowledged' as const } : item
        ),
      }));
      // Refresh stats
      get().fetchStats();
    } catch {
      // Silent fail
    }
  },

  openDetail: async (code: string) => {
    set({ detailLoading: true, detailModalVisible: true });
    try {
      const res = await warningApi.getWarningDetail(code);
      set({ detailStock: res.data, detailLoading: false });
    } catch {
      set({ detailStock: null, detailLoading: false });
    }
  },

  closeDetail: () => {
    set({ detailModalVisible: false, detailStock: null });
  },

  setPage: (page) => {
    set({ currentPage: page });
    get().fetchWarningList();
  },

  setPageSize: (size) => {
    set({ pageSize: size, currentPage: 1 });
    get().fetchWarningList();
  },

  addWarningItem: (item) => {
    set((state) => ({
      warningList: [item, ...state.warningList],
      total: state.total + 1,
    }));
    // Refresh stats
    get().fetchStats();
  },

  removeWarningItem: (id) => {
    set((state) => ({
      warningList: state.warningList.filter((item) => item.id !== id),
      total: Math.max(0, state.total - 1),
    }));
    get().fetchStats();
  },

  updateWarningStatus: (id, status) => {
    set((state) => ({
      warningList: state.warningList.map((item) =>
        item.id === id
          ? { ...item, processStatus: status as WarningItem['processStatus'] }
          : item
      ),
    }));
  },
}));
