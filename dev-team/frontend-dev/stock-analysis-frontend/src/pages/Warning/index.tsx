import React, { useCallback } from 'react';
import ErrorBoundary from '../../components/ErrorBoundary';
import { Modal, Descriptions, Space, Spin, Empty, Typography, Tag, Badge, Divider } from 'antd';
import { AlertOutlined } from '@ant-design/icons';
import WarningMonitorGrid from './WarningMonitorGrid';
import { useWarningStore } from '../../store/warningStore';
import type { WarningDetail } from '../../types/warning';
import { WarningTypeLabel, WarningLevelLabel, WarningLevelColor } from '../../types/warning';

const { Text, Paragraph } = Typography;

// ========== Warning Detail Sections ==========

/** Render a single warning detail section */
const DetailSection: React.FC<{
  title: string;
  trigger: boolean;
  children: React.ReactNode;
}> = ({ title, trigger, children }) => (
  <div style={{ marginBottom: 16 }}>
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
      <Badge status={trigger ? 'error' : 'default'} />
      <Text strong style={{ fontSize: 14 }}>{title}</Text>
      {trigger ? (
        <Tag color="red" style={{ fontSize: 11 }}>已触发</Tag>
      ) : (
        <Tag style={{ fontSize: 11 }}>正常</Tag>
      )}
    </div>
    {children}
  </div>
);

