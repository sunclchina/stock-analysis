import React from 'react';
import { Tag, Typography, Space, Badge } from 'antd';
import { ApiOutlined } from '@ant-design/icons';
import type { DataSourceState } from '../../types/market';

const { Text } = Typography;

interface DataSourceIndicatorProps {
  dataSource: DataSourceState | null;
}

const sourceNameMap: Record<string, string> = {
  tdx: '通达信',
  sina: '新浪财经',
  eastmoney: '东方财富',
  baostock: 'Baostock',
};

/** 数据源状态指示器 */
const DataSourceIndicator: React.FC<DataSourceIndicatorProps> = ({ dataSource }) => {
  if (!dataSource) {
    return (
      <Space size={4}>
        <ApiOutlined style={{ color: '#8c8c8c' }} />
        <Text type="secondary" style={{ fontSize: 12 }}>数据源：未知</Text>
      </Space>
    );
  }

  const statusColor = dataSource.status === 'online' ? 'green' : dataSource.status === 'degraded' ? 'orange' : 'red';
  const statusLabel = dataSource.status === 'online' ? '在线' : dataSource.status === 'degraded' ? '高延迟' : '离线';

  return (
    <Space size={12} wrap>
      <Space size={4}>
        <ApiOutlined style={{ color: '#1677ff' }} />
        <Text style={{ fontSize: 12 }}>
          数据源：
          <Text strong style={{ fontSize: 12 }}>
            {dataSource.name || sourceNameMap[dataSource.current] || dataSource.current}
          </Text>
        </Text>
        <Badge status={statusColor as 'success' | 'error' | 'warning'} text={
          <Text style={{ fontSize: 12, color: statusColor === 'green' ? '#52c41a' : statusColor === 'orange' ? '#faad14' : '#ff4d4f' }}>
            {statusLabel}
          </Text>
        } />
        {dataSource.latency > 0 && (
          <Text type="secondary" style={{ fontSize: 11 }}>
            {dataSource.latency}ms
          </Text>
        )}
      </Space>

      {dataSource.available && dataSource.available.length > 1 && (
        <Space size={4}>
          {dataSource.available.map((ds: { id: string; name: string; status: string; latency: number }) => (
            <Tag
              key={ds.id}
              color={ds.status === 'online' ? 'green' : ds.status === 'degraded' ? 'orange' : 'default'}
              style={{ fontSize: 10, lineHeight: '16px', margin: 0 }}
            >
              {sourceNameMap[ds.id] || ds.name || ds.id}
            </Tag>
          ))}
        </Space>
      )}

      {dataSource.lastUpdate && (
        <Text type="secondary" style={{ fontSize: 11 }}>
          最后更新: {dataSource.lastUpdate}
        </Text>
      )}
    </Space>
  );
};

export default DataSourceIndicator;
