/**
 * 帮助中心独立页面
 * 
 * 不包含左侧导航栏，全宽布局。
 * 路径：/help（新标签页打开）
 */
import React, { useState, useEffect } from 'react';
import { Card, Input, Typography, Space, Tag, Button, Spin, Row, Col, Divider, Form, Select, Empty, message, Alert } from 'antd';
import { useNavigate } from 'react-router-dom';
import {
  ArrowLeftOutlined, SearchOutlined, LikeOutlined, DislikeOutlined,
  SendOutlined, ClockCircleOutlined, EyeOutlined, FileTextOutlined,
} from '@ant-design/icons';
import { authFetch } from '../services/auth';

const { Text, Title } = Typography;
const { TextArea } = Input;
const API = '/api/v1/help';

const HelpPage: React.FC = () => {
  const navigate = useNavigate();
  const [categories, setCategories] = useState<any[]>([]);
  const [documents, setDocuments] = useState<any[]>([]);
  const [selectedCat, setSelectedCat] = useState<number | null>(null);
  const [currentDoc, setCurrentDoc] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[] | null>(null);
  const [contactForm] = Form.useForm();

  // 加载分类
  useEffect(() => {
    fetch(`${API}/categories`).then(r => r.json()).then(d => {
      const items = d.items || d || [];
      setCategories(items);
      if (items.length > 0) setSelectedCat(items[0].id);
    }).catch(() => {});
  }, []);

  // 按分类加载文档
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

  const renderDocDetail = () => {
    if (!currentDoc) return null;
    return (
      <div>
        <Button type="link" icon={<ArrowLeftOutlined />} onClick={() => setCurrentDoc(null)} style={{ marginBottom: 12, padding: 0 }}>
          返回列表
        </Button>
        <Tag style={{ marginBottom: 8 }}>{categories.find(c => c.id === currentDoc.category_id)?.name || ''}</Tag>
        <Title level={3}>{currentDoc.title}</Title>
        <Space style={{ marginBottom: 16 }}>
          <Text type="secondary"><ClockCircleOutlined /> {currentDoc.read_time || '?'} 分钟</Text>
          <Text type="secondary">更新于 {String(currentDoc.updated_at || currentDoc.published_at || '').slice(0, 10)}</Text>
          <Text type="secondary"><EyeOutlined /> {currentDoc.view_count || 0} 次浏览</Text>
        </Space>
        <Divider />
        <div style={{ fontSize: 14, lineHeight: 1.8, whiteSpace: 'pre-wrap' }}>
          {currentDoc.content || '暂无内容'}
        </div>
        <Divider />
        <Space>
          <Button icon={<LikeOutlined />} onClick={() => handleFeedback(1)}>有用 ({currentDoc.like_count || 0})</Button>
          <Button icon={<DislikeOutlined />} onClick={() => handleFeedback(2)}>无用 ({currentDoc.dislike_count || 0})</Button>
        </Space>
      </div>
    );
  };

  const renderContactForm = () => {
    const handleSubmit = async (vals: any) => {
      try {
        await authFetch(`${API}/contact`, { method: 'POST', body: JSON.stringify(vals) });
        message.success('提交成功，我们将尽快回复！');
        contactForm.resetFields();
      } catch { message.error('提交失败'); }
    };
    return (
      <div>
        <Title level={3}>联系我们</Title>
        <Card style={{ maxWidth: 600 }}>
          <Form form={contactForm} layout="vertical" onFinish={handleSubmit}>
            <Form.Item name="type" label="问题类型" rules={[{ required: true }]}>
              <Select options={[
                { label: '功能使用问题', value: 1 }, { label: '系统Bug报告', value: 2 },
                { label: '功能建议', value: 3 }, { label: '文档问题', value: 4 }, { label: '其他', value: 5 },
              ]} placeholder="请选择问题类型" />
            </Form.Item>
            <Form.Item name="title" label="问题标题" rules={[{ required: true }]}>
              <Input placeholder="简要描述您的问题" />
            </Form.Item>
            <Form.Item name="content" label="问题描述" rules={[{ required: true }]}>
              <TextArea rows={5} placeholder="详细描述您的问题..." />
            </Form.Item>
            <Form.Item name="contact" label="联系方式">
              <Input placeholder="邮箱/手机号（选填）" />
            </Form.Item>
            <Button type="primary" icon={<SendOutlined />} htmlType="submit">提交反馈</Button>
          </Form>
        </Card>
        <Divider />
        <Space direction="vertical">
          <Text>📧 邮箱：support@stock-system.com</Text>
          <Text>⏱ 回复时间：2个工作日内</Text>
        </Space>
      </div>
    );
  };

  const isContactCat = categories.find(c => c.id === selectedCat)?.name === '联系我们';
  const displayDocs = searchResults !== null ? searchResults : documents;

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', background: 'var(--bg)' }}>
      {/* 顶部栏 */}
      <div style={{
        position: 'sticky', top: 0, zIndex: 100,
        background: 'var(--sidebar-bg, #1a1a2e)', color: '#fff',
        padding: '12px 24px', display: 'flex', alignItems: 'center', gap: 16,
      }}>
        <span style={{ fontSize: 20, fontWeight: 700 }}>❓ 帮助中心</span>
        <Input prefix={<SearchOutlined />} placeholder="搜索文档..."
          value={searchQuery} onChange={e => setSearchQuery(e.target.value)}
          onPressEnter={handleSearch}
          style={{ maxWidth: 400, borderRadius: 6 }} />
        <div style={{ flex: 1 }} />
        <Button type="text" style={{ color: '#fff' }} icon={<ArrowLeftOutlined />}
          onClick={() => window.open('/', '_self')}>
          返回系统
        </Button>
      </div>

      {/* 主体 */}
      <div style={{ display: 'flex', flex: 1, overflow: 'auto' }}>
        {/* 左侧分类导航 */}
        <div style={{
          width: 260, flexShrink: 0, borderRight: '1px solid var(--border-color, #f0f0f0)',
          padding: '16px 0', background: 'var(--bg-card)',
        }}>
          {categories.map(cat => (
            <div key={cat.id} onClick={() => { setSelectedCat(cat.id); setSearchResults(null); setCurrentDoc(null); }}
              style={{
                padding: '10px 24px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8,
                background: selectedCat === cat.id ? 'var(--active-bg, #E8F3FF)' : 'transparent',
                color: selectedCat === cat.id ? '#165DFF' : 'var(--text-color)',
                fontWeight: selectedCat === cat.id ? 600 : 400,
                borderRight: selectedCat === cat.id ? '3px solid #165DFF' : '3px solid transparent',
              }}>
              <span>{cat.icon}</span>
              <span>{cat.name}</span>
            </div>
          ))}
        </div>

        {/* 右侧内容区 */}
        <div style={{ flex: 1, padding: 24, overflow: 'auto' }}>
          {currentDoc ? renderDocDetail() : isContactCat ? renderContactForm() : (
            <>
              {searchResults !== null && (
                <div style={{ marginBottom: 16 }}>
                  <Text>搜索结果：共找到 {searchResults.length} 条相关内容</Text>
                  <Button type="link" onClick={() => setSearchResults(null)}>清除搜索</Button>
                </div>
              )}
              {loading ? <Spin style={{ display: 'block', margin: '40px auto' }} /> : (
                displayDocs.length === 0 ? (
                  <Empty description={searchResults !== null ? '未找到相关文档' : '该分类暂无文档'} />
                ) : (
                  <Row gutter={[16, 16]}>
                    {displayDocs.map(doc => (
                      <Col key={doc.id} span={24}>
                        <Card hoverable size="small" onClick={() => {
                          if (!isContactCat) handleDocClick(doc);
                        }} style={{ borderRadius: 8 }}>
                          <Space direction="vertical" style={{ width: '100%' }} size={4}>
                            <Space>
                              <FileTextOutlined style={{ color: '#165DFF' }} />
                              <Text strong>{doc.title}</Text>
                              <Tag>{categories.find(c => c.id === doc.category_id)?.name || ''}</Tag>
                            </Space>
                            <Text type="secondary" style={{ fontSize: 13 }}>{doc.summary || ''}</Text>
                            <Space size={16}>
                              <Text type="secondary" style={{ fontSize: 12 }}>
                                <ClockCircleOutlined /> {doc.read_time || '?'} 分钟
                              </Text>
                              <Text type="secondary" style={{ fontSize: 12 }}>
                                <EyeOutlined /> {doc.view_count || 0}
                              </Text>
                            </Space>
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

      {/* 页脚 */}
      <div style={{
        textAlign: 'center', padding: '12px', fontSize: 12,
        color: '#999', borderTop: '1px solid var(--border-color, #f0f0f0)',
      }}>
        股票分析与投资决策系统 v1.0.0 · 帮助中心 · Copyright © 2026 闲适老翁
      </div>
    </div>
  );
};

export default HelpPage;
