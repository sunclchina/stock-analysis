/**
 * M04 智能选股页面
 * 三标签页：固定规则选股 + 自定义选股 + 指标选股
 */
import React, { useState } from 'react';
import { Tabs } from 'antd';
import { FundProjectionScreenOutlined, ToolOutlined, ThunderboltOutlined, BranchesOutlined } from '@ant-design/icons';
import ErrorBoundary from '../../components/ErrorBoundary';
import FixedSelectionTab from './FixedSelectionTab';
import CustomSelectionTab from './CustomSelectionTab';
import IndicatorSelectionTab from './IndicatorSelectionTab';
import PatternSelectionTab from './PatternSelectionTab';

const SelectionPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>(localStorage.getItem('selection_tab') || 'fixed');

  return (
    <div>
      <Tabs
        activeKey={activeTab}
        onChange={(k) => { setActiveTab(k); localStorage.setItem('selection_tab', k); }}
        items={[
          {
            key: 'fixed',
            label: <span><FundProjectionScreenOutlined style={{ marginRight: 6 }} />固定规则选股</span>,
            children: <ErrorBoundary><FixedSelectionTab /></ErrorBoundary>,
          },
          {
            key: 'custom',
            label: <span><ToolOutlined style={{ marginRight: 6 }} />自定义选股</span>,
            children: <ErrorBoundary><CustomSelectionTab /></ErrorBoundary>,
          },
          {
            key: 'indicator',
            label: <span><ThunderboltOutlined style={{ marginRight: 6 }} />指标选股</span>,
            children: <ErrorBoundary><IndicatorSelectionTab /></ErrorBoundary>,
          },
          {
            key: 'pattern',
            label: <span><BranchesOutlined style={{ marginRight: 6 }} />形态选股</span>,
            children: <ErrorBoundary><PatternSelectionTab /></ErrorBoundary>,
          },
        ]}
      />
    </div>
  );
};

export default SelectionPage;
