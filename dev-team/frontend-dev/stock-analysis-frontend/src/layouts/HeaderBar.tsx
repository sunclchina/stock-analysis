/**
 * 统一页眉组件（设计规范 v1.1 §2）
 * - 固定显示在右侧主内容区顶部
 * - 左侧：页面标题 + 面包屑导航
 * - 右侧：手动刷新 / 主题切换 / 通知 / 用户头像
 * - 移动端：汉堡菜单按钮 + 简化显示
 */
import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Button, Space, Tooltip, Badge, Dropdown, Tag, Typography } from 'antd';
import {
  ReloadOutlined,
  SunOutlined,
  MoonOutlined,
  BellOutlined,
  UserOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  MenuOutlined,
} from '@ant-design/icons';
import { useConfigStore } from '../store/configStore';
import { getCurrentUser, logout, isLoggedIn } from '../services/auth';

const { Text } = Typography;

let _nextOpenTs: number | null = null;

function formatCountdown(ms: number): string {
  if (ms <= 0) return '';
  const hrs = Math.floor(ms / 3600000);
  const mins = Math.floor((ms % 3600000) / 60000);
  if (hrs > 0) return `距离开盘还有${hrs}小时${mins}分钟`;
  return `距离开盘还有${mins}分钟`;
}

interface HeaderBarProps {
  themeMode: 'light' | 'dark';
  onToggleTheme: () => void;
  onRefresh?: () => void;
  /** 移动端汉堡菜单回调 */
  onMobileMenuClick?: () => void;
}

/** 页面标题映射 */
const pageTitles: Record<string, { title: string; breadcrumb?: string }> = {
  "/": { title: "仪表盘" },
  "/market": { title: "实时行情" },
  "/market-ext": { title: "全球指数/行业" },
  "/market-research": { title: "研报/公告/行业" },
  "/selection": { title: "智能选股" },
  "/analysis": { title: "智能分析" },
  "/warning": { title: "智能预警" },
  "/portfolio": { title: "资产组合" },
  "/notes": { title: "操盘笔记" },
  "/config": { title: "系统配置" },
  "/users": { title: "用户管理" },
  "/login": { title: "登录" },
  "/password": { title: "修改密码" },
};

