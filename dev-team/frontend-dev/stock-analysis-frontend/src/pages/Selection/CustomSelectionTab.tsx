// @ts-nocheck
﻿/**
 * 自定义夐盘股鏍囩项碉紙v2 鈥?鍥涘ぇ缁村害牌堬級
 *
 * 瀵圭収璁捐鏂标。 v2.0 搂4? * - 鍥涘ぇ缁村害条′件堣寖鍥?基本非?技盘术面/共振绫伙級
 * - 宸︿晶非㈡澘只姌只狅紝姣忕维度︾嫭绔婣ND/OR选昏緫
 * - 模板保守瓨/加载/删除?一唴缃粯璁ゆā条夸笉只垹闄わ級
 * - 只充晶缁撴灉灞曠ず堟帓度?瀵煎嚭/鍔犲叆鑷盘?瀛楁映射ve 鈫?CamelCase? * - 缁撴灉瓒呰繃500只彁绀哄鍔犵筛选夋潯价? */
import React, { useState, useCallback, useMemo, useEffect } from 'react';
import {
  Card, Button, Table, Tag, Space, Select, InputNumber, Input,
  Tooltip, message, Typography, Empty, Divider, Row, Col, Popconfirm,
  Modal, Descriptions, Spin, Form, Checkbox, Radio, Collapse, Switch, Alert,
} from 'antd';
import {
  PlayCircleOutlined, PlusOutlined, DeleteOutlined,
  StarOutlined, StarFilled, UnorderedListOutlined,
  ReloadOutlined, SortAscendingOutlined,
  SaveOutlined, FolderOpenOutlined, DownloadOutlined,
  SettingOutlined, ClearOutlined, ExclamationCircleOutlined,
  QuestionCircleOutlined,
} from '@ant-design/icons';
import { authFetch, getCurrentUser } from '../../services/auth';
import { useConfigStore } from '../../store/configStore';
import type { ColumnsType, SortOrder } from 'antd/es/table/interface';
import type {
  SelectionResultItem,
  CustomSelectionDimensions,
  ScopeDimension,
  FundamentalDimension,
  TechnicalDimension,
  ResonanceDimension,
  CustomSelectionTemplate,
} from '../../services/selectionApi';
import {
  customSelection,
  getSavedTemplates,
  saveTemplate as saveTemplateToLocal,
  deleteTemplate as deleteTemplateFromLocal,
  DEFAULT_TEMPLATES,
} from '../../services/selectionApi';
import { useHelp } from '../../services/help';

const { Text, Title } = Typography;
const { Panel } = Collapse;

// K线数据加载
  const DIM_ICONS: Record<string, string> = {
  scope: '🍛',
  fundamental: '🍵',
  technical: '🍳',
  resonance: '🔧',
};

const DIM_LABELS: Record<string, string> = {
  scope: "范围筛选",
  fundamental: "基本面筛选",
  technical: "技术面筛选",
  resonance: "共振类筛选",
};

// K线数据加载
  const COMMON_INDUSTRIES: string[] = []; // 鍔ㄦ盘佸姞杞斤紝瑙?useEffect

async function fetchIndustryList(): Promise<string[]> {
  try {
    const res = await fetch('/api/v1/selection/industries');
    const data = await res.json();
    return data?.items || [];
  } catch { return []; }
}

// K线数据加载
  const LOW_RESONANCE_OPTIONS = [
  { value: 'low_position', label: '相对低位{"<"}30%' },
  { value: 'rsi_lt_30', label: 'RSI<30' },
  { value: 'boll_lower', label: '布林下轨' },
  { value: 'bottom_break', label: '底部分型' },
  { value: 'neg_deviation_gt_8', label: '负乖离{">"}8%' },
];

const HIGH_RESONANCE_OPTIONS = [
  { value: 'high_position', label: '相对高位{">"}70%' },
  { value: 'rsi_gt_70', label: 'RSI>70' },
  { value: 'boll_upper', label: '布林上轨' },
  { value: 'top_break', label: '顶部分型' },
  { value: 'pos_deviation_gt_8', label: '正乖离{">"}12%' },
];

const MULTI_RESONANCE_OPTIONS = [
  { value: 'macd_golden', label: 'MACD金叉' },
  { value: 'ma_bullish', label: 'MA上涨排列' },
  { value: 'volume_expand', label: '量比>=1.2(放量)' },
  { value: 'rsi_gt_50', label: 'RSI{">"}50' },
  { value: 'price_above_ma20', label: '站稳MA20' },
  { value: 'trend_up', label: '趋势向上' },
  { value: 'price_position_30_70', label: '价位30%-70%' },
  { value: 'ma20_trend_up', label: 'MA20趋势向上' },
];

// ========== 状态盘佺被型?==========

interface DimensionState<T> {
  config: T;
  logic: 'and' | 'or';
  enabled: boolean;
}

// ========== Component ==========

