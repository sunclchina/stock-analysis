import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Table,
  Button,
  Tag,
  Space,
  Modal,
  Form,
  Input,
  Select,
  message,
  Typography,
  Empty,
  Tabs,
  Tooltip,
  Popconfirm,
  Divider,
  InputNumber,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  StarOutlined,
  ExportOutlined,
  ImportOutlined,
  FileTextOutlined,
  ReloadOutlined,
  SearchOutlined,
} from '@ant-design/icons';
import { authFetch } from '../../services/auth';
import type { ColumnsType } from 'antd/es/table';
import * as configApi from '../../services/configApi';
import type { Template } from '../../types';

const { Text, Paragraph } = Typography;
const { TextArea } = Input;

const templateTypeConfig: Record<string, { color: string; label: string }> = {
  selection: { color: 'blue', label: '选股模板' },
  premarket: { color: 'purple', label: '盘前提示模板' },
  analysis: { color: 'cyan', label: '智能分析模板' },
};

interface TemplateItem {
  id: string;
  name: string;
  type: string;
  filename: string;
  size: number;
  is_default: boolean;
  defaults_for?: string[];
  modified: string;
}

const TemplateTab: React.FC = () => {
  const [templates, setTemplates] = useState<TemplateItem[]>([]);
  const [activeType, setActiveType] = useState<string>('selection');
  const [modalOpen, setModalOpen] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewContent, setPreviewContent] = useState('');
  const [previewTitle, setPreviewTitle] = useState('');
  const [editingName, setEditingName] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();

  const loadTemplates = useCallback(async () => {
    setLoading(true);
    try {
      const res: any = await configApi.fetchTemplates();
      const list = res.templates ?? [];
      setTemplates(list);
    } catch {
      message.error('加载模板列表失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTemplates();
  }, [loadTemplates]);

  const filteredTemplates = templates.filter((t) => t.type === activeType);

  const handleCreate = () => {
    setEditingName(null);
    form.resetFields();
    form.setFieldsValue({ type: activeType });
    setModalOpen(true);
  };

  const handleEdit = async (item: TemplateItem) => {
    setEditingName(item.filename);
    form.setFieldsValue({ name: item.name, type: item.type, content: '' });
    // Load current content
    try {
      const res: any = await configApi.fetchTemplateContent(item.filename);
      form.setFieldsValue({ content: res.content || '' });
    } catch {
      // ignore
    }
    setModalOpen(true);
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      const filename = editingName || `${values.name}.md`;
      await configApi.saveTemplate({ name: filename, content: values.content, overwrite: true });
      message.success(`模板 ${filename} 已保存`);
      setModalOpen(false);
      loadTemplates();
    } catch (err: any) {
      if (err?.response?.data?.detail) message.error(err.response.data.detail);
    }
  };

  const handleDelete = async (item: TemplateItem) => {
    if (item.is_default) {
      message.warning('默认模板不可删除');
      return;
    }
    try {
      await configApi.deleteTemplate(item.filename);
      message.success(`模板 ${item.name} 已删除`);
      loadTemplates();
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '删除失败');
    }
  };

  // 根据模板文件名推断用途类型
  const inferTemplateType = (filename: string): string => {
    const lower = filename.toLowerCase();
    if (lower.includes('复盘') || lower.includes('review') || lower.includes('daily')) return 'review';
    if (lower.includes('批量') || lower.includes('batch')) return 'batch';
    if (lower.includes('个股') || lower.includes('stock')) return 'stock';
    if (lower.includes('选股') || lower.includes('selection')) return 'selection';
    if (lower.includes('盘前') || lower.includes('premarket')) return 'premarket';
    return '';
  };

  const handleSetDefault = async (item: TemplateItem) => {
    const ttype = inferTemplateType(item.filename);
    const typeLabel = {
      review: '复盘分析', batch: '批量分析', stock: '个股分析',
      premarket: '盘前提示', selection: '选股',
    }[ttype] || '全局';
    try {
      await configApi.setDefaultTemplate(item.filename, ttype);
      message.success(`模板 ${item.name} 已设为${typeLabel}默认`);
      await loadTemplates();
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '设置默认失败');
    }
  };

  const handlePreview = async (item: TemplateItem) => {
    setPreviewTitle(item.name);
    setPreviewContent('加载中...');
    setPreviewOpen(true);
    try {
      const res: any = await configApi.fetchTemplateContent(item.filename);
      setPreviewContent(res.content || '(空)');
    } catch {
      setPreviewContent('加载失败');
    }
  };

  const handleExport = async (item: TemplateItem) => {
    try {
      const blob = await configApi.exportTemplate(item.filename);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = item.filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      message.error('导出失败');
    }
  };

  
  const typeDefaultLabels: Record<string, string> = {
    review: '复盘默认', batch: '批量默认', stock: '个股默认',
    premarket: '盘前默认', selection: '选股默认',
  };

  const columns: ColumnsType<TemplateItem> = [
    {
      title: '模板名称', dataIndex: 'name', key: 'name',
      render: (name: string, record: TemplateItem) => {
        const badges: React.ReactNode[] = [];
        if (record.is_default) {
          badges.push(<Tag color="gold" key="global">默认</Tag>);
        }
        const defaultsFor = (record as any).defaults_for || [];
        defaultsFor.forEach((t: string) => {
          const label = typeDefaultLabels[t] || t;
          badges.push(<Tag color="orange" key={t}>{label}</Tag>);
        });
        return (
          <Space>
            <FileTextOutlined />
            <Text strong>{name}</Text>
            {badges}
          </Space>
        );
      },
    },
    {
      title: '类型', dataIndex: 'type', key: 'type', width: 120,
      render: (t: string) => {
        const cfg = templateTypeConfig[t];
        return <Tag color={cfg?.color}>{cfg?.label || t}</Tag>;
      },
    },
    {
      title: '大小', dataIndex: 'size', key: 'size', width: 80,
      render: (s: number) => `${(s / 1024).toFixed(1)}KB`,
    },
    {
      title: '修改时间', dataIndex: 'modified', key: 'modified', width: 170,
      render: (d: string) => new Date(d).toLocaleString('zh-CN'),
    },
    {
      title: '操作', key: 'action', width: 280,
      render: (_, record) => (
        <Space size="small" wrap>
          <Tooltip title="预览"><Button size="small" icon={<EyeOutlined />} onClick={() => handlePreview(record)} /></Tooltip>
          <Tooltip title="编辑"><Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)} /></Tooltip>
          <Tooltip title="设为默认"><Button size="small" icon={<StarOutlined />} onClick={() => handleSetDefault(record)} /></Tooltip>
          {(record as any).defaults_for?.length > 0 && (
            <Tag color="orange">{(record as any).defaults_for.map((t: string) => typeDefaultLabels[t] || t).join(' / ')}</Tag>
          )}
          {!record.is_default && (record as any).defaults_for?.length === 0 ? (
            <Popconfirm title="确认删除此模板？" onConfirm={() => handleDelete(record)} okText="删除" cancelText="取消">
              <Tooltip title="删除"><Button size="small" danger icon={<DeleteOutlined />} /></Tooltip>
            </Popconfirm>
          ) : (
            record.is_default && <Tag color="gold">全局默认</Tag>
          )}
          <Tooltip title="导出"><Button size="small" icon={<ExportOutlined />} onClick={() => handleExport(record)} /></Tooltip>
        </Space>
      ),
    },
  ];

  // Import handler
  const fileInputRef = React.useRef<HTMLInputElement>(null);
  const handleImportClick = () => fileInputRef.current?.click();
  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const content = await file.text();
    try {
      await configApi.saveTemplate({ name: file.name, content, overwrite: true });
      message.success(`模板 ${file.name} 已导入`);
      loadTemplates();
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '导入失败');
    }
    e.target.value = '';
  };

  return (
    <>
    <Card
      title={<Space><FileTextOutlined />模板管理</Space>}
      extra={
        <Space wrap>
          <input ref={fileInputRef} type="file" accept=".md,.txt,.json" style={{ display: 'none' }} onChange={handleFileChange} />
          <Button size="small" icon={<ReloadOutlined />} onClick={loadTemplates} loading={loading}>刷新</Button>
          <Button size="small" icon={<ImportOutlined />} onClick={handleImportClick}>导入模板</Button>
          <Button size="small" type="primary" icon={<PlusOutlined />} onClick={handleCreate}>新建模板</Button>
        </Space>
      }
    >
      <Tabs
        activeKey={activeType}
        onChange={(key) => setActiveType(key)}
        items={[
          { key: 'selection', label: '📊 选股模板' },
          { key: 'premarket', label: '🌅 盘前提示模板' },
          { key: 'analysis', label: '📋 智能分析模板' },
        ]}
      />

      {filteredTemplates.length === 0 ? (
        <Empty description="暂无模板，请导入或新建" />
      ) : (
        <div style={{ overflowX: 'auto', width: '100%' }}>
        <Table<TemplateItem>
          columns={columns}
          dataSource={filteredTemplates}
          rowKey="id"
          size="small"
          loading={loading}
          pagination={false}
          scroll={{ x: 'max-content' }}
        />
        </div>
      )}

      {/* 新建/编辑弹窗 */}
      <Modal
        title={editingName ? '编辑模板' : '新建模板'}
        open={modalOpen}
        onOk={handleSave}
        onCancel={() => setModalOpen(false)}
        okText="保存"
        cancelText="取消"
        width={720}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="type" label="模板类型">
            <Select disabled={!!editingName}
              options={[
                { label: '选股模板', value: 'selection' },
                { label: '盘前提示模板', value: 'premarket' },
                { label: '智能分析模板', value: 'analysis' },
              ]}
            />
          </Form.Item>
          <Form.Item name="name" label="模板名称" rules={[{ required: true }]}>
            <Input placeholder="如：我的盘前模板" disabled={!!editingName} />
          </Form.Item>
          <Form.Item name="content" label="模板内容" rules={[{ required: true }]}>
            <TextArea rows={16} placeholder="输入 Markdown 格式的模板内容..." />
          </Form.Item>
        </Form>
      </Modal>

      {/* 预览弹窗 */}
      <Modal
        title={previewTitle}
        open={previewOpen}
        onCancel={() => setPreviewOpen(false)}
        footer={<Button onClick={() => setPreviewOpen(false)}>关闭</Button>}
        width={720}
      >
        <div style={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: 13, lineHeight: 1.6, maxHeight: 500, overflow: 'auto' }}>
          {previewContent}
        </div>
      </Modal>
    </Card>

      <Divider />

      <Card title="📚 帮助文档管理" size="small" style={{ borderRadius: 8 }}>
        <HelpDocManager />
      </Card>
    </>
  );
};

