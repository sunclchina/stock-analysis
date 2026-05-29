/**
 * M04 鏅鸿兘閫夎偂妯″潡 API
 *
 * 瀵规帴鍚庣 /selection 璺敱銆? * 鍝嶅簲鏍煎紡瀵归綈鍚庣鍝嶅簲缁撴瀯 { items: [...], count: N, ... }銆? */
import apiClient from './api';

// ========== Types (瀵归綈璁捐鏂囨。搂5.3 杈撳嚭瀛楁)  ==========

export interface SelectionRequest {
  strategy?: string;          // 鍥哄畾閫夎偂: 'steady_trend' | 'reversal_breakout' | 'short_term_strong'
  template_id?: string;       // 鍚庣鍙傛暟鍚嶏紙浜岄€変竴锛?  limit?: number;             // 瀹归噺涓婇檺锛?~100锛岄粯璁?0锛?  max_results?: number;       // 鍚庣鍙傛暟鍚嶏紙浜岄€変竴锛?  dimensions?: CustomSelectionDimensions;  // 鑷畾涔夐€夎偂鍥涘ぇ缁村害
  min_score?: number;         // 鏈€浣庤瘎鍒嗛槇鍊
}

export interface SelectionResultItem {
  rank: number;
  code: string;
  name: string;
  industry: string;
  trendColor: 'red' | 'green' | 'yellow' | 'gray' | 'blue';
  resonanceStatus?: string;   // 鍏辨尟鐘舵€侊紙璁捐鏂囨。搂5.3瑕佹眰锛?  trendStrength: number;      // 0-100
  riskScore: number;          // 瓒婁綆瓒婂畨鍏?  riskLevel: 'low' | 'medium' | 'high';
  financeGrade: 'A' | 'B' | 'C' | 'D';
  compositeScore: number;     // 0-100
  operationAdvice: string;
  addedToWatchlist?: boolean;
}

export interface SelectionResponse {
  items: SelectionResultItem[];
  count: number;
  total_count?: number;
  message?: string;
  trading_session?: Record<string, any>;
  layer_counts?: Record<string, number>;
}

export interface SelectionTemplateInfo {
  id: string;
  name: string;
  description: string;
  max_results: number;
  layer_filter_counts?: any;
}

// ========== 鑷畾涔夐€夎偂鍥涘ぇ缁村害绫诲瀷 ==========

export interface DimensionRange {
  min?: number;
  max?: number;
}

export interface ScopeDimension {
  industries?: string[];
  market_cap?: DimensionRange;   // 鎬诲競鍊硷紙涓囧厓锛?  amount?: DimensionRange;       // 鎴愪氦棰濓紙涓囧厓锛?  logic?: 'and' | 'or';
}

export interface FundamentalDimension {
  profit_growth?: DimensionRange;  // 鍑€鍒╂鼎澧為暱鐜?%)
  debt_ratio?: DimensionRange;     // 璧勪骇璐熷€虹巼(%)
  pe?: DimensionRange;             // 甯傜泩鐜?  pb?: DimensionRange;             // 甯傚噣鐜?  roe?: { min: number };           // ROE闃堝€?%)
  gross_margin?: DimensionRange;   // 姣涘埄鐜?%)
  operate_cashflow_positive?: boolean;  // 缁忚惀鐜伴噾娴?0
  finance_grade?: string;          // 璐㈠姟绛夌骇("green"/"yellow"/"red")
  logic?: 'and' | 'or';
}

export interface TechnicalDimension {
  ma_type?: 'bullish' | 'bearish' | 'entanglement';  // 鍧囩嚎鎺掑垪
  price_above_ma?: 'ma5' | 'ma10' | 'ma20';           // 浠锋牸涓嶮A鍏崇郴
  macd_state?: string[];    // MACD鐘舵€? "golden"/"death"/"red_expand"绛?  volume_ratio?: DimensionRange;    // 閲忔瘮
  turnover_rate?: DimensionRange;   // 鎹㈡墜鐜?%)
  rsi_state?: 'gt_70' | 'lt_30' | 'gt_50' | 'lt_50';  // RSI鏉′欢
  bollinger_position?: 'upper' | 'middle' | 'lower' | 'below';  // 甯冩灄甯︿綅缃?  logic?: 'and' | 'or';
}

export interface ResonanceDimension {
  low_resonance?: string[];       // 浣庝綅鍏辨尟鏉′欢鍒楄〃
  high_resonance?: string[];      // 楂樹綅鍏辨尟鏉′欢鍒楄〃
  multi_resonance?: string[];     // 澶氭寚鏍囧叡鎸潯浠跺垪琛?  min_match?: number;             // 鑷冲皯婊¤冻N椤?  link_fixed_rules?: boolean;     // 鑱斿姩鍥哄畾瑙勫垯鍏辨尟浣撶郴
  logic?: 'and' | 'or';
}

export interface CustomSelectionDimensions {
  scope?: ScopeDimension;
  fundamental?: FundamentalDimension;
  technical?: TechnicalDimension;
  resonance?: ResonanceDimension;
}

// ========== 鑷畾涔夐€夎偂妯℃澘 ==========

export interface CustomSelectionTemplate {
  id: string;
  name: string;
  dimensions: CustomSelectionDimensions;
  max_results?: number;
  min_score?: number;
  isDefault?: boolean;
  createdAt?: string;
}

