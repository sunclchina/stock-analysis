/**
 * 统一侧栏导航组件（设计规范 v1.1 §1）
 * - 桌面：固定240px / 可折叠至60px，过渡动画0.3s
 * - 移动端（<768px）：右侧 Drawer 覆盖
 * - 顶部：K线抽象Logo + 系统名称
 * - 中部：核心导航项
 * - 底部：折叠按钮 / 主题切换 / 帮助中心
 * - 悬停渐变、当前标亮、预警角标
 */
import React, { useMemo } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, Button, Tooltip, Badge, Drawer } from 'antd';
import {
  DashboardOutlined,
  StockOutlined,
  FundProjectionScreenOutlined,
  BarChartOutlined,
  AlertOutlined,
  WalletOutlined,
  FileTextOutlined,
  SettingOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  SunOutlined,
  UserOutlined,
  MoonOutlined,
  QuestionCircleOutlined,
  CloseOutlined,
} from '@ant-design/icons';
import { useConfigStore } from '../store/configStore';
import { isAdmin } from '../services/auth';

const { Sider } = Layout;

interface SidebarProps {
  themeMode: 'light' | 'dark';
  onToggleTheme: () => void;
  onOpenHelp?: () => void;
  /** 移动端 Drawer 是否打开 */
  mobileOpen?: boolean;
  /** 关闭移动端 Drawer */
  onMobileClose?: () => void;
}

interface NavItemDef {
  key: string;
  label: string;
  path?: string;
  icon: React.ReactNode;
  badge?: number;
  children?: { key: string; label: string; path: string }[];
}

const navItems: NavItemDef[] = [
  { key: 'dashboard', label: '仪表盘', path: '/', icon: <DashboardOutlined /> },
  {
    key: 'market', label: '实时行情', path: '/market', icon: <StockOutlined />,
    children: [
      { key: 'market-overview', label: '行情概览', path: '/market' },
    ],
  },
  { key: 'selection', label: '智能选股', path: '/selection', icon: <FundProjectionScreenOutlined /> },
  {
    key: 'research', label: '研究中心', icon: <BarChartOutlined />,
    children: [
      { key: 'research-main', label: '研报/公告/行业', path: '/market-research' },
      { key: 'market-ext', label: '全球指数/行业', path: '/market-ext' },
    ],
  },
  { key: 'analysis', label: '智能分析', path: '/analysis', icon: <BarChartOutlined /> },
  { key: 'warning', label: '智能预警', path: '/warning', icon: <AlertOutlined /> },
  { key: 'portfolio', label: '资产组合', path: '/portfolio', icon: <WalletOutlined /> },
  { key: 'notes', label: '操盘笔记', path: '/notes', icon: <FileTextOutlined /> },
  { key: 'config', label: '系统配置', path: '/config', icon: <SettingOutlined /> },
];

const adminNav: NavItemDef = { key: 'users', label: '用户管理', path: '/users', icon: <UserOutlined /> };

