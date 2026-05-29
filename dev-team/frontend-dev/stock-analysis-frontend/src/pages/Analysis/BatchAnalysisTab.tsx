/**
 * 批量分析标签页
 * - 多选股票代码 → 生成报告 → 保存到文件 → 在下方报告列表中点击阅读
 * - 支持默认模板 / 无模板 两种模式
 */
import React, { useState, useCallback } from 'react';
import {
  Card, Button, Select, Space, message, Typography,
  Spin, Empty, Tag, Row, Col,
} from 'antd';
import {
  PlayCircleOutlined, ReloadOutlined,
  ClusterOutlined,
} from '@ant-design/icons';
import { batchAnalysis } from '../../services/analysisApi';

const { Text } = Typography;

const STORAGE_KEY = 'stock-batch-history';

interface BatchAnalysisTabProps {
  onReportGenerated?: () => void;
}

const BatchAnalysisTab: React.FC<BatchAnalysisTabProps> = ({ onReportGenerated }) => {
  const [selectedCodes, setSelectedCodes] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [hasRun, setHasRun] = useState(false);
  const [useTemplate, setUseTemplate] = useState<boolean>(true);

  // Stock history from localStorage
  const [stockHistory, setStockHistory] = useState<string[]>(
    () => {
      try {
        const raw = localStorage.getItem(STORAGE_KEY);
        return raw ? JSON.parse(raw) : [];
      } catch { return []; }
    }
  );

  function saveToHistory(codes: string[]) {
    const updated = [...new Set([...codes, ...stockHistory])].slice(0, 50);
    setStockHistory(updated);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
  }

  const handleGenerate = useCallback(async () => {
    if (selectedCodes.length === 0) {
      message.warning('请至少选择一只股票');
      return;
    }
    if (selectedCodes.length > 10) {
      message.warning('最多选择10只股票');
      return;
    }

    setLoading(true);
    setHasRun(false);
    try {
      const res = await batchAnalysis({
        codes: selectedCodes,
        use_template: useTemplate,
      });
      const data = (res as any).data || (res as any);
      const rawReport = data?.report ?? '';
      if (rawReport && typeof rawReport === 'string' && rawReport.length > 50) {
        saveToHistory(selectedCodes);
        onReportGenerated?.();
        message.success(`批量分析完成，共 ${selectedCodes.length} 只股票`);
      } else {
        message.warning('AI生成结果内容不足，请重试');
      }
    } catch (err) {
      console.error('批量分析失败:', err);
      message.error('分析接口调用失败，请稍后重试');
    } finally {
      setHasRun(true);
      setLoading(false);
    }
  }, [selectedCodes, useTemplate, onReportGenerated]);

  return (
    <div style={{ padding: '16px 0' }}>
      <Card size="small" style={{ marginBottom: 16, borderRadius: 8 }}>
        <Row gutter={[16, 16]} align="middle">
          <Col xs={24} sm={12} md={12}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Text strong style={{ fontSize: 12 }}>
                <ClusterOutlined style={{ marginRight: 4 }} />股票列表（最多10只）
              </Text>
              <Select
                mode="tags"
                value={selectedCodes}
                onChange={(vals: string[]) => setSelectedCodes(vals.filter(v => v.trim() !== '').slice(0, 10))}
                style={{ width: '100%' }}
                placeholder="输入股票代码后按回车添加，如 000001"
                maxCount={10}
                maxTagCount={5}
                tokenSeparators={[',', '，', ' ', ';']}
                options={stockHistory.map((code) => ({ value: code, label: code }))}
              />
            </Space>
          </Col>

          <Col xs={24} sm={6} md={4}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Text strong style={{ fontSize: 12 }}>模板</Text>
              <Space>
                <Tag color={useTemplate ? 'blue' : 'default'} style={{ cursor: 'pointer', fontSize: 11 }} onClick={() => setUseTemplate(true)}>默认模板</Tag>
                <Tag color={!useTemplate ? 'blue' : 'default'} style={{ cursor: 'pointer', fontSize: 11 }} onClick={() => setUseTemplate(false)}>无模板</Tag>
              </Space>
            </Space>
          </Col>

          <Col xs={24} sm={6} md={4} style={{ textAlign: 'center' }}>
            <Button type="primary" icon={<PlayCircleOutlined />} onClick={handleGenerate}
              loading={loading} size="middle" style={{ minWidth: 160 }} disabled={selectedCodes.length === 0}>
              生成批量分析
            </Button>
          </Col>

          <Col xs={24} sm={6} md={4} style={{ textAlign: 'center' }}>
            {selectedCodes.length > 0 && (
              <Text type="secondary" style={{ fontSize: 11 }}>已选 {selectedCodes.length} 只</Text>
            )}
          </Col>
        </Row>
      </Card>

      <Card size="small" style={{ borderRadius: 8 }}>
        {loading ? (
          <div style={{ textAlign: 'center', padding: 40 }}><Spin tip="正在生成批量分析报告..." /></div>
        ) : hasRun ? (
          <div style={{ textAlign: 'center', padding: 20 }}>
            <Tag color="green" style={{ fontSize: 14, padding: '4px 12px', marginBottom: 8 }}>
              ✓ 批量分析报告已生成（{selectedCodes.length} 只）
            </Tag>
            <div style={{ color: '#8c8c8c', fontSize: 12, marginTop: 8 }}>
              请在下方「已保存报告」列表中点击阅读按钮查看
            </div>
            <Button size="small" icon={<ReloadOutlined />} onClick={handleGenerate} loading={loading} style={{ marginTop: 8 }}>
              重新生成
            </Button>
          </div>
        ) : (
          <Empty description="选择股票后点击「生成批量分析」" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        )}
      </Card>
    </div>
  );
};

export default BatchAnalysisTab;
