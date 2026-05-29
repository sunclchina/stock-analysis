/**
 * 资产组合管理页面（M07）
 *
 * 4个内部标签页：
 *   虚拟账户 - 资产总览、新建/重置账户、自动交易开关
 *   持仓管理 - 持仓列表、买卖、清仓记录
 *   量化策略 - 策略列表、新建/编辑、导入导出
 *   回测平台 - 回测配置、执行、报告
 */

import React, { useState, useEffect, useCallback } from 'react';
import { Tabs, Card, Table, Button, Modal, Form, Input, InputNumber, Select,
         Space, Statistic, Row, Col, Tag, Typography, Divider, Empty, message,
         Popconfirm, Switch, Tooltip, Progress, Checkbox, Menu, Slider, Alert, Collapse } from 'antd';
import {
  PlusOutlined, WalletOutlined, ReloadOutlined,
  RiseOutlined, FallOutlined, DeleteOutlined,
  SettingOutlined, BarChartOutlined, ExportOutlined, ImportOutlined,
  PlayCircleOutlined, HistoryOutlined, QuestionCircleOutlined,
} from '@ant-design/icons';
import { authFetch } from '../services/auth';
import { useHelp } from '../services/help';

const { Text, Title } = Typography;

// ═════ API 基础路径 ═════
const API = '/api/v1/portfolio';

// ═════ 类型定义 ═════
interface Account {
  id: number; name: string; initial_capital: number;
  current_assets: number; available_cash: number; position_value: number;
  total_profit: number; total_profit_rate: number; position_ratio: number;
  auto_trade_enabled: number; strategy_id: number | null;
  auto_trade_status: number; version: number; status: number;
  created_at: string;
}

interface PositionItem {
  id: number; account_id: number; stock_code: string; stock_name: string;
  quantity: number; avg_cost: number; current_price: number;
  profit_loss: number; profit_loss_rate: number; source_type: number;
  position_value: number; cost_total: number; created_at: string;
}

interface TransactionItem {
  id: number; stock_code: string; stock_name: string;
  trade_type_label: string; quantity: number; price: number;
  amount: number; commission: number; strategy_label: string;
  notes: string; created_at: string;
}

interface CloseRecord {
  id: number; stock_code: string; stock_name: string;
  buy_time: string; sell_time: string; hold_days: number;
  total_profit: number; total_profit_rate: number;
  trade_type_label: string; reason: string;
}

interface Strategy {
  id: number; name: string; strategy_type: string;
  period: string; description: string;
  config_json: any; status: number; created_at: string;
}

interface BacktestTask {
  id: number; strategy_id: number;
  start_date: string; end_date: string;
  init_capital: number; result_json: any;
  status: number; status_label: string; created_at: string;
}