const CustomSelectionTab = () => {
  const { openHelp } = useHelp();
  // 鈹盘鈹盘 行业 分楄〃堝姩鎬佷粠后庣加载夆攢鈹盘
  const [industryOptions, setIndustryOptions] = React.useState<string[]>([]);
  React.useEffect(() => {
    fetchIndustryList().then(list => { if (list.length > 0) setIndustryOptions(list); });
  }, []);

  // K线数据加载
  const [scopeDim, setScopeDim] = useState<DimensionState<ScopeDimension>>({
    config: { industries: [], amount: {}, logic: 'and' },
    logic: 'and',
    enabled: false,
  });

  const [fundamentalDim, setFundamentalDim] = useState<DimensionState<FundamentalDimension>>({
    config: {
      profit_growth: {},
      debt_ratio: {},
      pe: {},
      pb: {},
      roe: { min: 15 },
      operate_cashflow_positive: false,
      logic: 'and',
    },
    logic: 'and',
    enabled: false,
  });

  const [technicalDim, setTechnicalDim] = useState<DimensionState<TechnicalDimension>>({
    config: {
      ma_type: undefined,
      price_above_ma: undefined,
      macd_state: [],
      volume_ratio: {},
      rsi_state: undefined,
      logic: 'and',
    },
    logic: 'and',
    enabled: false,
  });

  const [resonanceDim, setResonanceDim] = useState<DimensionState<ResonanceDimension>>({
    config: {
      low_resonance: [],
      high_resonance: [],
      multi_resonance: [],
      min_match: 2,
      link_fixed_rules: false,
      logic: 'and',
    },
    logic: 'and',
    enabled: false,
  });

  // K线数据加载
  const [loading, setLoading] = useState(false);
  // 加载缂撳瓨的勮嚜瀹氫箟选股结果
  const _uid = getCurrentUser()?.id || '0';
  const customCacheKey = `selection_custom_${_uid}`;
  const cachedCustom = localStorage.getItem(customCacheKey);
  const cachedCustomItems = cachedCustom ? (() => {
    try { return JSON.parse(cachedCustom).items || []; } catch { return []; }
  })() : [];
  const [results, setResults] = useState<SelectionResultItem[]>(cachedCustomItems);
  const [hasRun, setHasRun] = useState(cachedCustomItems.length > 0);
  const [detailStock, setDetailStock] = useState<any>(null);
  const [klineData, setKlineData] = useState<any[]>([]);
  const [klineLoading, setKlineLoading] = useState(false);

  // K线数据加载
  useEffect(() => {
    if (!detailStock) { setKlineData([]); return; }
    setKlineLoading(true);
    fetch(`/api/v1/market/kline/${detailStock.code}?count=60`)
      .then(r => r.json())
      .then(d => setKlineData(d?.klines || []))
      .catch(() => setKlineData([]))
      .finally(() => setKlineLoading(false));
  }, [detailStock]);
  const [maxResults, setMaxResults] = useState<number>(100);
  const [truncated, setTruncated] = useState(false);

  // 模板
  const [templateModalOpen, setTemplateModalOpen] = useState(false);
  const [saveModalOpen, setSaveModalOpen] = useState(false);
  const [templateName, setTemplateName] = useState('');

  const { watchlist, addWatchlistItem, removeWatchlistItem } = useConfigStore();
  const watchlistCodes = useMemo(() => new Set(watchlist.map((w) => w.code)), [watchlist]);

  // K线数据加载
  const templates = useMemo(() => getSavedTemplates(), []);

  // 鈹盘鈹盘 缁村害选氱敤分标崲 鈹盘鈹盘
  const toggleDim = useCallback((dim: string, enabled: boolean) => {
    const setters: Record<string, React.Dispatch<React.SetStateAction<any>>> = {
      scope: setScopeDim, fundamental: setFundamentalDim,
      technical: setTechnicalDim, resonance: setResonanceDim,
    };
    const prevs: Record<string, DimensionState<any>> = {
      scope: scopeDim, fundamental: fundamentalDim,
      technical: technicalDim, resonance: resonanceDim,
    };
    const setter = setters[dim];
    if (setter) {
      setter((prev: DimensionState<any>) => ({ ...prev, enabled }));
    }
  }, [scopeDim, fundamentalDim, technicalDim, resonanceDim]);

  const setDimLogic = useCallback((dim: string, logic: 'and' | 'or') => {
    const setters: Record<string, React.Dispatch<React.SetStateAction<any>>> = {
      scope: setScopeDim, fundamental: setFundamentalDim,
      technical: setTechnicalDim, resonance: setResonanceDim,
    };
    const setter = setters[dim];
    if (setter) {
      setter((prev: DimensionState<any>) => ({ ...prev, logic }));
    }
  }, []);

  // K线数据加载
  const buildDimensions = useCallback((): CustomSelectionDimensions => {
    const dims: CustomSelectionDimensions = {};

    if (scopeDim.enabled) {
      const scope: ScopeDimension = {};
      if (scopeDim.config.industries && scopeDim.config.industries.length > 0) {
        scope.industries = scopeDim.config.industries;
      }
      if (scopeDim.config.amount?.min !== undefined || scopeDim.config.amount?.max !== undefined) {
        scope.amount = { ...scopeDim.config.amount };
      }
      if (scopeDim.config.market_cap?.min !== undefined || scopeDim.config.market_cap?.max !== undefined) {
        scope.market_cap = { ...scopeDim.config.market_cap };
      }
      if (Object.keys(scope).length > 0) {
        scope.logic = scopeDim.logic;
        dims.scope = scope;
      }
    }

    if (fundamentalDim.enabled) {
      const fund: FundamentalDimension = {};
      if (fundamentalDim.config.profit_growth?.min !== undefined || fundamentalDim.config.profit_growth?.max !== undefined) {
        fund.profit_growth = { ...fundamentalDim.config.profit_growth };
      }
      if (fundamentalDim.config.debt_ratio?.min !== undefined || fundamentalDim.config.debt_ratio?.max !== undefined) {
        fund.debt_ratio = { ...fundamentalDim.config.debt_ratio };
      }
      if (fundamentalDim.config.pe?.min !== undefined || fundamentalDim.config.pe?.max !== undefined) {
        fund.pe = { ...fundamentalDim.config.pe };
      }
      if (fundamentalDim.config.pb?.min !== undefined || fundamentalDim.config.pb?.max !== undefined) {
        fund.pb = { ...fundamentalDim.config.pb };
      }
      if (fundamentalDim.config.roe?.min !== undefined) {
        fund.roe = { min: fundamentalDim.config.roe.min };
      }
      if (fundamentalDim.config.gross_margin?.min !== undefined || fundamentalDim.config.gross_margin?.max !== undefined) {
        fund.gross_margin = { ...fundamentalDim.config.gross_margin };
      }
      if (fundamentalDim.config.operate_cashflow_positive) {
        fund.operate_cashflow_positive = true;
      }
      if (fundamentalDim.config.finance_grade) {
        fund.finance_grade = fundamentalDim.config.finance_grade;
      }
      if (Object.keys(fund).length > 0) {
        fund.logic = fundamentalDim.logic;
        dims.fundamental = fund;
      }
    }

    // K线数据加载
  const techConfig = technicalDim.config;
    const hasTechCond = techConfig.ma_type || techConfig.price_above_ma || 
      (techConfig.macd_state && techConfig.macd_state.length > 0) ||
      techConfig.volume_ratio?.min !== undefined || techConfig.volume_ratio?.max !== undefined ||
      techConfig.turnover_rate?.min !== undefined || techConfig.turnover_rate?.max !== undefined ||
      techConfig.rsi_state || techConfig.bollinger_position;
    if (hasTechCond) {
      const tech: TechnicalDimension = {};
      if (techConfig.ma_type) tech.ma_type = techConfig.ma_type;
      if (techConfig.price_above_ma) tech.price_above_ma = techConfig.price_above_ma;
      if (techConfig.macd_state && techConfig.macd_state.length > 0) {
        tech.macd_state = [...techConfig.macd_state];
      }
      if (techConfig.volume_ratio?.min !== undefined || techConfig.volume_ratio?.max !== undefined) {
        tech.volume_ratio = { ...techConfig.volume_ratio };
      }
      if (techConfig.turnover_rate?.min !== undefined || techConfig.turnover_rate?.max !== undefined) {
        tech.turnover_rate = { ...techConfig.turnover_rate };
      }
      if (techConfig.rsi_state) tech.rsi_state = techConfig.rsi_state;
      if (techConfig.bollinger_position) tech.bollinger_position = techConfig.bollinger_position;
      if (Object.keys(tech).length > 0) {
        tech.logic = technicalDim.logic;
        dims.technical = tech;
      }
    }

    if (resonanceDim.enabled) {
      const res: ResonanceDimension = {};
      if (resonanceDim.config.low_resonance && resonanceDim.config.low_resonance.length > 0) {
        res.low_resonance = [...resonanceDim.config.low_resonance];
      }
      if (resonanceDim.config.high_resonance && resonanceDim.config.high_resonance.length > 0) {
        res.high_resonance = [...resonanceDim.config.high_resonance];
      }
      if (resonanceDim.config.multi_resonance && resonanceDim.config.multi_resonance.length > 0) {
        res.multi_resonance = [...resonanceDim.config.multi_resonance];
      }
      if (resonanceDim.config.min_match !== undefined) {
        res.min_match = resonanceDim.config.min_match;
      }
      if (resonanceDim.config.link_fixed_rules) {
        res.link_fixed_rules = true;
      }
      if (Object.keys(res).length > 0) {
        res.logic = resonanceDim.logic;
        dims.resonance = res;
      }
    }

    return dims;
  }, [scopeDim, fundamentalDim, technicalDim, resonanceDim]);

  // K线数据加载
  const handleRun = useCallback(async () => {
    const dims = buildDimensions();
    const dimCount = Object.keys(dims).length;
    if (dimCount === 0) {
      message.warning('请至少开启并配置一个筛选维度');
      return;
    }

    setLoading(true);
    setTruncated(false);
    try {
      const res = await customSelection(dims, maxResults);
      const rawItems: any[] = res?.items || [];
      const items: SelectionResultItem[] = rawItems.map((item: any) => ({
        rank: item.rank,
        code: item.code,
        name: item.name,
        industry: item.industry || '',
        trendColor: item.trendColor || item.trend_color,
        resonanceStatus: item.resonanceStatus || item.resonance_status,
        trendStrength: item.trendStrength ?? item.trend_strength ?? 0,
        riskScore: item.riskScore ?? item.risk_score ?? 50,
        riskLevel: item.riskLevel || item.risk_level || 'medium',
        financeGrade: item.financeGrade || item.finance_grade || 'B',
        compositeScore: item.compositeScore ?? item.total_score ?? 0,
        operationAdvice: item.operationAdvice || item.trade_advice || '',
        addedToWatchlist: watchlistCodes.has(item.code),
      }));
      setResults(items);
      // 缂撳瓨术自定义夐盘股缁撴灉
      const ccKey = `selection_custom_${getCurrentUser()?.id || '0'}`;
      localStorage.setItem(ccKey, JSON.stringify({
        items, truncated: res.truncated, total_count: res.total_count,
      }));
      setHasRun(true);

      if (res.truncated) {
        setTruncated(true);
        message.warning('结果超过500只，已截断，请增加筛选条件');
      } else if (items.length === 0) {
        message.info('当前条件未选出股票，请调整筛选条件')
      } else if (items.length >= 200) {
        message.info(`选出 ${items.length} 只，建议增加更多条件缩小范围`);
      } else {
        message.success(`选股完成，共 ${items.length} 只股票通过筛选`);
      }
    } catch (err) {
      console.error('自定义选股失败:', err);
      message.error('选股失败，请检查网络或联系管理员')
      setResults([]);
      setHasRun(true);
    } finally {
      setLoading(false);
    }
  }, [buildDimensions, maxResults, watchlistCodes]);

  // 鈹盘鈹盘 鑷盘股分标崲 鈹盘鈹盘

  const handleWatchlistToggle = useCallback(
    async (item: SelectionResultItem) => {
      if (item.addedToWatchlist) {
        try {
          await authFetch(`/api/v1/config/watchlist/${item.code}`, { method: 'DELETE' });
          removeWatchlistItem(item.code);
          setResults((prev) => prev.map((r) => r.code === item.code ? { ...r, addedToWatchlist: false } : r));
          message.success(`已从自选股移除 ${item.name}`);
        } catch { message.error('操作失败'); }
      } else {
        try {
          await authFetch('/api/v1/config/watchlist', {
            method: 'POST',
            body: JSON.stringify({ code: item.code, name: item.name }),
          });
          addWatchlistItem({ code: item.code, name: item.name, addedAt: new Date().toISOString() });
          setResults((prev) => prev.map((r) => r.code === item.code ? { ...r, addedToWatchlist: true } : r));
          message.success(`已从自选股移除 ${item.name}`);
        } catch { message.error('操作失败'); }
      }
    },
    [addWatchlistItem, removeWatchlistItem]
  );

  // K线数据加载
  const handleExport = useCallback(() => {
    if (results.length === 0) { message.warning('没有数据可以导出'); return; }
    const headers = ["Rank","Code","Name","Industry","Trend","Resonance","Strength","RiskScore","RiskLvl","FinGrade","Score","Advice"];
    const rows = results.map((r) => [r.rank, r.code, r.name, r.industry, r.trendColor, r.resonanceStatus || '-', r.trendStrength, r.riskScore, r.riskLevel, r.financeGrade, r.compositeScore, r.operationAdvice]);
    const csv = [headers.join(', , ...rows.map(r => r.join(', )].join('\n');
    const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `selection_results_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    message.success('导出成功');
  }, [results]);

  // K线数据加载
  const handleLoadTemplate = useCallback((tmpl: CustomSelectionTemplate) => {
    const d = tmpl.dimensions;
    if (!d) { message.warning('模板数据无效'); return; }

    if (d.scope) {
      setScopeDim({
        config: {
          industries: d.scope.industries || [],
          amount: d.scope.amount || {},
          market_cap: d.scope.market_cap || {},
        },
        logic: d.scope.logic || 'and',
        enabled: Object.keys(d.scope).some(k => k !== 'logic' && d.scope![k as keyof ScopeDimension] !== undefined),
      });
    } else {
      setScopeDim(prev => ({ ...prev, enabled: false }));
    }

    if (d.fundamental) {
      setFundamentalDim({
        config: {
          profit_growth: d.fundamental.profit_growth || {},
          debt_ratio: d.fundamental.debt_ratio || {},
          pe: d.fundamental.pe || {},
          pb: d.fundamental.pb || {},
          roe: d.fundamental.roe || { min: 15 },
          gross_margin: d.fundamental.gross_margin || {},
          operate_cashflow_positive: d.fundamental.operate_cashflow_positive || false,
          finance_grade: d.fundamental.finance_grade || '',
        },
        logic: d.fundamental.logic || 'and',
        enabled: Object.keys(d.fundamental).some(k => k !== 'logic'),
      });
    } else {
      setFundamentalDim(prev => ({ ...prev, enabled: false }));
    }

    if (d.technical) {
      setTechnicalDim({
        config: {
          ma_type: d.technical.ma_type || undefined,
          price_above_ma: d.technical.price_above_ma || undefined,
          macd_state: d.technical.macd_state || [],
          volume_ratio: d.technical.volume_ratio || {},
          turnover_rate: d.technical.turnover_rate || {},
          rsi_state: d.technical.rsi_state || undefined,
          bollinger_position: d.technical.bollinger_position || undefined,
        },
        logic: d.technical.logic || 'and',
        enabled: Object.keys(d.technical).some(k => k !== 'logic'),
      });
    } else {
      setTechnicalDim(prev => ({ ...prev, enabled: false }));
    }

    if (d.resonance) {
      setResonanceDim({
        config: {
          low_resonance: d.resonance.low_resonance || [],
          high_resonance: d.resonance.high_resonance || [],
          multi_resonance: d.resonance.multi_resonance || [],
          min_match: d.resonance.min_match ?? 2,
          link_fixed_rules: d.resonance.link_fixed_rules || false,
        },
        logic: d.resonance.logic || 'and',
        enabled: Object.keys(d.resonance).some(k => k !== 'logic'),
      });
    } else {
      setResonanceDim(prev => ({ ...prev, enabled: false }));
    }

    if (tmpl.max_results) setMaxResults(tmpl.max_results);
    setTemplateModalOpen(false);
    message.success(`已加载模板 ${tmpl.name}`);
  }, []);

  // K线数据加载
  const handleSaveTemplate = useCallback(() => {
    if (!templateName.trim()) { message.warning('请输入模板名称'); return; }
    const dims = buildDimensions();
    if (Object.keys(dims).length === 0) { message.warning('没有配置筛选条件'); return; }

    const newTmpl: CustomSelectionTemplate = {
      id: `custom_${Date.now()}`,
      name: templateName.trim(),
      dimensions: dims,
      max_results: maxResults,
      createdAt: new Date().toISOString(),
    };
    saveTemplateToLocal(newTmpl);
    message.success('模板已保存');
    setSaveModalOpen(false);
    setTemplateName('');
  }, [templateName, maxResults, buildDimensions]);

  // K线数据加载
  const handleDeleteTemplate = useCallback((id: string) => {
    deleteTemplateFromLocal(id);
    message.success('模板已删除')
  }, []);

  // 鈹盘鈹盘 重置 鈹盘鈹盘
  const handleReset = useCallback(() => {
    setScopeDim({ config: { industries: [], amount: {} }, logic: 'and', enabled: false });
    setFundamentalDim({
      config: { profit_growth: {}, debt_ratio: {}, pe: {}, pb: {}, roe: { min: 15 }, operate_cashflow_positive: false, gross_margin: {}, finance_grade: '' },
      logic: 'and', enabled: false,
    });
    setTechnicalDim({
      config: { ma_type: undefined, price_above_ma: undefined, macd_state: [], volume_ratio: {}, turnover_rate: {}, rsi_state: undefined, bollinger_position: undefined },
      logic: 'and', enabled: false,
    });
    setResonanceDim({
      config: { low_resonance: [], high_resonance: [], multi_resonance: [], min_match: 2, link_fixed_rules: false },
      logic: 'and', enabled: false,
    });
    setResults([]);
    setHasRun(false);
    setTruncated(false);
    message.info('已重置所有筛选条件')
  }, []);

  // K线数据加载
  const updateScope = useCallback((patch: Partial<ScopeDimension>) => {
    setScopeDim(prev => ({ ...prev, config: { ...prev.config, ...patch } }));
  }, []);
  const updateFundamental = useCallback((patch: Partial<FundamentalDimension>) => {
    setFundamentalDim(prev => ({ ...prev, config: { ...prev.config, ...patch } }));
  }, []);
  const updateTechnical = useCallback((patch: Partial<TechnicalDimension>) => {
    setTechnicalDim(prev => ({ ...prev, config: { ...prev.config, ...patch } }));
  }, []);
  const updateResonance = useCallback((patch: Partial<ResonanceDimension>) => {
    setResonanceDim(prev => ({ ...prev, config: { ...prev.config, ...patch } }));
  }, []);

  // K线数据加载
  const columns: ColumnsType<SelectionResultItem> = [
    { title: '排名', dataIndex: 'rank', key: 'rank', width: 60,
      sorter: (a, b) => a.rank - b.rank,
      render: (rank: number) => <Text strong style={{ color: rank <= 3 ? '#ff4d4f' : undefined }}>{rank}</Text>,
    },
    { title: '代码', dataIndex: 'code', key: 'code', width: 100,
      render: (code: string, record: any) => <a onClick={() => setDetailStock(record)} style={{ fontSize: 14, fontWeight: 700 }}>{code}</a>,
    },
    { title: '名称', dataIndex: 'name', key: 'name', width: 110,
      render: (name: string, record: any) => <a onClick={() => setDetailStock(record)} style={{ fontWeight: 600, fontSize: 13 }}>{name}</a>,
    },
    { title: '行业 ', dataIndex: 'industry', key: 'industry', width: 100,
      render: (industry: string) => industry ? <Tag style={{ fontSize: 11 }}>{industry}</Tag> : <Text type="secondary">-</Text>,
    },
    { title: '赋势', dataIndex: 'trendColor', key: 'trendColor', width: 55,
      render: (color: string) => {
        const m: Record<string, string> = { red: '#cf1322', green: '#389e0d', yellow: '#faad14', gray: '#8c8c8c', blue: '#1677ff' };
        return <Tooltip title={{ red: '\u4e0a\u6da8', green: '\u6b63\u5e38', blue: '\u53cd\u8f6c', yellow: '\u9884\u8b66', gray: '\u65e0\u6570\u636e' }[color] || color}>
          <div style={{ width: 14, height: 14, borderRadius: '50%', background: m[color] || '#8c8c8c', display: 'inline-block' }} />
        </Tooltip>;
      },
    },
    { title: '共振状态', dataIndex: 'resonanceStatus', key: 'resonanceStatus', width: 90,
      render: (status: string) => status ? <Tag color={status.includes('上涨') ? 'green' : status.includes('空头') ? 'red' : 'default'} style={{ fontSize: 11 }}>{status}</Tag> : <Text type="secondary">-</Text>,
    },
    { title: '强度', dataIndex: 'trendStrength', key: 'trendStrength', width: 85,
      sorter: (a, b) => a.trendStrength - b.trendStrength,
      render: (val: number) => <Text style={{ color: val >= 70 ? '#52c41a' : val >= 50 ? '#faad14' : '#8c8c8c' }}>{val}</Text>,
    },
    { title: '风险评分', dataIndex: 'riskScore', key: 'riskScore', width: 85,
      sorter: (a, b) => a.riskScore - b.riskScore,
      render: (val: number) => <Text style={{ color: val <= 30 ? '#52c41a' : val <= 60 ? '#faad14' : '#ff4d4f' }}>{val}</Text>,
    },
    { title: '风险等级', dataIndex: 'riskLevel', key: 'riskLevel', width: 75,
      render: (level: string) => {
        const lm: Record<string, string> = { low: '#52c41a', medium: '#faad14', high: '#ff4d4f' };
        const ll: Record<string, string> = { low: '低', medium: '中', high: '高' };
        return <Tag color={lm[level]} style={{ fontSize: 11 }}>{ll[level]}</Tag>;
      },
    },
    { title: '财务等级', dataIndex: 'financeGrade', key: 'financeGrade', width: 75,
      render: (grade: string) => {
        const gm: Record<string, string> = { A: '#52c41a', B: '#1677ff', C: '#faad14', D: '#ff4d4f' };
        return <Tag color={gm[grade]}>{grade}</Tag>;
      },
    },
    { title: '综合得分', dataIndex: 'compositeScore', key: 'compositeScore', width: 90,
      sorter: (a, b) => a.compositeScore - b.compositeScore,
      defaultSortOrder: 'descend' as SortOrder,
      render: (val: number) => (
        <Text strong style={{ color: val >= 90 ? '#52c41a' : val >= 85 ? '#1677ff' : val >= 70 ? '#faad14' : '#8c8c8c' }}>
          {val}
        </Text>
      ),
    },
    { title: '操作建议', dataIndex: 'operationAdvice', key: 'operationAdvice', width: 100,
      render: (advice: string) => <span style={{ fontSize: 12 }}>{advice}</span>,
    },
    { title: '操作', dataIndex: 'action', key: 'action', width: 70, fixed: 'right' as const,
      render: (_: unknown, record: SelectionResultItem) => (
        <Tooltip title={record.addedToWatchlist ? '移除' : '加入'}>
          <Button type="text" size="small"
            icon={record.addedToWatchlist ? <StarFilled style={{ color: '#faad14' }} /> : <StarOutlined />}
            onClick={() => handleWatchlistToggle(record)}
          />
        </Tooltip>
      ),
    },
  ];

  // K线数据加载
  const renderScopePanel = () => (
    <div style={{ padding: '8px 4px' }}>
      {/* 行业 澶氶盘?*/}
      <div style={{ marginBottom: 12 }}>
        <Text style={{ fontSize: 12, fontWeight: 500, display: 'block', marginBottom: 4 }}>行业 </Text>
        <Select
          mode="multiple" size="small" style={{ width: '100%' }}
          placeholder="选夋嫨行业 堝彲澶氶盘夛級"
          value={scopeDim.config.industries}
          onChange={(v: string[]) => updateScope({ industries: v })}
          filterOption={(input, option) =>
            ((option?.label as string) ?? '').toLowerCase().includes(input.toLowerCase())
          }
          options={industryOptions.length > 0 ? industryOptions.map(i => ({ value: i, label: i })) : []}
          loading={industryOptions.length === 0}
          maxTagCount={3}
        />
      </div>
      {/* Amount守尯闂?*/}
      <div style={{ marginBottom: 8 }}>
        <Text style={{ fontSize: 12, fontWeight: 500, display: 'block', marginBottom: 4 }}>成交额（亿元</Text>
        <Space size={4}>
          <InputNumber size="small" style={{ width: 80 }} placeholder="min"
            value={scopeDim.config.amount?.min}
            onChange={(v) => updateScope({ amount: { ...scopeDim.config.amount, min: v ?? undefined } })}
            min={0}
          />
          <Text type="secondary">~</Text>
          <InputNumber size="small" style={{ width: 80 }} placeholder="max"
            value={scopeDim.config.amount?.max}
            onChange={(v) => updateScope({ amount: { ...scopeDim.config.amount, max: v ?? undefined } })}
            min={0}
          />
        </Space>
      </div>
      {/* Market Cap煎尯闂?*/}
      <div>
        <Text style={{ fontSize: 12, fontWeight: 500, display: 'block', marginBottom: 4 }}>市值（亿元</Text>
        <Space size={4}>
          <InputNumber size="small" style={{ width: 80 }} placeholder="min"
            value={scopeDim.config.market_cap?.min}
            onChange={(v) => updateScope({ market_cap: { ...scopeDim.config.market_cap, min: v ?? undefined } })}
            min={0}
          />
          <Text type="secondary">~</Text>
          <InputNumber size="small" style={{ width: 80 }} placeholder="max"
            value={scopeDim.config.market_cap?.max}
            onChange={(v) => updateScope({ market_cap: { ...scopeDim.config.market_cap, max: v ?? undefined } })}
            min={0}
          />
        </Space>
      </div>
      <div style={{ marginTop: 8 }}>
        <Text type="secondary" style={{ fontSize: 11 }}>维度内逻辑（AND固定）</Text>
      </div>
    </div>
  );

  const renderFundamentalPanel = () => (
    <div style={{ padding: '8px 4px' }}>
      <Row gutter={[8, 10]}>
        <Col span={12}>
          <Text style={{ fontSize: 12, fontWeight: 500, display: 'block', marginBottom: 2 }}>ROE ≥ (%)</Text>
          <InputNumber size="small" style={{ width: '100%' }} placeholder="min"
            value={fundamentalDim.config.roe?.min}
            onChange={(v) => updateFundamental({ roe: { min: v ?? 15 } })}
            min={0} max={100}
          />
        </Col>
        <Col span={12}>
          <Text style={{ fontSize: 12, fontWeight: 500, display: 'block', marginBottom: 2 }}>ROE同比增长 (%)</Text>
          <InputNumber size="small" style={{ width: '100%' }} placeholder="min"
            value={fundamentalDim.config.profit_growth?.min}
            onChange={(v) => updateFundamental({ profit_growth: { ...fundamentalDim.config.profit_growth, min: v ?? undefined } })}
          />
        </Col>
        <Col span={12}>
          <Text style={{ fontSize: 12, fontWeight: 500, display: 'block', marginBottom: 2 }}>资产负债率 (%)</Text>
          <Space size={4} style={{ width: '100%' }}>
            <InputNumber size="small" style={{ width: '47%' }} placeholder="min"
              value={fundamentalDim.config.debt_ratio?.min}
              onChange={(v) => updateFundamental({ debt_ratio: { ...fundamentalDim.config.debt_ratio, min: v ?? undefined } })}
            />
            <Text type="secondary">~</Text>
            <InputNumber size="small" style={{ width: '47%' }} placeholder="max"
              value={fundamentalDim.config.debt_ratio?.max}
              onChange={(v) => updateFundamental({ debt_ratio: { ...fundamentalDim.config.debt_ratio, max: v ?? undefined } })}
            />
          </Space>
        </Col>
        <Col span={12}>
          <Text style={{ fontSize: 12, fontWeight: 500, display: 'block', marginBottom: 2 }}>PE（市盈率）</Text>
          <Space size={4} style={{ width: '100%' }}>
            <InputNumber size="small" style={{ width: '47%' }} placeholder="min"
              value={fundamentalDim.config.pe?.min}
              onChange={(v) => updateFundamental({ pe: { ...fundamentalDim.config.pe, min: v ?? undefined } })}
            />
            <Text type="secondary">~</Text>
            <InputNumber size="small" style={{ width: '47%' }} placeholder="max"
              value={fundamentalDim.config.pe?.max}
              onChange={(v) => updateFundamental({ pe: { ...fundamentalDim.config.pe, max: v ?? undefined } })}
            />
          </Space>
        </Col>
        <Col span={12}>
          <Text style={{ fontSize: 12, fontWeight: 500, display: 'block', marginBottom: 2 }}>PB（市净率）(%)</Text>
          <Space size={4} style={{ width: '100%' }}>
            <InputNumber size="small" style={{ width: '47%' }} placeholder="min"
              value={fundamentalDim.config.gross_margin?.min}
              onChange={(v) => updateFundamental({ gross_margin: { ...fundamentalDim.config.gross_margin, min: v ?? undefined } })}
            />
            <Text type="secondary">~</Text>
            <InputNumber size="small" style={{ width: '47%' }} placeholder="max"
              value={fundamentalDim.config.gross_margin?.max}
              onChange={(v) => updateFundamental({ gross_margin: { ...fundamentalDim.config.gross_margin, max: v ?? undefined } })}
            />
          </Space>
        </Col>
        <Col span={12}>
          <div style={{ marginTop: 18 }}>
            <Checkbox
              checked={fundamentalDim.config.operate_cashflow_positive}
              onChange={(e) => updateFundamental({ operate_cashflow_positive: e.target.checked })}
            >
              <Text style={{ fontSize: 12 }}>缁忚惀现金流?&gt; 0</Text>
            </Checkbox>
          </div>
        </Col>
        <Col span={24}>
          <Text style={{ fontSize: 12, fontWeight: 500, display: 'block', marginBottom: 2 }}>财务联动</Text>
          <Select size="small" style={{ width: '100%' }}
            placeholder="Enter"
            value={fundamentalDim.config.finance_grade || undefined}
            onChange={(v) => updateFundamental({ finance_grade: v || '' })}
            allowClear
            options={[
              { value: 'green', label: '🟢 安全无异常',},
              { value: 'yellow', label: '🟡 黄色预警' },
            ]}
          />
        </Col>
      </Row>
    </div>
  );

  const renderTechnicalPanel = () => (
    <div style={{ padding: '8px 4px' }}>
      {/* MA排列 */}
      <div style={{ marginBottom: 12 }}>
        <Text style={{ fontSize: 12, fontWeight: 500, display: 'block', marginBottom: 4 }}>MA排列</Text>
        <Radio.Group
          size="small" value={technicalDim.config.ma_type}
          onChange={(e) => updateTechnical({ ma_type: e.target.value })}
        >
          <Radio.Button value="bullish">上涨</Radio.Button>
          <Radio.Button value="bearish">空头</Radio.Button>
          <Radio.Button value="entanglement">纠缠</Radio.Button>
          <Radio.Button value={undefined}>无</Radio.Button>
        </Radio.Group>
      </div>

      {/* MACD 状态?*/}
      <div style={{ marginBottom: 12 }}>
        <Text style={{ fontSize: 12, fontWeight: 500, display: 'block', marginBottom: 4 }}>MACD 状态</Text>
        <Checkbox.Group
          value={technicalDim.config.macd_state}
          onChange={(v: any[]) => updateTechnical({ macd_state: v })}
        >
          <Space size={4} wrap>
            <Checkbox value="golden"><Text style={{ fontSize: 12 }}>金叉</Text></Checkbox>
            <Checkbox value="death"><Text style={{ fontSize: 12 }}>死叉</Text></Checkbox>
            <Checkbox value="red_expand"><Text style={{ fontSize: 12 }}>红柱放大</Text></Checkbox>
          </Space>
        </Checkbox.Group>
      </div>

      {/* 量比 */}
      <div style={{ marginBottom: 12 }}>
        <Text style={{ fontSize: 12, fontWeight: 500, display: 'block', marginBottom: 4 }}>量比</Text>
        <Space size={4}>
          <InputNumber size="small" style={{ width: 70 }} placeholder="min"
            value={technicalDim.config.volume_ratio?.min}
            onChange={(v) => updateTechnical({ volume_ratio: { ...technicalDim.config.volume_ratio, min: v ?? undefined } })}
            min={0} step={0.1}
          />
          <Text type="secondary">~</Text>
          <InputNumber size="small" style={{ width: 70 }} placeholder="max"
            value={technicalDim.config.volume_ratio?.max}
            onChange={(v) => updateTechnical({ volume_ratio: { ...technicalDim.config.volume_ratio, max: v ?? undefined } })}
            min={0} step={0.1}
          />
        </Space>
      </div>

      {/* Turnover鐜?*/}
      <div style={{ marginBottom: 12 }}>
        <Text style={{ fontSize: 12, fontWeight: 500, display: 'block', marginBottom: 4 }}>换手率(%)</Text>
        <Space size={4}>
          <InputNumber size="small" style={{ width: 70 }} placeholder="min"
            value={technicalDim.config.turnover_rate?.min}
            onChange={(v) => updateTechnical({ turnover_rate: { ...technicalDim.config.turnover_rate, min: v ?? undefined } })}
            min={0} step={0.1}
          />
          <Text type="secondary">~</Text>
          <InputNumber size="small" style={{ width: 70 }} placeholder="max"
            value={technicalDim.config.turnover_rate?.max}
            onChange={(v) => updateTechnical({ turnover_rate: { ...technicalDim.config.turnover_rate, max: v ?? undefined } })}
            min={0} step={0.1}
          />
        </Space>
      </div>

      {/* RSI */}
      <div style={{ marginBottom: 12 }}>
        <Text style={{ fontSize: 12, fontWeight: 500, display: 'block', marginBottom: 4 }}>RSI条件</Text>
        <Radio.Group
          size="small" value={technicalDim.config.rsi_state}
          onChange={(e) => updateTechnical({ rsi_state: e.target.value })}
        >
          <Radio.Button value="gt_70">超买{">"}70)</Radio.Button>
          <Radio.Button value="lt_30">超卖{"<"}30)</Radio.Button>
          <Radio.Button value="gt_50">{">"}50</Radio.Button>
          <Radio.Button value={undefined}>无</Radio.Button>
        </Radio.Group>
      </div>

      {/* 市冩灄市?*/}
      <div>
        <Text style={{ fontSize: 12, fontWeight: 500, display: 'block', marginBottom: 4 }}>布林带位置</Text>
        <Radio.Group
          size="small" value={technicalDim.config.bollinger_position}
          onChange={(e) => updateTechnical({ bollinger_position: e.target.value })}
        >
          <Radio.Button value="upper">上轨</Radio.Button>
          <Radio.Button value="middle">中轨</Radio.Button>
          <Radio.Button value="lower">下轨</Radio.Button>
          <Radio.Button value={undefined}>无</Radio.Button>
        </Radio.Group>
      </div>
    </div>
  );

  const renderResonancePanel = () => {
    const res = resonanceDim.config;
    const multiCount = res.multi_resonance?.length || 0;
    const maxMatch = Math.min(multiCount, res.min_match ?? 2);
    return (
      <div style={{ padding: '8px 4px' }}>
        {/* 位庝綅共振 */}
        <div style={{ marginBottom: 12 }}>
          <Text style={{ fontSize: 12, fontWeight: 500, display: 'block', marginBottom: 4 }}>低位共振条件</Text>
          <Checkbox.Group
            value={res.low_resonance}
            onChange={(v: any[]) => updateResonance({ low_resonance: v })}
          >
            <Space direction="vertical" size={2} style={{ width: '100%' }}>
              {LOW_RESONANCE_OPTIONS.map(opt => (
                <Checkbox key={opt.value} value={opt.value}>
                  <Text style={{ fontSize: 12 }}>{opt.label}</Text>
                </Checkbox>
              ))}
            </Space>
          </Checkbox.Group>
        </div>

        <Divider style={{ margin: '8px 0' }} />

        {/* 楂樹綅共振 */}
        <div style={{ marginBottom: 12 }}>
          <Text style={{ fontSize: 12, fontWeight: 500, display: 'block', marginBottom: 4 }}>高位共振条件</Text>
          <Checkbox.Group
            value={res.high_resonance}
            onChange={(v: any[]) => updateResonance({ high_resonance: v })}
          >
            <Space direction="vertical" size={2} style={{ width: '100%' }}>
              {HIGH_RESONANCE_OPTIONS.map(opt => (
                <Checkbox key={opt.value} value={opt.value}>
                  <Text style={{ fontSize: 12 }}>{opt.label}</Text>
                </Checkbox>
              ))}
            </Space>
          </Checkbox.Group>
        </div>

        <Divider style={{ margin: '8px 0' }} />

        {/* 澶氭寚鏍囧叡标?*/}
        <div style={{ marginBottom: 12 }}>
          <Text style={{ fontSize: 12, fontWeight: 500, display: 'block', marginBottom: 4 }}>多指标共振条件</Text>
          <Checkbox.Group
            value={res.multi_resonance}
            onChange={(v: any[]) => updateResonance({ multi_resonance: v })}
          >
            <Space direction="vertical" size={2} style={{ width: '100%' }}>
              {MULTI_RESONANCE_OPTIONS.map(opt => (
                <Checkbox key={opt.value} value={opt.value}>
                  <Text style={{ fontSize: 12 }}>{opt.label}</Text>
                </Checkbox>
              ))}
            </Space>
          </Checkbox.Group>
        </div>

        {/* 至少满足N项?*/}
        <div style={{ marginBottom: 8 }}>
          <Text style={{ fontSize: 12, fontWeight: 500, display: 'block', marginBottom: 4 }}>
            至少满足
            <Tag style={{ margin: '0 4px', fontSize: 11 }}>N={maxMatch}</Tag>
            项（目前共{multiCount}项）
          </Text>
          <InputNumber
            size="small" style={{ width: 80 }}
            min={1} max={Math.max(1, multiCount)}
            value={maxMatch}
            onChange={(v) => updateResonance({ min_match: v ?? 1 })}
          />
        </div>

        {/* 联动custom */}
        <div>
          <Checkbox
            checked={res.link_fixed_rules}
            onChange={(e) => updateResonance({ link_fixed_rules: e.target.checked })}
          >
            <Text style={{ fontSize: 12 }}>联动custom共振位撶郴堣秼鍔夸笂娑?共振鈮?项级</Text>
          </Checkbox>
        </div>
      </div>
    );
  };

  // K线数据加载
  const DimensionPanel = ({
    dimKey,
    title,
    children,
    state,
  }: {
    dimKey: string;
    title: string;
    children: React.ReactNode;
    state: DimensionState<any>;
  }) => (
    <Card
      size="small"
      style={{
        marginBottom: 8,
        borderRadius: 6,
        border: state.enabled ? '1px solid #1677ff' : '1px solid #f0f0f0',
      }}
      bodyStyle={{ padding: state.enabled ? '8px 12px' : '4px 12px' }}
      title={
        <Space style={{ width: '100%' }}>
          <span>{DIM_ICONS[dimKey]}</span>
          <Text strong style={{ fontSize: 13 }}>{title}</Text>
          {state.enabled && <Tag color="blue" style={{ fontSize: 10, marginLeft: 4 }}>已启用</Tag>}
        </Space>
      }
      extra={
        <Space size={4}>
          {dimKey !== 'scope' && (
            <Select
              size="small" style={{ width: 65 }}
              value={state.logic}
              onChange={(v) => setDimLogic(dimKey, v)}
            >
              <Select.Option value="and">AND</Select.Option>
              <Select.Option value="or">OR</Select.Option>
            </Select>
          )}
          <Switch
            size="small" checked={state.enabled}
            onChange={(v) => toggleDim(dimKey, v)}
            checkedChildren="开启" unCheckedChildren="关闭"
          />
        </Space>
      }
    >
      {state.enabled ? children : (
        <Text type="secondary" style={{ fontSize: 12, display: 'block', textAlign: 'center', padding: '4px 0' }}>
          点击开启此维度
        </Text>
      )}
    </Card>
  );

  // K线数据加载
  return (
    <div style={{ padding: '16px 0' }}>
      {/* 项堕儴宸ュ叿鏍?*/}
      <div style={{ marginBottom: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
        <Space>
          <Button size="small" icon={<FolderOpenOutlined />} onClick={() => setTemplateModalOpen(true)}>
            加载模板
          </Button>
          <Button size="small" icon={<SaveOutlined />} onClick={() => setSaveModalOpen(true)}>
            保存当前条件
          </Button>
          <Button size="small" icon={<ClearOutlined />} onClick={handleReset}>
            重置
          </Button>
          <Tooltip title="查看帮助">
            <Button type="text" size="small" icon={<QuestionCircleOutlined style={{ fontSize: 16, color: '#1677ff' }} />}
              onClick={() => openHelp('custom-selection')} />
          </Tooltip>
        </Space>
        <Space>
          <Text style={{ fontSize: 12 }}>上限</Text>
          <InputNumber size="small" min={1} max={500} value={maxResults}
            onChange={(v) => setMaxResults(v ?? 100)} style={{ width: 65 }}
          />
          <Text type="secondary" style={{ fontSize: 12 }}>只</Text>
          <Button
            type="primary" icon={<PlayCircleOutlined />}
            onClick={handleRun} loading={loading}
            style={{ minWidth: 120 }}
          >
            一键筛选          </Button>
        </Space>
      </div>

      {/* 成柇璀﹀憡 */}
      {truncated && (
        <Alert
          message="超过500只，已截断"
          description="请增加筛选条件" type="warning" showIcon icon={<ExclamationCircleOutlined />}
          style={{ marginBottom: 12, borderRadius: 6 }}
          closable
          onClose={() => setTruncated(false)}
        />
      )}

      <Row gutter={12}>
        {/* Dim︿晶通洓澶х维度﹂面条?*/}
        <Col xs={24} md={10} lg={9}>
          <div style={{ maxHeight: 'calc(100vh - 260px)', overflowY: 'auto', paddingRight: 4 }}>
            <DimensionPanel dimKey="scope" title="范围" state={scopeDim}>
              {renderScopePanel()}
            </DimensionPanel>
            <DimensionPanel dimKey="fundamental" title="基本面" state={fundamentalDim}>
              {renderFundamentalPanel()}
            </DimensionPanel>
            <DimensionPanel dimKey="technical" title="技术面" state={technicalDim}>
              {renderTechnicalPanel()}
            </DimensionPanel>
            <DimensionPanel dimKey="resonance" title="共振类" state={resonanceDim}>
              {renderResonancePanel()}
            </DimensionPanel>
          </div>
          <div style={{ marginTop: 8, textAlign: 'center' }}>
            <Text type="secondary" style={{ fontSize: 11 }}>
              维度间逻辑一?AND堟墍术夊启鐢ㄧ维度﹀悓鏃舵弧瓒筹級
            </Text>
          </div>
        </Col>

        {/* 只充晶氱粨鏋滃睍绀?*/}
        <Col xs={24} md={14} lg={15}>
          <Card
            size="small" style={{ borderRadius: 8 }}
            bodyStyle={{ padding: hasRun ? 0 : '24px' }}
            title={
              <Space>
                <span>选股结果</span>
                {hasRun && <Tag color="blue">{results.length} 只</Tag>}
              </Space>
            }
            extra={
              hasRun ? (
                <Space>
                  <SortAscendingOutlined style={{ opacity: 0.45 }} />
                  <Button size="small" icon={<DownloadOutlined />} onClick={handleExport}>
                    导出CSV
                  </Button>
                  <Button size="small" icon={<ReloadOutlined />} onClick={handleRun} loading={loading}>
                    重新选股
                  </Button>
                </Space>
              ) : null
            }
          >
            {!hasRun ? (
              <Empty description="暂无结果 - add filter criteria and click search" />
            ) : (
              <Table
                columns={columns}
                dataSource={results}
                rowKey="code"
                loading={loading}
                size="small"
                scroll={{ x: 1200 }}
                pagination={{
                  pageSize: 20, showSizeChanger: true, showQuickJumper: true,
                  pageSizeOptions: ['10', '20', '50'],
                  showTotal: (total, range) => `${range[0]}-${range[1]} / 共${total} `,
                }}
                locale={{ emptyText: <Empty description="暂无结果条′件术盘夊嚭鑲＄エ" /> }}
              />
            )}
          </Card>
        </Col>
      </Row>

      {/* 模板加载 Modal */}
      <Modal
        title="Save as Template"
        open={templateModalOpen}
        onCancel={() => setTemplateModalOpen(false)}
        footer={null}
        width={540}
      >
        <div style={{ maxHeight: 420, overflow: 'auto' }}>
          {templates.length === 0 ? (
            <Empty description="鏆傛棤保守瓨的勬ā条?" />
          ) : (
            templates.map((tmpl) => {
              const dims = tmpl.dimensions || {};
              const enabledDims = Object.keys(dims).filter(k => dims[k as keyof typeof dims]);
              return (
                <Card
                  key={tmpl.id}
                  size="small"
                  style={{ marginBottom: 8, borderRadius: 6 }}
                  bodyStyle={{ padding: '10px 14px' }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <Text strong>{tmpl.name}</Text>
                      {tmpl.isDefault && <Tag color="blue" style={{ marginLeft: 8, fontSize: 10 }}>内置</Tag>}
                      <div style={{ marginTop: 4, display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                        {enabledDims.map(d => (
                          <Tag key={d} style={{ fontSize: 10, margin: 0 }}>
                            {DIM_ICONS[d] || ''} {DIM_LABELS[d] || d}
                          </Tag>
                        ))}
                        <Text type="secondary" style={{ fontSize: 11 }}>
                          {tmpl.max_results ? `上限${tmpl.max_results}` : ''}
                          {tmpl.createdAt ? ` | ${new Date(tmpl.createdAt).toLocaleDateString()}` : ''}
                        </Text>
                      </div>
                    </div>
                    <Space>
                      <Button size="small" type="primary" onClick={() => handleLoadTemplate(tmpl)}>
                        加载
                      </Button>
                      {!tmpl.isDefault && (
                        <Popconfirm title="纭畾删除姝ゆā条匡紵" onConfirm={() => handleDeleteTemplate(tmpl.id)}>
                          <Button size="small" danger>删除</Button>
                        </Popconfirm>
                      )}
                    </Space>
                  </div>
                </Card>
              );
            })
          )}
        </div>
      </Modal>

      {/* 模板保守瓨 Modal */}
      <Modal
        title="Save Template"
        open={saveModalOpen}
        onCancel={() => setSaveModalOpen(false)}
        onOk={handleSaveTemplate}
        okText="保存"
      >
        <Form layout="vertical">
          <Form.Item label="模板名称" required>
            <Input
              placeholder="输入模板名称" />
          </Form.Item>
          <div>
            <Text type="secondary" style={{ fontSize: 12 }}>
            {Object.keys(buildDimensions()).map(d => DIM_LABELS[d] || d).join('銆') || '鏃'}
            </Text>
          </div>
        </Form>
      </Modal>

      {/* 鑲＄エ璇︽儏圭獥 */}
      <Modal title={detailStock ? `${detailStock.code} ${detailStock.name}` : ''} open={!!detailStock} onCancel={() => { setDetailStock(null); setKlineData([]); }} footer={null} width={700}>
        {detailStock && <>
          <Descriptions column={2} size="small" bordered style={{ marginBottom: 16 }}>
            <Descriptions.Item label="价格">{detailStock.price ?? '-'}</Descriptions.Item>
            <Descriptions.Item label="涨跌幅">{detailStock.changePct != null ? `${detailStock.changePct}%` : '-'}</Descriptions.Item>
            <Descriptions.Item label="综合得分">{detailStock.compositeScore}</Descriptions.Item>
            <Descriptions.Item label="风险评分">{detailStock.riskScore}</Descriptions.Item>
            <Descriptions.Item label="风险等级">{detailStock.riskLevel}</Descriptions.Item>
            <Descriptions.Item label="强度">{detailStock.trendStrength}</Descriptions.Item>
            <Descriptions.Item label="共振状态">{detailStock.resonanceStatus || '-'}</Descriptions.Item>
            <Descriptions.Item label="财务等级">{detailStock.financeGrade}</Descriptions.Item>
            <Descriptions.Item label="Info" span={2}>
              <Text strong style={{ color: detailStock.compositeScore >= 85 ? '#52c41a' : '#faad14' }}>{detailStock.operationAdvice}</Text>
            </Descriptions.Item>
          </Descriptions>
          <Divider style={{ margin: '8px 0', fontSize: 13 }}>K线图</Divider>
          <div style={{ width: '100%', height: 320 }}>
            {klineLoading ? <div style={{ textAlign: 'center', paddingTop: 120 }}><Spin /></div>
            : klineData.length > 0 ? <KLineChart data={klineData} />
            : <Text type="secondary" style={{ display: 'block', textAlign: 'center', paddingTop: 120 }}>暂无K线数据</Text>}
          </div>
        </>}
      </Modal>
    </div>
  );
};

// K线数据加载
  const KLineChart: React.FC<{ data: any[]; }> = ({ data }) => {
  const chartRef = React.useRef<any>(null);
  const containerRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (!containerRef.current || data.length === 0) return;
    import('echarts').then(echarts => {
      if (chartRef.current) chartRef.current.dispose();
      const chart = echarts.init(containerRef.current!);
      chartRef.current = chart;
      const kdata = data.map((k: any) => [
        k.date || k.trade_date || '',
        k.open !== undefined ? Number(k.open) : Number(k.open_price),
        k.close !== undefined ? Number(k.close) : Number(k.close_price),
        k.low !== undefined ? Number(k.low) : Number(k.low_price),
        k.high !== undefined ? Number(k.high) : Number(k.high_price),
        k.volume || 0,
      ]);
      const dates = kdata.map((d: any) => d[0]);
      const values = kdata.map((d: any) => [d[1], d[2], d[3], d[4]]);
      const volumes = kdata.map((d: any) => d[5]);
      chart.setOption({
        tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
        grid: [
          { left: '8%', right: '5%', top: '5%', height: '65%' },
          { left: '8%', right: '5%', top: '78%', height: '15%' },
        ],
        xAxis: [
          { type: 'category', data: dates, gridIndex: 0, axisLabel: { rotate: 30, fontSize: 10 } },
          { type: 'category', data: dates, gridIndex: 1, axisLabel: { show: false } },
        ],
        yAxis: [
          { type: 'value', gridIndex: 0, scale: true, splitNumber: 5 },
          { type: 'value', gridIndex: 1, splitNumber: 3 },
        ],
        series: [
          { type: 'candlestick', data: values, xAxisIndex: 0, yAxisIndex: 0,
            itemStyle: { color: '#ef5350', color0: '#26a69a', borderColor: '#ef5350', borderColor0: '#26a69a' } },
          { type: 'bar', data: volumes, xAxisIndex: 1, yAxisIndex: 1,
            itemStyle: { color: (p: any) => { const b = values[p.dataIndex]; return b ? (b[0] > b[1] ? '#ef5350' : '#26a69a') : '#999'; } } },
        ],
        dataZoom: [{ type: 'inside', xAxisIndex: [0, 1], start: Math.max(0, 100 - 60 * 100 / data.length), end: 100 }],
      });
      window.addEventListener('resize', () => chart.resize());
    });
    return () => { if (chartRef.current) chartRef.current.dispose(); };
  }, [data]);

  return <div ref={containerRef} style={{ width: '100%', height: '100%' }} />;
};

export default CustomSelectionTab;

