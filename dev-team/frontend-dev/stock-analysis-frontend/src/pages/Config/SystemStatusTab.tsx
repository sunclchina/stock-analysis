import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Progress,
  Tag,
  Table,
  Space,
  Typography,
  Divider,
  Alert,
  Descriptions,
  Button,
} from 'antd';
import {
  ReloadOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ExclamationCircleOutlined,
  SmileOutlined,
  GithubOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { ServiceStatus } from '../../types';

const { Text, Title } = Typography;

const mockSystemInfo = {
  version: 'v1.0.0',
  buildTime: '2026-04-29 13:00',
  nodeVersion: 'v24.15.0',
  platform: 'Windows_NT 10.0.26100',
};

const mockServices: ServiceStatus[] = [
  { name: 'API 网关', status: 'running', uptime: '3h 12m', port: 8000 },
  { name: '数据源服务', status: 'running', uptime: '3h 12m' },
  { name: '预警引擎', status: 'running', uptime: '2h 45m' },
  { name: '选股引擎', status: 'running', uptime: '3h 12m' },
  { name: '分析引擎 (AI)', status: 'running', uptime: '1h 30m' },
  { name: 'WebSocket 服务', status: 'running', uptime: '3h 12m', port: 8080 },
  { name: '数据库 (SQLite)', status: 'running', uptime: '3h 12m' },
  { name: '缓存服务', status: 'running', uptime: '3h 12m' },
];

const statusConfig: Record<string, { color: string; icon: React.ReactNode; text: string }> = {
  running: { color: 'green', icon: <CheckCircleOutlined />, text: '运行中' },
  stopped: { color: 'red', icon: <CloseCircleOutlined />, text: '已停止' },
  error: { color: 'orange', icon: <ExclamationCircleOutlined />, text: '异常' },
};

const SystemStatusTab: React.FC = () => {
  const [cpu, setCpu] = useState(0);
  const [memory, setMemory] = useState(0);
  const [disk, setDisk] = useState(0);
  const [services, setServices] = useState<ServiceStatus[]>(mockServices);
  const [uptime, setUptime] = useState('0h 0m');
  const [loading, setLoading] = useState(false);

  const fetchSystemStatus = () => {
    setLoading(true);
    // Simulate system info fetch
    setTimeout(() => {
      setCpu(Math.floor(Math.random() * 60 + 10));
      setMemory(Math.floor(Math.random() * 50 + 20));
      setDisk(Math.floor(Math.random() * 30 + 40));
      setUptime(`${Math.floor(Math.random() * 12 + 1)}h ${Math.floor(Math.random() * 60)}m`);
      setLoading(false);
    }, 500);
  };

  useEffect(() => {
    fetchSystemStatus();
    const interval = setInterval(fetchSystemStatus, 10000);
    return () => clearInterval(interval);
  }, []);

  const serviceColumns: ColumnsType<ServiceStatus> = [
    {
      title: '服务名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: string) => {
        const cfg = statusConfig[status] || statusConfig.error;
        return (
          <Tag color={cfg.color} icon={cfg.icon}>
            {cfg.text}
          </Tag>
        );
      },
    },
    {
      title: '运行时长',
      dataIndex: 'uptime',
      key: 'uptime',
      width: 120,
    },
    {
      title: '端口',
      dataIndex: 'port',
      key: 'port',
      width: 100,
      render: (port: number | undefined) => (port ? <Text code>{port}</Text> : '-'),
    },
  ];

  return (
    <Card
      title="系统状态"
      extra={
        <Button
          icon={<ReloadOutlined />}
          onClick={fetchSystemStatus}
          loading={loading}
        >
          刷新
        </Button>
      }
    >
      {/* 系统资源 */}
      <Title level={5}>系统资源</Title>
      <Row gutter={[24, 24]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={8}>
          <Card size="small">
            <Statistic title="CPU 使用率" value={cpu} suffix="%" />
            <Progress
              percent={cpu}
              strokeColor={cpu > 80 ? '#ff4d4f' : cpu > 50 ? '#faad14' : '#52c41a'}
              showInfo={false}
              style={{ marginTop: 8 }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card size="small">
            <Statistic title="内存使用率" value={memory} suffix="%" />
            <Progress
              percent={memory}
              strokeColor={memory > 80 ? '#ff4d4f' : memory > 50 ? '#faad14' : '#52c41a'}
              showInfo={false}
              style={{ marginTop: 8 }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card size="small">
            <Statistic title="磁盘使用率" value={disk} suffix="%" />
            <Progress
              percent={disk}
              strokeColor={disk > 90 ? '#ff4d4f' : disk > 70 ? '#faad14' : '#52c41a'}
              showInfo={false}
              style={{ marginTop: 8 }}
            />
          </Card>
        </Col>
      </Row>

      <Alert
        message={
          cpu > 80 || memory > 80 || disk > 90
            ? '系统资源使用率较高，建议检查资源占用情况'
            : '系统运行状态良好'
        }
        type={cpu > 80 || memory > 80 || disk > 90 ? 'warning' : 'success'}
        showIcon
        style={{ marginBottom: 24 }}
      />

      {/* 服务运行状态 */}
      <Title level={5}>服务状态</Title>
      <div style={{ overflowX: 'auto', width: '100%' }}>
      <Table
        columns={serviceColumns}
        dataSource={services}
        rowKey="name"
        pagination={false}
        size="small"
        scroll={{ x: 'max-content' }}
        style={{ marginBottom: 24 }}
      />
      </div>

      {/* 版本信息 */}
      <Title level={5}>版本信息</Title>
      <div style={{ overflowX: 'auto', width: '100%' }}>
      <Descriptions column={{ xs: 1, sm: 2 }} size="small" bordered>
        <Descriptions.Item label="系统版本">{mockSystemInfo.version}</Descriptions.Item>
        <Descriptions.Item label="构建时间">{mockSystemInfo.buildTime}</Descriptions.Item>
        <Descriptions.Item label="Node.js 版本">{mockSystemInfo.nodeVersion}</Descriptions.Item>
        <Descriptions.Item label="运行平台">{mockSystemInfo.platform}</Descriptions.Item>
        <Descriptions.Item label="系统运行时长">{uptime}</Descriptions.Item>
        <Descriptions.Item label="技术栈">
          React 18 + TypeScript + Ant Design 5
        </Descriptions.Item>
      </Descriptions>
      </div>

      <div style={{ marginTop: 16, textAlign: 'center' }}>
        <Text type="secondary">
          <SmileOutlined style={{ marginRight: 4 }} />
          股票分析与投资决策系统 v1.0.0
        </Text>
      </div>
    </Card>
  );
};

export default SystemStatusTab;