// ========== 3涓唴缃粯璁ゆā鏉?==========

export const DEFAULT_TEMPLATES: CustomSelectionTemplate[] = [
  {
    id: 'default_short_term',
    name: '短线共振模板',
    dimensions: {
      technical: {
        ma_type: 'bullish',
        volume_ratio: { min: 0.8 },
        logic: 'and',
      },
      resonance: {
        multi_resonance: ['ma_bullish', 'rsi_gt_50', 'price_above_ma20', 'trend_up', 'ma20_trend_up'],
        min_match: 2,
        logic: 'and',
      },
    },
    max_results: 30,
    min_score: 75,
    isDefault: true,
  },
  {
    id: 'default_long_term_value',
    name: '长线价值模板',
    dimensions: {
      fundamental: {
        profit_growth: { min: 15 },
        roe: { min: 15 },
        pe: { min: 10, max: 30 },
        finance_grade: 'green',
        logic: 'and',
      },
    },
    max_results: 20,
    min_score: 80,
    isDefault: true,
  },
  {
    id: 'default_low_reversal',
    name: '低位反转模板',
    dimensions: {
      resonance: {
        low_resonance: ['low_position', 'rsi_lt_30', 'boll_lower', 'neg_deviation_gt_8'],
        min_match: 2,
        logic: 'and',
      },
      scope: {
        amount: { min: 1000 },
        logic: 'and',
      },
    },
    max_results: 30,
    min_score: 70,
    isDefault: true,
  },
];

// ========== Fixed Selection ==========

/**
 * 鍥哄畾瑙勫垯閫夎偂銆? * POST /selection/fixed
 */
export async function fixedSelection(
  strategy: string,
  limit?: number
): Promise<SelectionResponse> {
  const body: any = {
    strategy: strategy,
    template_id: strategy,
  };
  if (limit !== undefined) {
    body.limit = limit;
    body.max_results = limit;
  }
  return apiClient.post('/selection/fixed', body);
}

// ========== Custom Selection (鍥涘ぇ缁村害) ==========

/**
 * 鑷畾涔夐€夎偂锛堝洓澶х淮搴︼級銆? * POST /selection/custom
 */
export async function customSelection(
  dimensions: CustomSelectionDimensions,
  limit?: number,
  minScore?: number
): Promise<SelectionResponse> {
  const body: any = {
    dimensions: dimensions,
  };
  if (limit !== undefined) {
    body.max_results = limit;
  }
  if (minScore !== undefined) {
    // 鍚庡彴鏆備笉鏀寔鐙珛鐨刴in_score锛屼繚鐣欎负鍏煎
  }
  return apiClient.post('/selection/custom', body);
}

// ========== Templates ==========

/**
 * 鑾峰彇鍥哄畾閫夎偂妯℃澘鍒楄〃銆? * GET /selection/templates
 */
export async function getSelectionTemplates(): Promise<{
  templates: SelectionTemplateInfo[];
  count: number;
}> {
  return apiClient.get('/selection/templates');
}

// ========== 鏈嶅姟绔嚜瀹氫箟閫夎偂妯℃澘绠＄悊 ==========

/**
 * 鑾峰彇鏈嶅姟绔嚜瀹氫箟閫夎偂妯℃澘鍒楄〃銆? * GET /selection/custom-templates
 */
export async function getCustomTemplates(): Promise<{
  templates: CustomSelectionTemplate[];
  count: number;
}> {
  return apiClient.get('/selection/custom-templates');
}

/**
 * 淇濆瓨鑷畾涔夐€夎偂妯℃澘鍒版湇鍔＄銆? * POST /selection/custom-templates
 */
export async function saveCustomTemplate(
  template: CustomSelectionTemplate
): Promise<{ success: boolean; template: CustomSelectionTemplate }> {
  return apiClient.post('/selection/custom-templates', template);
}

/**
 * 鍒犻櫎鏈嶅姟绔殑鑷畾涔夐€夎偂妯℃澘銆? * DELETE /selection/custom-templates/{id}
 */
export async function deleteCustomTemplate(
  templateId: string
): Promise<{ success: boolean }> {
  return apiClient.delete(`/selection/custom-templates/${templateId}`);
}

// ========== 鑷畾涔夐€夎偂妯℃澘锛堟湰鍦扮鐞嗭級 ==========

const STORAGE_KEY = 'custom-selection-templates';

export function getSavedTemplates(): CustomSelectionTemplate[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const saved: CustomSelectionTemplate[] = raw ? JSON.parse(raw) : [];
    // 鍚堝苟榛樿妯℃澘锛堜笉鍙垹闄わ級
    const defaultIds = new Set(DEFAULT_TEMPLATES.map(t => t.id));
    const filtered = saved.filter(t => !defaultIds.has(t.id));
    return [...DEFAULT_TEMPLATES, ...filtered];
  } catch {
    return DEFAULT_TEMPLATES;
  }
}

export function saveTemplate(template: CustomSelectionTemplate): void {
  const saved = getSavedTemplates().filter(t => !t.isDefault);
  const idx = saved.findIndex(t => t.id === template.id);
  if (idx >= 0) {
    saved[idx] = template;
  } else {
    saved.push(template);
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(saved));
}

export function deleteTemplate(id: string): void {
  const saved = getSavedTemplates().filter(t => !t.isDefault && t.id !== id);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(saved));
}


