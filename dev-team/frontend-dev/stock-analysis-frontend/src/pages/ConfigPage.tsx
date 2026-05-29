import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { Tabs, Typography } from 'antd';
import ErrorBoundary from '../components/ErrorBoundary';
import {
  SettingOutlined,
  StarOutlined,
  MonitorOutlined,
  ApiOutlined,
  FileTextOutlined,
  UserOutlined,
  DashboardOutlined,
  MessageOutlined,
} from '@ant-design/icons';
import SettingsTab from './Config/SettingsTab';
import WatchlistTab from './Config/WatchlistTab';
import MonitorPoolTab from './Config/MonitorPoolTab';
import DataSourceTab from './Config/DataSourceTab';
import TemplateTab from './Config/TemplateTab';
import ProfileTab from './Config/ProfileTab';
import SystemStatusTab from './Config/SystemStatusTab';
import ContactsTab from './Config/ContactsTab';

const { Title } = Typography;

const ConfigPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState('profile');
  const [tabPosition, setTabPosition] = useState<'left' | 'top'>('left');

  // 响应式：手机浏览器自动切换为顶部标签
  useEffect(() => {
    const checkWidth = () => {
      setTabPosition(window.innerWidth < 768 ? 'top' : 'left');
    };
    checkWidth();
    window.addEventListener('resize', checkWidth);
    return () => window.removeEventListener('resize', checkWidth);
  }, []);

  // 支持 URL 参数 ?tab=xxx
  const location = useLocation();
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const tab = params.get('tab');
    if (tab) setActiveTab(tab);
  }, [location.search]);

  const tabItems = [
    {
      key: 'settings',
      label: '系统设置',
      icon: <SettingOutlined />,
      children: <SettingsTab />,
    },
    {
      key: 'watchlist',
      label: '自选股',
      icon: <StarOutlined />,
      children: <WatchlistTab />,
    },
    {
      key: 'monitor',
      label: '监控池',
      icon: <MonitorOutlined />,
      children: <MonitorPoolTab />,
    },
    {
      key: 'datasource',
      label: '数据源',
      icon: <ApiOutlined />,
      children: <DataSourceTab />,
    },
    {
      key: 'templates',
      label: '模板管理',
      icon: <FileTextOutlined />,
      children: <TemplateTab />,
    },
    {
      key: 'profile',
      label: '个人设置',
      icon: <UserOutlined />,
      children: <ProfileTab />,
    },
    {
      key: 'contacts',
      label: '联系我们',
      icon: <MessageOutlined />,
      children: <ContactsTab />,
    },
    {
      key: 'system',
      label: '系统状态',
      icon: <DashboardOutlined />,
      children: <SystemStatusTab />,
    },
  ];

  return (
    <ErrorBoundary title="系统配置异常" description="配置模块发生异常，请重试。">
      <div style={{ padding: 'max(12px, min(24px, 3vw))' }}>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          tabPosition={tabPosition}
          items={tabItems}
          style={{ minHeight: 500 }}
        />
      </div>
    </ErrorBoundary>
  );
};

export default ConfigPage;
