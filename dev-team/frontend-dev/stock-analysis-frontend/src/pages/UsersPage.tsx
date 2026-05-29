/**
 * 用户管理页面（管理员专用）。
 * 用户列表、新增、编辑、禁用/启用、重置密码、强制下线、删除。
 * 账号/昵称/角色 均可编辑。
 */
import React, { useState, useEffect, useCallback } from 'react';
import { Card, Table, Button, Space, Tag, Modal, Form, Input, Select, message, Popconfirm, Typography, Switch } from 'antd';
import { PlusOutlined, ReloadOutlined, LogoutOutlined, DeleteOutlined, UserOutlined, EditOutlined } from '@ant-design/icons';
import { authFetch } from '../services/auth';

const { Text } = Typography;

interface UserItem {
  id: number;
  username: string;
  nickname: string;
  email: string;
  phone: string;
  role: string;
  status: number;
  last_login_ip: string;
  last_login_at: string;
  created_at: string;
}

const UsersPage: React.FC = () => {
  const [users, setUsers] = useState<UserItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<UserItem | null>(null);
  const [form] = Form.useForm();
  const [editForm] = Form.useForm();

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    try {
      const r = await authFetch('/api/v1/admin/users');
      const d = await r.json();
      setUsers(d.items || []);
    } catch { message.error('获取用户列表失败'); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchUsers(); }, [fetchUsers]);

  const handleCreate = async (values: any) => {
    try {
      const r = await authFetch('/api/v1/admin/users', {
        method: 'POST', body: JSON.stringify(values),
      });
      const d = await r.json();
      if (!r.ok) { message.error(d.detail || '创建失败'); return; }
      message.success(d.message);
      setCreateModalOpen(false);
      form.resetFields();
      fetchUsers();
    } catch { message.error('创建失败'); }
  };

  const handleToggleStatus = async (user: UserItem) => {
    const newStatus = user.status === 1 ? 0 : 1;
    try {
      const r = await authFetch(`/api/v1/admin/users/${user.id}/status`, {
        method: 'PUT', body: JSON.stringify({ status: newStatus }),
      });
      if (!r.ok) { const d = await r.json(); message.error(d.detail); return; }
      message.success(newStatus === 1 ? '已启用' : '已禁用');
      fetchUsers();
    } catch { message.error('操作失败'); }
  };



  const handleForceLogout = async (user: UserItem) => {
    try {
      const r = await authFetch(`/api/v1/admin/users/${user.id}/logout`, { method: 'POST' });
      const d = await r.json();
      message.success(d.message || '已强制下线');
    } catch { message.error('操作失败'); }
  };

  const handleDelete = async (user: UserItem) => {
    try {
      const r = await authFetch(`/api/v1/admin/users/${user.id}`, { method: 'DELETE' });
      const d = await r.json();
      if (!r.ok) { message.error(d.detail); return; }
      message.success('用户已删除');
      fetchUsers();
    } catch { message.error('删除失败'); }
  };

  // 打开编辑弹窗
  const openEdit = (user: UserItem) => {
    setSelectedUser(user);
    // Form 用 key 重新挂载，避免 setFieldsValue 时机问题
    setEditModalOpen(true);
  };

  // 提交编辑
  const handleEdit = async (values: any) => {
    if (!selectedUser) return;
    try {
      const r = await authFetch(`/api/v1/admin/users/${selectedUser.id}`, {
        method: 'PUT', body: JSON.stringify(values),
      });
      const d = await r.json();
      if (!r.ok) { message.error(d.detail || '更新失败'); return; }
      message.success('用户信息已更新');
      setEditModalOpen(false);
      setSelectedUser(null);
      editForm.resetFields();
      fetchUsers();
    } catch { message.error('更新失败'); }
  };

  const columns = [
    {
      title: '账号',
      dataIndex: 'username',
      key: 'username',
      width: 120,
      render: (v: string, record: UserItem) => (
        <a onClick={() => openEdit(record)} style={{ cursor: 'pointer' }}>
          {v}
        </a>
      ),
    },
    {
      title: '昵称',
      dataIndex: 'nickname',
      key: 'nickname',
      width: 130,
      render: (v: string, record: UserItem) => (
        <a onClick={() => openEdit(record)} style={{ cursor: 'pointer' }}>
          {v || '-'}
        </a>
      ),
    },
    {
      title: '角色',
      dataIndex: 'role',
      key: 'role',
      width: 90,
      render: (v: string, record: UserItem) => (
        <a onClick={() => openEdit(record)}>
          <Tag color={v === 'admin' ? 'red' : 'blue'} style={{ cursor: 'pointer' }}>
            {v === 'admin' ? '管理员' : '普通用户'}
          </Tag>
        </a>
      ),
    },
    {
      title: '状态', dataIndex: 'status', key: 'status', width: 80,
      render: (v: number) => <Tag color={v === 1 ? 'green' : 'default'}>{v === 1 ? '启用' : '禁用'}</Tag>,
    },
    {
      title: '最后登录', key: 'last_login', width: 170,
      render: (_: any, r: UserItem) => (
        <Text type="secondary" style={{ fontSize: 12 }} ellipsis>
          {r.last_login_ip ? `${r.last_login_ip} ` : ''}{r.last_login_at ? r.last_login_at.slice(0, 16) : ''}
        </Text>
      ),
    },
    {
      title: '注册时间', dataIndex: 'created_at', key: 'created_at', width: 100,
      render: (v: string) => <Text type="secondary" style={{ fontSize: 12 }}>{v ? v.slice(0, 10) : '-'}</Text>,
    },
    {
      title: '操作', key: 'action', width: 330,
      render: (_: any, record: UserItem) => (
        <Space size={4}>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(record)}>编辑</Button>
          <Switch checked={record.status === 1} size="small" onChange={() => handleToggleStatus(record)}
            checkedChildren="启用" unCheckedChildren="禁用" />
  
          <Button size="small" icon={<LogoutOutlined />} onClick={() => handleForceLogout(record)}>下线</Button>
          <Popconfirm title="确定删除此用户？" onConfirm={() => handleDelete(record)}>
            <Button size="small" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Card
        title={<Space><UserOutlined />用户管理</Space>}
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={fetchUsers} loading={loading}>刷新</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModalOpen(true)}>新增用户</Button>
          </Space>
        }
        style={{ borderRadius: 8 }}
      >
        <Table
          dataSource={users} columns={columns} rowKey="id" loading={loading} size="small"
          pagination={{ pageSize: 20 }} scroll={{ x: 1000 }}
        />
      </Card>

      {/* 新增用户弹窗 */}
      <Modal title="新增用户" open={createModalOpen} onCancel={() => setCreateModalOpen(false)} footer={null}>
        <Form form={form} onFinish={handleCreate} layout="vertical">
          <Form.Item name="username" label="账号" rules={[{ required: true, min: 2 }]}>
            <Input placeholder="登录账号" />
          </Form.Item>
          <Form.Item name="password" label="初始密码" rules={[{ required: true, min: 6 }]}>
            <Input.Password placeholder="至少6位" />
          </Form.Item>
          <Form.Item name="nickname" label="昵称">
            <Input placeholder="显示名称" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" block>创建</Button>
          </Form.Item>
        </Form>
      </Modal>

      {/* 编辑用户弹窗（含密码） — 用 key 强制重建 Form，避免字段残留 */}
      <Modal
        title={`编辑用户 - ${selectedUser?.username || ''}`}
        open={editModalOpen}
        onCancel={() => { setEditModalOpen(false); setSelectedUser(null); }}
        onOk={() => editForm.submit()}
        okText="保存"
        width={460}
        destroyOnClose
      >
        {selectedUser && (
          <Form
            form={editForm}
            onFinish={handleEdit}
            layout="vertical"
            key={selectedUser.id}
            initialValues={{
              username: selectedUser.username,
              nickname: selectedUser.nickname,
              role: selectedUser.role,
              password: '',
            }}
          >
            <Form.Item name="username" label="账号" rules={[{ required: true, min: 2, message: '账号至少2个字符' }]}>
              <Input placeholder="登录账号" />
            </Form.Item>
            <Form.Item name="nickname" label="昵称">
              <Input placeholder="显示名称" />
            </Form.Item>
            <Form.Item name="role" label="角色">
              <Select
                options={[
                  { label: '管理员', value: 'admin' },
                  { label: '普通用户', value: 'user' },
                ]}
              />
            </Form.Item>
            <Form.Item name="password" label="密码（留空不修改）">
              <Input.Password placeholder="至少6位，留空则保持不变" />
            </Form.Item>
          </Form>
        )}
      </Modal>
    </div>
  );
};

export default UsersPage;