const HelpDocManager: React.FC = () => {
  const [docs, setDocs] = useState<any[]>([]);
  const [categories, setCategories] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editDoc, setEditDoc] = useState<any | null>(null);
  const [form] = Form.useForm();
  const [searchText, setSearchText] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [d, c] = await Promise.all([
        fetch('/api/v1/help/documents?page_size=100').then(r => r.json()),
        fetch('/api/v1/help/categories').then(r => r.json()),
      ]);
      setDocs(d.items || []);
      setCategories(c.items || []);
    } catch {}
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleSave = async () => {
    try {
      const vals = await form.validateFields();
      const url = editDoc ? `/api/v1/admin/help/documents/${editDoc.id}` : '/api/v1/admin/help/documents';
      const method = editDoc ? 'PUT' : 'POST';
      await authFetch(url, { method, body: JSON.stringify(vals) });
      message.success(editDoc ? '文档已更新' : '文档已创建');
      setModalOpen(false); setEditDoc(null); form.resetFields(); load();
    } catch { message.error('保存失败'); }
  };

  const handleDelete = async (id: number) => {
    try {
      await authFetch(`/api/v1/admin/help/documents/${id}`, { method: 'DELETE' });
      message.success('文档已删除');
      load();
    } catch { message.error('删除失败'); }
  };

  const filtered = docs.filter((d: any) =>
    !searchText || d.title?.includes(searchText) || (d.tags || '').includes(searchText)
  );
  const catMap: Record<number, string> = {};
  categories.forEach((c: any) => { catMap[c.id] = c.name; });

  const columns: any = [
    { title: '标题', dataIndex: 'title', key: 't', width: 200, render: (t: string) => <Text strong>{t}</Text> },
    { title: '分类', dataIndex: 'category_id', key: 'c', width: 80, render: (v: number) => <Tag>{catMap[v] || '-'}</Tag> },
    { title: 'slug', dataIndex: 'slug', key: 's', width: 130, ellipsis: true },
    { title: '状态', dataIndex: 'status', key: 'st', width: 60, render: (v: number) => v === 1 ? <Tag color="blue">发布</Tag> : <Tag>草稿</Tag> },
    { title: '浏览', dataIndex: 'view_count', key: 'vc', width: 50 },
    { title: '更新时间', dataIndex: 'updated_at', key: 'u', width: 100, render: (v: string) => String(v || '').slice(0, 10) },
    { title: '操作', key: 'action', width: 120, render: (_: any, r: any) => (
      <Space size="small">
        <Button size="small" onClick={() => { setEditDoc(r); form.setFieldsValue(r); setModalOpen(true); }}>编辑</Button>
        <Popconfirm title="确认删除？" onConfirm={() => handleDelete(r.id)}>
          <Button size="small" danger>删除</Button>
        </Popconfirm>
      </Space>
    )},
  ];

  return (
    <div>
      <div style={{ marginBottom: 12, display: 'flex', flexWrap: 'wrap', gap: 8, justifyContent: 'space-between', alignItems: 'center' }}>
        <Input placeholder="搜索文档..." value={searchText} onChange={e => setSearchText(e.target.value)}
          style={{ width: 280, maxWidth: '100%' }} prefix={<SearchOutlined />} />
        <Space wrap>
          <Button size="small" onClick={load} icon={<ReloadOutlined />}>刷新</Button>
          <Button type="primary" size="small" icon={<PlusOutlined />}
            onClick={() => { setEditDoc(null); form.resetFields(); setModalOpen(true); }}>新建文档</Button>
        </Space>
      </div>
      <div style={{ overflowX: 'auto', width: '100%' }}>
      <Table dataSource={filtered} columns={columns} rowKey="id" size="small" loading={loading} pagination={{ pageSize: 10 }} scroll={{ x: 'max-content' }} />
      </div>
      <Modal title={editDoc ? '编辑文档' : '新建文档'} open={modalOpen} onCancel={() => { setModalOpen(false); setEditDoc(null); }}
        onOk={handleSave} width={700} destroyOnClose>
        <Form form={form} layout="vertical" size="small">
          <Form.Item name="title" label="标题" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="slug" label="URL标识" rules={[{ required: true }]}><Input placeholder="英文标识" /></Form.Item>
          <Form.Item name="category_id" label="分类" rules={[{ required: true }]}>
            <Select options={categories.map((c: any) => ({ label: `${c.icon} ${c.name}`, value: c.id }))} />
          </Form.Item>
          <Form.Item name="summary" label="摘要"><Input.TextArea rows={2} /></Form.Item>
          <Form.Item name="content" label="正文 (Markdown)" rules={[{ required: true }]}><Input.TextArea rows={8} /></Form.Item>
          <Form.Item name="tags" label="标签（逗号分隔）"><Input placeholder="选股,策略,指标" /></Form.Item>
          <Form.Item name="read_time" label="阅读时间（分钟）"><InputNumber min={1} style={{ width: 120 }} /></Form.Item>
          <Form.Item name="status" label="状态">
            <Select options={[{ label: '发布', value: 1 }, { label: '草稿', value: 0 }]} style={{ width: 120 }} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default TemplateTab;
