import React, { useState } from 'react';
import { Card, Tag, Tooltip } from 'antd';
import { UpOutlined, DownOutlined, InfoCircleOutlined } from '@ant-design/icons';

interface CollapsibleCardProps {
  title: string;
  icon?: React.ReactNode;
  extra?: React.ReactNode;
  children?: React.ReactNode;
  defaultCollapsed?: boolean;
  collapsible?: boolean;
  dataSource?: string;
  badge?: number;
  badgeColor?: string;
  style?: React.CSSProperties;
  bodyStyle?: React.CSSProperties;
  className?: string;
  loading?: boolean;
  empty?: boolean;
  emptyText?: string;
}

const cardStyle: React.CSSProperties = {
  borderRadius: 8,
  boxShadow: '0 1px 4px rgba(0,0,0,0.08)',
  background: 'var(--content-card-bg)',
  height: '100%',
};

const CollapsibleCard: React.FC<CollapsibleCardProps> = ({
  title,
  icon,
  extra,
  children,
  defaultCollapsed = false,
  collapsible = true,
  dataSource,
  badge,
  badgeColor = '#ff4d4f',
  style,
  bodyStyle,
  className,
  loading = false,
  empty = false,
  emptyText = '暂无数据',
}) => {
  const [collapsed, setCollapsed] = useState(defaultCollapsed);

  const titleNode = (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      {icon && <span style={{ fontSize: 16 }}>{icon}</span>}
      <span style={{ fontSize: 14, fontWeight: 600 }}>{title}</span>
      {badge !== undefined && badge > 0 && (
        <Tag color={badgeColor} style={{ borderRadius: 10, marginLeft: 4 }}>
          {badge}
        </Tag>
      )}
    </div>
  );

  const extraNode = (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      {dataSource && (
        <Tooltip title={`数据来源: ${dataSource}`}>
          <InfoCircleOutlined style={{ fontSize: 12, color: 'var(--content-text)', opacity: 0.45 }} />
        </Tooltip>
      )}
      {extra}
      {collapsible && (
        <span
          onClick={() => setCollapsed(!collapsed)}
          style={{ cursor: 'pointer', fontSize: 12, color: 'var(--content-text)', opacity: 0.45 }}
        >
          {collapsed ? <DownOutlined /> : <UpOutlined />}
        </span>
      )}
    </div>
  );

  return (
    <Card
      size="small"
      title={titleNode}
      extra={extraNode}
      style={{ ...cardStyle, ...style }}
      bodyStyle={{
        padding: collapsed ? '0 12px' : '12px',
        maxHeight: collapsed ? 0 : undefined,
        overflow: collapsed ? 'hidden' : undefined,
        ...bodyStyle,
        // Ensure smooth collapse animation
        transition: 'padding 0.2s ease, max-height 0.2s ease',
      }}
      className={className}
      loading={loading}
    >
      {empty && !loading ? (
        <div style={{ textAlign: 'center', padding: '24px 0', color: 'var(--content-text)', opacity: 0.45 }}>
          {emptyText}
        </div>
      ) : (
        children || null
      )}
    </Card>
  );
};

export default CollapsibleCard;
