/**
 * 决策仪表盘组件
 * 对监控池股票逐个计算量化评分，展示买卖建议。
 */
import React, { useEffect, useState } from 'react';
import {
  Card, Tag, Table, Typography, Space, Spin, Progress, Tooltip, Empty,
} from 'antd';
import {
  RiseOutlined, FallOutlined, MinusOutlined, DashboardOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { getDecisionBoard, DecisionStock } from '../services/dashboardApi';

const { Text } = Typography;

const DecisionBoard: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [stocks, setStocks] = useState<DecisionStock[]>([]);
  const [stats, setStats] = useState<{ bullish: number; bearish: number; neutral: number; avg_score: number; total: number } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getDecisionBoard();
      const data = res.data || res || { stocks: [], stats: null };
      setStocks(data.stocks || []);
      setStats(data.stats || null);
      if (!data.stocks || data.stocks.length === 0) {
        setError('暂无数据，请先添加监控股票');
      }
    } catch (e: any) {
      setError(e?.message || '加载失败');
    }
    setLoading(false);
  };

  useEffect(() => { fetchData(); }, []);

  const signalTag = (type: string) => {
    if (type === 'bullish') return <Tag color="green">看多 🟢</Tag>;
    if (type === 'bearish') return <Tag color="red">看空 🔴</Tag>;
    return <Tag color="default">观望 ⚪</Tag>;
  };

  const scoreBar = (score: number) => {
    const color = score >= 65 ? '#52c41a' : score >= 45 ? '#faad14' : '#ff4d4f';
    return (
      <Tooltip title={`综合评分: ${score}/100`}>
        <Progress
          percent={score}
          size="small"
          strokeColor={color}
          showInfo={false}
          style={{ width: 80, marginRight: 6 }}
        />
        <Text style={{ color, fontWeight: 600, fontSize: 12 }}>{score}</Text>
      </Tooltip>
    );
  };

  const breakdownTooltip = (record: DecisionStock) => (
    <div>
      <div>趋势: {record.scores.trend}/30</div>
      <div>动量: {record.scores.momentum}/25</div>
      <div>量价: {record.scores.volume}/20</div>
      <div>风控: {record.scores.risk}/25</div>
      {record.details.anomalies.length > 0 && (
        <div style={{ marginTop: 4 }}>
          异动: {record.details.anomalies.join(', ')}
        </div>
      )}
    </div>
  );

  const columns: ColumnsType<DecisionStock> = [
    {
      title: '代码', dataIndex: 'code', width: 80, key: 'code',
      render: (v: string) => <Text code style={{ fontWeight: 700 }}>{v}</Text>,
    },
    {
      title: '名称', dataIndex: 'name', width: 90, key: 'name',
      render: (v: string) => <Text style={{ fontWeight: 500 }}>{v}</Text>,
    },
    {
      title: '最新价', dataIndex: 'price', width: 80, key: 'price',
      align: 'right',
      render: (v: number) => v?.toFixed(2),
    },
    {
      title: '涨跌幅', dataIndex: 'change_pct', width: 80, key: 'change_pct',
      align: 'right',
      render: (v: number) => {
        if (v == null) return '-';
        const color = v >= 0 ? '#cf1322' : '#389e0d';
        return <Text style={{ color, fontWeight: 600 }}>{v > 0 ? '+' : ''}{v.toFixed(2)}%</Text>;
      },
      sorter: (a, b) => (a.change_pct ?? 0) - (b.change_pct ?? 0),
    },
    {
      title: '信号', dataIndex: 'signal_type', width: 80, key: 'signal',
      render: (_: any, r: DecisionStock) => signalTag(r.signal_type),
    },
    {
      title: '评分', dataIndex: 'total_score', width: 120, key: 'score',
      sorter: (a, b) => a.total_score - b.total_score,
      render: (_: any, r: DecisionStock) => (
        <Tooltip title={breakdownTooltip(r)}>
          {scoreBar(r.total_score)}
        </Tooltip>
      ),
    },
    {
      title: '建议', dataIndex: 'action', width: 80, key: 'action',
      render: (v: string) => <Text style={{ fontWeight: 500 }}>{v}</Text>,
    },
    {
      title: '趋势', dataIndex: ['details', 'trend'], width: 70, key: 'trend',
      render: (v: string) => <Tag style={{ fontSize: 11 }}>{v}</Tag>,
    },
    {
      title: '异动', key: 'anomalies', width: 120,
      render: (_: any, r: DecisionStock) => (
        r.details?.anomalies?.length > 0
          ? <Tag color="orange" style={{ fontSize: 11 }}>{r.details.anomalies.length}项</Tag>
          : '-'
      ),
    },
  ];

  return (
    <Card
      size="small"
      style={{ borderRadius: 8, marginTop: 12, width: '100%' }}
      title={
        <Space>
          <DashboardOutlined style={{ color: '#722ed1', fontSize: 16 }} />
          <span style={{ fontSize: 16, fontWeight: 700 }}>决策参考</span>
          {stats && (
            <>
              <Tag color="green">看多 {stats.bullish}</Tag>
              <Tag color="red">看空 {stats.bearish}</Tag>
              <Tag color="default">观望 {stats.neutral}</Tag>
              <Text type="secondary" style={{ fontSize: 12 }}>
                平均评分 {stats.avg_score} | 共 {stats.total} 只
              </Text>
            </>
          )}
          {loading && <Spin size="small" />}
        </Space>
      }
      extra={
        <Text type="secondary" style={{ fontSize: 12, cursor: 'pointer' }} onClick={fetchData}>
          <ReloadOutlined /> 刷新
        </Text>
      }
    >
      {error && !loading ? (
        <Empty description={error} />
      ) : (
        <Table<DecisionStock>
          columns={columns}
          dataSource={stocks}
          rowKey="code"
          size="small"
          loading={false}
          pagination={false}
          scroll={{ x: 800 }}
        />
      )}
    </Card>
  );
};

export default DecisionBoard;
