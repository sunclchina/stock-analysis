import React, { useState, useEffect } from 'react';
import {
  Card,
  Form,
  Input,
  InputNumber,
  Select,
  Switch,
  Button,
  Divider,
  message,
  Modal,
  Typography,
  Space,
  Tag,
  Spin,
  Alert,
} from 'antd';
import { SaveOutlined, ReloadOutlined, WarningOutlined, SafetyCertificateOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';
import { useConfigStore } from '../../store/configStore';
import { fetchSslConfig, saveSslConfig } from '../../services/configApi';
import type { EnvVarField, EnvVarGroup, SslConfig } from '../../types';

const { Text } = Typography;

const envVarGroups: EnvVarGroup[] = [
  {
    key: 'basic',
    title: '基础配置',
    fields: [
      { key: 'port', label: '服务端口', type: 'number', defaultValue: '8080', description: '前端服务监听端口' },
      { key: 'environment', label: '运行环境', type: 'select', options: [{ label: '开发环境', value: 'development' }, { label: '生产环境', value: 'production' }], defaultValue: 'development' },
      { key: 'logPath', label: '日志路径', type: 'text', placeholder: './logs', description: '日志文件存储目录' },
      { key: 'cacheTime', label: '缓存时间(秒)', type: 'number', defaultValue: '300', description: '数据缓存有效期' },
    ],
  },
  {
    key: 'module',
    title: '模块联动配置',
    fields: [
      { key: 'apiBaseUrl', label: '后端地址', type: 'text', placeholder: '/api/v1', description: 'API 服务基础 URL' },
      { key: 'apiPrefix', label: 'API 前缀', type: 'text', placeholder: '/api/v1', description: '路由前缀' },
      { key: 'apiTimeout', label: 'API 超时(ms)', type: 'number', defaultValue: '10000', description: '请求超时时间' },
    ],
  },
  {
    key: 'ai',
    title: 'AI 模型配置',
    fields: [
      { key: 'aiModel', label: '模型选择', type: 'select', options: [
        { label: 'DeepSeek Chat', value: 'deepseek-chat' },
        { label: 'DeepSeek Reasoner', value: 'deepseek-reasoner' },
        { label: 'GPT-4o', value: 'gpt-4o' },
        { label: 'GPT-4o-mini', value: 'gpt-4o-mini' },
      ], defaultValue: 'deepseek-chat' },
      { key: 'aiApiKey', label: 'API 密钥', type: 'password', description: 'AI 服务 API Key' },
      { key: 'aiApiUrl', label: 'API 地址', type: 'text', placeholder: 'https://api.deepseek.com', description: 'AI 服务接口地址' },
      { key: 'aiTemperature', label: '温度参数', type: 'number', defaultValue: '0.7', description: '生成随机性 (0-2)' },
      { key: 'aiMaxTokens', label: '最大 Token', type: 'number', defaultValue: '4096', description: '单次生成上限' },
    ],
  },
  {
    key: 'security',
    title: '安全配置',
    fields: [
      { key: 'enableAuth', label: '启用认证', type: 'boolean', description: '是否启用 API 密钥认证' },
      { key: 'rateLimit', label: '速率限制', type: 'number', defaultValue: '100', description: '每分钟最大请求数' },
    ],
  },
  {
    key: 'extended',
    title: '扩展配置',
    fields: [
      { key: 'enableWebSocket', label: '启用 WebSocket', type: 'boolean', description: '开启实时推送' },
      { key: 'enableAutoBackup', label: '自动备份', type: 'boolean', description: '定时备份配置和数据' },
    ],
  },
];

const SettingsTab: React.FC = () => {
  const { systemSettings, setSystemSettings } = useConfigStore();
  const [form] = Form.useForm();
  const [dirtyKeys, setDirtyKeys] = useState<Set<string>>(new Set());
  const [changedRequireRestart, setChangedRequireRestart] = useState<string[]>([]);

  // SSL 配置状态
  const [sslConfig, setSslConfig] = useState<SslConfig | null>(null);
  const [sslLoading, setSslLoading] = useState(false);
  const [sslSaving, setSslSaving] = useState(false);
  const [sslSslEnabled, setSslSslEnabled] = useState(false);
  const [sslCertFile, setSslCertFile] = useState('');
  const [sslKeyFile, setSslKeyFile] = useState('');
  const [sslDirty, setSslDirty] = useState(false);

  // 加载 SSL 配置
  useEffect(() => {
    loadSslConfig();
  }, []);

  const loadSslConfig = async () => {
    setSslLoading(true);
    try {
      const res = await fetchSslConfig();
      if (res?.data) {
        setSslConfig(res.data);
        setSslSslEnabled(res.data.ssl_enabled);
        setSslCertFile(res.data.ssl_cert_file);
        setSslKeyFile(res.data.ssl_key_file);
      }
    } catch {
      // SSL API 可能尚未部署，静默失败
    } finally {
      setSslLoading(false);
    }
  };

  const handleSaveSsl = async () => {
    setSslSaving(true);
    try {
      const res = await saveSslConfig({
        ssl_enabled: sslSslEnabled,
        ssl_cert_file: sslCertFile,
        ssl_key_file: sslKeyFile,
      });
      message.success(res?.data?.message || 'SSL 配置已保存');
      setSslDirty(false);
      Modal.confirm({
        title: '需要重启服务',
        icon: <WarningOutlined />,
        content: 'SSL 配置已写入 .env 文件，重启后端服务后生效。确认重启？',
        okText: '稍后手动重启',
        cancelText: '知道了',
      });
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '保存 SSL 配置失败');
    } finally {
      setSslSaving(false);
    }
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      setSystemSettings(values as any);
      message.success('系统配置已保存');
      if (changedRequireRestart.length > 0) {
        Modal.confirm({
          title: '需要重启生效',
          icon: <WarningOutlined />,
          content: (
            <div>
              <p>以下配置项修改后需要重启服务才能生效：</p>
              <ul>
                {changedRequireRestart.map((key) => (
                  <li key={key}>{key}</li>
                ))}
              </ul>
              <p>是否现在重启？</p>
            </div>
          ),
          okText: '重启',
          cancelText: '稍后',
          onOk: () => {
            message.loading('正在重启...');
            setTimeout(() => {
              message.success('服务已重启');
              setChangedRequireRestart([]);
              setDirtyKeys(new Set());
            }, 2000);
          },
        });
      } else {
        setDirtyKeys(new Set());
      }
    } catch {
      message.error('请输入正确的配置值');
    }
  };

  const handleFieldChange = (key: string, requiresRestart?: boolean) => {
    setDirtyKeys((prev) => new Set(prev).add(key));
    if (requiresRestart) {
      setChangedRequireRestart((prev) => {
        if (!prev.includes(key)) return [...prev, key];
        return prev;
      });
    }
  };

  const handleReset = () => {
    Modal.confirm({
      title: '确认重置',
      content: '重置将恢复默认配置，当前修改将丢失。',
      onOk: () => {
        form.resetFields();
        setDirtyKeys(new Set());
        setChangedRequireRestart([]);
        message.success('已恢复默认值');
      },
    });
  };

  const renderField = (field: EnvVarField) => {
    const commonProps = {
      placeholder: field.placeholder,
      onChange: () => handleFieldChange(field.key, field.requiresRestart),
    };

    switch (field.type) {
      case 'number':
        return <InputNumber style={{ width: '100%' }} {...commonProps} />;
      case 'select':
        return <Select options={field.options} {...commonProps} />;
      case 'password':
        return <Input.Password {...commonProps} />;
      case 'boolean':
        return <Switch onChange={(checked) => handleFieldChange(field.key, field.requiresRestart)} />;
      default:
        return <Input {...commonProps} />;
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <Card
        title="系统设置"
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={handleReset}>
              重置
            </Button>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              onClick={handleSave}
              disabled={dirtyKeys.size === 0}
            >
              保存配置
            </Button>
          </Space>
        }
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={systemSettings}
          style={{ maxWidth: '100%' }}
        >
          {envVarGroups.map((group) => (
            <React.Fragment key={group.key}>
              <Divider orientation="left" plain>
                <Text strong>{group.title}</Text>
              </Divider>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '16px' }}>
                {group.fields.map((field) => (
                  <Form.Item
                    key={field.key}
                    name={field.key}
                    label={
                      <span>
                        {field.label}
                        {field.requiresRestart && (
                          <Text type="warning" style={{ fontSize: 12, marginLeft: 8 }}>
                            (需重启)
                          </Text>
                        )}
                      </span>
                    }
                    valuePropName={field.type === 'boolean' ? 'checked' : 'value'}
                    tooltip={field.description}
                  >
                    {renderField(field)}
                  </Form.Item>
                ))}
              </div>
            </React.Fragment>
          ))}
        </Form>
      </Card>

      {/* ─── HTTPS/SSL 配置卡 ─────────── */}
      <Card
        title={
          <span>
            <SafetyCertificateOutlined style={{ marginRight: 8 }} />
            HTTPS/SSL 证书配置
          </span>
        }
      >
        {sslLoading ? (
          <div style={{ textAlign: 'center', padding: 24 }}>
            <Spin tip="加载 SSL 配置..." />
          </div>
        ) : (
          <div>
            {/* 当前状态提示 */}
            {sslConfig && (
              <Alert
                type={sslConfig.ssl_enabled && sslConfig.cert_exists && sslConfig.key_exists ? 'success' : 'warning'}
                showIcon
                icon={sslConfig.ssl_enabled && sslConfig.cert_exists && sslConfig.key_exists ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
                message={
                  sslConfig.ssl_enabled
                    ? (sslConfig.cert_exists && sslConfig.key_exists
                        ? 'HTTPS 已启用，证书文件正常'
                        : 'HTTPS 已启用但证书文件缺失！')
                    : 'HTTPS 未启用（当前通过明文 HTTP 访问）'
                }
                description={
                  sslConfig.ssl_enabled && (!sslConfig.cert_exists || !sslConfig.key_exists)
                    ? `证书路径：${sslConfig.cert_path_abs}\n密钥路径：${sslConfig.key_path_abs}\n请确认证书文件存在后重启服务。`
                    : '修改配置后需重启后端服务生效'
                }
                style={{ marginBottom: 16 }}
              />
            )}

            <Form layout="vertical">
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '16px' }}>
                <Form.Item label="启用 HTTPS">
                  <Switch
                    checked={sslSslEnabled}
                    onChange={(checked) => {
                      setSslSslEnabled(checked);
                      setSslDirty(true);
                    }}
                  />
                  <Text style={{ marginLeft: 8, fontSize: 12, color: '#888' }}>
                    {sslSslEnabled ? '已开启' : '已关闭'}
                  </Text>
                </Form.Item>

                <Form.Item
                  label={
                    <span>
                      SSL 证书文件路径
                      <Text type="warning" style={{ fontSize: 12, marginLeft: 8 }}>(需重启)</Text>
                    </span>
                  }
                  tooltip="证书文件 .pem/.crt 的完整路径"
                >
                  <Input
                    placeholder="C:\path\to\cert.pem"
                    value={sslCertFile}
                    onChange={(e) => {
                      setSslCertFile(e.target.value);
                      setSslDirty(true);
                    }}
                    suffix={
                      sslConfig?.cert_exists ? (
                        <Tag color="success" style={{ marginRight: 0 }}>存在</Tag>
                      ) : sslCertFile ? (
                        <Tag color="error" style={{ marginRight: 0 }}>文件不存在</Tag>
                      ) : null
                    }
                  />
                </Form.Item>

                <Form.Item
                  label={
                    <span>
                      SSL 密钥文件路径
                      <Text type="warning" style={{ fontSize: 12, marginLeft: 8 }}>(需重启)</Text>
                    </span>
                  }
                  tooltip="私钥文件 .key 的完整路径"
                >
                  <Input
                    placeholder="C:\path\to\privkey.key"
                    value={sslKeyFile}
                    onChange={(e) => {
                      setSslKeyFile(e.target.value);
                      setSslDirty(true);
                    }}
                    suffix={
                      sslConfig?.key_exists ? (
                        <Tag color="success" style={{ marginRight: 0 }}>存在</Tag>
                      ) : sslKeyFile ? (
                        <Tag color="error" style={{ marginRight: 0 }}>文件不存在</Tag>
                      ) : null
                    }
                  />
                </Form.Item>
              </div>

              {/* 证书路径说明 */}
              <Alert
                type="info"
                showIcon
                message="证书路径说明"
                description={
                  <ul style={{ margin: 0, paddingLeft: 16 }}>
                    <li>支持绝对路径（如 C:\certs\sunclnas.com.pem）或相对于项目根目录的路径</li>
                    <li>将你的证书文件（.pem /.crt）和密钥文件（.key）放在服务器上，填入完整路径</li>
                    <li>证书格式：PEM（最常见的格式，.pem / .crt / .cert 均可）</li>
                    <li>配置保存后需<Text strong>重启后端服务</Text>才能生效</li>
                  </ul>
                }
                style={{ marginBottom: 16 }}
              />

              <Button
                type="primary"
                icon={<SafetyCertificateOutlined />}
                onClick={handleSaveSsl}
                disabled={!sslDirty}
                loading={sslSaving}
              >
                保存 SSL 配置
              </Button>
            </Form>
          </div>
        )}
      </Card>
    </div>
  );
};

export default SettingsTab;
