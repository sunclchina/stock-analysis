/**
 * 大盘复盘标签页
 * - 选日期 + 选股票 → 生成报告 → 保存到文件 → 在下方报告列表中点击阅读
 * - 支持默认模板 / 无模板 两种模式
 */
import React, { useState, useCallback } from 'react';
import {
  Card, Button, DatePicker, Select, Space, message, Typography,
  Spin, Empty, Tag, Row, Col,
} from 'antd';
import {
  PlayCircleOutlined, ReloadOutlined,
  CalendarOutlined, StockOutlined,
} from '@ant-design/icons';
import type { Dayjs } from 'dayjs';
import { postReview } from '../../services/analysisApi';

const { Text } = Typography;

const STORAGE_KEY = 'stock-review-history';

interface ReviewTabProps {
  onReportGenerated?: () => void;
}

const ReviewTab: React.FC<ReviewTabProps> = ({ onReportGenerated }) => {
  const [selectedDate, setSelectedDate] = useState<Dayjs | null>(null);
  const [selectedStocks, setSelectedStocks] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [hasRun, setHasRun] = useState(false);
  const [useTemplate, setUseTemplate] = useState<boolean>(true);

  const [stockHistory, setStockHistory] = useState<string[]>(
    () => {
      try {
        const raw = localStorage.getItem(STORAGE_KEY);
        return raw ? JSON.parse(raw) : [];
      } catch { return []; }
    }
  );

  function saveStockHistory(code: string) {
    const updated = [code, ...stockHistory.filter(c => c !== code)].slice(0, 50);
    setStockHistory(updated);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
  }

  const handleRemoveStock = useCallback((code: string) => {
    setSelectedStocks((prev) => prev.filter((c) => c !== code));
  }, []);

  const handleGenerate = useCallback(async () => {
    if (!selectedDate) {
      message.warning('请选择复盘日期');
      return;
    }
    setLoading(true);
    setHasRun(false);
    try {
      const dateStr = selectedDate.format('YYYY-MM-DD');
      const res: any = await postReview({
        date: dateStr,
        watch_stocks: selectedStocks.length > 0 ? selectedStocks : undefined,
        use_template: useTemplate,
      });
      const data = res?.data ?? res ?? {};
      const rawReport = data?.report ?? '';
      if (rawReport && typeof rawReport === 'string' && rawReport.length > 50) {
        onReportGenerated?.();
        message.success('大盘复盘分析完成');
      } else {
        message.warning('AI生成结果内容不足');
      }
    } catch (err) {
      console.error('大盘复盘失败:', err);
      message.error('分析接口暂不可用');
    } finally {
      setHasRun(true);
      setLoading(false);
    }
  }, [selectedDate, selectedStocks, useTemplate, onReportGenerated]);

  return (
    <div style={{ padding: '16px 0' }}>
      <Card size="small" style={{ marginBottom: 16, borderRadius: 8 }}>
        <Row gutter={[16, 16]} align="middle">
          <Col xs={24} sm={8} md={6}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Text strong style={{ fontSize: 12 }}>
                <CalendarOutlined style={{ marginRight: 4 }} />复盘日期
              </Text>
              <DatePicker
                value={selectedDate}
                onChange={(d) => setSelectedDate(d)}
                style={{ width: '100%' }}
                placeholder="选择复盘日期"
                allowClear
              />
            </Space>
          </Col>

          <Col xs={24} sm={8} md={8}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Text strong style={{ fontSize: 12 }}>
                <StockOutlined style={{ marginRight: 4 }} />关注股票（可选，最多10只）
              </Text>
              <div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginBottom: 6 }}>
                  {selectedStocks.map((code) => (
                    <Tag key={code} closable onClose={() => handleRemoveStock(code)} color="blue" style={{ fontSize: 11 }}>
                      {code}
                    </Tag>
                  ))}
                </div>
                <Select
                  mode="tags"
                  value={selectedStocks}
                  onChange={(vals: string[]) => {
                    const added = vals.filter(v => !selectedStocks.includes(v));
                    added.forEach(c => { if (c.trim() && selectedStocks.length + 1 <= 10) saveStockHistory(c.trim().toUpperCase()); });
                    setSelectedStocks(vals.filter(v => v.trim() !== '').slice(0, 10));
                  }}
                  style={{ width: '100%' }}
                  placeholder="输入股票代码后按回车添加"
                  maxCount={10}
                  tokenSeparators={[',', '，', ' ', ';']}
                  options={stockHistory.map((code) => ({ value: code, label: code }))}
                />
              </div>
            </Space>
          </Col>

          <Col xs={12} sm={4} md={3}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Text strong style={{ fontSize: 12 }}>模板</Text>
              <Space>
                <Tag color={useTemplate ? 'blue' : 'default'} style={{ cursor: 'pointer', fontSize: 11 }} onClick={() => setUseTemplate(true)}>默认模板</Tag>
                <Tag color={!useTemplate ? 'blue' : 'default'} style={{ cursor: 'pointer', fontSize: 11 }} onClick={() => setUseTemplate(false)}>无模板</Tag>
              </Space>
            </Space>
          </Col>

          <Col xs={12} sm={4} md={3} style={{ textAlign: 'center' }}>
            <Button type="primary" icon={<PlayCircleOutlined />} onClick={handleGenerate}
              loading={loading} size="middle" style={{ minWidth: 140 }}>
              生成复盘分析
            </Button>
          </Col>
        </Row>
      </Card>

      <Card size="small" style={{ borderRadius: 8 }}>
        {loading ? (
          <div style={{ textAlign: 'center', padding: 40 }}><Spin tip="正在生成复盘分析报告..." /></div>
        ) : hasRun ? (
          <div style={{ textAlign: 'center', padding: 20 }}>
            <Tag color="green" style={{ fontSize: 14, padding: '4px 12px', marginBottom: 8 }}>
              ✓ 大盘复盘分析报告已生成
            </Tag>
            <div style={{ color: '#8c8c8c', fontSize: 12, marginTop: 8 }}>
              请在下方「已保存报告」列表中点击阅读按钮查看
            </div>
            <Button size="small" icon={<ReloadOutlined />} onClick={handleGenerate} loading={loading} style={{ marginTop: 8 }}>
              重新生成
            </Button>
          </div>
        ) : (
          <Empty description="选择日期后点击「生成复盘分析」" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        )}
      </Card>
    </div>
  );
};

export default ReviewTab;
