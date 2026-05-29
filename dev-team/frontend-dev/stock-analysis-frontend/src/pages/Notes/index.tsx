/**
 * 操盘笔记页面
 * - 列表展示：置顶 + 时间倒序
 * - 新建/编辑/删除
 * - 标签筛选 + 关键词搜索
 * - 关联股票显示
 */
import React, { useEffect, useState, useCallback } from 'react';
import {
  Card, Table, Button, Space, Tag, Typography, Modal, Drawer, Form, Input,
  Popconfirm, message, Empty, Tooltip, Badge, Divider,
} from 'antd';
import {
  PlusOutlined, EditOutlined, DeleteOutlined, PushpinOutlined,
  PushpinFilled, SearchOutlined, FileTextOutlined, FundOutlined,
  ReloadOutlined, TagOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import {
  listNotes, createNote, updateNote, deleteNote,
  type TradingNote, type NoteCreatePayload, type NoteUpdatePayload,
} from '../../services/noteApi';

const { Text, Paragraph } = Typography;
const { TextArea } = Input;

// ─── 标签颜色映射 ───

const TAG_COLORS: Record<string, string> = {
  '建仓': 'green',
  '加仓': 'blue',
  '减仓': 'orange',
  '清仓': 'red',
  '预警': 'volcano',
  '复盘': 'purple',
  '大盘': 'geekblue',
  '策略': 'cyan',
  '观察': 'lime',
  '操作': 'gold',
};

function tagColor(tag: string): string {
  for (const [k, v] of Object.entries(TAG_COLORS)) {
    if (tag.includes(k)) return v;
  }
  return 'default';
}

// ─── 主页面 ───

const NotesPage: React.FC = () => {
  const [notes, setNotes] = useState<TradingNote[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingNote, setEditingNote] = useState<TradingNote | null>(null);
  const [keyword, setKeyword] = useState('');
  const [page, setPage] = useState(1);
  const [submitting, setSubmitting] = useState(false);
  const [detailNote, setDetailNote] = useState<TradingNote | null>(null);

  const [form] = Form.useForm();

  const fetchNotes = useCallback(async () => {
    setLoading(true);
    try {
      const res = await listNotes({ keyword: keyword || undefined, page, page_size: 20 });
      setNotes(res.notes);
      setTotal(res.total);
    } catch (e: any) {
      message.error('加载笔记失败: ' + (e?.message || ''));
    }
    setLoading(false);
  }, [keyword, page]);

  useEffect(() => { fetchNotes(); }, [fetchNotes]);

  // 新建
  const handleAdd = () => {
    setEditingNote(null);
    form.resetFields();
    setModalOpen(true);
  };

  // 编辑
  const handleEdit = (note: TradingNote) => {
    setEditingNote(note);
    setModalOpen(true);
  };

  // 保存
  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);
      if (editingNote) {
        const payload: NoteUpdatePayload = {};
        if (values.title !== editingNote.title) payload.title = values.title;
        if (values.content !== editingNote.content) payload.content = values.content;
        if (values.stock_code !== editingNote.stock_code) payload.stock_code = values.stock_code;
        if (values.stock_name !== editingNote.stock_name) payload.stock_name = values.stock_name;
        if (values.tags !== editingNote.tags) payload.tags = values.tags;
        await updateNote(editingNote.id, payload);
        message.success('笔记已更新');
      } else {
        await createNote(values as NoteCreatePayload);
        message.success('笔记已创建');
      }
      setModalOpen(false);
      fetchNotes();
    } catch (e: any) {
      if (e?.errorFields) return; // 表单校验失败
      message.error('保存失败: ' + (e?.message || ''));
    }
    setSubmitting(false);
  };

  // 删除
  const handleDelete = async (id: number) => {
    try {
      await deleteNote(id);
      message.success('笔记已删除');
      fetchNotes();
    } catch (e: any) {
      message.error('删除失败: ' + (e?.message || ''));
    }
  };

  // 置顶/取消置顶
  const handleTogglePin = async (note: TradingNote) => {
    try {
      await updateNote(note.id, { is_pinned: !note.is_pinned });
      message.success(note.is_pinned ? '已取消置顶' : '已置顶');
      fetchNotes();
    } catch (e: any) {
      message.error('操作失败: ' + (e?.message || ''));
    }
  };

  const columns: ColumnsType<TradingNote> = [
    {
      title: '标题', dataIndex: 'title', key: 'title', width: 200, ellipsis: true,
      render: (v: string, r: TradingNote) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: 4, maxWidth: '100%', overflow: 'hidden' }}>
          {r.is_pinned && <PushpinFilled style={{ color: '#faad14', fontSize: 14, flexShrink: 0 }} />}
          <Button type="link" style={{ padding: 0, height: 'auto', fontWeight: 600, fontSize: 14, textAlign: 'left', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '100%' }}
            onClick={() => setDetailNote(r)} title={v}>
            {v}
          </Button>
        </div>
      ),
    },
    {
      title: '内容', dataIndex: 'content', key: 'content',
      ellipsis: true,
      render: (v: string) => (
        <Paragraph ellipsis={{ rows: 1 }} style={{ margin: 0, color: '#666' }}>
          {v || '(空)'}
        </Paragraph>
      ),
    },
    {
      title: '关联股票', key: 'stock', width: 130,
      render: (_: any, r: TradingNote) => (
        r.stock_code ? (
          <Tag icon={<FundOutlined />} color="blue">
            {r.stock_code} {r.stock_name}
          </Tag>
        ) : <Text type="secondary">—</Text>
      ),
    },
    {
      title: '标签', dataIndex: 'tags', key: 'tags', width: 180,
      render: (v: string) => {
        if (!v) return <Text type="secondary">—</Text>;
        return (
          <Space size={4} wrap>
            {v.split(',').filter(Boolean).map((t: string) => (
              <Tag key={t} color={tagColor(t.trim())} style={{ margin: 0 }}>
                {t.trim()}
              </Tag>
            ))}
          </Space>
        );
      },
    },
    {
      title: '更新时间', dataIndex: 'updated_at', key: 'updated_at', width: 150,
      render: (v: string) => <Text type="secondary" style={{ fontSize: 12 }}>{v}</Text>,
    },
    {
      title: '操作', key: 'action', width: 140, fixed: 'right',
      render: (_: any, r: TradingNote) => (
        <Space>
          <Tooltip title={r.is_pinned ? '取消置顶' : '置顶'}>
            <Button type="text" size="small" icon={r.is_pinned ? <PushpinFilled style={{ color: '#faad14' }} /> : <PushpinOutlined />}
              onClick={() => handleTogglePin(r)} />
          </Tooltip>
          <Tooltip title="编辑">
            <Button type="text" size="small" icon={<EditOutlined />} onClick={() => handleEdit(r)} />
          </Tooltip>
          <Popconfirm title="确定删除这篇笔记？" onConfirm={() => handleDelete(r.id)} okText="删除" cancelText="取消">
            <Tooltip title="删除">
              <Button type="text" size="small" danger icon={<DeleteOutlined />} />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: 16, height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* 顶部操作栏 */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: 12, flexShrink: 0,
      }}>
        <Space size={16}>
          <span style={{ fontSize: 18, fontWeight: 700 }}>
            <FileTextOutlined style={{ marginRight: 8, color: '#165DFF' }} />
            操盘笔记
          </span>
          <Badge count={total} showZero style={{ backgroundColor: '#165DFF' }} />
        </Space>
        <Space>
          <Input.Search
            placeholder="搜索笔记..."
            allowClear
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            onSearch={() => { setPage(1); fetchNotes(); }}
            style={{ width: 240 }}
            prefix={<SearchOutlined />}
          />
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
            新建笔记
          </Button>
          <Button icon={<ReloadOutlined />} onClick={fetchNotes} loading={loading} />
        </Space>
      </div>

      {/* 笔记列表 */}
      <Card style={{ flex: 1, overflow: 'auto', borderRadius: 8 }} bodyStyle={{ padding: 0 }}>
        <Table<TradingNote>
          columns={columns}
          dataSource={notes}
          rowKey="id"
          loading={loading}
          pagination={{
            current: page,
            pageSize: 20,
            total,
            onChange: (p) => setPage(p),
            showTotal: (t) => `共 ${t} 条`,
            size: 'small',
          }}
          scroll={{ x: 900, y: 'calc(100vh - 280px)' }}
          locale={{ emptyText: <Empty description="暂无操盘笔记，点击右上角新建" /> }}
          size="middle"
        />
      </Card>

      {/* 新建/编辑弹窗 */}
      <Modal
        title={
          <Space>
            <FileTextOutlined style={{ color: '#165DFF' }} />
            {editingNote ? '编辑笔记' : '新建笔记'}
          </Space>
        }
        open={modalOpen}
        onOk={handleSave}
        onCancel={() => setModalOpen(false)}
        confirmLoading={submitting}
        okText={editingNote ? '保存' : '创建'}
        cancelText="取消"
        width={640}
        destroyOnClose
        key={editingNote?.id ?? 'new'}
        afterOpenChange={(open) => {
          if (open) {
            if (editingNote) {
              form.setFieldsValue({
                title: editingNote.title,
                content: editingNote.content,
                stock_code: editingNote.stock_code,
                stock_name: editingNote.stock_name,
                tags: editingNote.tags,
              });
            } else {
              form.resetFields();
            }
          } else {
            setEditingNote(null);
          }
        }}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="title" label="标题" rules={[{ required: true, message: '请输入笔记标题' }]}>
            <Input placeholder="输入笔记标题" maxLength={128} />
          </Form.Item>
          <Form.Item name="content" label="正文">
            <TextArea rows={6} placeholder="记录你的操盘思考、观察要点..." />
          </Form.Item>
          <Space style={{ width: '100%' }} size={16}>
            <Form.Item name="stock_code" label="股票代码" style={{ width: 140 }}>
              <Input placeholder="如 600519" maxLength={10} />
            </Form.Item>
            <Form.Item name="stock_name" label="股票名称" style={{ width: 160 }}>
              <Input placeholder="如 贵州茅台" maxLength={32} />
            </Form.Item>
            <Form.Item name="tags" label="标签" style={{ flex: 1 }}>
              <Input placeholder="逗号分隔，如 建仓,白酒" maxLength={256} />
            </Form.Item>
          </Space>
        </Form>
      </Modal>

      {/* 详情抽屉 */}
      <Drawer
        title={
          <Space>
            <FileTextOutlined style={{ color: '#165DFF' }} />
            <span>{detailNote?.title || '笔记详情'}</span>
            {detailNote?.is_pinned && <PushpinFilled style={{ color: '#faad14', fontSize: 14 }} />}
          </Space>
        }
        placement="right"
        width={560}
        open={!!detailNote}
        onClose={() => setDetailNote(null)}
        extra={
          <Space>
            {detailNote && (
              <>
                <Tooltip title={detailNote.is_pinned ? '取消置顶' : '置顶'}>
                  <Button size="small" icon={detailNote.is_pinned ? <PushpinFilled style={{ color: '#faad14' }} /> : <PushpinOutlined />}
                    onClick={() => { handleTogglePin(detailNote); setDetailNote(null); }} />
                </Tooltip>
                <Tooltip title="编辑">
                  <Button size="small" icon={<EditOutlined />}
                    onClick={() => { setDetailNote(null); handleEdit(detailNote); }} />
                </Tooltip>
                <Popconfirm title="确定删除这篇笔记？" onConfirm={() => { handleDelete(detailNote!.id); setDetailNote(null); }} okText="删除" cancelText="取消">
                  <Tooltip title="删除">
                    <Button size="small" danger icon={<DeleteOutlined />} />
                  </Tooltip>
                </Popconfirm>
              </>
            )}
          </Space>
        }
      >
        {detailNote && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {/* 元信息 */}
            <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap', fontSize: 13, color: '#888' }}>
              {detailNote.stock_code && (
                <Tag icon={<FundOutlined />} color="blue">
                  {detailNote.stock_code} {detailNote.stock_name}
                </Tag>
              )}
              {detailNote.tags && detailNote.tags.split(',').filter(Boolean).map((t: string) => (
                <Tag key={t} color={tagColor(t.trim())}>{t.trim()}</Tag>
              ))}
            </div>

            <Divider style={{ margin: '4px 0' }} />

            {/* 正文 */}
            <div style={{
              fontSize: 14,
              lineHeight: 1.8,
              whiteSpace: 'pre-wrap',
              color: 'var(--content-text, #333)',
              padding: '8px 0',
            }}>
              {detailNote.content || <Text type="secondary">（无正文内容）</Text>}
            </div>

            <Divider style={{ margin: '4px 0' }} />

            {/* 时间 */}
            <div style={{ fontSize: 12, color: '#aaa', display: 'flex', justifyContent: 'space-between' }}>
              <span>创建时间：{detailNote.created_at}</span>
              <span>更新时间：{detailNote.updated_at}</span>
            </div>
          </div>
        )}
      </Drawer>
    </div>
  );
};

export default NotesPage;
