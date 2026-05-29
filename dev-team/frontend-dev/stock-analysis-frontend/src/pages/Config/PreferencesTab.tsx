import React from 'react';
import {
  Card,
  Form,
  Select,
  Slider,
  Switch,
  Radio,
  Button,
  Divider,
  message,
  Typography,
  Space,
  InputNumber,
} from 'antd';
import {
  SaveOutlined,
  BulbOutlined,
  SoundOutlined,
  BgColorsOutlined,
  ColumnWidthOutlined,
  ClockCircleOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import { useConfigStore } from '../../store/configStore';
import type { ThemeMode, LayoutDensity, ExportFormat } from '../../types';

const { Text, Title } = Typography;

const PreferencesTab: React.FC = () => {
  const { userPreferences, setUserPreferences } = useConfigStore();
  const [form] = Form.useForm();

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      setUserPreferences(values);
      message.success('偏好设置已保存');
    } catch {
      message.error('请检查输入');
    }
  };

  return (
    <Card
      title="用户偏好"
      extra={
        <Button type="primary" icon={<SaveOutlined />} onClick={handleSave}>
          保存偏好
        </Button>
      }
    >
      <Form
        form={form}
        layout="vertical"
        initialValues={userPreferences}
        style={{ maxWidth: 640 }}
        onValuesChange={(changedValues) => {
          // Auto-save certain preferences
          if ('theme' in changedValues || 'fontSize' in changedValues || 'layout' in changedValues) {
            // Apply immediately
            setUserPreferences(changedValues);
          }
        }}
      >
        {/* 界面风格 */}
        <Divider orientation="left" plain>
          <Space>
            <BulbOutlined />
            <Text strong>界面风格</Text>
          </Space>
        </Divider>

        <Form.Item name="theme" label="主题模式">
          <Radio.Group>
            <Radio.Button value="light">☀️ 浅色模式</Radio.Button>
            <Radio.Button value="dark">🌙 深色模式</Radio.Button>
            <Radio.Button value="auto">🔄 跟随系统</Radio.Button>
          </Radio.Group>
        </Form.Item>

        <Form.Item name="fontSize" label="字体大小">
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <Slider
              min={12}
              max={24}
              step={1}
              style={{ flex: 1 }}
              marks={{
                12: '12',
                14: '14',
                16: '16',
                18: '18',
                20: '20',
                24: '24',
              }}
            />
            <InputNumber
              min={12}
              max={24}
              step={1}
              value={form.getFieldValue('fontSize')}
              onChange={(val) => form.setFieldsValue({ fontSize: val })}
              style={{ width: 60 }}
            />
          </div>
        </Form.Item>

        <Form.Item name="layout" label="布局密度">
          <Radio.Group>
            <Radio.Button value="compact">紧凑</Radio.Button>
            <Radio.Button value="default">正常</Radio.Button>
            <Radio.Button value="loose">宽松</Radio.Button>
          </Radio.Group>
        </Form.Item>

        {/* 预警设置 */}
        <Divider orientation="left" plain>
          <Space>
            <BgColorsOutlined />
            <Text strong>预警设置</Text>
          </Space>
        </Divider>

        <Form.Item name="alertHighlight" label="预警高亮" valuePropName="checked">
          <Switch checkedChildren="开启" unCheckedChildren="关闭" />
        </Form.Item>

        <Form.Item name="alertSound" label="预警声音" valuePropName="checked">
          <Switch checkedChildren="开启" unCheckedChildren="关闭" />
        </Form.Item>

        {/* 刷新设置 */}
        <Divider orientation="left" plain>
          <Space>
            <ClockCircleOutlined />
            <Text strong>刷新设置</Text>
          </Space>
        </Divider>

        <Form.Item name="autoRefreshInterval" label="自动刷新频率">
          <Select
            options={[
              { label: '1秒', value: 1000 },
              { label: '3秒', value: 3000 },
              { label: '5秒（默认）', value: 5000 },
              { label: '10秒', value: 10000 },
              { label: '30秒', value: 30000 },
              { label: '关闭自动刷新', value: 0 },
            ]}
          />
        </Form.Item>

        {/* 导出设置 */}
        <Divider orientation="left" plain>
          <Space>
            <FileTextOutlined />
            <Text strong>导出设置</Text>
          </Space>
        </Divider>

        <Form.Item name="defaultExportFormat" label="默认导出格式">
          <Radio.Group>
            <Radio.Button value="txt">纯文本 (.txt)</Radio.Button>
            <Radio.Button value="markdown">Markdown (.md)</Radio.Button>
            <Radio.Button value="pdf">PDF</Radio.Button>
          </Radio.Group>
        </Form.Item>

        <Divider />

        <div style={{ padding: 16, background: '#f5f5f5', borderRadius: 8 }}>
          <Text type="secondary">
            💡 提示：界面风格、字体大小、布局密度的修改将即时生效，无需保存。
          </Text>
        </div>
      </Form>
    </Card>
  );
};

export default PreferencesTab;
