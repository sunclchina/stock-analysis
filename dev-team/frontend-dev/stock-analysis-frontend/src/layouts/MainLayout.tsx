/**
 * 主布局组件（设计规范 v1.1 §7）
 * - 固定侧栏（240px/60px）+ 右侧页眉（56px）+ 滚动内容区
 * - 无固定页脚，内容底部展示版权
 * - 修复：滚动失效、侧栏底部定位、版权字号
 */
import React, { useState, useCallback, useRef } from 'react';
import { Outlet, useNavigate } from 'react-router-dom';
import { Layout } from 'antd';
import Sidebar from './Sidebar';
import HeaderBar from './HeaderBar';
import { useConfigStore } from '../store/configStore';
import { isLoggedIn } from '../services/auth';
import HelpDrawer from '../components/HelpDrawer';
import { HelpContext } from '../services/help';
import type { ThemeMode } from '../types';

const { Content } = Layout;

interface MainLayoutProps {
  themeMode: ThemeMode;
  onToggleTheme: () => void;
}

const MainLayout: React.FC<MainLayoutProps> = ({ themeMode, onToggleTheme }) => {
  const navigate = useNavigate();
  
  // 未登录跳转登录页
  React.useEffect(() => {
    if (!isLoggedIn()) {
      navigate('/login', { replace: true });
    }
  }, []);

  const [helpOpen, setHelpOpen] = useState(false);
  const [helpSlug, setHelpSlug] = useState<string | undefined>(undefined);
  const helpSlugRef = useRef<string | undefined>(undefined);

  const openHelp = useCallback((slug?: string) => {
    helpSlugRef.current = slug;
    setHelpSlug(slug);
    setHelpOpen(true);
  }, []);

  const handleHelpClose = useCallback(() => {
    setHelpOpen(false);
    setHelpSlug(undefined);
    helpSlugRef.current = undefined;
  }, []);

  const sidebarCollapsed = useConfigStore((s) => s.sidebarCollapsed);
  const loggedIn = isLoggedIn();
  const sidebarWidth = loggedIn ? (sidebarCollapsed ? 60 : 240) : 0;

  return (
    <HelpContext.Provider value={{ openHelp }}>
    <Layout style={{ height: '100vh', background: 'var(--content-bg)' }}>
      {/* 固定侧栏 */}
      <Sidebar themeMode={themeMode} onToggleTheme={onToggleTheme} onOpenHelp={() => openHelp()} />

      {/* 右侧主区域 */}
      <Layout
        style={{
          marginLeft: sidebarWidth,
          background: 'var(--content-bg)',
          transition: 'margin-left 0.3s ease',
          height: '100vh',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {/* 页眉（固定56px） */}
        <HeaderBar themeMode={themeMode} onToggleTheme={onToggleTheme} />

        {/* 内容区（可滚动，flex列布局让版权沉底） */}
        <Content
          style={{
            padding: 24,
            background: 'var(--content-bg)',
            color: 'var(--content-text)',
            overflow: 'auto',
            flex: 1,
            height: '100%',
          }}
        >
          <Outlet />
        </Content>

      {/* 页面底部版权（固定页脚，匹配页眉配色） */}
      <div
        style={{
          textAlign: 'center',
          padding: '10px 24px',
          fontSize: 13,
          fontWeight: 400,
          color: 'rgba(255,255,255,0.6)',
          background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)',
          borderTop: '1px solid rgba(255,255,255,0.08)',
          flexShrink: 0,
        }}
      >
        股票分析与投资决策系统 v1.0.0  Copyright © 2026 闲适老翁 · 版权所有
      </div>
      </Layout>
      <HelpDrawer open={helpOpen} onClose={handleHelpClose} initialSlug={helpSlug} />
    </Layout>
    </HelpContext.Provider>
  );
};

export default MainLayout;
