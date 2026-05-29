import React, { useState, useEffect, useRef } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Button,
  Tag,
  Space,
  message,
  Typography,
  Spin,
  Alert,
  Divider,
  Radio,
  Modal,
  Form,
  Input,
  Switch,
  Tooltip,
  Popconfirm,
} from 'antd';
import {
  ApiOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ExclamationCircleOutlined,
  ReloadOutlined,
  ThunderboltOutlined,
  SwapOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  LinkOutlined,
  KeyOutlined,
  ExperimentOutlined,
} from '@ant-design/icons';
import { useConfigStore } from '../../store/configStore';
import type { DataSourceStatus, DataSourceId, CustomDataSource } from '../../types';
import {
  fetchDataSourceStatus,
  testDataSourceConnection,
  switchDataSource,
  fetchCustomDataSources,
  addCustomDataSource,
  updateCustomDataSource,
  deleteCustomDataSource,
  testCustomDataSource,
} from '../../services/configApi';

const { Text, Title } = Typography;

const dataSourceMeta: Record<DataSourceId, { name: string; icon: string; description: string }> = {
  tdx: { name: '通达信本地', icon: '📁', description: '本地DS_STK.DAT + .day二进制文件解析' },
  sina: { name: '新浪财经', icon: '🌐', description: '新浪财经实时行情API' },
  eastmoney: { name: '东方财富', icon: '📊', description: '东方财富基本面/财务数据' },
  baostock: { name: 'Baostock+', icon: '🗄️', description: '历史日线/分钟线批量数据' },
  akshare: { name: 'AkShare数据源', icon: '🔌', description: '概念板块/个股资金流/基本面信息（免费备用）' },
};

const statusIcon: Record<string, React.ReactNode> = {
  online: <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 24 }} />,
  offline: <CloseCircleOutlined style={{ color: '#ff4d4f', fontSize: 24 }} />,
  degraded: <ExclamationCircleOutlined style={{ color: '#faad14', fontSize: 24 }} />,
};

const statusBadge: Record<string, { color: string; text: string }> = {
  online: { color: 'green', text: '🟢 在线' },
  offline: { color: 'red', text: '🔴 离线' },
  degraded: { color: 'orange', text: '🟡 降级' },
};

