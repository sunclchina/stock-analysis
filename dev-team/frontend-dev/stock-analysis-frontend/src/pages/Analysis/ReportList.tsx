/**
 * 分析报告文件列表
 * 显示已保存的报告，支持下载、删除、点击阅读
 */
import React, { useEffect, useState, useCallback } from 'react';
import { Card, List, Button, Space, Tag, Tooltip, Modal, message, Spin, Empty, Typography } from 'antd';
import {
  FileTextOutlined, DeleteOutlined, DownloadOutlined,
  EyeOutlined, ReloadOutlined,
} from '@ant-design/icons';
import apiClient from '../../services/api';
import ReportRenderer from './ReportRenderer';

const { Text } = Typography;

interface ReportItem {
  id: string;
  title: string;
  type: string;
  date: string;
  created_at: string;
  size: number;
  preview: string;
}

const typeLabels: Record<string, string> = {
  review: '复盘分析',
  stock: '个股分析',
  batch: '批量分析',
};
const typeColors: Record<string, string> = {
  review: 'blue',
  stock: 'green',
  batch: 'purple',
};

interface ReportListProps {
  refreshKey?: number;
  onReadReport?: (content: string, title: string) => void;
}

const ReportList: React.FC<ReportListProps> = ({ refreshKey, onReadReport }) => {
  const [items, setItems] = useState<ReportItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [reading, setReading] = useState(false);
  const [readContent, setReadContent] = useState('');

  const fetchReports = useCallback(async () => {
    setLoading(true);
    try {
      const res: any = await apiClient.get('/analysis/reports');
      const data = res?.items ?? res?.data?.items ?? [];
      setItems(data);
    } catch (e) {
      console.error('获取报告列表失败:', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchReports(); }, [fetchReports, refreshKey]);

  const handleDelete = useCallback(async (id: string) => {
    Modal.confirm({
      title: '确认删除',
      content: '删除后将无法恢复，确定要删除此报告吗？',
      onOk: async () => {
        try {
          await apiClient.delete(`/analysis/report/${encodeURIComponent(id)}`);
          message.success('已删除');
          fetchReports();
        } catch { message.error('删除失败'); }
      },
    });
  }, [fetchReports]);

  const handleRead = useCallback(async (id: string, title: string) => {
    setReading(true);
    try {
      const res: any = await apiClient.get(`/analysis/download/${encodeURIComponent(id)}`, {
        params: { format: 'markdown' },
      });
      const content = typeof res === 'string' ? res : (res?.data ?? '');
      if (onReadReport) {
        onReadReport(content, title);
      } else {
        setReadContent(content);
      }
    } catch { message.error('读取报告失败'); }
    finally { setReading(false); }
  }, [onReadReport]);

  const handleDownload = useCallback(async (id: string, fmt: 'md' | 'txt') => {
    try {
      const format = fmt === 'md' ? 'markdown' : 'txt';
      const res: any = await apiClient.get(`/analysis/download/${encodeURIComponent(id)}`, {
        params: { format },
      });
      const content = typeof res === 'string' ? res : (res?.data ?? '');
      const blob = new Blob([content], { type: fmt === 'md' ? 'text/markdown' : 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = id.replace('.md', `.${fmt}`);
      a.click();
      URL.revokeObjectURL(url);
    } catch { message.error('下载失败'); }
  }, []);

  return (
    <Card
      size="small"
      title={
        <Space>
          <FileTextOutlined />
          <span>已保存报告</span>
          {items.length > 0 && <Tag>{items.length}</Tag>}
        </Space>
      }
      extra={
        <Button size="small" shape="round" icon={<ReloadOutlined />} onClick={fetchReports} loading={loading}>
          刷新
        </Button>
      }
      style={{ borderRadius: 8, marginTop: 16 }}
      bodyStyle={{ padding: items.length === 0 ? '40px 16px' : '4px 16px', maxHeight: 300, overflowY: 'auto' }}
    >
      {loading ? (
        <div style={{ textAlign: 'center', padding: 20 }}><Spin /></div>
      ) : items.length === 0 ? (
        <Empty description="暂无已保存报告" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      ) : (
        <List
          dataSource={items}
          renderItem={(item) => (
            <List.Item
              style={{ padding: '8px 0', borderBottom: '1px solid #f0f0f0' }}
              actions={[
                <Tooltip key="read" title="阅读">
                  <Button type="link" size="small" icon={<EyeOutlined />}
                    onClick={() => handleRead(item.id, item.title)} />
                </Tooltip>,
                <Tooltip key="dl-md" title="下载Markdown">
                  <Button type="link" size="small" icon={<DownloadOutlined />}
                    onClick={() => handleDownload(item.id, 'md')} />
                </Tooltip>,
                <Tooltip key="delete" title="删除">
                  <Button type="link" size="small" danger icon={<DeleteOutlined />}
                    onClick={() => handleDelete(item.id)} />
                </Tooltip>,
              ]}
            >
              <List.Item.Meta
                title={
                  <Space size={4}>
                    <Tag color={typeColors[item.type] || 'default'} style={{ fontSize: 10, lineHeight: '18px' }}>
                      {typeLabels[item.type] || item.type}
                    </Tag>
                    <Text style={{ fontSize: 13 }} ellipsis={{ tooltip: item.title }}>
                      {item.title}
                    </Text>
                  </Space>
                }
                description={
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    {item.created_at} · {(item.size / 1024).toFixed(1)}KB
                  </Text>
                }
              />
            </List.Item>
          )}
        />
      )}

      {/* 阅读弹窗（使用Markdown渲染） */}
      <Modal
        title="报告内容"
        open={!!readContent}
        onCancel={() => setReadContent('')}
        footer={null}
        width={900}
      >
        <Spin spinning={reading}>
          <div style={{ maxHeight: '70vh', overflowY: 'auto', padding: '0 8px' }}>
            <ReportRenderer sections={[]} rawContent={readContent} />
          </div>
        </Spin>
      </Modal>
    </Card>
  );
};

export default ReportList;
