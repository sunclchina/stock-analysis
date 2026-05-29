import React, { useState } from 'react';
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
} from 'antd';
import { SaveOutlined, ReloadOutlined, WarningOutlined } from '@ant-design/icons';
import { useConfigStore } from '../../store/configStore';
import type { EnvVarField, EnvVarGroup } from '../../types';

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
  );
};

export default SettingsTab;