/** Warning detail modal content */
const WarningDetailContent: React.FC<{ detail: WarningDetail }> = ({ detail }) => {
  return (
    <div style={{ maxHeight: '60vh', overflowY: 'auto' }}>
      {/* Overall info */}
      <div style={{ marginBottom: 16, padding: '12px 16px', background: 'rgba(0,0,0,0.02)', borderRadius: 8 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <Space>
            <Text strong style={{ fontSize: 16 }}>{detail.stockName}</Text>
            <Text type="secondary">{detail.stockCode}</Text>
          </Space>
          <Tag color={WarningLevelColor[detail.overallLevel]}>
            综合评级: {WarningLevelLabel[detail.overallLevel]}
          </Tag>
        </div>
        <Text>{detail.operationAdvice}</Text>
        <div style={{ marginTop: 4 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            最后更新: {detail.lastUpdate}
          </Text>
        </div>
      </div>

      <Divider style={{ margin: '12px 0' }} />

      {/* Price Warning */}
      <DetailSection title="价格预警" trigger={detail.priceWarning.trigger}>
        {detail.priceWarning.trigger ? (
          <Descriptions size="small" column={2}>
            <Descriptions.Item label="当前价格">{detail.priceWarning.currentPrice}</Descriptions.Item>
            <Descriptions.Item label="上限">{detail.priceWarning.upperLimit}</Descriptions.Item>
            <Descriptions.Item label="下限">{detail.priceWarning.lowerLimit}</Descriptions.Item>
            <Descriptions.Item label="级别">
              <Tag color={WarningLevelColor[detail.priceWarning.level]}>{WarningLevelLabel[detail.priceWarning.level]}</Tag>
            </Descriptions.Item>
          </Descriptions>
        ) : (
          <Text type="secondary">价格正常，未触发预警</Text>
        )}
        <Paragraph style={{ margin: 0, fontSize: 12, color: '#8c8c8c', marginTop: 4 }}>
          {detail.priceWarning.message}
        </Paragraph>
      </DetailSection>

      {/* Updown Warning */}
      <DetailSection title="涨跌预警" trigger={detail.updownWarning.trigger}>
        {detail.updownWarning.trigger ? (
          <Descriptions size="small" column={2}>
            <Descriptions.Item label="开盘价">{detail.updownWarning.openPrice}</Descriptions.Item>
            <Descriptions.Item label="当前价">{detail.updownWarning.currentPrice}</Descriptions.Item>
            <Descriptions.Item label="涨跌幅">{detail.updownWarning.changePercent.toFixed(2)}%</Descriptions.Item>
            <Descriptions.Item label="级别">
              <Tag color={WarningLevelColor[detail.updownWarning.level]}>{WarningLevelLabel[detail.updownWarning.level]}</Tag>
            </Descriptions.Item>
          </Descriptions>
        ) : (
          <Text type="secondary">涨跌幅正常</Text>
        )}
        <Paragraph style={{ margin: 0, fontSize: 12, color: '#8c8c8c', marginTop: 4 }}>
          {detail.updownWarning.message}
        </Paragraph>
      </DetailSection>

      {/* Trend Warning */}
      <DetailSection title="趋势预警" trigger={detail.trendWarning.trigger}>
        {detail.trendWarning.trigger ? (
          <Descriptions size="small" column={3}>
            <Descriptions.Item label="MA5">{detail.trendWarning.ma5?.toFixed(2) || '-'}</Descriptions.Item>
            <Descriptions.Item label="MA10">{detail.trendWarning.ma10?.toFixed(2) || '-'}</Descriptions.Item>
            <Descriptions.Item label="MA20">{detail.trendWarning.ma20?.toFixed(2) || '-'}</Descriptions.Item>
            <Descriptions.Item label="MA60">{detail.trendWarning.ma60?.toFixed(2) || '-'}</Descriptions.Item>
            <Descriptions.Item label="交叉信号">{detail.trendWarning.crossSignal}</Descriptions.Item>
            <Descriptions.Item label="级别">
              <Tag color={WarningLevelColor[detail.trendWarning.level]}>{WarningLevelLabel[detail.trendWarning.level]}</Tag>
            </Descriptions.Item>
          </Descriptions>
        ) : (
          <Text type="secondary">均线系统正常</Text>
        )}
        <Paragraph style={{ margin: 0, fontSize: 12, color: '#8c8c8c', marginTop: 4 }}>
          {detail.trendWarning.message}
        </Paragraph>
      </DetailSection>

      {/* Resonance Warning */}
      <DetailSection title="共振预警" trigger={detail.resonanceWarning.trigger}>
        {detail.resonanceWarning.trigger ? (
          <div>
            <div style={{ marginBottom: 4 }}>
              <Text>综合评分: </Text>
              <Text strong style={{ color: detail.resonanceWarning.score > 60 ? '#ff4d4f' : '#faad14' }}>
                {detail.resonanceWarning.score}
              </Text>
            </div>
            <Descriptions size="small" column={1}>
              {detail.resonanceWarning.items.map((item, idx) => (
                <Descriptions.Item key={idx} label={item.name}>
                  <Space>
                    <Text>{item.score}分</Text>
                    <Badge status={item.status ? 'error' : 'default'} />
                    {item.status ? <Text type="danger">异常</Text> : <Text type="secondary">正常</Text>}
                  </Space>
                </Descriptions.Item>
              ))}
            </Descriptions>
          </div>
        ) : (
          <Text type="secondary">各指标未出现共振</Text>
        )}
        <Paragraph style={{ margin: 0, fontSize: 12, color: '#8c8c8c', marginTop: 4 }}>
          {detail.resonanceWarning.message}
        </Paragraph>
      </DetailSection>

      {/* Finance Warning */}
      <DetailSection title="财务预警" trigger={detail.financeWarning.trigger}>
        {detail.financeWarning.trigger ? (
          <Descriptions size="small" column={2}>
            <Descriptions.Item label="PE">{detail.financeWarning.pe?.toFixed(2) || '-'}</Descriptions.Item>
            <Descriptions.Item label="PB">{detail.financeWarning.pb?.toFixed(2) || '-'}</Descriptions.Item>
            <Descriptions.Item label="ROE">{detail.financeWarning.roe?.toFixed(2) || '-'}%</Descriptions.Item>
            <Descriptions.Item label="负债率">{detail.financeWarning.debtRatio?.toFixed(2) || '-'}%</Descriptions.Item>
          </Descriptions>
        ) : (
          <Text type="secondary">财务指标正常</Text>
        )}
        <Paragraph style={{ margin: 0, fontSize: 12, color: '#8c8c8c', marginTop: 4 }}>
          {detail.financeWarning.message}
        </Paragraph>
      </DetailSection>

      {/* Event Warning */}
      <DetailSection title="突发预警" trigger={detail.eventWarning.trigger}>
        {detail.eventWarning.trigger ? (
          <div>
            {detail.eventWarning.events.map((evt, idx) => (
              <div key={idx} style={{ marginBottom: 8, padding: 8, background: 'rgba(255,77,79,0.05)', borderRadius: 4 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                  <Tag color="red">{evt.type}</Tag>
                  <Tag color={evt.impact === 'high' ? 'red' : evt.impact === 'medium' ? 'orange' : 'default'}>
                    {evt.impact === 'high' ? '重大影响' : evt.impact === 'medium' ? '中等影响' : '轻微影响'}
                  </Tag>
                </div>
                <Text style={{ fontSize: 12 }}>{evt.description}</Text>
              </div>
            ))}
          </div>
        ) : (
          <Text type="secondary">无突发异常事件</Text>
        )}
        <Paragraph style={{ margin: 0, fontSize: 12, color: '#8c8c8c', marginTop: 4 }}>
          {detail.eventWarning.message}
        </Paragraph>
      </DetailSection>

      {/* Risk Score */}
      <DetailSection title="风险评分" trigger={detail.riskScore.score > 60}>
        <Descriptions size="small" column={2}>
          <Descriptions.Item label="综合风险评分">
            <Text strong style={{ color: detail.riskScore.score > 60 ? '#ff4d4f' : detail.riskScore.score > 40 ? '#faad14' : '#52c41a' }}>
              {detail.riskScore.score}
            </Text>
          </Descriptions.Item>
          <Descriptions.Item label="级别">
            <Tag color={WarningLevelColor[detail.riskScore.level]}>{WarningLevelLabel[detail.riskScore.level]}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="基础分">{detail.riskScore.baseScore}</Descriptions.Item>
          <Descriptions.Item label="动态分">{detail.riskScore.dynamicScore}</Descriptions.Item>
        </Descriptions>
        <Paragraph style={{ margin: 0, fontSize: 12, color: '#8c8c8c', marginTop: 4 }}>
          {detail.riskScore.message}
        </Paragraph>
      </DetailSection>
    </div>
  );
};

// ========== Main Page Component ==========

const WarningPage: React.FC = () => {
  const {
    detailModalVisible, detailStock, detailLoading,
    openDetail, closeDetail,
  } = useWarningStore();

  const handleOpenDetail = useCallback((code: string) => {
    openDetail(code);
  }, [openDetail]);

  return (
    <div style={{ width: '100%' }}>
      <WarningMonitorGrid onOpenDetail={handleOpenDetail} />

      <Modal
        title={
          <Space>
            <AlertOutlined />
            <span>预警详情</span>
            {detailStock && (
              <span style={{ fontSize: 14, fontWeight: 400 }}>
                - {detailStock.stockName} ({detailStock.stockCode})
              </span>
            )}
          </Space>
        }
        open={detailModalVisible}
        onCancel={closeDetail}
        footer={null}
        width={720}
        destroyOnClose
      >
        <Spin spinning={detailLoading}>
          {detailStock ? (
            <WarningDetailContent detail={detailStock} />
          ) : !detailLoading ? (
            <Empty description="暂无预警详情" />
          ) : null}
        </Spin>
      </Modal>
    </div>
  );
};

const WrappedWarningPage: React.FC = () => (
  <ErrorBoundary title="智能预警异常" description="预警模块发生异常，请重试或检查后端状态。">
    <WarningPage />
  </ErrorBoundary>
);

export default WrappedWarningPage;
