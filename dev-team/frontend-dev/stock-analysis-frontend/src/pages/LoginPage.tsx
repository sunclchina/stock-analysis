/**
 * 登录页面。
 * 居中卡片布局，与系统整体风格一致。
 */
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Input, Button, Form, Typography, Space, message, Alert } from 'antd';
import { UserOutlined, LockOutlined, FundOutlined } from '@ant-design/icons';

const { Text, Title } = Typography;

const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleLogin = async (values: { username: string; password: string }) => {
    setLoading(true);
    setError('');
    try {
      // 先检查后端是否在线
      try {
        const health = await fetch('/api/v1/health', { method: 'GET' });
        if (!health.ok) throw new Error('backend down');
      } catch {
        setError('后端服务未启动或连接失败，请确认 :8000 端口已运行');
        setLoading(false);
        return;
      }
      const r = await fetch('/api/v1/user/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values),
      });
      const data = await r.json();
      if (!r.ok) {
        setError(data.detail || '登录失败');
        return;
      }
      // 保存 Token
      localStorage.setItem('token', data.token);
      localStorage.setItem('refresh_token', data.refresh_token);
      localStorage.setItem('user', JSON.stringify(data.user));

      // 首次登录需修改密码
      if (data.user.need_change_password) {
        window.location.href = '/password';
      } else {
        window.location.href = '/';
      }
    } catch (e) {
      setError('网络连接失败，请确认后端服务是否已启动（端口8000）');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)',
    }}>
      <Card
        style={{
          width: '90%',
          maxWidth: 400,
          borderRadius: 12,
          boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
        }}
        styles={{ body: { padding: window.innerWidth < 480 ? '28px 20px' : '40px 36px' } }}
      >
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <FundOutlined style={{ fontSize: 48, color: '#165DFF', marginBottom: 12 }} />
          <Title level={3} style={{ margin: 0, marginBottom: 4 }}>股票分析系统</Title>
          <Text type="secondary">分析与投资决策平台</Text>
        </div>

        {error && (
          <Alert message={error} type="error" showIcon style={{ marginBottom: 16 }} closable onClose={() => setError('')} />
        )}

        <Form
          onFinish={handleLogin}
          size="large"
          autoComplete="off"
        >
          <Form.Item name="username" rules={[{ required: true, message: '请输入账号' }]}>
            <Input prefix={<UserOutlined />} placeholder="账号" />
          </Form.Item>
          <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password prefix={<LockOutlined />} placeholder="密码" />
          </Form.Item>
          <Form.Item style={{ marginBottom: 12 }}>
            <Button type="primary" htmlType="submit" block loading={loading}>
              登 录
            </Button>
          </Form.Item>
          <div style={{ textAlign: 'center' }}>
            <Text type="secondary" style={{ fontSize: 12 }}>
              默认账号: admin / admin123
            </Text>
          </div>
        </Form>
      </Card>
    </div>
  );
};

export default LoginPage;
