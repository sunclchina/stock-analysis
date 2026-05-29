/**
 * 个股分析标签页
 * - 选择股票代码 → 生成报告 → 保存到文件 → 在下方报告列表中点击阅读
 * - 支持默认模板 / 无模板 两种模式
 */
import React, { useState, useCallback, useRef, useMemo } from 'react';
import {
  Card, Button, Input, Space, message, Typography,
  Spin, Empty, Tag, Row, Col,
} from 'antd';
import {
  PlayCircleOutlined, ReloadOutlined,
  StarOutlined, StarFilled, StockOutlined,
} from '@ant-design/icons';
import { stockAnalysis } from '../../services/analysisApi';
import { useConfigStore } from '../../store/configStore';

const { Text } = Typography;

const STORAGE_KEY = 'stock-analysis-history';

interface StockAnalysisTabProps {
  onReportGenerated?: () => void;
}

const StockAnalysisTab: React.FC<StockAnalysisTabProps> = ({ onReportGenerated }) => {
  const [selectedCode, setSelectedCode] = useState<string | undefined>(undefined);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const [hasRun, setHasRun] = useState(false);
  const [generatedCode, setGeneratedCode] = useState<string>('');
  const [useTemplate, setUseTemplate] = useState<boolean>(true);
  const inputRef = useRef<any>(null);

  const { watchlist, addWatchlistItem, removeWatchlistItem } = useConfigStore();
  const watchlistCodes = useMemo(() => new Set(watchlist.map((w) => w.code)), [watchlist]);
  const isInWatchlist = selectedCode ? watchlistCodes.has(selectedCode) : false;

  // Stock history from localStorage
  const [stockHistory, setStockHistory] = useState<string[]>(
    () => {
      try {
        const raw = localStorage.getItem(STORAGE_KEY);
        return raw ? JSON.parse(raw) : [];
      } catch { return []; }
    }
  );

  function saveToHistory(code: string) {
    const updated = [code, ...stockHistory.filter(c => c !== code)].slice(0, 50);
    setStockHistory(updated);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
  }

  const handleSelectStock = useCallback((code: string) => {
    const c = code.trim().toUpperCase();
    if (c) {
      setSelectedCode(c);
      setInputValue(c);
      setHasRun(false);
      setGeneratedCode('');
      saveToHistory(c);
    }
  }, [stockHistory]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && inputValue.trim()) {
      handleSelectStock(inputValue);
    }
  }, [inputValue, handleSelectStock]);

  const handleGenerate = useCallback(async () => {
    if (!selectedCode) {
      message.warning('请选择要分析的股票');
      return;
    }
    setLoading(true);
    setHasRun(false);
    try {
      const res = await stockAnalysis(selectedCode, useTemplate);
      const data = (res as any).data || (res as any);
      const rawReport = data?.report ?? '';
      if (rawReport && typeof rawReport === 'string' && rawReport.length > 50) {
        setGeneratedCode(selectedCode);
        onReportGenerated?.();
        message.success(`${selectedCode} 个股分析完成`);
      } else {
        message.warning('AI生成结果内容不足，请重试');
      }
    } catch (err) {
      console.error('个股分析失败:', err);
      message.error('分析接口调用失败，请稍后重试');
    } finally {
      setHasRun(true);
      setLoading(false);
    }
  }, [selectedCode, useTemplate, onReportGenerated]);

  const handleWatchlistToggle = useCallback(() => {
    if (!selectedCode) return;
    if (isInWatchlist) {
      removeWatchlistItem(selectedCode);
      message.success(`已将 ${selectedCode} 移出自选股`);
    } else {
      addWatchlistItem({ code: selectedCode, name: selectedCode, addedAt: new Date().toISOString() });
      message.success(`已将 ${selectedCode} 加入自选股`);
    }
  }, [selectedCode, isInWatchlist, addWatchlistItem, removeWatchlistItem]);

  return (
    <div style={{ padding: '16px 0' }}>
      <Card size="small" style={{ marginBottom: 16, borderRadius: 8 }}>
        <Row gutter={[16, 16]} align="middle">
          <Col xs={24} sm={12} md={12}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Text strong style={{ fontSize: 12 }}>
                <StockOutlined style={{ marginRight: 4 }} />股票代码
              </Text>
              <Input
                ref={inputRef}
                value={inputValue}
                onChange={(e) => { setInputValue(e.target.value); setSelectedCode(undefined); }}
                onKeyDown={handleKeyDown}
                placeholder="输入股票代码后按回车，如 000001"
                allowClear
                onClear={() => { setInputValue(''); setSelectedCode(undefined); }}
                style={{ width: '100%' }}
              />
              {stockHistory.length > 0 && !selectedCode && (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 4 }}>
                  <Text type="secondary" style={{ fontSize: 11, lineHeight: '22px' }}>历史：</Text>
                  {stockHistory.slice(0, 10).map((code) => (
                    <Tag key={code} style={{ cursor: 'pointer', fontSize: 11 }} onClick={() => handleSelectStock(code)}>{code}</Tag>
                  ))}
                </div>
              )}
              {selectedCode && (
                <div style={{ marginTop: 4 }}><Tag color="blue" style={{ fontSize: 12 }}>{selectedCode} ✓</Tag></div>
              )}
            </Space>
          </Col>

          <Col xs={24} sm={8} md={4}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Text strong style={{ fontSize: 12 }}>模板</Text>
              <Space>
                <Tag color={useTemplate ? 'blue' : 'default'} style={{ cursor: 'pointer', fontSize: 11 }} onClick={() => setUseTemplate(true)}>默认模板</Tag>
                <Tag color={!useTemplate ? 'blue' : 'default'} style={{ cursor: 'pointer', fontSize: 11 }} onClick={() => setUseTemplate(false)}>无模板</Tag>
              </Space>
            </Space>
          </Col>

          <Col xs={24} sm={8} md={4} style={{ textAlign: 'center' }}>
            <Button type="primary" icon={<PlayCircleOutlined />} onClick={handleGenerate}
              loading={loading} size="middle" style={{ minWidth: 160 }} disabled={!selectedCode}>
              生成个股分析
            </Button>
          </Col>

          <Col xs={24} sm={8} md={4} style={{ textAlign: 'center' }}>
            {selectedCode && (
              <Button icon={isInWatchlist ? <StarFilled style={{ color: '#faad14' }} /> : <StarOutlined />}
                onClick={handleWatchlistToggle} size="middle">
                {isInWatchlist ? '已关注' : '加入自选'}
              </Button>
            )}
          </Col>
        </Row>
      </Card>

      <Card size="small" style={{ borderRadius: 8 }}>
        {loading ? (
          <div style={{ textAlign: 'center', padding: 40 }}><Spin tip="正在生成分析报告..." /></div>
        ) : hasRun && generatedCode ? (
          <div style={{ textAlign: 'center', padding: 20 }}>
            <Tag color="green" style={{ fontSize: 14, padding: '4px 12px', marginBottom: 8 }}>
              ✓ {generatedCode} 分析报告已生成
            </Tag>
            <div style={{ color: '#8c8c8c', fontSize: 12, marginTop: 8 }}>
              请在下方「已保存报告」列表中点击阅读按钮查看
            </div>
            <Button size="small" icon={<ReloadOutlined />} onClick={handleGenerate} loading={loading} style={{ marginTop: 8 }}>
              重新生成
            </Button>
          </div>
        ) : (
          <Empty description="选择股票后点击「生成个股分析」" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        )}
      </Card>
    </div>
  );
};

export default StockAnalysisTab;
