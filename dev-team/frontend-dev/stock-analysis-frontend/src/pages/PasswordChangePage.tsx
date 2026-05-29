/**
 * 修改密码页面（首次登录强制跳转）。
 */
import React, { useState } from 'react';
import { Card, Input, Button, Form, Typography, message, Alert } from 'antd';
import { LockOutlined, KeyOutlined } from '@ant-design/icons';

const { Text, Title } = Typography;

const PasswordChangePage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (values: { old_password: string; new_password: string; confirm: string }) => {
    if (values.new_password !== values.confirm) {
      setError('两次密码不一致');
      return;
    }
    if (values.new_password.length < 6) {
      setError('密码至少6位');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const token = localStorage.getItem('token');
      const r = await fetch('/api/v1/user/password', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
        body: JSON.stringify({ old_password: values.old_password, new_password: values.new_password }),
      });
      const data = await r.json();
      if (!r.ok) {
        setError(data.detail || '修改失败');
        return;
      }
      message.success('密码修改成功');
      // 清除旧 Token，跳转登录
      localStorage.removeItem('token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    } catch (e) {
      setError('网络错误');
    } finally {
      setLoading(false);
    }
  };

  const user = JSON.parse(localStorage.getItem('user') || '{}');

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)',
    }}>
      <Card style={{ width: 420, borderRadius: 12, boxShadow: '0 8px 32px rgba(0,0,0,0.3)' }}
        styles={{ body: { padding: '36px' } }}>
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <KeyOutlined style={{ fontSize: 40, color: '#faad14', marginBottom: 8 }} />
          <Title level={4} style={{ margin: 0, marginBottom: 4 }}>首次登录，请修改密码</Title>
          <Text type="secondary">欢迎 {user.nickname || user.username}</Text>
        </div>

        <Alert message="为了账号安全，首次登录必须修改默认密码" type="warning" showIcon style={{ marginBottom: 16 }} />

        {error && <Alert message={error} type="error" showIcon style={{ marginBottom: 12 }} closable onClose={() => setError('')} />}

        <Form onFinish={handleSubmit} size="large">
          <Form.Item name="old_password" rules={[{ required: true, message: '请输入当前密码' }]}>
            <Input.Password prefix={<LockOutlined />} placeholder="当前密码" />
          </Form.Item>
          <Form.Item name="new_password" rules={[
            { required: true, message: '请输入新密码' },
            { min: 6, message: '密码至少6位' },
          ]}>
            <Input.Password prefix={<LockOutlined />} placeholder="新密码" />
          </Form.Item>
          <Form.Item name="confirm" rules={[
            { required: true, message: '请确认新密码' },
          ]}>
            <Input.Password prefix={<LockOutlined />} placeholder="确认新密码" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" block loading={loading}>
              确认修改
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
};

export default PasswordChangePage;
