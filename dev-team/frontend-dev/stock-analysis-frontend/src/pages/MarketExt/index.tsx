import React, { useEffect, useState } from 'react';
import { Card, Table, Tag, Typography, Spin, Row, Col, Space, Tabs } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined, MinusOutlined } from '@ant-design/icons';
import {
  fetchGlobalIndices,
  fetchIndustryRanking,
  fetchIndustryMoneyFlow,
  fetchStockMoneyFlow,
} from '../../services/marketExtApi';

const { Text, Title } = Typography;

function fmtMoney(v: any): string {
  const n = Number(v) || 0;
  const abs = Math.abs(n);
  if (abs >= 100000000) return (n / 100000000).toFixed(2) + '亿';
  if (abs >= 10000) return (n / 10000).toFixed(2) + '万';
  return n.toFixed(2);
}

function ChangeTag({ v }: { v: any }) {
  const n = Number(v) || 0;
  if (n === 0) return <Tag>0.00%</Tag>;
  const color = n > 0 ? 'red' : 'green';
  const icon = n > 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />;
  return <Tag color={color}>{icon} {n > 0 ? '+' : ''}{n.toFixed(2)}%</Tag>;
}

// ========== 1. 全球指数 ==========
export const GlobalIndices: React.FC = () => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    fetchGlobalIndices().then(d => { console.log('全球指数:', d); setData(d); }).catch(e => console.error(e)).finally(() => setLoading(false));
  }, []);
  if (loading) return <Spin style={{ display: 'block', margin: '40px auto' }} />;
  if (!data) return <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>暂无数据</div>;
  return (
    <Row gutter={[12, 12]}>
      {data.groups?.map((group: any) => (
        <Col xs={24} sm={12} lg={6} key={group.name}>
          <Card size="small" title={group.name} style={{ borderRadius: 8 }}>
            {group.items?.map((item: any) => (
              <div key={item.code} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', borderBottom: '1px solid #f0f0f0' }}>
                <Text style={{ fontSize: 13 }}>{item.name}</Text>
                <Space size={8}>
                  <Text strong style={{ fontSize: 13 }}>{item.price?.toFixed(2)}</Text>
                  <ChangeTag v={item.change_pct} />
                </Space>
              </div>
            ))}
          </Card>
        </Col>
      ))}
    </Row>
  );
};

// ========== 2. 行业排名 ==========
export const IndustryRanking: React.FC = () => {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    fetchIndustryRanking().then(d => { console.log('行业排名:', d); setData(d); }).catch(e => console.error(e)).finally(() => setLoading(false));
  }, []);
  const columns = [
    { title: '排名', key: 'rank', width: 50, render: (_: any, __: any, i: number) => i + 1 },
    { title: '行业名称', dataIndex: 'name', key: 'name' },
    { title: '行业涨幅', dataIndex: 'avg_change_pct', key: 'avg_change_pct', render: (v: any) => <ChangeTag v={v} />, sorter: (a: any, b: any) => a.avg_change_pct - b.avg_change_pct },
    { title: '5日涨幅', dataIndex: 'change_5d', key: 'change_5d', render: (v: any) => <ChangeTag v={v} /> },
    { title: '20日涨幅', dataIndex: 'change_20d', key: 'change_20d', render: (v: any) => <ChangeTag v={v} /> },
    { title: '领涨股', key: 'leader', render: (_: any, r: any) => r.leading_stock ? <><Text>{r.leading_stock}</Text><Text type="secondary" style={{ marginLeft: 4, fontSize: 12 }}>{r.leading_stock_price?.toFixed(2)}</Text></> : '-' },
    { title: '涨幅', dataIndex: 'leading_stock_change', key: 'leading_stock_change', render: (v: any) => <ChangeTag v={v} /> },
  ];
  return <Table dataSource={data} columns={columns} rowKey={(r: any) => r.code || r.name} loading={loading} size="small" pagination={{ pageSize: 20 }} scroll={{ x: 800 }} />;
};

// ========== 3. 个股资金流向 ==========
export const StockMoneyFlow: React.FC = () => {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [sort, setSort] = useState('netamount');
  useEffect(() => {
    fetchStockMoneyFlow(sort).then(d => { console.log('资金流向:', d); setData(d); }).catch(e => console.error(e)).finally(() => setLoading(false));
  }, [sort]);

  const sortOptions = [
    { label: '净流入', value: 'netamount' },
    { label: '主力净流入率', value: 'ratioamount' },
    { label: '流入', value: 'inamount' },
    { label: '流出', value: 'outamount' },
  ];

  const columns = [
    { title: '排名', key: 'rank', width: 50, render: (_: any, __: any, i: number) => i + 1 },
    { title: '代码', dataIndex: 'code', width: 90 },
    { title: '名称', dataIndex: 'name', width: 100 },
    { title: '最新价', dataIndex: 'trade', render: (v: any) => Number(v)?.toFixed(2) || '-' },
    { title: '涨跌幅', dataIndex: 'changepercent', render: (v: any) => <ChangeTag v={v} /> },
    { title: '换手率', dataIndex: 'turnover', render: (v: any) => v + '%' },
    { title: '流入(万)', dataIndex: 'inamount', render: (v: any) => <Text style={{ color: '#f5222d' }}>{fmtMoney(v)}</Text> },
    { title: '流出(万)', dataIndex: 'outamount', render: (v: any) => <Text style={{ color: '#52c41a' }}>{fmtMoney(v)}</Text> },
    { title: '净流入(万)', dataIndex: 'netamount', render: (v: any) => <Text style={{ color: Number(v) > 0 ? '#f5222d' : '#52c41a' }}>{fmtMoney(v)}</Text> },
    { title: '净流入率', dataIndex: 'ratioamount', render: (v: any) => v + '%' },
    { title: '主力净流入率', dataIndex: 'ts_ratioamount', render: (v: any) => v + '%' },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 12 }}>
        <Text strong>排序：</Text>
        {sortOptions.map(o => (
          <Tag key={o.value} color={sort === o.value ? 'blue' : 'default'} style={{ cursor: 'pointer' }} onClick={() => setSort(o.value)}>{o.label}</Tag>
        ))}
      </Space>
      <Table dataSource={data} columns={columns} rowKey={(r: any, i: number) => r.code || String(i)} loading={loading} size="small" pagination={{ pageSize: 20 }} scroll={{ x: 1100 }} />
    </div>
  );
};

// ========== 主页面 ==========
const MarketExtPage: React.FC = () => {
  const [tab, setTab] = useState('indices');
  const items = [
    { key: 'indices', label: '全球指数', children: <GlobalIndices /> },
    { key: 'industry', label: '行业排名', children: <IndustryRanking /> },
    { key: 'moneyflow', label: '个股资金流向', children: <StockMoneyFlow /> },
  ];
  return (
    <div>
      <Card style={{ borderRadius: 8, marginBottom: 12 }} styles={{ body: { padding: '12px 16px' } }}>
        <Space>
          <Title level={5} style={{ margin: 0 }}>📊 高级市场数据</Title>
          <Text type="secondary">数据来源：腾讯财经 / 新浪财经</Text>
        </Space>
      </Card>
      <Card style={{ borderRadius: 8 }} styles={{ body: { padding: '12px 16px' } }}>
        <Tabs activeKey={tab} onChange={setTab} items={items} />
      </Card>
    </div>
  );
};

export default MarketExtPage;
