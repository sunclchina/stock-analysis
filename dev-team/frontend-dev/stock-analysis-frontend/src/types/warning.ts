// ========== M03 智能预警类型 ==========

/** 预警级别 */
export type WarningLevel = 'high' | 'medium' | 'low';

/** 预警类型 */
export type WarningType =
  | 'price'
  | 'updown'
  | 'trend'
  | 'resonance'
  | 'finance'
  | 'event'
  | 'risk';

/** 预警类型中文映射 */
export const WarningTypeLabel: Record<WarningType, string> = {
  price: '价格预警',
  updown: '涨跌预警',
  trend: '趋势预警',
  resonance: '共振预警',
  finance: '财务预警',
  event: '突发预警',
  risk: '风险评分',
};

/** 预警级别中文映射 */
export const WarningLevelLabel: Record<WarningLevel, string> = {
  high: '高',
  medium: '中',
  low: '低',
};

/** 预警级别颜色 */
export const WarningLevelColor: Record<WarningLevel, string> = {
  high: '#ff4d4f',
  medium: '#faad14',
  low: '#52c41a',
};

/** 处理状态 */
export type ProcessStatus = 'pending' | 'acknowledged' | 'resolved';

/** 预警项 */
export interface WarningItem {
  id: string;
  stockCode: string;
  stockName: string;
  warningType: WarningType;
  level: WarningLevel;
  triggerTime: string;
  currentValue: string;
  threshold: string;
  operationAdvice: string;
  processStatus: ProcessStatus;
  message: string;
}

/** 预警汇总统计 */
export interface WarningStats {
  total: number;
  unprocessed: number;
  byType: Record<WarningType, number>;
  byLevel: Record<WarningLevel, number>;
}

/** 预警详情 - 完整的股票预警信息 */
export interface WarningDetail {
  stockCode: string;
  stockName: string;
  priceWarning: {
    trigger: boolean;
    currentPrice: number;
    upperLimit: number;
    lowerLimit: number;
    level: WarningLevel;
    message: string;
  };
  updownWarning: {
    trigger: boolean;
    openPrice: number;
    currentPrice: number;
    changePercent: number;
    level: WarningLevel;
    message: string;
  };
  trendWarning: {
    trigger: boolean;
    ma5: number;
    ma10: number;
    ma20: number;
    ma60: number;
    crossSignal: string;
    level: WarningLevel;
    message: string;
  };
  resonanceWarning: {
    trigger: boolean;
    score: number;
    items: { name: string; score: number; status: boolean }[];
    level: WarningLevel;
    message: string;
  };
  financeWarning: {
    trigger: boolean;
    pe: number;
    pb: number;
    roe: number;
    debtRatio: number;
    level: WarningLevel;
    message: string;
  };
  eventWarning: {
    trigger: boolean;
    events: { type: string; description: string; impact: string }[];
    level: WarningLevel;
    message: string;
  };
  riskScore: {
    score: number;
    baseScore: number;
    dynamicScore: number;
    level: WarningLevel;
    message: string;
  };
  operationAdvice: string;
  overallLevel: WarningLevel;
  lastUpdate: string;
}

/** 预警筛选条件 */
export interface WarningFilter {
  type: WarningType | 'all';
  level: WarningLevel | 'all';
  keyword: string;
  processStatus: ProcessStatus | 'all';
}

/** 预警列表查询参数 */
export interface WarningListParams {
  page: number;
  pageSize: number;
  filter: WarningFilter;
}