const DataSourceTab: React.FC = () => {
  const { dataSources, setDataSources, updateDataSourceStatus } = useConfigStore();
  const [testingId, setTestingId] = useState<string | null>(null);
  const [autoRefreshing, setAutoRefreshing] = useState(true);
  const [switchingId, setSwitchingId] = useState<string | null>(null);
  const autoRefreshRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ─── 自定义数据源状态 ───
  const [customSources, setCustomSources] = useState<CustomDataSource[]>([]);
  const [customLoading, setCustomLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingSource, setEditingSource] = useState<CustomDataSource | null>(null);
  const [testingCustom, setTestingCustom] = useState(false);
  const [testResult, setTestResult] = useState<{ status: string; latency?: number; message: string } | null>(null);
  const [form] = Form.useForm();

  // 将后端数据源对象映射到前端 DataSourceStatus 格式
  const mapSources = (sources: any[]): DataSourceStatus[] => {
    return sources.map((ds: any) => ({
      id: ds.name === 'tdx_local' ? 'tdx' : ds.name === 'eastmoney' ? 'eastmoney' : ds.name === 'akshare' ? 'akshare' : ds.name || 'unknown',
      name: ds.name === 'tdx_local' ? '通达信本地' : ds.name === 'eastmoney' ? '东方财富' : ds.name === 'sina' ? '新浪财经' : ds.name === 'akshare' ? 'AkShare数据源' : ds.name || '未知',
      type: ds.is_primary ? 'primary' : 'backup',
      status: ds.status || 'unknown',
      lastCheck: new Date().toISOString(),
      latency: ds.latency || 0,
      description: ds.description || (ds.name === 'tdx_local' ? '本地DS_STK.DAT + .day二进制文件解析' : ds.name === 'sina' ? '新浪财经实时行情API' : ds.name === 'eastmoney' ? '东方财富基本面/财务数据' : ''),
    }));
  };

  // 从后端加载真实数据源状态
  const loadDataSources = () => {
    fetchDataSourceStatus().then((res: any) => {
      if (res?.sources) {
        // 过滤掉自定义数据源（自定义数据源由独立API管理）
        const builtinSources = res.sources.filter((s: any) => s.type !== 'custom');
        setDataSources(mapSources(builtinSources));
      }
    }).catch(() => {/* 加载失败，显示空状态 */});
  };

  // 加载自定义数据源
  const loadCustomSources = () => {
    setCustomLoading(true);
    fetchCustomDataSources().then((res: any) => {
      if (res?.sources) {
        setCustomSources(res.sources);
      }
    }).catch(() => {
      message.warning('加载自定义数据源失败');
    }).finally(() => {
      setCustomLoading(false);
    });
  };

  useEffect(() => {
    loadDataSources();
    loadCustomSources();
  }, [setDataSources]);

  // Auto-refresh every 30s
  useEffect(() => {
    if (autoRefreshing) {
      autoRefreshRef.current = setInterval(loadDataSources, 30000);
    }
    return () => {
      if (autoRefreshRef.current) {
        clearInterval(autoRefreshRef.current);
      }
    };
  }, [autoRefreshing, setDataSources]);

  const handleTestConnection = async (id: string) => {
    setTestingId(id);
    try {
      const res: any = await testDataSourceConnection(id as DataSourceId);
      if (res?.status === 'ok') {
        updateDataSourceStatus(id, 'online', res.latency || 0);
        message.success(`${dataSourceMeta[id as DataSourceId]?.name || id} 连通性测试完成 (${res.latency || 0}ms)`);
      } else {
        updateDataSourceStatus(id, 'degraded', 0);
        message.warning(`${dataSourceMeta[id as DataSourceId]?.name || id} 连通性测试异常`);
      }
    } catch {
      updateDataSourceStatus(id, 'offline', 0);
      message.error(`${dataSourceMeta[id as DataSourceId]?.name || id} 连接测试失败`);
    } finally {
      setTestingId(null);
    }
  };

  const handleSwitch = async (id: string) => {
    setSwitchingId(id);
    try {
      await switchDataSource(id as DataSourceId);
      message.success(`已切换到 ${dataSourceMeta[id as DataSourceId]?.name || id}`);
      loadDataSources();
    } catch {
      message.error('切换失败');
    } finally {
      setSwitchingId(null);
    }
  };

  // ─── 自定义数据源操作 ───

  const openAddModal = () => {
    setEditingSource(null);
    setTestResult(null);
    form.resetFields();
    form.setFieldsValue({ enabled: true });
    setModalVisible(true);
  };

  const openEditModal = (source: CustomDataSource) => {
    setEditingSource(source);
    setTestResult(null);
    form.setFieldsValue({
      name: source.name,
      api_url: source.api_url,
      api_key: '',
      description: source.description || '',
      enabled: source.enabled,
    });
    setModalVisible(true);
  };

  const closeModal = () => {
    setModalVisible(false);
    setEditingSource(null);
    setTestResult(null);
    form.resetFields();
  };

  const handleTestCustom = async () => {
    try {
      const values = await form.validateFields(['api_url', 'api_key']);
      setTestingCustom(true);
      setTestResult(null);
      const res: any = await testCustomDataSource(values.api_url, values.api_key);
      setTestResult({
        status: res?.status || 'error',
        latency: res?.latency,
        message: res?.message || '测试完成',
      });
      if (res?.status === 'ok') {
        message.success(`连接测试成功 (${res.latency}ms)`);
      } else {
        message.warning(`连接测试异常: ${res?.message}`);
      }
    } catch {
      message.error('请填写API地址和密钥');
    } finally {
      setTestingCustom(false);
    }
  };

  const handleSaveCustom = async () => {
    try {
      const values = await form.validateFields();
      if (editingSource) {
        // 更新
        const updateData: Partial<CustomDataSource> = {
          name: values.name,
          api_url: values.api_url,
          description: values.description || '',
          enabled: values.enabled,
        };
        if (values.api_key) {
          updateData.api_key = values.api_key;
        }
        await updateCustomDataSource(editingSource.id!, updateData);
        message.success(`自定义数据源 '${values.name}' 已更新`);
      } else {
        // 新增
        await addCustomDataSource({
          name: values.name,
          api_url: values.api_url,
          api_key: values.api_key || '',
          description: values.description || '',
          enabled: values.enabled,
        });
        message.success(`自定义数据源 '${values.name}' 已添加`);
      }
      closeModal();
      loadCustomSources();
    } catch (err: any) {
      if (err?.response?.data?.detail) {
        message.error(err.response.data.detail);
      } else if (err?.errorFields) {
        // form validation error, already handled by antd
      } else {
        message.error('保存失败');
      }
    }
  };

  const handleDeleteCustom = async (id: number, name: string) => {
    try {
      await deleteCustomDataSource(id);
      message.success(`自定义数据源 '${name}' 已删除`);
      loadCustomSources();
    } catch {
      message.error('删除失败');
    }
  };

  const handleTestExisting = async (source: CustomDataSource) => {
    setTestingId(`custom-${source.id}`);
    // 使用存储的信息测试：先通过list接口获取原始API key是不可能的（被掩码了）
    // 仅为已有数据源提供快速测试，复用测试端点需要重新输入密钥
    // 提示用户通过编辑查看
    message.info('请在编辑模式下修改并测试连接');
    setTestingId(null);
  };

  return (
    <>
      {/* 预配置数据源卡片 */}
      <Card
        title="数据源管理"
        extra={
          <Space>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => {
                loadDataSources();
                loadCustomSources();
              }}
            >
              刷新状态
            </Button>
          </Space>
        }
      >
        <Alert
          message="数据源优先级：通达信本地（主力）→ 新浪财经（备用）→ 东方财富（备用）→ Baostock+（应急降级）"
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />

        {/* Auto-refresh toggle */}
        <div style={{ marginBottom: 16, display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 8 }}>
          <Text style={{ whiteSpace: 'nowrap' }}>自动刷新状态：</Text>
          <Radio.Group
            value={autoRefreshing ? 'on' : 'off'}
            onChange={(e) => setAutoRefreshing(e.target.value === 'on')}
            size="small"
          >
            <Radio.Button value="on">开启（每30秒）</Radio.Button>
            <Radio.Button value="off">关闭</Radio.Button>
          </Radio.Group>
        </div>

        <Row gutter={[16, 16]}>
          {dataSources.map((ds) => {
            const meta = dataSourceMeta[ds.id as DataSourceId];
            const badge = statusBadge[ds.status];
            return (
              <Col xs={24} sm={12} lg={6} key={ds.id}>
                <Card
                  hoverable
                  size="small"
                  style={{
                    borderLeft: `4px solid ${
                      ds.status === 'online'
                        ? '#52c41a'
                        : ds.status === 'degraded'
                        ? '#faad14'
                        : '#ff4d4f'
                    }`,
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12, marginBottom: 12 }}>
                    <span style={{ fontSize: 32 }}>{meta?.icon || '🔌'}</span>
                    <div>
                      <Text strong style={{ fontSize: 16 }}>{ds.name}</Text>
                      <br />
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {ds.type === 'primary' ? '主力数据源' : ds.type === 'backup' ? '备用数据源' : '应急数据源'}
                      </Text>
                    </div>
                  </div>

                  <div style={{ marginBottom: 12 }}>
                    <Space>
                      {statusIcon[ds.status]}
                      <Tag color={badge.color}>{badge.text}</Tag>
                    </Space>
                  </div>

                  <div style={{ marginBottom: 12 }}>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {ds.description}
                    </Text>
                  </div>

                  <div style={{ marginBottom: 8 }}>
                    <Text style={{ fontSize: 12 }}>
                      延迟: <Text strong>{ds.latency > 0 ? `${ds.latency}ms` : 'N/A'}</Text>
                    </Text>
                    <br />
                    <Text style={{ fontSize: 12 }}>
                      最后检测: <Text strong>{new Date(ds.lastCheck).toLocaleTimeString('zh-CN')}</Text>
                    </Text>
                  </div>

                  <Divider style={{ margin: '8px 0' }} />

                  <Space>
                    <Button
                      size="small"
                      icon={<ThunderboltOutlined />}
                      loading={testingId === ds.id}
                      onClick={() => handleTestConnection(ds.id)}
                    >
                      测试
                    </Button>
                    <Button
                      size="small"
                      type="primary"
                      icon={<SwapOutlined />}
                      loading={switchingId === ds.id}
                      onClick={() => handleSwitch(ds.id)}
                      disabled={ds.status === 'offline'}
                    >
                      切换
                    </Button>
                  </Space>
                </Card>
              </Col>
            );
          })}
        </Row>

        <div style={{ marginTop: 16 }}>
          <Text type="secondary">
            系统将根据数据源优先级和状态自动选择最优数据源。当主力数据源连续3次请求失败时自动切换至备用数据源。
          </Text>
        </div>
      </Card>

      {/* ─── 自定义数据源区域 ─── */}
      <Card
        title="自定义数据源（付费第三方）"
        style={{ marginTop: 16 }}
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={openAddModal}>
            添加数据源
          </Button>
        }
      >
        <Spin spinning={customLoading}>
          {customSources.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '32px 0' }}>
              <Text type="secondary">
                暂无自定义数据源。点击「添加数据源」按钮添加第三方付费数据源（如 Wind、聚宽、Tushare 等）。
              </Text>
            </div>
          ) : (
            <Row gutter={[16, 16]}>
              {customSources.map((source) => (
                <Col xs={24} sm={12} lg={8} key={source.id}>
                  <Card
                    size="small"
                    hoverable
                    style={{
                      borderLeft: `4px solid ${source.enabled ? '#1890ff' : '#d9d9d9'}`,
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12, marginBottom: 12 }}>
                      <span style={{ fontSize: 28 }}>🔌</span>
                      <div style={{ flex: 1 }}>
                        <Text strong style={{ fontSize: 15 }}>{source.name}</Text>
                        <br />
                        <Tag color={source.enabled ? 'blue' : 'default'}>
                          {source.enabled ? '已启用' : '已禁用'}
                        </Tag>
                      </div>
                    </div>

                    <div style={{ marginBottom: 8 }}>
                      <Space>
                        <LinkOutlined style={{ color: '#999' }} />
                        <Text
                          type="secondary"
                          style={{ fontSize: 12 }}
                          ellipsis={{ tooltip: source.api_url }}
                        >
                          {source.api_url.length > 40
                            ? source.api_url.slice(0, 40) + '...'
                            : source.api_url}
                        </Text>
                      </Space>
                    </div>

                    {source.description && (
                      <div style={{ marginBottom: 8 }}>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {source.description}
                        </Text>
                      </div>
                    )}

                    <div style={{ marginBottom: 8 }}>
                      <Text style={{ fontSize: 12, color: '#999' }}>
                        添加于 {source.created_at ? new Date(source.created_at).toLocaleDateString('zh-CN') : '--'}
                      </Text>
                    </div>

                    <Divider style={{ margin: '8px 0' }} />

                    <Space>
                      <Tooltip title="编辑配置">
                        <Button
                          size="small"
                          icon={<EditOutlined />}
                          onClick={() => openEditModal(source)}
                        >
                          编辑
                        </Button>
                      </Tooltip>
                      <Popconfirm
                        title={`确定删除数据源「${source.name}」？`}
                        onConfirm={() => handleDeleteCustom(source.id!, source.name)}
                        okText="确定"
                        cancelText="取消"
                      >
                        <Tooltip title="删除数据源">
                          <Button size="small" danger icon={<DeleteOutlined />}>
                            删除
                          </Button>
                        </Tooltip>
                      </Popconfirm>
                    </Space>
                  </Card>
                </Col>
              ))}
            </Row>
          )}
        </Spin>
      </Card>

      {/* ─── 添加/编辑自定义数据源模态框 ─── */}
      <Modal
        title={editingSource ? '编辑自定义数据源' : '添加自定义数据源'}
        open={modalVisible}
        onCancel={closeModal}
        width={560}
        footer={
          <Space>
            <Button onClick={closeModal}>取消</Button>
            <Button
              icon={<ExperimentOutlined />}
              loading={testingCustom}
              onClick={handleTestCustom}
            >
              测试连接
            </Button>
            <Button type="primary" onClick={handleSaveCustom}>
              {editingSource ? '保存' : '添加'}
            </Button>
          </Space>
        }
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="数据源名称"
            rules={[{ required: true, message: '请输入数据源名称' }]}
          >
            <Input placeholder="例如：我的Wind数据" />
          </Form.Item>

          <Form.Item
            name="api_url"
            label="API地址"
            rules={[{ required: true, message: '请输入API地址' }]}
          >
            <Input placeholder="https://api.example.com/data" />
          </Form.Item>

          <Form.Item
            name="api_key"
            label={editingSource ? 'API密钥（留空不修改）' : 'API密钥'}
            rules={editingSource ? [] : [{ required: true, message: '请输入API密钥' }]}
          >
            <Input.Password
              placeholder={editingSource ? '输入新密钥覆盖旧密钥' : '输入API密钥'}
              prefix={<KeyOutlined />}
            />
          </Form.Item>

          <Form.Item name="description" label="描述（可选）">
            <Input.TextArea
              placeholder="数据源用途说明"
              rows={2}
            />
          </Form.Item>

          <Form.Item name="enabled" label="启用状态" valuePropName="checked">
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
          </Form.Item>
        </Form>

        {/* 测试结果 */}
        {testResult && (
          <Alert
            type={testResult.status === 'ok' ? 'success' : 'warning'}
            message={
              <Space>
                <Text>
                  {testResult.status === 'ok' ? '✅ 连接成功' : '❌ 连接失败'}
                </Text>
                {testResult.latency !== undefined && (
                  <Text type="secondary">{testResult.latency}ms</Text>
                )}
              </Space>
            }
            description={testResult.message}
            showIcon
            closable
            onClose={() => setTestResult(null)}
          />
        )}
      </Modal>
    </>
  );
};

export default DataSourceTab;
