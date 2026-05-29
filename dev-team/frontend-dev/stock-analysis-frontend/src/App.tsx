import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ConfigProvider, theme as antdTheme } from 'antd';
import { StyleProvider } from '@ant-design/cssinjs';
import MainLayout from './layouts/MainLayout';
import ErrorBoundary from './components/ErrorBoundary';
import DashboardPage from './pages/DashboardPage';
import MarketPage from './pages/MarketPage';
import MarketExtPage from './pages/MarketExtPage';
import MarketResearchPage from './pages/MarketResearchPage';
import SelectionPage from './pages/SelectionPage';
import AnalysisPage from './pages/AnalysisPage';
import WarningPage from './pages/WarningPage';
import ConfigPage from './pages/ConfigPage';
import PortfolioPage from './pages/PortfolioPage';
import LoginPage from './pages/LoginPage';
import HelpPage from './pages/HelpPage';
import NotesPage from './pages/Notes';
import PasswordChangePage from './pages/PasswordChangePage';
import UsersPage from './pages/UsersPage';
import { usePreference } from './hooks/usePreference';

const App: React.FC = () => {
  const { theme, toggleTheme } = usePreference();

  return (
    <BrowserRouter>
      <ErrorBoundary title="系统异常" description="应用渲染过程中发生严重错误，请尝试刷新。若问题持续，检查后端是否正常运行。">
        <StyleProvider hashPriority="high">
        <ConfigProvider
          theme={{
          algorithm:
            theme === 'dark'
              ? antdTheme.darkAlgorithm
              : antdTheme.defaultAlgorithm,
        }}
      >
        <Routes>
          <Route path="/help" element={<HelpPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/password" element={<PasswordChangePage />} />
          <Route element={<MainLayout themeMode={theme} onToggleTheme={toggleTheme} />}>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/logo" element={
              <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%', background: '#0d1f3c' }}>
                <img src="/logo.svg" alt="logo" style={{ width: 240, height: 240, objectFit: 'contain' }} />
              </div>
            } />
            <Route path="/market" element={<MarketPage />} />
            <Route path="/market-ext" element={<MarketExtPage />} />
            <Route path="/market-research" element={<MarketResearchPage />} />
            <Route path="/selection" element={<SelectionPage />} />
            <Route path="/analysis" element={<AnalysisPage />} />
            <Route path="/warning" element={<WarningPage />} />
            <Route path="/notes" element={<NotesPage />} />
            <Route path="/portfolio" element={<PortfolioPage />} />
            <Route path="/config" element={<ConfigPage />} />
            <Route path="/users" element={<UsersPage />} />
          </Route>
        </Routes>
        </ConfigProvider>
        </StyleProvider>
      </ErrorBoundary>
    </BrowserRouter>
  );
};

export default App;
