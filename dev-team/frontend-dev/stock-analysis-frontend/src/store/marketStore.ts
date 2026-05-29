import { create } from 'zustand';
import type {
  MarketIndex,
  StockQuote,
  PremarketTip,
  KLineData,
  TimeShareData,
  TechnicalIndicators,
  DataSourceState,
  QuoteFilter,
} from '../types/market';
import * as marketApi from '../services/marketApi';

interface MarketState {
  // 大盘指数
  marketIndices: MarketIndex[];
  indicesLoading: boolean;

  // 行情列表
  stockQuotes: StockQuote[];
  quotesLoading: boolean;
  quoteFilter: QuoteFilter;

  // 盘前提示
  premarketTip: PremarketTip | null;
  tipLoading: boolean;
  tipGenerating: boolean;

  // 数据源
  dataSourceState: DataSourceState | null;

  // 个股详情（弹窗侧栏）
  detailOpen: boolean;
  detailCode: string | null;
  detailQuote: StockQuote | null;
  detailKline: KLineData | null;
  detailTimeshare: TimeShareData | null;
  detailIndicators: TechnicalIndicators | null;
  detailLoading: boolean;

  // 自动刷新
  refreshInterval: number;      // 默认5000ms
  autoRefreshEnabled: boolean;

  // Actions
  fetchMarketIndices: (silent?: boolean) => Promise<void>;
  fetchStockQuotes: (codes?: string, silent?: boolean) => Promise<void>;
  fetchPremarketTip: () => Promise<void>;
  generatePremarketTip: () => Promise<void>;
  fetchDataSourceState: () => Promise<void>;

  setQuoteFilter: (filter: Partial<QuoteFilter>) => void;
  setRefreshInterval: (interval: number) => void;
  setAutoRefresh: (enabled: boolean) => void;

  openDetail: (code: string) => Promise<void>;
  closeDetail: () => void;
  refreshDetail: () => Promise<void>;

  // WebSocket data update (批量合并)
  applyQuoteUpdate: (quotes: StockQuote[]) => void;

  // 重置
  reset: () => void;
}

const defaultFilter: QuoteFilter = {
  keyword: '',
  tag: 'all',
  sortField: '',
  sortOrder: null,
};