const HeaderBar: React.FC<HeaderBarProps> = ({ themeMode, onToggleTheme, onMobileMenuClick }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { sidebarCollapsed, toggleSidebar } = useConfigStore();
  const pageInfo = pageTitles[location.pathname] || { title: '' };

  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);
  useEffect(() => {
    const onResize = () => setIsMobile(window.innerWidth < 768);
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  const pad = (n: number) => String(n).padStart(2, '0');
  const d = new Date();
  const [timeStr, setTimeStr] = useState(
    `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  );
  const [session, setSession] = useState(d.getDay() === 0 || d.getDay() === 6 ? '非交易日' : '');
  const [countdown, setCountdown] = useState('');

  useEffect(() => {
    const tick = setInterval(() => {
      const n = new Date();
      setTimeStr(`${n.getFullYear()}-${pad(n.getMonth()+1)}-${pad(n.getDate())} ${pad(n.getHours())}:${pad(n.getMinutes())}:${pad(n.getSeconds())}`);
    }, 1000);

    const refresh = setInterval(() => {
      fetch('/api/v1/market/is-trading-day').then(r=>r.json()).then(d => {
        if(d.session) setSession(d.session);
        if(d.next_open_timestamp) {
          _nextOpenTs = d.next_open_timestamp;
          const diff = _nextOpenTs - Date.now();
          setCountdown(diff > 0 ? formatCountdown(diff) : '');
        }
      }).catch(()=>{});
    }, 30000);

    fetch('/api/v1/market/is-trading-day').then(r=>r.json()).then(d => {
      if(d.session) setSession(d.session);
      if(d.next_open_timestamp) {
        _nextOpenTs = d.next_open_timestamp;
        const diff = _nextOpenTs - Date.now();
        setCountdown(diff > 0 ? formatCountdown(diff) : '');
      }
    }).catch(()=>{});

    return () => { clearInterval(tick); clearInterval(refresh); };
  }, []);

  useEffect(() => {
    const calc = setInterval(() => {
      if (!_nextOpenTs) { setCountdown(''); return; }
      const diff = _nextOpenTs - Date.now();
      if (diff <= 0) { setCountdown(''); return; }
      setCountdown(formatCountdown(diff));
    }, 1000);
    return () => clearInterval(calc);
  }, []);

  const user = getCurrentUser();
  const loggedIn = isLoggedIn();

  const userMenuItems = [
    ...(user?.role === 'admin' ? [{ key: 'admin', label: '用户管理', onClick: () => navigate('/users') }] : []),
    { key: 'profile', label: '个人设置', onClick: () => navigate('/config?tab=profile') },
    { key: 'logout', label: '退出登录', danger: true, onClick: () => logout() },
  ];

  return (
    <header
      className="header-bar"
      style={{
        height: 'var(--header-height)',
        background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)',
        borderBottom: '1px solid rgba(255,255,255,0.08)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: isMobile ? '0 8px' : '0 24px',
        position: 'sticky',
        top: 0,
        zIndex: 50,
        transition: 'background 0.3s',
      }}
    >
      {/* 左侧：移动端汉堡菜单 + 标题 + 时间/状态 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: isMobile ? 6 : 12, overflow: 'hidden' }}>
        {/* 移动端汉堡菜单（始终显示） */}
        <Button
          type="text"
          icon={<MenuOutlined />}
          onClick={onMobileMenuClick}
          className="mobile-menu-btn"
          style={{ color: '#ffffff', fontSize: 20 }}
        />

        {!isMobile && sidebarCollapsed && (
          <Tooltip title="展开侧栏">
            <Button
              type="text"
              icon={<MenuUnfoldOutlined />}
              onClick={toggleSidebar}
              style={{ color: '#ffffff', fontSize: 18 }}
            />
          </Tooltip>
        )}
        <h1
          style={{
            margin: 0,
            fontSize: isMobile ? 16 : 18,
            fontWeight: 700,
            color: '#ffffff',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            maxWidth: isMobile ? 120 : undefined,
          }}
        >
          {pageInfo.title}
        </h1>
        {/* 桌面端显示面包屑 */}
        {!isMobile && pageInfo.breadcrumb && (
          <span
            className="header-breadcrumb"
            style={{
              fontSize: 14, color: 'rgba(255,255,255,0.65)',
              marginLeft: 8, paddingLeft: 12,
              borderLeft: '1px solid rgba(255,255,255,0.15)',
            }}
          >
            {pageInfo.breadcrumb}
          </span>
        )}
        {/* 时间（桌面端显示） */}
        {!isMobile && (
          <span className="header-timestamp" style={{
            marginLeft: 16, paddingLeft: 16,
            borderLeft: '1px solid rgba(255,255,255,0.15)',
            fontSize: 13, color: 'rgba(255,255,255,0.65)',
            fontFamily: 'monospace', whiteSpace: 'nowrap',
          }}>
            {timeStr}
          </span>
        )}
        {!isMobile && (
          <Tag className="header-session-tag" color={session.includes('非交易日') || session.includes('盘前') || session.includes('午休') ? 'default' : 'green'}
            style={{ fontSize: 11, margin: 0 }}>
            {session || '非交易时段'}
          </Tag>
        )}
        {!isMobile && countdown && (
          <Text className="header-countdown" style={{ fontSize: 11, color: '#FFD700', whiteSpace: 'nowrap' }}>{countdown}</Text>
        )}
      </div>

      {/* 右侧操作区 */}
      <Space size={isMobile ? 8 : 16} align="center">
        {!isMobile && (
          <Tooltip title="手动刷新">
            <Button
              type="text"
              icon={<ReloadOutlined />}
              onClick={() => window.location.reload()}
              style={{ color: '#ffffff', fontSize: 18 }}
              className="header-icon-btn"
            />
          </Tooltip>
        )}

        <Tooltip title={themeMode === 'dark' ? '切换浅色模式' : '切换深色模式'}>
          <Button
            type="text"
            icon={themeMode === 'dark' ? <SunOutlined style={{ color: 'var(--theme-toggle-color)' }} /> : <MoonOutlined />}
            onClick={onToggleTheme}
            style={{ color: '#ffffff', fontSize: isMobile ? 16 : 18 }}
            className="header-icon-btn"
          />
        </Tooltip>

        {loggedIn && (
          <Dropdown menu={{ items: userMenuItems }} placement="bottomRight" trigger={['click']}>
            <Button type="text"
              style={{
                color: '#ffffff', display: 'flex', alignItems: 'center',
                gap: 4, fontSize: isMobile ? 13 : 14,
              }}
              className="header-icon-btn"
            >
              <UserOutlined />
              {!isMobile && (user?.nickname || user?.username || '未登录')}
            </Button>
          </Dropdown>
        )}
      </Space>

      <style>{`
        .header-icon-btn:hover {
          color: #4C8CFF !important;
          background: rgba(22, 93, 255, 0.08) !important;
        }
        .header-icon-btn:active {
          transform: scale(0.95);
        }
      `}</style>
    </header>
  );
};

export default HeaderBar;
