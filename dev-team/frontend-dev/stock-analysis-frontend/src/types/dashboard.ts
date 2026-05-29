// ========== M01 仪表盘类型 ==========

/** 核心分析结论 */
export interface CoreAnalysis {
  priceWarning: string;       // 股价预警
  marketJudgment: string;    // 大盘判断
  sentiment: string;         // 情绪判断
  operationAdvice: string;   // 操作建议
  updatedAt: string;
}

/** 盘前提示 */
export interface PremarketTip {
  date: string;
  marketPrediction: string;   // 大盘预判
  keyLevels: string;          // 关键点位
  sectorRecommendations: string[];  // 板块推荐
  riskTips: string[];         // 风险提示
  updatedAt: string;
}

/** 实时行情快照 */
export interface StockSnapshot {
  code: string;
  name: string;
  price: number;
  changePercent: number;
  trendColor: 'red' | 'green' | 'gray';
}

/** 预警汇总项 */
export interface WarningSummaryItem {
  type: string;           // 预警类型
  typeLabel: string;      // 中文标签
  level: 'high' | 'medium' | 'low';
  stockCode: string;
  stockName: string;
  message: string;
  unprocessedCount: number;
  totalCount: number;
}

/** 自选/监控池汇总 */
export interface PoolSummary {
  watchlistCount: number;
  monitorCount: number;
  activeMonitorCount: number;
  items: { code: string; name: string; status: string; price?: number; changePercent?: number }[];
}

/** 系统状态 */
export interface SystemStatusInfo {
  dataSources: {
    id: string;
    name: string;
    status: 'online' | 'offline' | 'degraded';
    latency: number;
  }[];
  resources: {
    cpu: number;
    memory: number;
    uptime: string;
  };
}