// ═════ 工具函数 ═════
const fmtMoney = (v: number) => `¥${v.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const fmtPct = (v: number) => `${(v || 0) >= 0 ? '+' : ''}${(v || 0).toFixed(2)}%`;

// ═════ 标签页：虚拟账户 ═════
const AccountsTab: React.FC = () => {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [strategies, setStrategies] = useState<any[]>([]);
  const [form] = Form.useForm();

  // 策略列表在load()中一并加载

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [ar, sr] = await Promise.all([
        authFetch(`${API}/accounts`),
        authFetch(`${API}/strategies`),
      ]);
      const ad = await ar.json();
      const sd = await sr.json();
      setAccounts(ad.items || []);
      setStrategies(sd.items || []);
    } catch { message.error('加载账户失败'); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleCreate = async (vals: any) => {
    try {
      const r = await authFetch(`${API}/accounts`, {
        method: 'POST', body: JSON.stringify(vals),
      });
      const data = await r.json();
      if (data.success) { message.success('账户创建成功'); setModalOpen(false); form.resetFields(); load(); }
      else message.error(data.message || '创建失败');
    } catch { message.error('创建账户失败'); }
  };

  const handleReset = async (id: number) => {
    try {
      const r = await authFetch(`${API}/accounts/${id}/reset`, { method: 'POST' });
      const data = await r.json();
      if (data.success) { message.success('账户已重置'); load(); }
    } catch { message.error('重置失败'); }
  };

  const handleArchive = async (id: number) => {
    try {
      const r = await authFetch(`${API}/accounts/${id}`, { method: 'DELETE' });
      const data = await r.json();
      if (data.success) { message.success('账户已归档'); load(); }
    } catch { message.error('归档失败'); }
  };

  const handleTradeToggle = async (id: number, enabled: number) => {
    try {
      await authFetch(`${API}/accounts/${id}`, {
        method: 'PUT', body: JSON.stringify({ auto_trade_enabled: enabled }),
      });
      load();
    } catch { message.error('切换失败'); }
  };

  const handleBindStrategy = async (accountId: number, strategyId: number | undefined) => {
    try {
      await authFetch(`${API}/accounts/${accountId}`, {
        method: 'PUT', body: JSON.stringify({ strategy_id: strategyId || null }),
      });
      load();
    } catch { message.error('绑定策略失败'); }
  };

  const columns = [
    { title: '账户名称', dataIndex: 'name', key: 'name', render: (t: string, r: Account) => (
      <Space><WalletOutlined /><Text strong>{t}</Text><Tag color={r.auto_trade_enabled ? 'blue' : 'default'}>{r.auto_trade_enabled ? '自动' : '手动'}</Tag></Space>
    )},
    { title: '总资产', dataIndex: 'current_assets', key: 'ca', render: fmtMoney },
    { title: '可用资金', dataIndex: 'available_cash', key: 'ac', render: (v: number) => <Text type={v > 0 ? 'success' : 'secondary'}>{fmtMoney(v)}</Text> },
    { title: '持仓市值', dataIndex: 'position_value', key: 'pv', render: fmtMoney },
    { title: '总收益', dataIndex: 'total_profit', key: 'tp', render: (v: number) => <Text type={v >= 0 ? 'danger' : 'success'}>{fmtMoney(v)}</Text> },
    { title: '收益率', dataIndex: 'total_profit_rate', key: 'tpr', render: (v: number) => <Text type={v >= 0 ? 'danger' : 'success'}>{fmtPct(v)}</Text> },
    { title: '仓位', dataIndex: 'position_ratio', key: 'pr', render: (v: number) => <Progress percent={Math.round(v)} size="small" strokeColor={v > 70 ? '#F53F3F' : '#165DFF'} /> },
    { title: '策略', key: 'strategy', render: (_: any, r: Account) => (
      <Select size="small" value={r.strategy_id || undefined} placeholder="未绑定"
        onChange={(val) => handleBindStrategy(r.id, val)}
        options={strategies.filter(s => s.status === 1).map((s: any) => ({ label: s.name, value: s.id }))}
        style={{ width: 110 }} allowClear />
    )},
    { title: '操作', key: 'action', render: (_: any, r: Account) => (
      <Space size="small">
        <Tooltip title={r.auto_trade_enabled ? '切换手动' : '切换自动'}>
          <Switch checked={!!r.auto_trade_enabled} onChange={(c) => handleTradeToggle(r.id, c ? 1 : 0)} size="small" />
        </Tooltip>
        <Popconfirm title="确认重置账户？" onConfirm={() => handleReset(r.id)}>
          <Button size="small" icon={<ReloadOutlined />} />
        </Popconfirm>
        <Popconfirm title="确认归档？" onConfirm={() => handleArchive(r.id)}>
          <Button size="small" icon={<DeleteOutlined />} danger />
        </Popconfirm>
      </Space>
    )},
  ];

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Space>
          <Statistic title="账户数" value={accounts.length} suffix="个" />
          <Statistic title="总资产" value={accounts.reduce((s, a) => s + a.current_assets, 0)} precision={0} prefix="¥" />
        </Space>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>新建账户</Button>
      </div>
      <Table dataSource={accounts} columns={columns} rowKey="id" loading={loading} pagination={false} size="small" />
      <Modal title="新建虚拟账户" open={modalOpen} onCancel={() => setModalOpen(false)} onOk={() => form.submit()} destroyOnClose>
        <Form form={form} layout="vertical" onFinish={handleCreate} initialValues={{ name: '新账户', initial_capital: 1000000 }}>
          <Form.Item name="name" label="账户名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="initial_capital" label="初始资金（元）" rules={[{ required: true }]}>
            <InputNumber min={10000} max={100000000} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

// ═════ 标签页：持仓管理 ═════
const PositionsTab: React.FC = () => {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [selectedAccount, setSelectedAccount] = useState<number | null>(null);
  const [positions, setPositions] = useState<PositionItem[]>([]);
  const [closeRecords, setCloseRecords] = useState<CloseRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [tradeModal, setTradeModal] = useState(false);
  const [tradeType, setTradeType] = useState<'buy' | 'sell'>('buy');
  const [form] = Form.useForm();

  useEffect(() => {
    authFetch(`${API}/accounts`).then(r => r.json()).then(d => setAccounts(d.items || []));
  }, []);

  const loadPositions = useCallback(async (aid: number) => {
    setLoading(true);
    try {
      const [pr, cr] = await Promise.all([
        authFetch(`${API}/positions/${aid}`).then(r => r.json()),
        authFetch(`${API}/close-records/${aid}`).then(r => r.json()),
      ]);
      setPositions(pr.items || []);
      setCloseRecords(cr.items || []);
    } catch { message.error('加载持仓失败'); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => {
    if (selectedAccount) loadPositions(selectedAccount);
  }, [selectedAccount, loadPositions]);

  const accountOptions = accounts.map(a => ({ label: a.name, value: a.id }));

  const handleTrade = async (vals: any) => {
    const endpoint = tradeType === 'buy' ? `${API}/positions/buy` : `${API}/positions/sell`;
    try {
      const r = await authFetch(endpoint, {
        method: 'POST', body: JSON.stringify({ ...vals, account_id: selectedAccount }),
      });
      const data = await r.json();
      if (data.success) { message.success(data.message); setTradeModal(false); form.resetFields(); if (selectedAccount) loadPositions(selectedAccount); }
      else message.error(data.message || '操作失败');
    } catch { message.error('交易失败'); }
  };

  const posColumns = [
    { title: '代码', dataIndex: 'stock_code', key: 'code' },
    { title: '名称', dataIndex: 'stock_name', key: 'name' },
    { title: '数量', dataIndex: 'quantity', key: 'qty' },
    { title: '成本价', dataIndex: 'avg_cost', key: 'cost', render: (v: number) => v.toFixed(3) },
    { title: '现价', dataIndex: 'current_price', key: 'price', render: (v: number) => v.toFixed(3) },
    { title: '持仓市值', dataIndex: 'position_value', key: 'pv', render: fmtMoney },
    { title: '收益', dataIndex: 'profit_loss', key: 'pl', render: (v: number) => (
      <Text type={v >= 0 ? 'danger' : 'success'}>{v >= 0 ? '+' : ''}{v.toFixed(2)}</Text>
    )},
    { title: '收益率', dataIndex: 'profit_loss_rate', key: 'plr', render: (v: number) => (
      <Tag color={v >= 0 ? '#F53F3F' : '#00B42A'}>{v >= 0 ? '+' : ''}{v.toFixed(2)}%</Tag>
    )},
    { title: '来源', dataIndex: 'source_type', key: 'src', render: (v: number) => v ? <Tag color="blue">自动</Tag> : <Tag>手动</Tag> },
  ];

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Space>
          <Select options={accountOptions} placeholder="选择账户" style={{ width: 200 }} onChange={setSelectedAccount} allowClear />
          {selectedAccount && <Text type="secondary">持仓 {positions.length} 只</Text>}
        </Space>
        {selectedAccount && (
          <Space>
            <Button icon={<RiseOutlined />} type="primary" onClick={() => { setTradeType('buy'); setTradeModal(true); }}>买入</Button>
            <Button icon={<FallOutlined />} danger onClick={() => { setTradeType('sell'); setTradeModal(true); }}>卖出</Button>
          </Space>
        )}
      </div>

      {selectedAccount ? (
        <>
          <Table dataSource={positions} columns={posColumns} rowKey="id" loading={loading} size="small" pagination={false} />
          <Divider orientation="left"><HistoryOutlined /> 清仓记录</Divider>
          {closeRecords.length > 0 ? (
            <Table dataSource={closeRecords} rowKey="id" size="small" pagination={false}
              columns={[
                { title: '代码', dataIndex: 'stock_code' },
                { title: '名称', dataIndex: 'stock_name' },
                { title: '持仓天数', dataIndex: 'hold_days', render: (v: number) => `${v}天` },
                { title: '清仓收益', dataIndex: 'total_profit', render: (v: number) => <Text type={v >= 0 ? 'danger' : 'success'}>{v.toFixed(2)}</Text> },
                { title: '收益率', dataIndex: 'total_profit_rate', render: (v: number) => <Tag color={v >= 0 ? '#F53F3F' : '#00B42A'}>{v.toFixed(2)}%</Tag> },
                { title: '类型', dataIndex: 'trade_type_label' },
                { title: '原因', dataIndex: 'reason' },
              ]}
            />
          ) : <Empty description="暂无清仓记录" />}
        </>
      ) : (
        <Empty description="请先选择一个账户" />
      )}

      <Modal title={tradeType === 'buy' ? '买入股票' : '卖出股票'} open={tradeModal} onCancel={() => setTradeModal(false)} onOk={() => form.submit()} destroyOnClose>
        <Form form={form} layout="vertical" onFinish={handleTrade}>
          <Form.Item name="stock_code" label="股票代码" rules={[{ required: true }]}><Input placeholder="如 000001" /></Form.Item>
          {tradeType === 'buy' && <Form.Item name="stock_name" label="股票名称"><Input placeholder="可选" /></Form.Item>}
          <Form.Item name="quantity" label="数量（股）" rules={[{ required: true }]}><InputNumber min={100} style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="price" label="成交价" rules={[{ required: true }]}><InputNumber min={0.01} step={0.001} style={{ width: '100%' }} /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

// ═════ 策略配置默认值 ═════
const defaultConfig = {
  signal_sources: { selection: false, custom_template: false, monitor: false, watchlist: false },
  buy_rules: { enabled: false, trend_up: false, trend_reversal: false, excl_oscillate: false, excl_down: false,
    ma20_stand: false, ma_multi_up: false, macd_golden: false, macd_red_expand: false,
    kdj_golden: false, rsi_up: false, volume_break: false,
    resonance: { enabled: false, count: 3 }, risk_score: { enabled: false, max: 30 },
    risk_level_green: false, risk_level_yellow: false, excl_high_risk: false,
    fin_safe: false, no_negative_events: false, excl_st: false },
  sell_rules: { enabled: false, trend_turn: false, trend_down: false, break_ma20: false, ma_multi_down: false,
    macd_dead: false, macd_green_expand: false, kdj_dead_high: false, rsi_down: false, volume_break_weak: false,
    risk_rise: { enabled: false, threshold: 20 }, risk_red: false, high_risk_alert: false, bad_news: false },
  add_position: { enabled: false, triggers: { fundamentals: false, tech_strong: false, trend_confirm: false,
    resonance_enhanced: false, news_good: false, risk_down: false },
    tier1: 20, tier2: 30, tier3: 50 },
  reduce_position: { enabled: false, triggers: { fundamentals_bad: false, tech_break: false, trend_weak: false,
    resonance_lost: false, bad_events: false, risk_up: false },
    tier1: 20, tier2: 30, tier3: 50 },
  risk_control: { max_stocks: 10, max_single_pct: 30, max_industry: 5, max_total_pct: 95, single_buy_pct: 20 },
  stop: { profit_enabled: false, profit_pct: 30, loss_enabled: false, loss_pct: 10 },
};

const CheckboxGroup = ({ form, name, label, options }: any) => (
  <Form.Item name={name} label={label}>
    <Checkbox.Group options={options} />
  </Form.Item>
);

// ═════ 策略编辑器弹窗 ═════
const StrategyEditor: React.FC<{
  open: boolean;
  strategy: Strategy | null;
  onClose: () => void;
  onSaved: () => void;
}> = ({ open, strategy, onClose, onSaved }) => {
  const [form] = Form.useForm();
  const [activeSection, setActiveSection] = useState('basic');
  const isEdit = !!strategy;

  useEffect(() => {
    if (open) {
      if (strategy) {
        const cfg = strategy.config_json || {};
        form.setFieldsValue({
          name: strategy.name,
          strategy_type: strategy.strategy_type,
          period: strategy.period,
          description: strategy.description,
          ...cfg,
        });
      } else {
        form.resetFields();
        form.setFieldsValue({
          strategy_type: '波段', period: '日',
          ...defaultConfig,
        });
      }
      setActiveSection('basic');
    }
  }, [open, strategy, form]);

  const handleSave = async () => {
    try {
      const vals = await form.validateFields();
      // 拆分为基础字段和 config_json
      const { name, strategy_type, period, description } = vals;
      const config_json = { ...vals };
      delete config_json.name; delete config_json.strategy_type;
      delete config_json.period; delete config_json.description;

      const url = isEdit ? `${API}/strategies/${strategy!.id}` : `${API}/strategies`;
      const method = isEdit ? 'PUT' : 'POST';
      const r = await authFetch(url, {
        method, body: JSON.stringify({ name, strategy_type, period, description, config_json }),
      });
      const d = await r.json();
      if (d.success) {
        message.success(isEdit ? '策略已更新' : '策略已创建');
        onClose();
        onSaved();
      } else message.error(d.message);
    } catch { message.error('请检查表单填写'); }
  };

  const sections = [
    { key: 'basic', label: '基础信息' },
    { key: 'signals', label: '信号来源' },
    { key: 'buy', label: '买入规则' },
    { key: 'sell', label: '卖出规则' },
    { key: 'addpos', label: '加仓机制' },
    { key: 'redpos', label: '减仓机制' },
    { key: 'risk', label: '仓位风控' },
    { key: 'stop', label: '止盈止损' },
  ];

  return (
    <Modal
      title={isEdit ? `编辑策略：${strategy!.name}` : '新建策略'}
      open={open}
      onCancel={onClose}
      onOk={handleSave}
      width={860}
      okText="保存策略"
      destroyOnClose
      style={{ top: 20 }}
    >
      <Row gutter={16}>
        <Col span={5}>
          <Menu
            mode="inline"
            selectedKeys={[activeSection]}
            onClick={({ key }) => setActiveSection(key)}
            items={sections.map(s => ({ key: s.key, label: s.label }))}
            style={{ borderRight: 0, background: 'transparent' }}
          />
        </Col>
        <Col span={19} style={{ maxHeight: 500, overflowY: 'auto' }}>
          <Form form={form} layout="vertical" size="small" initialValues={defaultConfig}>
            {/* ── 基础信息 ── */}
            <div style={{ display: activeSection === 'basic' ? 'block' : 'none' }}>
              <Title level={5}>基础信息</Title>
              <Form.Item name="name" label="策略名称" rules={[{ required: true }]}>
                <Input placeholder="如：短线共振策略" />
              </Form.Item>
              <Space style={{ width: '100%' }} wrap>
                <Form.Item name="strategy_type" label="策略类型">
                  <Select style={{ width: 140 }} options={[
                    { label: '短线', value: '短线' }, { label: '波段', value: '波段' },
                    { label: '价值', value: '价值' }, { label: '反转', value: '反转' },
                  ]} />
                </Form.Item>
                <Form.Item name="period" label="适用周期">
                  <Select style={{ width: 120 }} options={[
                    { label: '日', value: '日' }, { label: '周', value: '周' }, { label: '月', value: '月' },
                  ]} />
                </Form.Item>
              </Space>
              <Form.Item name="description" label="备注说明">
                <Input.TextArea rows={3} placeholder="描述策略思路、适用场景等" />
              </Form.Item>
            </div>

            {/* ── 信号来源 ── */}
            <div style={{ display: activeSection === 'signals' ? 'block' : 'none' }}>
              <Title level={5}>信号来源</Title>
              <Text type="secondary">选择策略的信号数据来源（可多选）</Text>
              <div style={{ marginTop: 12 }}>
                <Form.Item name={['signal_sources', 'selection']} valuePropName="checked">
                  <Checkbox>智能选股结果</Checkbox>
                </Form.Item>
                <Form.Item name={['signal_sources', 'custom_template']} valuePropName="checked">
                  <Checkbox>自定义选股模板</Checkbox>
                </Form.Item>
                <Form.Item name={['signal_sources', 'monitor']} valuePropName="checked">
                  <Checkbox>监控股票池</Checkbox>
                </Form.Item>
                <Form.Item name={['signal_sources', 'watchlist']} valuePropName="checked">
                  <Checkbox>自选股列表</Checkbox>
                </Form.Item>
              </div>
            </div>

            {/* ── 买入规则 ── */}
            <div style={{ display: activeSection === 'buy' ? 'block' : 'none' }}>
              <Title level={5}>自动买入规则</Title>
              <Form.Item name={['buy_rules', 'enabled']} valuePropName="checked">
                <Checkbox>启用自动买入</Checkbox>
              </Form.Item>
              <Divider>趋势条件</Divider>
              <Form.Item name={['buy_rules', 'trend_up']} valuePropName="checked"><Checkbox>趋势 = 🟢 上涨</Checkbox></Form.Item>
              <Form.Item name={['buy_rules', 'trend_reversal']} valuePropName="checked"><Checkbox>趋势 = 🔃 反转</Checkbox></Form.Item>
              <Form.Item name={['buy_rules', 'excl_oscillate']} valuePropName="checked"><Checkbox>排除震荡趋势</Checkbox></Form.Item>
              <Form.Item name={['buy_rules', 'excl_down']} valuePropName="checked"><Checkbox>排除下跌趋势</Checkbox></Form.Item>
              <Divider>技术指标条件</Divider>
              <Form.Item name={['buy_rules', 'ma20_stand']} valuePropName="checked"><Checkbox>站稳 MA20 日均线</Checkbox></Form.Item>
              <Form.Item name={['buy_rules', 'ma_multi_up']} valuePropName="checked"><Checkbox>均线多头排列</Checkbox></Form.Item>
              <Form.Item name={['buy_rules', 'macd_golden']} valuePropName="checked"><Checkbox>MACD 金叉</Checkbox></Form.Item>
              <Form.Item name={['buy_rules', 'macd_red_expand']} valuePropName="checked"><Checkbox>MACD 红柱扩大</Checkbox></Form.Item>
              <Form.Item name={['buy_rules', 'kdj_golden']} valuePropName="checked"><Checkbox>KDJ 低位金叉</Checkbox></Form.Item>
              <Form.Item name={['buy_rules', 'rsi_up']} valuePropName="checked"><Checkbox>RSI 低位向上拐头</Checkbox></Form.Item>
              <Form.Item name={['buy_rules', 'volume_break']} valuePropName="checked"><Checkbox>放量突破箱体/压力位</Checkbox></Form.Item>
              <Divider>共振与风险</Divider>
              <Space>
                <Form.Item name={['buy_rules', 'resonance', 'enabled']} valuePropName="checked"><Checkbox>多头共振</Checkbox></Form.Item>
                <Form.Item name={['buy_rules', 'resonance', 'count']} label="≥"><InputNumber min={1} max={10} style={{ width: 60 }} /></Form.Item>
                <Text type="secondary">项</Text>
              </Space>
              <Space>
                <Form.Item name={['buy_rules', 'risk_score', 'enabled']} valuePropName="checked"><Checkbox>风险评分 ≤</Checkbox></Form.Item>
                <Form.Item name={['buy_rules', 'risk_score', 'max']}><InputNumber min={0} max={100} style={{ width: 60 }} /></Form.Item>
              </Space>
              <Form.Item name={['buy_rules', 'risk_level_green']} valuePropName="checked"><Checkbox>风险等级 = 🟢</Checkbox></Form.Item>
              <Form.Item name={['buy_rules', 'risk_level_yellow']} valuePropName="checked"><Checkbox>风险等级 = 🟡</Checkbox></Form.Item>
              <Form.Item name={['buy_rules', 'excl_high_risk']} valuePropName="checked"><Checkbox>排除高风险标的</Checkbox></Form.Item>
              <Divider>财务与事件</Divider>
              <Form.Item name={['buy_rules', 'fin_safe']} valuePropName="checked"><Checkbox>财务等级 = 🟢 安全</Checkbox></Form.Item>
              <Form.Item name={['buy_rules', 'no_negative_events']} valuePropName="checked"><Checkbox>无减持、质押、违约、立案等负面</Checkbox></Form.Item>
              <Form.Item name={['buy_rules', 'excl_st']} valuePropName="checked"><Checkbox>剔除 ST、*ST、退市风险股</Checkbox></Form.Item>
              <Divider />
              <Alert type="info" showIcon message="执行优先级" description="止盈止损 > 卖出/清仓 > 减仓 > 加仓 > 买入。卖出/减仓触发时，同一股票的买入/加仓信号在本周期内暂不执行。" />
            </div>

            {/* ── 卖出规则 ── */}
            <div style={{ display: activeSection === 'sell' ? 'block' : 'none' }}>
              <Title level={5}>自动卖出规则</Title>
              <Form.Item name={['sell_rules', 'enabled']} valuePropName="checked">
                <Checkbox>启用自动卖出</Checkbox>
              </Form.Item>
              <Divider>趋势破位</Divider>
              <Form.Item name={['sell_rules', 'trend_turn']} valuePropName="checked"><Checkbox>趋势 = 🔴 转跌</Checkbox></Form.Item>
              <Form.Item name={['sell_rules', 'trend_down']} valuePropName="checked"><Checkbox>趋势 = 🔴 下跌</Checkbox></Form.Item>
              <Form.Item name={['sell_rules', 'break_ma20']} valuePropName="checked"><Checkbox>跌破 MA20 日均线</Checkbox></Form.Item>
              <Form.Item name={['sell_rules', 'ma_multi_down']} valuePropName="checked"><Checkbox>均线空头排列</Checkbox></Form.Item>
              <Divider>技术指标转弱</Divider>
              <Form.Item name={['sell_rules', 'macd_dead']} valuePropName="checked"><Checkbox>MACD 死叉</Checkbox></Form.Item>
              <Form.Item name={['sell_rules', 'macd_green_expand']} valuePropName="checked"><Checkbox>MACD 绿柱扩大</Checkbox></Form.Item>
              <Form.Item name={['sell_rules', 'kdj_dead_high']} valuePropName="checked"><Checkbox>KDJ 高位死叉</Checkbox></Form.Item>
              <Form.Item name={['sell_rules', 'rsi_down']} valuePropName="checked"><Checkbox>RSI 高位向下</Checkbox></Form.Item>
              <Form.Item name={['sell_rules', 'volume_break_weak']} valuePropName="checked"><Checkbox>放量破位弱势</Checkbox></Form.Item>
              <Divider>风险与事件</Divider>
              <Space>
                <Form.Item name={['sell_rules', 'risk_rise', 'enabled']} valuePropName="checked"><Checkbox>风险评分升 ≥</Checkbox></Form.Item>
                <Form.Item name={['sell_rules', 'risk_rise', 'threshold']}><InputNumber min={0} max={100} style={{ width: 60 }} /></Form.Item>
              </Space>
              <Form.Item name={['sell_rules', 'risk_red']} valuePropName="checked"><Checkbox>风险等级 = 🔴</Checkbox></Form.Item>
              <Form.Item name={['sell_rules', 'high_risk_alert']} valuePropName="checked"><Checkbox>高风险预警触发</Checkbox></Form.Item>
              <Form.Item name={['sell_rules', 'bad_news']} valuePropName="checked"><Checkbox>出现利空消息</Checkbox></Form.Item>
            </div>

            {/* ── 加仓机制 ── */}
            <div style={{ display: activeSection === 'addpos' ? 'block' : 'none' }}>
              <Title level={5}>加仓机制</Title>
              <Form.Item name={['add_position', 'enabled']} valuePropName="checked">
                <Checkbox>启用加仓</Checkbox>
              </Form.Item>
              <Divider>触发条件</Divider>
              <Form.Item name={['add_position', 'triggers', 'fundamentals']} valuePropName="checked"><Checkbox>基本面持续向好</Checkbox></Form.Item>
              <Form.Item name={['add_position', 'triggers', 'tech_strong']} valuePropName="checked"><Checkbox>技术面强势延续</Checkbox></Form.Item>
              <Form.Item name={['add_position', 'triggers', 'trend_confirm']} valuePropName="checked"><Checkbox>趋势确认加强</Checkbox></Form.Item>
              <Form.Item name={['add_position', 'triggers', 'resonance_enhanced']} valuePropName="checked"><Checkbox>共振信号增强</Checkbox></Form.Item>
              <Form.Item name={['add_position', 'triggers', 'news_good']} valuePropName="checked"><Checkbox>利好消息催化</Checkbox></Form.Item>
              <Form.Item name={['add_position', 'triggers', 'risk_down']} valuePropName="checked"><Checkbox>风险评分下降</Checkbox></Form.Item>
              <Divider>加仓比例</Divider>
              <Text type="secondary">三级阶梯加仓，分别占计划加仓资金的比例</Text>
              <Space style={{ marginTop: 8 }}>
                <Form.Item name={['add_position', 'tier1']} label="第一档 %"><Slider min={5} max={50} style={{ width: 120 }} /></Form.Item>
                <Form.Item name={['add_position', 'tier2']} label="第二档 %"><Slider min={5} max={50} style={{ width: 120 }} /></Form.Item>
                <Form.Item name={['add_position', 'tier3']} label="第三档 %"><Slider min={5} max={50} style={{ width: 120 }} /></Form.Item>
              </Space>
            </div>

            {/* ── 减仓机制 ── */}
            <div style={{ display: activeSection === 'redpos' ? 'block' : 'none' }}>
              <Title level={5}>减仓机制</Title>
              <Form.Item name={['reduce_position', 'enabled']} valuePropName="checked">
                <Checkbox>启用减仓</Checkbox>
              </Form.Item>
              <Divider>触发条件</Divider>
              <Form.Item name={['reduce_position', 'triggers', 'fundamentals_bad']} valuePropName="checked"><Checkbox>基本面恶化</Checkbox></Form.Item>
              <Form.Item name={['reduce_position', 'triggers', 'tech_break']} valuePropName="checked"><Checkbox>技术面破位</Checkbox></Form.Item>
              <Form.Item name={['reduce_position', 'triggers', 'trend_weak']} valuePropName="checked"><Checkbox>趋势转弱</Checkbox></Form.Item>
              <Form.Item name={['reduce_position', 'triggers', 'resonance_lost']} valuePropName="checked"><Checkbox>共振信号消失</Checkbox></Form.Item>
              <Form.Item name={['reduce_position', 'triggers', 'bad_events']} valuePropName="checked"><Checkbox>负面事件发生</Checkbox></Form.Item>
              <Form.Item name={['reduce_position', 'triggers', 'risk_up']} valuePropName="checked"><Checkbox>风险评分上升</Checkbox></Form.Item>
              <Divider>减仓比例</Divider>
              <Text type="secondary">三级阶梯减仓，分别占当前持仓的比例</Text>
              <Space style={{ marginTop: 8 }}>
                <Form.Item name={['reduce_position', 'tier1']} label="第一档 %"><Slider min={5} max={50} style={{ width: 120 }} /></Form.Item>
                <Form.Item name={['reduce_position', 'tier2']} label="第二档 %"><Slider min={5} max={50} style={{ width: 120 }} /></Form.Item>
                <Form.Item name={['reduce_position', 'tier3']} label="第三档 %"><Slider min={5} max={50} style={{ width: 120 }} /></Form.Item>
              </Space>
            </div>

            {/* ── 仓位风控 ── */}
            <div style={{ display: activeSection === 'risk' ? 'block' : 'none' }}>
              <Title level={5}>仓位风控</Title>
              <Form.Item name={['risk_control', 'max_stocks']} label="最大持仓股票数">
                <InputNumber min={1} max={50} />
              </Form.Item>
              <Form.Item name={['risk_control', 'max_single_pct']} label="单只股票最大仓位（%）">
                <Slider min={5} max={100} />
              </Form.Item>
              <Form.Item name={['risk_control', 'max_industry']} label="单行业最大持股数">
                <InputNumber min={1} max={20} />
              </Form.Item>
              <Form.Item name={['risk_control', 'max_total_pct']} label="总仓位上限（%）">
                <Slider min={30} max={100} />
              </Form.Item>
              <Form.Item name={['risk_control', 'single_buy_pct']} label="单次买入占比（%）">
                <Slider min={5} max={50} />
              </Form.Item>
            </div>

            {/* ── 止盈止损 ── */}
            <div style={{ display: activeSection === 'stop' ? 'block' : 'none' }}>
              <Title level={5}>止盈止损</Title>
              <Divider>止盈</Divider>
              <Form.Item name={['stop', 'profit_enabled']} valuePropName="checked">
                <Checkbox>启用止盈</Checkbox>
              </Form.Item>
              <Form.Item name={['stop', 'profit_pct']} label="止盈触发收益率（%）">
                <Slider min={5} max={200} />
              </Form.Item>
              <Divider>止损</Divider>
              <Form.Item name={['stop', 'loss_enabled']} valuePropName="checked">
                <Checkbox>启用止损</Checkbox>
              </Form.Item>
              <Form.Item name={['stop', 'loss_pct']} label="止损触发亏损率（%）">
                <Slider min={2} max={30} />
              </Form.Item>
            </div>
          </Form>
        </Col>
      </Row>
    </Modal>
  );
};

// ═════ 标签页：量化策略 ═════
const StrategiesTab: React.FC = () => {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [loading, setLoading] = useState(false);
  const [editorOpen, setEditorOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<Strategy | null>(null);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await authFetch(`${API}/strategies`);
      const data = await r.json();
      setStrategies(data.items || []);
    } catch { message.error('加载策略失败'); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleNew = () => {
    setEditTarget(null);
    setEditorOpen(true);
  };

  const handleEdit = (s: Strategy) => {
    setEditTarget(s);
    setEditorOpen(true);
  };

  const handleDelete = async (id: number) => {
    try {
      const r = await authFetch(`${API}/strategies/${id}`, { method: 'DELETE' });
      const d = await r.json();
      if (d.success) { message.success('策略已删除'); load(); }
    } catch { message.error('删除失败'); }
  };

  const handleExport = async (s: Strategy) => {
    try {
      const blob = new Blob([JSON.stringify(s, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `strategy_${s.name}_${s.id}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch { message.error('导出失败'); }
  };

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const text = await file.text();
      const parsed = JSON.parse(text);
      const { name, strategy_type, period, description, config_json } = parsed;
      const r = await authFetch(`${API}/strategies`, {
        method: 'POST',
        body: JSON.stringify({ name, strategy_type, period, description, config_json }),
      });
      const d = await r.json();
      if (d.success) { message.success('策略导入成功'); load(); }
      else message.error(d.message || '导入失败');
    } catch { message.error('导入文件格式错误'); }
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const columns = [
    { title: '策略名称', dataIndex: 'name', key: 'name', render: (t: string) => <Text strong>{t}</Text> },
    { title: '类型', dataIndex: 'strategy_type', key: 'type', render: (t: string) => <Tag>{t}</Tag> },
    { title: '周期', dataIndex: 'period', key: 'period' },
    { title: '状态', dataIndex: 'status', key: 'status', render: (s: number) => s === 1 ? <Tag color="green">启用</Tag> : <Tag>停用</Tag> },
    { title: '描述', dataIndex: 'description', key: 'desc', ellipsis: true },
    { title: '创建时间', dataIndex: 'created_at', key: 'created', render: (t: string) => t?.slice(0, 10) },
    { title: '操作', key: 'action', render: (_: any, r: Strategy) => (
      <Space size="small">
        <Button size="small" icon={<SettingOutlined />} onClick={() => handleEdit(r)}>编辑</Button>
        <Button size="small" icon={<ExportOutlined />} onClick={() => handleExport(r)}>导出</Button>
        <Popconfirm title="确认删除策略？" onConfirm={() => handleDelete(r.id)}>
          <Button size="small" icon={<DeleteOutlined />} danger />
        </Popconfirm>
      </Space>
    )},
  ];

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Statistic title="策略总数" value={strategies.length} suffix="个" />
        <Space>
          <Button icon={<ImportOutlined />} onClick={() => fileInputRef.current?.click()}>导入</Button>
          <input ref={fileInputRef} type="file" accept=".json" style={{ display: 'none' }} onChange={handleImport} />
          <Button type="primary" icon={<PlusOutlined />} onClick={handleNew}>新建策略</Button>
        </Space>
      </div>
      <Table dataSource={strategies} columns={columns} rowKey="id" loading={loading} size="small" pagination={false} />
      <StrategyEditor open={editorOpen} strategy={editTarget} onClose={() => setEditorOpen(false)} onSaved={load} />
    </div>
  );
};

