/**
 * 缁熶竴项电湁缁勪件堣璁¤范?v1.1 搂2?
 * - 固定鏄剧ず鍦ㄥ彸渚т富鍐呭鍖洪《閮?
 * - 宸︿晶氶〉非㈡额?+ 非㈠寘灞戝鑸?
 * - 取充晶氭墜鍔ㄥ埛鏂?/ 一婚分标崲 / 选氱煡 / 用户澶村儚
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
}

/** 项甸面标题映射 */
const pageTitles: Record<string, { title: string; breadcrumb?: string }> = {
  "/": { title: "仪表盘" },
  "/market": { title: "实时行情" },
  "/selection": { title: "智能选股", breadcrumb: "固定规则选股 / 自定义选股" },
  "/analysis": { title: "智能分析", breadcrumb: "大盘复盘 / 个股分析 / 批量分析" },
  "/warning": { title: "智能预警" },
  "/config": { title: "系统配置", breadcrumb: "设置 / 自选股 / 监控池 / 数据源 / 模板 / 偏好 / 状态" },
  "/users": { title: "用户管理" },
  "/password-change": { title: "修改密码" },
};

const HeaderBar: React.FC<HeaderBarProps> = ({ themeMode, onToggleTheme }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { sidebarCollapsed, toggleSidebar } = useConfigStore();
  const pageInfo = pageTitles[location.pathname] || { title: '' };
  const pad = (n: number) => String(n).padStart(2, '0');
  const d = new Date();
  const [timeStr, setTimeStr] = useState(`${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`);
  const [session, setSession] = useState(d.getDay() === 0 || d.getDay() === 6 ? '非交易日' : '');
  const [countdown, setCountdown] = useState('');

  useEffect(() => {
    // 姣忕鏇存柊鏃堕棿
    const tick = setInterval(() => {
      const n = new Date();
      setTimeStr(`${n.getFullYear()}-${pad(n.getMonth()+1)}-${pad(n.getDate())} ${pad(n.getHours())}:${pad(n.getMinutes())}:${pad(n.getSeconds())}`);
    }, 1000);
    // K线数据加载
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
    // 棣栨鍔犺浇
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

  // K线数据加载
  useEffect(() => {
    const calc = setInterval(() => {
      if (!_nextOpenTs) { setCountdown(''); return; }
      const diff = _nextOpenTs - Date.now();
      if (diff <= 0) { setCountdown(''); return; }
      setCountdown(formatCountdown(diff));
    }, 1000);
    return () => clearInterval(calc);
  }, []);

  // 用户保℃伅
  const user = getCurrentUser();
  const loggedIn = isLoggedIn();

  const userMenuItems = [
    ...(user?.role === 'admin' ? [{ key: 'admin', label: '用户管理', onClick: () => navigate('/users') }] : []),
    { key: 'profile', label: '个人设置', onClick: () => navigate('/config?tab=profile') },
    { key: 'logout', label: '退出登录', danger: true, onClick: () => logout() },
  ];

  // 模拟通知数据
  const hasNotification = false;

  return (
    <header
      style={{
        height: 'var(--header-height)',
        background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)',
        borderBottom: '1px solid rgba(255,255,255,0.08)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 24px',
        position: 'sticky',
        top: 0,
        zIndex: 50,
        transition: 'background 0.3s',
      }}
    >
      {/* 宸︿晶氭姌取犳寜閽?+ 项甸面标题 + 鏃堕棿保℃伅 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        {sidebarCollapsed && (
          <Tooltip title="灞曞紑渚ф爮">
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
            fontSize: 18,
            fontWeight: 700,
            color: '#ffffff',
            whiteSpace: 'nowrap',
          }}
        >
          {pageInfo.title}
        </h1>
        {pageInfo.breadcrumb && (
          <span
            style={{
              fontSize: 14,
              color: 'rgba(255,255,255,0.65)',
              marginLeft: 8,
              paddingLeft: 12,
              borderLeft: '1px solid rgba(255,255,255,0.15)',
            }}
          >
            {pageInfo.breadcrumb}
          </span>
        )}
        {/* 鏃堕棿/交易鏃?值掕鏃?*/}
        <span style={{
          marginLeft: 16, paddingLeft: 16, borderLeft: '1px solid rgba(255,255,255,0.15)',
          fontSize: 13, color: 'rgba(255,255,255,0.65)', fontFamily: 'monospace', whiteSpace: 'nowrap',
        }}>
          {timeStr}
        </span>
        <Tag color={session.includes('非交易日') || session.includes('盘前') || session.includes('午休') ? 'default' : 'green'} style={{ fontSize: 11, margin: 0 }}>
          {session || '非交易时段'}
        </Tag>
        {countdown && <Text style={{ fontSize: 11, color: '#FFD700' }}>{countdown}</Text>}
      </div>

      {/* 取充晶氭搷位滃尯 */}
      <Space size={16} align="center">
        <Tooltip title="鎵姩分锋柊">
          <Button
            type="text"
            icon={<ReloadOutlined />}
            onClick={() => window.location.reload()}
            style={{
              color: '#ffffff',
              fontSize: 18,
              transition: 'color 0.2s',
            }}
            className="header-icon-btn"
          />
        </Tooltip>

        <Tooltip title={themeMode === 'dark' ? '分标崲流呰壊妯″紡' : '分标崲娣辫壊妯″紡'}>
          <Button
            type="text"
            icon={
              themeMode === 'dark' ? (
                <SunOutlined style={{ color: 'var(--theme-toggle-color)' }} />
              ) : (
                <MoonOutlined />
              )
            }
            onClick={onToggleTheme}
            style={{
              color: '#ffffff',
              fontSize: 18,
              transition: 'color 0.2s',
            }}
            className="header-icon-btn"
          />
        </Tooltip>

        {(userMenuItems.length > 0) && (
          <Dropdown menu={{ items: userMenuItems }} placement="bottomRight" trigger={['click']}>
            <Button type="text"
              style={{
                color: '#ffffff',
                display: 'flex',
                alignItems: 'center',
                gap: 4,
                fontSize: 14,
              }}
              className="header-icon-btn"
            >
              <UserOutlined />
              {user?.nickname || user?.username || '未登录'}
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


