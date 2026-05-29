/**
 * 帮助中心抽屉组件
 * 替代新标签页打开，以 Drawer 形式浮在主页面上
 */
import React, { useState, useEffect, useCallback } from 'react';
import { Drawer, Input, Typography, Space, Tag, Button, Spin, Row, Col, Divider, Form, Select, Empty, message, Card } from 'antd';
import {
  SearchOutlined, LikeOutlined, DislikeOutlined, SendOutlined,
  ClockCircleOutlined, EyeOutlined, FileTextOutlined, CloseOutlined,
} from '@ant-design/icons';
import { authFetch } from '../services/auth';

const { Text, Title } = Typography;
const { TextArea } = Input;
const API = '/api/v1/help';

interface HelpDrawerProps {
  open: boolean;
  onClose: () => void;
  initialSlug?: string;
}

const HelpDrawer: React.FC<HelpDrawerProps> = ({ open, onClose, initialSlug }) => {
  const [categories, setCategories] = useState<any[]>([]);
  const [documents, setDocuments] = useState<any[]>([]);
  const [selectedCat, setSelectedCat] = useState<number | null>(null);
  const [currentDoc, setCurrentDoc] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[] | null>(null);
  const [contactForm] = Form.useForm();

  useEffect(() => {
    if (!open) return;
    fetch(`${API}/categories`).then(r => r.json()).then(d => {
      const items = d.items || d || [];
      setCategories(items);
      if (items.length > 0) {
        setSelectedCat(items[0].id);
        setCurrentDoc(null);
        setSearchResults(null);
      }
      // 如果 initialSlug 有值，自动打开对应文档
      if (initialSlug && items.length > 0) {
        loadDocBySlug(initialSlug);
      }
    }).catch(() => {});
  }, [open, initialSlug]);

  useEffect(() => {
    if (!selectedCat) return;
    setLoading(true);
    setCurrentDoc(null);
    fetch(`${API}/documents?category_id=${selectedCat}&status=1`).then(r => r.json())
      .then(d => setDocuments(d.items || []))
      .catch(() => setDocuments([]))
      .finally(() => setLoading(false));
  }, [selectedCat]);

  const handleSearch = async () => {
    if (!searchQuery.trim()) { setSearchResults(null); return; }
    setLoading(true);
    try {
      const r = await fetch(`${API}/search?q=${encodeURIComponent(searchQuery)}`);
      const d = await r.json();
      setSearchResults(d.items || []);
    } catch { setSearchResults([]); }
    finally { setLoading(false); }
  };

  const loadDocBySlug = async (slug: string) => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/documents/slug/${slug}`);
      if (!r.ok) { setLoading(false); return; }
      const doc = await r.json();
      setCurrentDoc(doc);
      setSelectedCat(doc.category_id);
    } catch { message.error('加载文档失败'); }
    finally { setLoading(false); }
  };

  const handleDocClick = async (doc: any) => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/documents/${doc.id}`);
      setCurrentDoc(await r.json());
    } catch { message.error('加载文档失败'); }
    finally { setLoading(false); }
  };

  const handleFeedback = async (type: number) => {
    if (!currentDoc) return;
    try {
      await authFetch(`${API}/feedback`, {
        method: 'POST',
        body: JSON.stringify({ document_id: currentDoc.id, feedback_type: type }),
      });
      message.success('感谢您的反馈！');
    } catch { message.error('提交失败'); }
  };

  const isContactCat = categories.find(c => c.id === selectedCat)?.name === '联系我们';
  const displayDocs = searchResults !== null ? searchResults : documents;

  const catNames = Object.fromEntries(categories.map(c => [c.id, c.name]));

  return (
    <Drawer
      title={<span style={{ fontSize: 18, fontWeight: 700 }}>❓ 帮助中心</span>}
      placement="right"
      width={780}
      open={open}
      onClose={onClose}
      extra={<Button type="text" icon={<CloseOutlined />} onClick={onClose} />}
      styles={{ body: { padding: 0, display: 'flex', flexDirection: 'column' } }}
    >
      {/* 搜索栏 */}
      <div style={{ padding: '12px 16px', borderBottom: '1px solid #f0f0f0' }}>
        <Input prefix={<SearchOutlined />} placeholder="搜索文档..."
          value={searchQuery} onChange={e => setSearchQuery(e.target.value)}
          onPressEnter={handleSearch}
          style={{ borderRadius: 6 }} />
      </div>

      <div style={{ display: 'flex', flex: 1, overflow: 'auto' }}>
        {/* 左侧分类 */}
        <div style={{ width: 160, flexShrink: 0, borderRight: '1px solid #f0f0f0', padding: '8px 0' }}>
          {categories.map(cat => (
            <div key={cat.id} onClick={() => { setSelectedCat(cat.id); setSearchResults(null); setCurrentDoc(null); }}
              style={{
                padding: '8px 16px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6, fontSize: 13,
                background: selectedCat === cat.id ? '#E8F3FF' : 'transparent',
                color: selectedCat === cat.id ? '#165DFF' : 'inherit',
                fontWeight: selectedCat === cat.id ? 600 : 400,
              }}>
              <span>{cat.icon}</span>
              <span>{cat.name}</span>
            </div>
          ))}
        </div>

        {/* 右侧内容 */}
        <div style={{ flex: 1, padding: 16, overflow: 'auto' }}>
          {currentDoc ? (
            <div>
              <Button type="link" onClick={() => setCurrentDoc(null)} style={{ padding: 0, marginBottom: 8 }}>
                ← 返回列表
              </Button>
              <Tag style={{ marginBottom: 6 }}>{catNames[currentDoc.category_id] || ''}</Tag>
              <Title level={4} style={{ margin: '4px 0' }}>{currentDoc.title}</Title>
              <Space size={12} style={{ marginBottom: 12, fontSize: 12 }}>
                <Text type="secondary"><ClockCircleOutlined /> {currentDoc.read_time || '?'} 分钟</Text>
                <Text type="secondary">更新于 {String(currentDoc.updated_at || '').slice(0, 10)}</Text>
                <Text type="secondary"><EyeOutlined /> {currentDoc.view_count || 0}</Text>
              </Space>
              <Divider style={{ margin: '8px 0' }} />
              <div style={{ fontSize: 14, lineHeight: 1.8, whiteSpace: 'pre-wrap' }}>
                {currentDoc.content || '暂无内容'}
              </div>
              <Divider style={{ margin: '8px 0' }} />
              <Space>
                <Button size="small" icon={<LikeOutlined />} onClick={() => handleFeedback(1)}>有用 ({currentDoc.like_count || 0})</Button>
                <Button size="small" icon={<DislikeOutlined />} onClick={() => handleFeedback(2)}>无用 ({currentDoc.dislike_count || 0})</Button>
              </Space>
            </div>
          ) : isContactCat ? (
            <div>
              <Title level={4}>联系我们</Title>
              <Card size="small" style={{ maxWidth: 500 }}>
                <Form form={contactForm} layout="vertical" size="small" onFinish={async (vals) => {
                  try {
                    await authFetch(`${API}/contact`, { method: 'POST', body: JSON.stringify(vals) });
                    message.success('提交成功！');
                    contactForm.resetFields();
                  } catch { message.error('提交失败'); }
                }}>
                  <Form.Item name="type" label="问题类型" rules={[{ required: true }]}>
                    <Select options={[
                      { label: '功能使用问题', value: 1 }, { label: '系统Bug报告', value: 2 },
                      { label: '功能建议', value: 3 }, { label: '文档问题', value: 4 }, { label: '其他', value: 5 },
                    ]} placeholder="请选择" />
                  </Form.Item>
                  <Form.Item name="title" label="问题标题" rules={[{ required: true }]}><Input placeholder="简要描述" /></Form.Item>
                  <Form.Item name="content" label="问题描述" rules={[{ required: true }]}><TextArea rows={4} placeholder="详细描述..." /></Form.Item>
                  <Form.Item name="contact" label="联系方式"><Input placeholder="邮箱/手机号（选填）" /></Form.Item>
                  <Button type="primary" icon={<SendOutlined />} htmlType="submit">提交反馈</Button>
                </Form>
              </Card>
              <Divider />
              <Text type="secondary">📧 闲适老翁：1398121777@qq.com</Text>
            </div>
          ) : (
            <>
              {searchResults !== null && (
                <div style={{ marginBottom: 12 }}>
                  <Text type="secondary">搜索结果：共 {searchResults.length} 条</Text>
                  <Button type="link" size="small" onClick={() => setSearchResults(null)}>清除</Button>
                </div>
              )}
              {loading ? <Spin style={{ display: 'block', margin: '24px auto' }} /> : (
                displayDocs.length === 0 ? (
                  <Empty description={searchResults !== null ? '未找到相关文档' : '暂无文档'} />
                ) : (
                  <Row gutter={[0, 8]}>
                    {displayDocs.map(doc => (
                      <Col key={doc.id} span={24}>
                        <Card size="small" hoverable onClick={() => handleDocClick(doc)} style={{ borderRadius: 6 }}>
                          <Space direction="vertical" size={2} style={{ width: '100%' }}>
                            <Space>
                              <FileTextOutlined style={{ color: '#165DFF' }} />
                              <Text strong style={{ fontSize: 13 }}>{doc.title}</Text>
                              <Tag style={{ fontSize: 11 }}>{catNames[doc.category_id] || ''}</Tag>
                            </Space>
                            <Text type="secondary" style={{ fontSize: 12 }}>{doc.summary || ''}</Text>
                          </Space>
                        </Card>
                      </Col>
                    ))}
                  </Row>
                )
              )}
            </>
          )}
        </div>
      </div>
    </Drawer>
  );
};

export default HelpDrawer;
