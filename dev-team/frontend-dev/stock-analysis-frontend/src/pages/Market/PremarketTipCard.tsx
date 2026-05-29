import React from 'react';
import { Card, Tag, Button, Spin, Typography, Space, Collapse } from 'antd';
import {
  ThunderboltOutlined,
  ReloadOutlined,
  SyncOutlined,
  DownloadOutlined,
  WarningOutlined,
  RiseOutlined,
  FallOutlined,
  GlobalOutlined,
  BulbOutlined,
  FundOutlined,
  AimOutlined,
  SafetyOutlined,
  DownOutlined,
} from '@ant-design/icons';
import type { PremarketTip } from '../../types/market';

const { Text } = Typography;

interface PremarketTipCardProps {
  tip: PremarketTip | null;
  loading: boolean;
  generating: boolean;
  onRefresh: () => void;
  onGenerate: () => void;
}

const sectionIcons: Record<string, React.ReactNode> = {
  '外围市场概况': <GlobalOutlined />,
  '重要消息与政策': <BulbOutlined />,
  '指数技术面预判': <FundOutlined />,
  '热点方向跟踪': <AimOutlined />,
  '操作策略建议': <SafetyOutlined />,
};

function renderContent(text: string): React.ReactNode {
  // 直接渲染为pre-wrap格式，保持所有换行和格式
  return (
    <div style={{ fontSize: 13, lineHeight: 1.9, whiteSpace: 'pre-wrap', color: '#333' }}>
      {text}
    </div>
  );
}

const PremarketTipCard: React.FC<PremarketTipCardProps> = ({
  tip, loading, generating, onRefresh, onGenerate,
}) => {
  const handleDownload = () => {
    if (!tip) return;
    const parts: string[] = [];
    parts.push(`盘前提示 — ${tip.date || ''}`);
    parts.push('='.repeat(40));
    if (tip.sections) {
      for (const sec of tip.sections) {
        parts.push(`\n【${sec.title}】`);
        parts.push(sec.content);
      }
    } else if (tip.marketPrediction) {
      parts.push('');
      parts.push(tip.marketPrediction);
    }
    if (tip.updatedAt) {
      parts.push(`\n更新于: ${tip.updatedAt}`);
    }
    const blob = new Blob([parts.join('\n')], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `盘前提示_${tip.date || '今日'}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <Card
      size="small"
      title={
        <Space>
          <ThunderboltOutlined style={{ color: '#faad14', fontSize: 18 }} />
          <span style={{ fontSize: 16, fontWeight: 700, color: '#d48806' }}>盘前提示</span>
          {tip?.date && (
            <Text type="secondary" style={{ fontSize: 12, fontWeight: 400 }}>
              {tip.date}
            </Text>
          )}
          {tip?.dataSource && (
            <Tag color="default" style={{ fontSize: 10, marginLeft: 4 }}>{tip.dataSource}</Tag>
          )}
        </Space>
      }
      extra={
        <Space size="small">
          <Button size="small" shape="round" icon={<DownloadOutlined />} onClick={handleDownload} disabled={!tip} style={{ borderColor: '#13c2c2', color: '#13c2c2' }}>下载</Button>
          <Button size="small" shape="round" icon={<ReloadOutlined />} onClick={onRefresh} loading={loading} type="primary" ghost>刷新</Button>
          <Button size="small" shape="round" type="primary" icon={<SyncOutlined />} onClick={onGenerate} loading={generating}>重新生成</Button>
        </Space>
      }
      style={{ borderRadius: 8 }}
      styles={{ body: { padding: '8px 16px 4px' } }}
    >
      <Spin spinning={loading || generating}>
        {!tip ? (
          <div style={{ textAlign: 'center', padding: 24 }}>
            <Text type="secondary">暂无盘前提示数据，请点击"重新生成"</Text>
          </div>
        ) : (
          <div style={{ maxHeight: 320, overflowY: 'auto' }}>
            {/* 五大板块折叠面板 */}
            {tip.sections && tip.sections.length > 0 ? (
              <Collapse
                ghost
                size="small"
                defaultActiveKey={tip.sections.slice(0, 2).map((_, i) => String(i))}
                expandIcon={({ isActive }) => <DownOutlined rotate={isActive ? -180 : 0} style={{ fontSize: 10 }} />}
                items={tip.sections.map((section, idx) => ({
                  key: String(idx),
                  label: (
                    <Space size={6}>
                      {sectionIcons[section.title] || <BulbOutlined />}
                      <Text strong style={{ fontSize: 13 }}>{section.title}</Text>
                    </Space>
                  ),
                  children: (
                    <div style={{ padding: '4px 0 4px 4px' }}>
                      {renderContent(section.content)}
                    </div>
                  ),
                }))}
              />
            ) : (
              <div style={{ maxHeight: 280, overflowY: 'auto', lineHeight: 1.8, whiteSpace: 'pre-wrap', fontSize: 13 }}>
                {tip.marketPrediction}
              </div>
            )}

            {/* 更新时间 */}
            {tip.updatedAt && (
              <div style={{ marginTop: 4, textAlign: 'right' }}>
                <Text type="secondary" style={{ fontSize: 10 }}>
                  更新于: {tip.updatedAt}
                </Text>
              </div>
            )}
          </div>
        )}
      </Spin>
    </Card>
  );
};

export default PremarketTipCard;