/** 桌面端侧栏内容（独立出来供 Drawer 复用） */
const SidebarContent: React.FC<{
  collapsed: boolean;
  selectedKey: string;
  menuItems: any[];
  handleMenuClick: (info: { key: string }) => void;
  themeMode: 'light' | 'dark';
  onToggleTheme: () => void;
  onOpenHelp?: () => void;
  navigate: (path: string) => void;
}> = ({ collapsed, selectedKey, menuItems, handleMenuClick, themeMode, onToggleTheme, onOpenHelp, navigate }) => (
  <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
    {/* 顶部：Logo + 系统名称 */}
    <div
      style={{
        height: 110,
        flexShrink: 0,
        display: 'flex',
        alignItems: 'center',
        justifyContent: collapsed ? 'center' : 'flex-start',
        padding: collapsed ? 0 : '0 18px',
        gap: collapsed ? 0 : 16,
        borderBottom: '1px solid rgba(255,255,255,0.08)',
        cursor: 'pointer',
        transition: 'padding 0.3s',
      }}
      onClick={() => navigate('/')}
    >
      <img src="/logo.svg" alt="logo" style={{ width: 60, height: 60, flexShrink: 0, objectFit: 'contain', cursor: 'pointer' }} />
      {!collapsed && (
        <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.2 }}>
          <span style={{
            color: '#fff', fontSize: 24, fontWeight: 700, letterSpacing: 2.5,
            background: 'linear-gradient(90deg, #FFFFFF, #8BC5FF)',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
          }}>
            股票分析
          </span>
          <span style={{ color: 'rgba(255,255,255,0.65)', fontSize: 16, fontWeight: 500, letterSpacing: 3, marginTop: 2 }}>
            与投资决策
          </span>
        </div>
      )}
    </div>

    {/* 导航菜单 */}
    <div style={{ flex: 1, overflowY: 'auto', padding: '4px 0', minHeight: 0 }}>
      <Menu
        theme="dark"
        mode="inline"
        inlineCollapsed={collapsed}
        selectedKeys={[selectedKey]}
        items={menuItems}
        onClick={handleMenuClick}
        style={{ borderInlineEnd: 'none', background: 'transparent' }}
        className="sidebar-menu"
      />
    </div>

    {/* 底部 */}
    <div style={{
      flexShrink: 0, borderTop: '1px solid rgba(255,255,255,0.08)',
      padding: collapsed ? '6px 0' : '6px 10px',
      display: 'flex', flexDirection: 'column', gap: 2,
      background: 'var(--sidebar-bg)',
    }}>
      <Tooltip title={collapsed ? '展开侧栏' : '折叠侧栏'} placement="right">
        <Button type="text" size="small"
          icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
          onClick={() => useConfigStore.getState().toggleSidebar()}
          className="sidebar-bottom-btn"
          style={{ color: 'var(--sidebar-text)', justifyContent: collapsed ? 'center' : 'flex-start' }}
        >
          {!collapsed && <span>折叠菜单</span>}
        </Button>
      </Tooltip>
      <Tooltip title={themeMode === 'dark' ? '切换浅色模式' : '切换深色模式'} placement="right">
        <Button type="text" size="small"
          icon={themeMode === 'dark' ? <SunOutlined style={{ color: 'var(--theme-toggle-color)' }} /> : <MoonOutlined />}
          onClick={onToggleTheme}
          className="sidebar-bottom-btn"
          style={{ color: 'var(--sidebar-text)', justifyContent: collapsed ? 'center' : 'flex-start' }}
        >
          {!collapsed && <span>{themeMode === 'dark' ? '浅色模式' : '深色模式'}</span>}
        </Button>
      </Tooltip>
      <Tooltip title="查看使用指南与常见问题" placement="right">
        <Button type="text" size="small" icon={<QuestionCircleOutlined />}
          onClick={() => onOpenHelp?.()}
          className="sidebar-bottom-btn"
          style={{ color: 'var(--sidebar-text)', justifyContent: collapsed ? 'center' : 'flex-start' }}
        >
          {!collapsed && <span>帮助中心</span>}
        </Button>
      </Tooltip>
    </div>

    <style>{`
      .sidebar-menu .ant-menu-item {
        height: 44px !important;
        line-height: 44px !important;
        margin: 2px 8px !important;
        border-radius: 8px !important;
        transition: all 0.2s ease !important;
      }
      .sidebar-menu .ant-menu-item:hover {
        background: linear-gradient(135deg, #E8F3FF22, #D1E7FF33) !important;
        transform: scale(1.02);
      }
      .sidebar-menu .ant-menu-item:active {
        transform: scale(0.98);
      }
      .sidebar-menu .ant-menu-item-selected {
        background: linear-gradient(135deg, #165DFF, #0E42D2) !important;
        box-shadow: 0 2px 6px rgba(22,93,255,0.3) !important;
      }
      .sidebar-menu .ant-menu-item-selected .ant-menu-title-content {
        color: #fff !important;
        font-weight: 600;
      }
      .sidebar-menu .ant-menu-item-selected .anticon {
        color: #fff !important;
      }
      .sidebar-bottom-btn {
        width: 100% !important;
        display: flex !important;
        align-items: center !important;
        gap: 8px !important;
        padding: 4px 12px !important;
        height: 34px !important;
        border-radius: 6px !important;
        transition: all 0.2s !important;
      }
      .sidebar-bottom-btn:hover {
        background: rgba(255,255,255,0.08) !important;
        color: #fff !important;
      }
    `}</style>
  </div>
);