export const useMarketStore = create<MarketState>((set, get) => ({
  // Initial state
  marketIndices: [],
  indicesLoading: false,

  stockQuotes: [],
  quotesLoading: false,
  quoteFilter: { ...defaultFilter },

  premarketTip: null,
  tipLoading: false,
  tipGenerating: false,

  dataSourceState: null,

  detailOpen: false,
  detailCode: null,
  detailQuote: null,
  detailKline: null,
  detailTimeshare: null,
  detailIndicators: null,
  detailLoading: false,

  refreshInterval: 30000,
  autoRefreshEnabled: true,

  // ========== API Fetch ==========

  fetchMarketIndices: async (silent?: boolean) => {
    if (!silent) set({ indicesLoading: true });
    try {
      const res = await marketApi.getMarketOverview();
      set({ marketIndices: res.data, indicesLoading: false });
    } catch {
      set({ indicesLoading: false });
    }
  },

  fetchStockQuotes: async (codes?: string, silent?: boolean) => {
    if (typeof codes === 'boolean') { silent = codes; codes = undefined; }
    if (!silent) set({ quotesLoading: true });
    try {
      const res = await marketApi.getBatchQuotes(codes);
      const newQuotes = res.data;
      // 非交易日/数据源不可用时 API 可能返回空数组，此时保留已有数据不覆盖
      if (Array.isArray(newQuotes) && newQuotes.length > 0) {
        // 合并新老数据：保留旧数据的换手率/振幅/异动等低频字段，避免刷新覆盖
        set((state) => {
          const oldMap = new Map(state.stockQuotes.map((q) => [q.code, q]));
          const merged = newQuotes.map((nq) => {
            const old = oldMap.get(nq.code);
            if (!old) return nq;
            return {
              ...nq,
              // 换手率：新数据没有或为0时，保留旧值
              turnoverRate: (nq.turnoverRate && nq.turnoverRate > 0) ? nq.turnoverRate : old.turnoverRate,
              // 振幅：同上
              amplitude: (nq.amplitude && nq.amplitude > 0) ? nq.amplitude : old.amplitude,
              // 异动：保留上次检测结果（下次检测再更新）
              anomalies: nq.anomalies?.length ? nq.anomalies : old.anomalies,
            };
          });
          return { stockQuotes: merged, quotesLoading: false };
        });
      } else {
        set({ quotesLoading: false });
      }
    } catch {
      set({ quotesLoading: false });
    }
  },

  fetchPremarketTip: async () => {
    set({ tipLoading: true });
    try {
      const res = await marketApi.getPremarketTip();
      set({ premarketTip: res.data, tipLoading: false });
    } catch {
      set({ tipLoading: false });
    }
  },

  generatePremarketTip: async () => {
    set({ tipGenerating: true });
    try {
      const res = await marketApi.generatePremarketTip();
      set({ premarketTip: res.data, tipGenerating: false });
    } catch {
      set({ tipGenerating: false });
    }
  },

  fetchDataSourceState: async () => {
    try {
      const res = await marketApi.getDataSourceState();
      set({ dataSourceState: res.data });
    } catch {
      // Silent fail
    }
  },

  // ========== Filter & Settings ==========

  setQuoteFilter: (partial) => {
    set((state) => ({
      quoteFilter: { ...state.quoteFilter, ...partial },
    }));
  },

  setRefreshInterval: (interval) => {
    set({ refreshInterval: interval });
  },

  setAutoRefresh: (enabled) => {
    set({ autoRefreshEnabled: enabled });
  },

  // ========== Detail Drawer ==========

  openDetail: async (code: string) => {
    set({ detailOpen: true, detailCode: code, detailLoading: true });
    try {
      const [quoteRes, klineRes, timeshareRes, indicatorsRes] = await Promise.all([
        marketApi.getQuote(code).catch(() => null),
        marketApi.getKlineData(code).catch(() => null),
        marketApi.getTimeShareData(code).catch(() => null),
        marketApi.getTechnicalIndicators(code).catch(() => null),
      ]);
      set({
        detailQuote: quoteRes?.data || null,
        detailKline: klineRes?.data || null,
        detailTimeshare: timeshareRes?.data || null,
        detailIndicators: indicatorsRes?.data || null,
        detailLoading: false,
      });
    } catch {
      set({ detailLoading: false });
    }
  },

  closeDetail: () => {
    set({
      detailOpen: false,
      detailCode: null,
      detailQuote: null,
      detailKline: null,
      detailTimeshare: null,
      detailIndicators: null,
    });
  },

  refreshDetail: async () => {
    const code = get().detailCode;
    if (!code) return;
    set({ detailLoading: true });
    try {
      const [quoteRes, klineRes] = await Promise.all([
        marketApi.getQuote(code).catch(() => null),
        marketApi.getKlineData(code).catch(() => null),
      ]);
      set({
        detailQuote: quoteRes?.data || get().detailQuote,
        detailKline: klineRes?.data || get().detailKline,
        detailLoading: false,
      });
    } catch {
      set({ detailLoading: false });
    }
  },

  // ========== WebSocket Update ==========

  applyQuoteUpdate: (quotes) => {
    if (!Array.isArray(quotes) || quotes.length === 0) return;
    set((state) => {
      const existingMap = new Map(state.stockQuotes.map((q) => [q.code, q]));
      for (const update of quotes) {
        const old = existingMap.get(update.code);
        if (old) {
          // WebSocket 过来的通常是部分更新（价格变化），保留旧数据的低频字段
          existingMap.set(update.code, {
            ...old,
            ...update,
            turnoverRate: (update.turnoverRate && update.turnoverRate > 0) ? update.turnoverRate : old.turnoverRate,
            amplitude: (update.amplitude && update.amplitude > 0) ? update.amplitude : old.amplitude,
            anomalies: update.anomalies?.length ? update.anomalies : old.anomalies,
          });
        } else {
          existingMap.set(update.code, update);
        }
      }
      return { stockQuotes: Array.from(existingMap.values()) };
    });
  },

  // ========== Reset ==========

  reset: () => {
    set({
      marketIndices: [],
      stockQuotes: [],
      premarketTip: null,
      dataSourceState: null,
      detailOpen: false,
      detailCode: null,
      detailQuote: null,
      detailKline: null,
      detailTimeshare: null,
      detailIndicators: null,
    });
  },
}));
