/**
 * 个人设置标签页（设计文档 §4）。
 * 包含：基础信息、安全设置、个性化、数据与隐私。
 */
import React, { useState, useEffect } from 'react';
import { Card, Form, Input, Button, Select, Switch, Radio, Upload, message, Space, Typography, Divider, Modal, Popconfirm } from 'antd';
import { UserOutlined, LockOutlined, KeyOutlined, SaveOutlined, ApiOutlined } from '@ant-design/icons';
import { authFetch, getCurrentUser } from '../../services/auth';
import apiClient from '../../services/api';
import { useConfigStore } from '../../store/configStore';

const { Text, Title } = Typography;

const ProfileTab: React.FC = () => {
  const [basicForm] = Form.useForm();
  const [prefForm] = Form.useForm();
  const [pwdForm] = Form.useForm();
  const [saving, setSaving] = useState(false);
  const [pwdModalOpen, setPwdModalOpen] = useState(false);
  const [savingQgqp, setSavingQgqp] = useState(false);
  const [qgqpForm] = Form.useForm();
  const setUserPreferences = useConfigStore((s) => s.setUserPreferences);

  // 加载用户信息和偏好
  useEffect(() => {
    authFetch('/api/v1/user/profile').then(r => r.json()).then(d => {
      basicForm.setFieldsValue({
        nickname: d.nickname, email: d.email, phone: d.phone,
      });
    }).catch(() => {});
    authFetch('/api/v1/user/preference').then(r => r.json()).then(d => {
      prefForm.setFieldsValue({
        theme: d.theme || 'light',
        font_size: d.font_size || '14',
        layout_mode: d.layout_mode || 'normal',
        refresh_interval: d.refresh_interval || 5,
        auto_refresh: d.auto_refresh !== false,
        alert_refresh_interval: d.alert_refresh_interval || 1,
        warn_sound: d.warn_sound !== false,
        default_export_format: d.default_export_format || 'txt',
      });
    }).catch(() => {});
    // 加载东财标识
    apiClient.get('/config/preferences/eastmoney_qgqp_b_id').then((res: any) => {
      if (res?.value) qgqpForm.setFieldsValue({ eastmoney_qgqp_b_id: res.value });
    }).catch(() => {});
  }, []);

  // 保存基本信息
  const saveBasic = async () => {
    setSaving(true);
    try {
      const values = await basicForm.validateFields();
      const r = await authFetch('/api/v1/user/profile', {
        method: 'PUT', body: JSON.stringify(values),
      });
      const d = await r.json();
      if (!r.ok) { message.error(d.detail); return; }
      message.success('保存成功');
    } catch { message.error('保存失败'); }
    finally { setSaving(false); }
  };

  // 保存偏好
  const savePref = async () => {
    setSaving(true);
    try {
      const values = await prefForm.validateFields();
      const r = await authFetch('/api/v1/user/preference', {
        method: 'PUT', body: JSON.stringify(values),
      });
      if (!r.ok) { message.error('保存失败'); return; }
      message.success('偏好已保存');
      setUserPreferences(values);  // 同步到本地状态
    } catch { message.error('保存失败'); }
    finally { setSaving(false); }
  };

  // 保存东财标识
  const saveQgqp = async () => {
    setSavingQgqp(true);
    try {
      const values = await qgqpForm.validateFields();
      const res: any = await apiClient.put('/config/preferences', { eastmoney_qgqp_b_id: values.eastmoney_qgqp_b_id || '' });
      if (res?.status === 'ok') {
        message.success('东财唯一标识已保存');
      } else {
        message.error('保存失败');
      }
    } catch { message.error('保存失败'); }
    finally { setSavingQgqp(false); }
  };

  // 修改密码
  const changePwd = async (values: any) => {
    if (values.new_password !== values.confirm) { message.error('两次密码不一致'); return; }
    try {
      const r = await authFetch('/api/v1/user/password', {
        method: 'PUT', body: JSON.stringify({ old_password: values.old_password, new_password: values.new_password }),
      });
      const d = await r.json();
      if (!r.ok) { message.error(d.detail); return; }
      message.success('密码已修改，请重新登录');
      pwdForm.resetFields();
      setPwdModalOpen(false);
      // 清除Token，跳转登录页
      setTimeout(() => {
        localStorage.removeItem('token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
        window.location.href = '/login';
      }, 1500);
    } catch { message.error('修改失败'); }
  };

  const user = getCurrentUser();

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      {/* 基础信息 */}
      <Card title={<Space><UserOutlined />基础信息</Space>} size="small">
        <Form form={basicForm} layout="vertical" style={{ maxWidth: 500 }}>
          <Form.Item name="nickname" label="昵称" rules={[{ required: true }]}>
            <Input placeholder="显示名称" />
          </Form.Item>
          <Form.Item name="email" label="邮箱">
            <Input placeholder="用于找回密码" />
          </Form.Item>
          <Form.Item name="phone" label="手机号">
            <Input placeholder="用于找回密码" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" icon={<SaveOutlined />} onClick={saveBasic} loading={saving}>保存</Button>
          </Form.Item>
        </Form>
      </Card>

      {/* 安全设置 */}
      <Card title={<Space><LockOutlined />安全设置</Space>} size="small">
        <Space direction="vertical">
          <div>
            <Text strong>登录账号：</Text>
            <Text>{user?.username}</Text>
          </div>
          <Button icon={<KeyOutlined />} onClick={() => setPwdModalOpen(true)}>修改密码</Button>
        </Space>
      </Card>

      {/* 个性化（原用户偏好） */}
      <Card title={<Space><UserOutlined />个性化</Space>} size="small">
        <Form form={prefForm} layout="vertical" style={{ maxWidth: 500 }}>
          <Form.Item name="theme" label="主题模式">
            <Select options={[
              { value: 'light', label: '浅色' },
              { value: 'dark', label: '深色' },
            ]} />
          </Form.Item>
          <Form.Item name="font_size" label="字体大小">
            <Select options={[
              { value: '12', label: '小(12px)' },
              { value: '14', label: '中(14px)' },
              { value: '16', label: '大(16px)' },
            ]} />
          </Form.Item>
          <Form.Item name="layout_mode" label="布局模式">
            <Select options={[
              { value: 'normal', label: '正常' },
              { value: 'compact', label: '紧凑' },
            ]} />
          </Form.Item>
          <Form.Item name="auto_refresh" label="自动刷新" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="refresh_interval" label="刷新频率（秒）">
            <Select options={[
              { value: 3, label: '3秒' },
              { value: 5, label: '5秒' },
              { value: 10, label: '10秒' },
              { value: 30, label: '30秒' },
            ]} />
          </Form.Item>
          <Form.Item name="warn_sound" label="预警声音" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="default_export_format" label="默认导出格式">
            <Select options={[
              { value: 'txt', label: 'TXT' },
              { value: 'md', label: 'Markdown' },
              { value: 'pdf', label: 'PDF' },
            ]} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" icon={<SaveOutlined />} onClick={savePref} loading={saving}>保存偏好</Button>
          </Form.Item>
        </Form>
      </Card>

      {/* 东财标识配置 */}
      <Card title={<Space><ApiOutlined />数据源配置</Space>} size="small">
        <Form form={qgqpForm} layout="vertical" style={{ maxWidth: 500 }}>
          <Form.Item name="eastmoney_qgqp_b_id" label="东财用户标识（qgqp_b_id）"
            help="打开东财选股页面，F12 → 任意请求Cookie中找到 qgqp_b_id 的值。选股器需要此标识才能正常工作。">
            <Input.Password placeholder="输入 qgqp_b_id" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" icon={<SaveOutlined />} onClick={saveQgqp} loading={savingQgqp}>保存</Button>
          </Form.Item>
        </Form>
      </Card>

      {/* 修改密码弹窗 */}
      <Modal title="修改密码" open={pwdModalOpen} onCancel={() => setPwdModalOpen(false)} footer={null}>
        <Form form={pwdForm} onFinish={changePwd} layout="vertical">
          <Form.Item name="old_password" label="当前密码" rules={[{ required: true }]}>
            <Input.Password />
          </Form.Item>
          <Form.Item name="new_password" label="新密码" rules={[{ required: true, min: 6 }]}>
            <Input.Password />
          </Form.Item>
          <Form.Item name="confirm" label="确认新密码" rules={[{ required: true }]}>
            <Input.Password />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" block>确认修改</Button>
          </Form.Item>
        </Form>
      </Modal>
    </Space>
  );
};

export default ProfileTab;