// ═════ 标签页：回测平台 ═════
const BacktestTab: React.FC = () => {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [records, setRecords] = useState<BacktestTask[]>([]);
  const [loading, setLoading] = useState(false);
  const [detailVisible, setDetailVisible] = useState(false);
  const [detailData, setDetailData] = useState<BacktestTask | null>(null);
  const [form] = Form.useForm();

  const loadStrategies = useCallback(async () => {
    try {
      const r = await authFetch(`${API}/strategies`);
      const d = await r.json();
      setStrategies(d.items || []);
    } catch { /* ignore */ }
  }, []);

  const loadRecords = useCallback(async () => {
    setLoading(true);
    try {
      const r = await authFetch(`${API}/backtest/tasks`);
      const d = await r.json();
      setRecords(d.items || []);
    } catch { message.error('加载回测记录失败'); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { loadStrategies(); loadRecords(); }, [loadStrategies, loadRecords]);

  const handleRun = async (vals: any) => {
    try {
      const r = await authFetch(`${API}/backtest`, {
        method: 'POST', body: JSON.stringify(vals),
      });
      const d = await r.json();
      if (d.success) {
        const warnMsg = d.warnings?.length ? `（${d.warnings.length}只标的失败）` : '';
        message.success(`回测任务已提交${warnMsg}`);
        form.resetFields();
        loadRecords();
      } else {
        // 后端返回 error 字段，前端取 error
        message.error(d.error || d.message || '提交失败');
      }
    } catch (e) {
      message.error('提交回测失败：网络错误');
    }
  };

  const handleDelete = async (id: number) => {
    try {
      const r = await authFetch(`${API}/backtest/${id}`, { method: 'DELETE' });
      const d = await r.json();
      if (d.success) { message.success('记录已删除'); loadRecords(); }
    } catch { message.error('删除失败'); }
  };

  const handleClearAll = async () => {
    try {
      const r = await authFetch(`${API}/backtest/clear`, { method: 'POST' });
      const d = await r.json();
      if (d.success) { message.success('已清空所有记录'); loadRecords(); }
    } catch { message.error('清空失败'); }
  };

  const showDetail = (item: BacktestTask) => {
    setDetailData(item);
    setDetailVisible(true);
  };

  const strategyOptions = strategies.map(s => ({ label: s.name, value: s.id }));

  const columns = [
    { title: '策略', dataIndex: 'strategy_id', key: 'sid', render: (id: number) => strategies.find(s => s.id === id)?.name || `ID:${id}` },
    { title: '日期范围', key: 'range', render: (_: any, r: BacktestTask) => `${r.start_date} ~ ${r.end_date}` },
    { title: '初始资金', dataIndex: 'init_capital', key: 'capital', render: fmtMoney },
    { title: '收益', key: 'profit', render: (_: any, r: BacktestTask) => {
      const s = r.result_json?.summary || {};
      const ret = s.total_return;
      if (ret == null) return '-';
      return <Text style={{ color: ret >= 0 ? '#F53F3F' : '#00B42A', fontWeight: 600 }}>{ret >= 0 ? '+' : ''}{ret.toFixed(2)}%</Text>;
    }},
    { title: '年化', key: 'annual', render: (_: any, r: BacktestTask) => {
      const s = r.result_json?.summary || {};
      const ann = s.annual_return;
      if (ann == null) return '-';
      return <Text style={{ color: ann >= 0 ? '#F53F3F' : '#00B42A' }}>{ann.toFixed(2)}%</Text>;
    }},
    { title: '回撤', key: 'mdd', render: (_: any, r: BacktestTask) => {
      const s = r.result_json?.summary || {};
      const mdd = s.max_drawdown;
      return mdd != null ? <Text style={{ color: '#00B42A' }}>{mdd.toFixed(2)}%</Text> : '-';
    }},
    { title: '状态', dataIndex: 'status_label', key: 'status', render: (l: string) => {
      const colorMap: Record<string, string> = { pending: 'orange', running: 'blue', done: 'green', failed: 'red' };
      return <Tag color={colorMap[l] || 'default'}>{l}</Tag>;
    }},
    { title: '创建时间', dataIndex: 'created_at', key: 'created', render: (t: string) => t?.slice(0, 16) },
    { title: '操作', key: 'action', render: (_: any, r: BacktestTask) => (
      <Space size="small">
        <Button size="small" icon={<BarChartOutlined />} onClick={() => showDetail(r)}>查看报告</Button>
        <Popconfirm title="确认删除？" onConfirm={() => handleDelete(r.id)}>
          <Button size="small" icon={<DeleteOutlined />} danger />
        </Popconfirm>
      </Space>
    )},
  ];

  // 回测详情弹窗
  const renderDetail = () => {
    if (!detailData) return null;
    const rj = detailData.result_json || {};
    const summary = rj.summary || {};
    const metrics: Record<string, any> = {
      total_return: { label: '累计收益', value: summary.final_assets, fmt: fmtMoney },
      total_return_rate: { label: '累计收益率', value: summary.total_return, fmt: (v: number) => `${(v >= 0 ? '+' : '')}${(v || 0).toFixed(2)}%` },
      annual_return_rate: { label: '年化收益率', value: summary.annual_return, fmt: (v: number) => `${(v || 0).toFixed(2)}%` },
      max_drawdown: { label: '最大回撤', value: summary.max_drawdown, fmt: (v: number) => `${(v || 0).toFixed(2)}%` },
      win_rate: { label: '胜率', value: summary.win_rate, fmt: (v: number) => `${(v || 0).toFixed(1)}%` },
      trade_count: { label: '交易次数', value: summary.total_trades, fmt: (v: number) => String(v || 0) },
      profit_loss_ratio: { label: '盈亏比', value: summary.profit_loss_ratio, fmt: (v: number) => (v || 0).toFixed(2) },
    };
    const equityCurve = rj.equity_curve || [];
    const monthlyReturns = rj.monthly_returns || [];
    const trades = rj.trades || [];

    return (
      <Modal
        title={`回测报告 - ${strategies.find(s => s.id === detailData.strategy_id)?.name || ''}`}
        open={detailVisible}
        onCancel={() => setDetailVisible(false)}
        width={900}
        footer={<Button onClick={() => setDetailVisible(false)}>关闭</Button>}
        style={{ top: 20 }}
      >
        {/* 收益指标卡片 */}
        <Card size="small" title="收益指标" style={{ marginBottom: 16 }}>
          <Row gutter={[16, 16]}>
            {Object.values(metrics).map((m: any) => (
              <Col span={6} key={m.label}>
                <Statistic title={m.label} value={m.value} formatter={() => m.fmt(m.value)} />
              </Col>
            ))}
          </Row>
        </Card>

        {/* 收益曲线表 */}
        <Card size="small" title="收益曲线" style={{ marginBottom: 16 }}>
          {equityCurve.length > 0 ? (
            <Table dataSource={equityCurve} rowKey="date" size="small" pagination={false}
              columns={[
                { title: '日期', dataIndex: 'date', key: 'date' },
                { title: '现金', dataIndex: 'cash', key: 'cash', render: (v: number) => fmtMoney(v || 0) },
                { title: '持仓市值', dataIndex: 'position_value', key: 'pv', render: (v: number) => fmtMoney(v || 0) },
                { title: '总资产', dataIndex: 'total_assets', key: 'ta', render: (v: number) => fmtMoney(v || 0) },
              ]}
            />
          ) : <Empty description="暂无收益曲线数据" />}
        </Card>

        {/* 月度收益卡片 */}
        <Card size="small" title="月度收益" style={{ marginBottom: 16 }}>
          {monthlyReturns.length > 0 ? (
            <Row gutter={[8, 8]}>
              {monthlyReturns.map((m: any) => (
                <Col span={4} key={m.month}>
                  <Card size="small" hoverable style={{ textAlign: 'center' }}>
                    <Text type="secondary" style={{ fontSize: 12 }}>{m.month}</Text>
                    <div>
                      <Text type={m.return >= 0 ? 'danger' : 'success'} strong>
                        {fmtPct(m.return)}
                      </Text>
                    </div>
                  </Card>
                </Col>
              ))}
            </Row>
          ) : <Empty description="暂无月度收益数据" />}
        </Card>

        {/* 交易明细 */}
        <Card size="small" title="交易明细">
          {trades.length > 0 ? (
            <Table dataSource={trades} rowKey="id" size="small" pagination={false}
              columns={[
                { title: '日期', dataIndex: 'date', key: 'date' },
                { title: '代码', dataIndex: 'stock_code', key: 'code' },
                { title: '名称', dataIndex: 'stock_name', key: 'name' },
                { title: '方向', dataIndex: 'direction', key: 'dir', render: (v: string) => (
                  <Tag color={v === 'buy' ? 'red' : 'green'}>{v === 'buy' ? '买入' : '卖出'}</Tag>
                )},
                { title: '数量', dataIndex: 'quantity', key: 'qty' },
                { title: '价格', dataIndex: 'price', key: 'price', render: (v: number) => v?.toFixed(3) },
                { title: '金额', dataIndex: 'amount', key: 'amt', render: fmtMoney },
              ]}
            />
          ) : <Empty description="暂无交易明细" />}
        </Card>
      </Modal>
    );
  };

  return (
    <div>
      {/* 回测配置 */}
      <Card title="回测配置" size="small" style={{ marginBottom: 16 }}>
        <Form form={form} layout="inline" onFinish={handleRun} initialValues={{ init_capital: 1000000 }}>
          <Form.Item name="strategy_id" label="策略" rules={[{ required: true }]}>
            <Select options={strategyOptions} placeholder="选择策略" style={{ width: 180 }} />
          </Form.Item>
          <Form.Item name="start_date" label="开始日期" rules={[{ required: true }]}>
            <Input placeholder="YYYY-MM-DD" style={{ width: 130 }} />
          </Form.Item>
          <Form.Item name="end_date" label="结束日期" rules={[{ required: true }]}>
            <Input placeholder="YYYY-MM-DD" style={{ width: 130 }} />
          </Form.Item>
          <Form.Item name="init_capital" label="初始资金">
            <InputNumber min={10000} max={100000000} style={{ width: 140 }} />
          </Form.Item>
          <Form.Item name="stock_codes" label="标的代码">
            <Input placeholder="可选，逗号分隔" style={{ width: 180 }} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" icon={<PlayCircleOutlined />} htmlType="submit">开始回测</Button>
          </Form.Item>
        </Form>
      </Card>

      {/* 回测说明 */}
      <Collapse
        items={[{
          key: 'help',
          label: '回测说明',
          children: (
            <div>
              <Title level={5}>回测流程</Title>
              <Text>1. 选择策略和日期范围 → 2. 设置初始资金 → 3. 可选指定标的代码 → 4. 点击"开始回测" → 5. 等待系统执行 → 6. 查看回测报告</Text>
              <Divider />
              <Title level={5}>复权处理</Title>
              <Text>回测使用前复权价格。分红、送转股等事件自动调整历史价格，确保回测收益与实际交易一致。</Text>
              <Divider />
              <Title level={5}>费率模型</Title>
              <Text>买入佣金万2.5（最低5元），卖出佣金万2.5（最低5元）+ 印花税千1。滑点模型默认0.01元，可在策略配置中调整。</Text>
            </div>
          ),
        }]}
        style={{ marginBottom: 16 }}
      />

      {/* 回测记录 */}
      <div>
        <div style={{ marginBottom: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Text strong style={{ fontSize: 16 }}>回测记录</Text>
          {records.length > 0 && (
            <Popconfirm title="确认清空所有回测记录？" onConfirm={handleClearAll}>
              <Button icon={<DeleteOutlined />} danger size="small">清空记录</Button>
            </Popconfirm>
          )}
        </div>
        <Table dataSource={records} columns={columns} rowKey="id" loading={loading} size="small" pagination={false} />
      </div>

      {renderDetail()}
    </div>
  );
};

// ═════ 主页面组件 ═════
const PortfolioPage: React.FC = () => {
  const { openHelp } = useHelp();
  const [activeTab, setActiveTab] = useState('accounts');

  const tabItems = [
    { key: 'accounts', label: <span><WalletOutlined /> 虚拟账户</span>, children: <AccountsTab /> },
    { key: 'positions', label: <span><BarChartOutlined /> 持仓管理</span>, children: <PositionsTab /> },
    { key: 'strategies', label: <span><SettingOutlined /> 量化策略</span>, children: <StrategiesTab /> },
    { key: 'backtest', label: <span><PlayCircleOutlined /> 回测平台</span>, children: <BacktestTab /> },
  ];

  return (
    <div style={{ padding: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
        <Title level={3} style={{ margin: 0 }}>资产组合管理</Title>
        <Tooltip title="查看帮助文档">
          <Button type="text" size="small" icon={<QuestionCircleOutlined style={{ fontSize: 16, color: '#1677ff' }} />}
            onClick={() => openHelp('portfolio-overview')} />
        </Tooltip>
      </div>
      <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />
    </div>
  );
};

export default PortfolioPage;