const Sidebar: React.FC<SidebarProps> = ({ themeMode, onToggleTheme, onOpenHelp, mobileOpen, onMobileClose }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const { sidebarCollapsed, toggleSidebar } = useConfigStore();

  const activeItem = navItems.find((item) => item.path === location.pathname);
  let selectedKey = activeItem?.key || 'dashboard';
  if (!activeItem) {
    for (const parent of navItems) {
      const child = parent.children?.find((c) => c.path === location.pathname);
      if (child) { selectedKey = child.key; break; }
    }
  }

  const handleMenuClick = (info: { key: string }) => {
    const item = navItems.find((n) => n.key === info.key);
    if (item && item.path) { navigate(item.path); if (onMobileClose) onMobileClose(); return; }
    for (const parent of navItems) {
      const child = parent.children?.find((c) => c.key === info.key);
      if (child) { navigate(child.path); if (onMobileClose) onMobileClose(); return; }
    }
    if (info.key === 'users') { navigate('/users'); if (onMobileClose) onMobileClose(); }
  };

  const collapsed = sidebarCollapsed;

  const menuItems = navItems.map((item) => {
    if (item.children) {
      return {
        key: item.key, icon: item.icon, label: item.label,
        children: item.children.map((child) => ({ key: child.key, label: child.label })),
      };
    }
    return {
      key: item.key,
      icon: item.badge !== undefined && item.badge > 0 ? (
        <Badge count={item.badge} size="small" color="#FF4D4F" offset={[4, -4]}>{item.icon}</Badge>
      ) : item.icon,
      label: (
        <span>
          {item.label}
          {item.badge !== undefined && item.badge > 0 && (
            <span style={{ marginLeft: 6, fontSize: 11, color: '#FF4D4F', fontWeight: 600 }}>({item.badge})</span>
          )}
        </span>
      ),
    };
  });
  if (isAdmin()) {
    menuItems.push({ key: adminNav.key, icon: adminNav.icon, label: <span>{adminNav.label}</span> });
  }

  return (
    <>
      {/* 桌面端侧栏 */}
      <Sider
        width={240}
        collapsedWidth={60}
        collapsed={collapsed}
        className="desktop-sidebar"
        style={{
          height: '100vh', position: 'fixed', left: 0, top: 0, bottom: 0,
          zIndex: 100, overflow: 'hidden', background: 'var(--sidebar-bg)',
          transition: 'width 0.3s ease !important',
        }}
      >
        <SidebarContent
          collapsed={collapsed}
          selectedKey={selectedKey}
          menuItems={menuItems}
          handleMenuClick={handleMenuClick}
          themeMode={themeMode}
          onToggleTheme={onToggleTheme}
          onOpenHelp={onOpenHelp}
          navigate={navigate}
        />
      </Sider>

      {/* 移动端 Drawer */}
      <Drawer
        placement="left"
        width={280}
        open={mobileOpen}
        onClose={onMobileClose}
        styles={{ body: { padding: 0, background: 'var(--sidebar-bg)' } }}
        closeIcon={null}
        className="mobile-sidebar-drawer"
      >
        <div style={{ position: 'absolute', top: 8, right: 8, zIndex: 10 }}>
          <Button type="text" icon={<CloseOutlined style={{ color: '#fff' }} />} onClick={onMobileClose} />
        </div>
        <SidebarContent
          collapsed={false}
          selectedKey={selectedKey}
          menuItems={menuItems}
          handleMenuClick={handleMenuClick}
          themeMode={themeMode}
          onToggleTheme={onToggleTheme}
          onOpenHelp={onOpenHelp}
          navigate={navigate}
        />
      </Drawer>
    </>
  );
};

export default Sidebar;
