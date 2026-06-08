/**
 * M05 智能分析页面
 * 三标签页：大盘复盘 + 个股分析 + 批量分析
 */
import React, { useState, useEffect } from 'react';
import ErrorBoundary from '../../components/ErrorBoundary';
import { Tabs } from 'antd';
import { BarChartOutlined, StockOutlined, ClusterOutlined } from '@ant-design/icons';
import ReviewTab from './ReviewTab';
import StockAnalysisTab from './StockAnalysisTab';
import BatchAnalysisTab from './BatchAnalysisTab';
import ReportList from './ReportList';

const AnalysisPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>('review');
  const [refreshKey, setRefreshKey] = useState(0);
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);
  useEffect(() => {
    const onResize = () => setIsMobile(window.innerWidth < 768);
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  return (
    <div>
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        type="card"
        size={isMobile ? 'small' : 'middle'}
        style={{ background: 'var(--content-card-bg)', borderRadius: 8, padding: isMobile ? '4px' : '0 16px' }}
        items={[
          {
            key: 'review',
            label: (
              <span>
                {isMobile ? '' : <BarChartOutlined style={{ marginRight: 6 }} />}
                大盘复盘
              </span>
            ),
            children: <ErrorBoundary><ReviewTab onReportGenerated={() => setRefreshKey(k => k + 1)} /></ErrorBoundary>,
          },
          {
            key: 'stock',
            label: (
              <span>
                {isMobile ? '' : <StockOutlined style={{ marginRight: 6 }} />}
                个股分析
              </span>
            ),
            children: <ErrorBoundary><StockAnalysisTab onReportGenerated={() => setRefreshKey(k => k + 1)} /></ErrorBoundary>,
          },
          {
            key: 'batch',
            label: (
              <span>
                {isMobile ? '' : <ClusterOutlined style={{ marginRight: 6 }} />}
                批量分析
              </span>
            ),
            children: <BatchAnalysisTab onReportGenerated={() => setRefreshKey(k => k + 1)} />,
          },
        ]}
      />

      {/* 报告列表 */}
      <ReportList refreshKey={refreshKey} />
    </div>
  );
};

const WrappedAnalysisPage: React.FC = () => (
  <ErrorBoundary title="智能分析异常" description="分析模块发生异常，请重试或检查后端状态。">
    <AnalysisPage />
  </ErrorBoundary>
);

export default WrappedAnalysisPage;
