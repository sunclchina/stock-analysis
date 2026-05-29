/**
 * 联系我们管理（管理员专用）。
 * 查看用户提交的问题/Bug/建议，支持回复和处理状态标记。
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Table,
  Tag,
  Button,
  Space,
  Modal,
  Input,
  message,
  Typography,
  Select,
  Badge,
  Statistic,
  Row,
  Col,
  Empty,
  Descriptions,
} from 'antd';
import {
  ReloadOutlined,
  MessageOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  ToolOutlined,
} from '@ant-design/icons';
import { authFetch } from '../../services/auth';

const { Text, Paragraph } = Typography;
const { TextArea } = Input;

// 简单日期格式化
function fmtDate(iso: string | null, full = false): string {
  if (!iso) return '-';
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, '0');
  const MM = pad(d.getMonth() + 1);
  const DD = pad(d.getDate());
  const hh = pad(d.getHours());
  const mm = pad(d.getMinutes());
  if (full) {
    return `${d.getFullYear()}-${MM}-${DD} ${hh}:${mm}:${pad(d.getSeconds())}`;
  }
  return `${MM}-${DD} ${hh}:${mm}`;
}

const typeConfig: Record<number, { label: string; color: string }> = {
  1: { label: '使用问题', color: 'blue' },
  2: { label: 'Bug', color: 'red' },
  3: { label: '建议', color: 'orange' },
  4: { label: '文档', color: 'purple' },
  5: { label: '其他', color: 'default' },
};

const statusConfig: Record<number, { label: string; color: string; icon: React.ReactNode }> = {
  0: { label: '待处理', color: 'orange', icon: <ClockCircleOutlined /> },
  1: { label: '处理中', color: 'blue', icon: <ToolOutlined /> },
  2: { label: '已解决', color: 'green', icon: <CheckCircleOutlined /> },
  3: { label: '已关闭', color: 'default', icon: <CloseCircleOutlined /> },
};

interface ContactItem {
  id: number;
  type: number;
  type_label: string;
  title: string;
  content: string;
  contact: string;
  user_id: number;
  status: number;
  status_label: string;
  reply: string;
  replied_by: string;
  replied_at: string | null;
  created_at: string;
}

interface StatsInfo {
  total: number;
  pending: number;
}

const ContactsTab: React.FC = () => {
  const [items, setItems] = useState<ContactItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [statusFilter, setStatusFilter] = useState<number | undefined>(undefined);
  const [stats, setStats] = useState<StatsInfo>({ total: 0, pending: 0 });

  // 回复弹窗
  const [replyModalOpen, setReplyModalOpen] = useState(false);
  const [replyTarget, setReplyTarget] = useState<ContactItem | null>(null);
  const [replyText, setReplyText] = useState('');
  const [replyLoading, setReplyLoading] = useState(false);

  // 详情弹窗
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [detailTarget, setDetailTarget] = useState<ContactItem | null>(null);

  const fetchContacts = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (statusFilter !== undefined) params.set('status', String(statusFilter));
      params.set('page', String(page));
      params.set('page_size', String(pageSize));

      const r = await authFetch(`/api/v1/admin/help/contacts?${params}`);
      const d = await r.json();
      if (!r.ok) { message.error(d.detail || '获取失败'); return; }
      setItems(d.items || []);
      setTotal(d.total || 0);
    } catch {
      message.error('获取反馈列表失败');
    } finally {
      setLoading(false);
    }
  }, [statusFilter, page, pageSize]);

  const fetchStats = useCallback(async () => {
    try {
      const r = await authFetch('/api/v1/admin/help/statistics');
      const d = await r.json();
      if (d?.contacts) {
        setStats(d.contacts);
      }
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    fetchContacts();
    fetchStats();
  }, [fetchContacts, fetchStats]);

  const handleReply = async () => {
    if (!replyTarget || !replyText.trim()) {
      message.warning('请输入回复内容');
      return;
    }
    setReplyLoading(true);
    try {
      const r = await authFetch(`/api/v1/admin/help/contacts/${replyTarget.id}/reply`, {
        method: 'POST',
        body: JSON.stringify({ reply: replyText.trim() }),
      });
      if (!r.ok) {
        const d = await r.json();
        message.error(d.detail || '回复失败');
        return;
      }
      message.success('回复成功');
      setReplyModalOpen(false);
      setReplyText('');
      setReplyTarget(null);
      fetchContacts();
      fetchStats();
    } catch {
      message.error('回复失败');
    } finally {
      setReplyLoading(false);
    }
  };

  const openReply = (item: ContactItem) => {
    setReplyTarget(item);
    setReplyText(item.reply || '');
    setReplyModalOpen(true);
  };

  const openDetail = (item: ContactItem) => {
    setDetailTarget(item);
    setDetailModalOpen(true);
  };

  const columns = [
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      width: 90,
      render: (type: number) => {
        const cfg = typeConfig[type] || typeConfig[5];
        return <Tag color={cfg.color}>{cfg.label}</Tag>;
      },
    },
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
      render: (title: string, record: ContactItem) => (
        <a onClick={() => openDetail(record)} style={{ cursor: 'pointer' }}>
          {title}
        </a>
      ),
    },
    {
      title: '联系方式',
      dataIndex: 'contact',
      key: 'contact',
      width: 130,
      render: (v: string) => v || '-',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (status: number) => {
        const cfg = statusConfig[status] || statusConfig[0];
        return <Tag color={cfg.color} icon={cfg.icon}>{cfg.label}</Tag>;
      },
    },
    {
      title: '提交时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 130,
      render: (v: string) => fmtDate(v),
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_: any, record: ContactItem) => (
        <Button
          type="link"
          size="small"
          icon={<MessageOutlined />}
          onClick={() => openReply(record)}
        >
          {record.status === 2 || record.status === 3 ? '查看回复' : '回复'}
        </Button>
      ),
    },
  ];

  return (
    <>
      {/* 统计卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={12} sm={12}>
          <Card size="small" hoverable>
            <Statistic
              title="全部反馈"
              value={stats.total || total}
              prefix={<MessageOutlined />}
              valueStyle={{ fontSize: 22 }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={12}>
          <Card size="small" hoverable>
            <Statistic
              title="待处理"
              value={stats.pending || 0}
              valueStyle={{ fontSize: 22, color: (stats.pending || 0) > 0 ? '#faad14' : undefined }}
              prefix={<Badge count={(stats.pending || 0) > 0 ? stats.pending : 0} size="small" />}
            />
          </Card>
        </Col>
      </Row>

      {/* 列表 */}
      <Card
        title="用户反馈列表"
        size="small"
        extra={
          <Space>
            <Select
              allowClear
              placeholder="筛选状态"
              style={{ width: 120 }}
              value={statusFilter}
              onChange={(val) => {
                setStatusFilter(val);
                setPage(1);
              }}
              options={[
                { label: '待处理', value: 0 },
                { label: '处理中', value: 1 },
                { label: '已解决', value: 2 },
                { label: '已关闭', value: 3 },
              ]}
            />
            <Button
              icon={<ReloadOutlined />}
              onClick={() => { fetchContacts(); fetchStats(); }}
              loading={loading}
            >
              刷新
            </Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={items}
          rowKey="id"
          loading={loading}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            showTotal: (t) => `共 ${t} 条`,
            onChange: (p, ps) => { setPage(p); setPageSize(ps); },
          }}
          locale={{ emptyText: <Empty description="暂无用户反馈" /> }}
          size="small"
        />
      </Card>

      {/* 回复弹窗 */}
      <Modal
        title={`回复反馈：${replyTarget?.title || ''}`}
        open={replyModalOpen}
        onCancel={() => { setReplyModalOpen(false); setReplyTarget(null); setReplyText(''); }}
        onOk={handleReply}
        confirmLoading={replyLoading}
        okText="回复并标记已解决"
        width={600}
      >
        {replyTarget && (
          <div style={{ marginBottom: 16 }}>
            <Tag color={typeConfig[replyTarget.type]?.color}>
              {replyTarget.type_label}
            </Tag>
            <Text strong>{replyTarget.title}</Text>
            <Paragraph
              style={{
                marginTop: 8,
                padding: 8,
                background: '#f5f5f5',
                borderRadius: 4,
                whiteSpace: 'pre-wrap',
              }}
              copyable
            >
              {replyTarget.content}
            </Paragraph>
            {replyTarget.contact && (
              <Text type="secondary" style={{ fontSize: 12 }}>
                联系方式：{replyTarget.contact}
              </Text>
            )}
          </div>
        )}
        <div style={{ marginTop: 8 }}>
          <Text strong>管理员回复：</Text>
          <TextArea
            rows={4}
            value={replyText}
            onChange={(e) => setReplyText(e.target.value)}
            placeholder="在此输入回复内容..."
            style={{ marginTop: 4 }}
          />
        </div>
      </Modal>

      {/* 详情弹窗 */}
      <Modal
        title="反馈详情"
        open={detailModalOpen}
        onCancel={() => { setDetailModalOpen(false); setDetailTarget(null); }}
        footer={<Button onClick={() => { setDetailModalOpen(false); }}>关闭</Button>}
        width={600}
      >
        {detailTarget && (
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="类型">
              <Tag color={typeConfig[detailTarget.type]?.color}>
                {detailTarget.type_label}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="标题">{detailTarget.title}</Descriptions.Item>
            <Descriptions.Item label="详细描述">
              <Paragraph style={{ whiteSpace: 'pre-wrap', margin: 0 }}>
                {detailTarget.content}
              </Paragraph>
            </Descriptions.Item>
            <Descriptions.Item label="联系方式">{detailTarget.contact || '-'}</Descriptions.Item>
            <Descriptions.Item label="提交时间">
              {fmtDate(detailTarget.created_at, true)}
            </Descriptions.Item>
            <Descriptions.Item label="状态">
              <Tag color={statusConfig[detailTarget.status]?.color}>
                {detailTarget.status_label}
              </Tag>
            </Descriptions.Item>
            {detailTarget.reply && (
              <>
                <Descriptions.Item label="管理员回复">{detailTarget.reply}</Descriptions.Item>
                <Descriptions.Item label="回复人">{detailTarget.replied_by || '-'}</Descriptions.Item>
                <Descriptions.Item label="回复时间">
                  {fmtDate(detailTarget.replied_at, true)}
                </Descriptions.Item>
              </>
            )}
          </Descriptions>
        )}
      </Modal>
    </>
  );
};

export default ContactsTab;
