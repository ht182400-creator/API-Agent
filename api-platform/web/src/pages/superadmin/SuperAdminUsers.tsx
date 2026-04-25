/**
 * 超级管理员 - 用户管理页面
 * 数据从数据库获取
 */

import { useState, useEffect } from 'react'
import '../../styles/cyber-theme.css'
import { Table, Tag, Button, Space, Modal, Form, Select, Input, message, Popconfirm, Card, Avatar, Typography, Pagination } from 'antd'
import { UserOutlined, EditOutlined, DeleteOutlined, SafetyOutlined, SearchOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { userApi, userTypeLabels, userTypeColors, roleLabels, UserListItem } from '../../api/superadmin'
import { useDevice } from '../../hooks/useDevice'

const { Text } = Typography

export default function SuperAdminUsers() {
  const { isMobile } = useDevice()
  const [users, setUsers] = useState<UserListItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [loading, setLoading] = useState(false)
  const [editModalVisible, setEditModalVisible] = useState(false)
  const [editingUser, setEditingUser] = useState<UserListItem | null>(null)
  const [form] = Form.useForm()

  useEffect(() => {
    loadUsers()
  }, [page, pageSize])

  const loadUsers = async () => {
    try {
      setLoading(true)
      const data = await userApi.list({ page, page_size: pageSize })
      setUsers(data.items || [])
      setTotal(data.total || 0)
    } catch (error) {
      console.error('加载用户列表失败:', error)
      message.error('加载用户列表失败')
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = async (keyword: string) => {
    try {
      setLoading(true)
      setPage(1)
      const data = await userApi.list({ page: 1, page_size: pageSize, keyword })
      setUsers(data.items || [])
      setTotal(data.total || 0)
    } catch (error) {
      console.error('搜索用户失败:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleEdit = (user: UserListItem) => {
    setEditingUser(user)
    form.setFieldsValue({
      user_type: user.user_type,
      role: user.role,
      user_status: user.user_status,
      vip_level: user.vip_level,
    })
    setEditModalVisible(true)
  }

  const handleDelete = async (userId: string) => {
    try {
      await userApi.delete(userId)
      message.success('用户已删除')
      loadUsers()
    } catch (error: any) {
      message.error(error.message || '删除失败')
    }
  }

  const handleUpdate = async () => {
    try {
      const values = await form.validateFields()
      if (!editingUser) return
      
      await userApi.update(editingUser.id, values)
      message.success(`用户 ${editingUser.username} 已更新`)
      setEditModalVisible(false)
      loadUsers()
    } catch (error: any) {
      console.error('表单验证失败:', error)
      message.error(error.message || '更新失败')
    }
  }

  const columns: ColumnsType<UserListItem> = [
    { 
      title: 'ID', 
      dataIndex: 'id', 
      key: 'id', 
      width: 80,
      ellipsis: true,
      render: (id: string) => <code style={{ fontSize: 11 }}>{id.slice(0, 8)}...</code>
    },
    { title: '用户名', dataIndex: 'username', key: 'username', width: 100, ellipsis: true },
    { title: '邮箱', dataIndex: 'email', key: 'email', width: 160, ellipsis: true },
    { title: '手机', dataIndex: 'phone', key: 'phone', width: 120, ellipsis: true },
    { 
      title: '用户类型', 
      dataIndex: 'user_type', 
      key: 'user_type',
      width: 100,
      render: (type: string) => <Tag color={userTypeColors[type]}>{userTypeLabels[type] || type}</Tag>
    },
    { 
      title: '角色', 
      dataIndex: 'role', 
      key: 'role',
      width: 100,
      render: (role: string) => <Tag>{roleLabels[role] || role}</Tag>
    },
    { 
      title: '状态', 
      dataIndex: 'user_status', 
      key: 'user_status',
      render: (status: string) => (
        <Tag color={status === 'active' ? 'green' : status === 'disabled' ? 'orange' : 'red'}>
          {status === 'active' ? '正常' : status === 'disabled' ? '禁用' : '已删除'}
        </Tag>
      )
    },
    { 
      title: 'VIP', 
      dataIndex: 'vip_level', 
      key: 'vip_level',
      render: (level: number) => level > 0 ? <Tag color="gold">VIP {level}</Tag> : '-'
    },
    { 
      title: '创建时间', 
      dataIndex: 'created_at', 
      key: 'created_at',
      width: 120,
      render: (time: string) => new Date(time).toLocaleDateString('zh-CN')
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_, record) => (
        <Space>
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)}>
            编辑
          </Button>
          {record.user_type !== 'super_admin' && (
            <Popconfirm 
              title="确认删除此用户？" 
              description="删除后用户将无法登录"
              onConfirm={() => handleDelete(record.id)}
              okText="确认"
              cancelText="取消"
            >
              <Button type="link" size="small" danger icon={<DeleteOutlined />}>
                删除
              </Button>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ]

  return (
    <div style={{ padding: 24 }} className="bamboo-bg-pattern">
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2><UserOutlined /> 全局用户管理</h2>
          <p style={{ color: '#999' }}>管理所有用户账户、角色和权限</p>
        </div>
        <Space>
          <Input.Search
            placeholder="搜索用户名/邮箱"
            allowClear
            onSearch={handleSearch}
            style={{ width: 200 }}
            prefix={<SearchOutlined />}
          />
        </Space>
      </div>

      {isMobile ? (
        // 移动端：卡片列表
        <>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {users.map((user) => (
              <Card
                key={user.id}
                size="small"
                style={{ borderRadius: 8, boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }}
                bodyStyle={{ padding: 12 }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
                  <Avatar size={40} style={{ background: 'var(--gradient-cyber)' }} icon={<UserOutlined />} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <Text strong style={{ display: 'block', fontSize: 15 }}>{user.username}</Text>
                    <Text type="secondary" style={{ fontSize: 12 }}>{user.email}</Text>
                  </div>
                  <Tag color={userTypeColors[user.user_type]} style={{ marginInlineEnd: 0 }}>{userTypeLabels[user.user_type]}</Tag>
                </div>
                <div style={{ fontSize: 12, color: '#666', marginBottom: 8 }}>
                  <div>手机：{user.phone || '-'}</div>
                  <div>角色：<Tag style={{ marginInlineEnd: 0 }}>{roleLabels[user.role] || user.role}</Tag></div>
                  <div>状态：<Tag color={user.user_status === 'active' ? 'green' : user.user_status === 'disabled' ? 'orange' : 'red'} style={{ marginInlineEnd: 0 }}>{user.user_status === 'active' ? '正常' : user.user_status === 'disabled' ? '禁用' : '已删除'}</Tag></div>
                  <div>VIP：{user.vip_level > 0 ? <Tag color="gold" style={{ marginInlineEnd: 0 }}>VIP {user.vip_level}</Tag> : '-'}</div>
                  <div>ID：<code style={{ fontSize: 10 }}>{user.id.slice(0, 12)}...</code></div>
                  <div>创建：{new Date(user.created_at).toLocaleDateString('zh-CN')}</div>
                </div>
                <div style={{ display: 'flex', gap: 8, borderTop: '1px solid #f0f0f0', paddingTop: 8 }}>
                  <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(user)}>编辑</Button>
                  {user.user_type !== 'super_admin' && (
                    <Popconfirm title="确认删除此用户？" description="删除后用户将无法登录" onConfirm={() => handleDelete(user.id)} okText="确认" cancelText="取消" okButtonProps={{ danger: true }}>
                      <Button size="small" danger icon={<DeleteOutlined />}>删除</Button>
                    </Popconfirm>
                  )}
                </div>
              </Card>
            ))}
          </div>
          <div style={{ marginTop: 16, textAlign: 'center' }}>
            <Pagination current={page} pageSize={pageSize} total={total} showSizeChanger={false} onChange={(p, ps) => { setPage(p); setPageSize(ps) }} size="small" />
          </div>
        </>
      ) : (
        // 桌面端：表格
        <Table
          columns={columns}
          dataSource={users}
          rowKey="id"
          loading={loading}
          scroll={{ x: 1000 }}
          size="small"
          pagination={{
            current: page,
            pageSize: pageSize,
            total: total,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (t) => `共 ${t} 条`,
            onChange: (p, ps) => {
              setPage(p)
              setPageSize(ps)
            },
          }}
        />
      )}

      <Modal
        title={`编辑用户: ${editingUser?.username}`}
        open={editModalVisible}
        onOk={handleUpdate}
        onCancel={() => setEditModalVisible(false)}
        width={500}
        okText="保存"
        cancelText="取消"
      >
        <Form form={form} layout="vertical">
          <Form.Item label="用户类型" name="user_type" rules={[{ required: true }]}>
            <Select>
              <Select.Option value="super_admin">超级管理员</Select.Option>
              <Select.Option value="admin">管理员</Select.Option>
              <Select.Option value="owner">仓库所有者</Select.Option>
              <Select.Option value="developer">开发者</Select.Option>
              <Select.Option value="user">普通用户</Select.Option>
            </Select>
          </Form.Item>
          
          <Form.Item label="系统角色" name="role" rules={[{ required: true }]}>
            <Select>
              <Select.Option value="super_admin">超级管理员</Select.Option>
              <Select.Option value="admin">管理员</Select.Option>
              <Select.Option value="developer">开发者</Select.Option>
              <Select.Option value="user">普通用户</Select.Option>
            </Select>
          </Form.Item>
          
          <Form.Item label="账户状态" name="user_status" rules={[{ required: true }]}>
            <Select>
              <Select.Option value="active">正常</Select.Option>
              <Select.Option value="disabled">禁用</Select.Option>
            </Select>
          </Form.Item>
          
          <Form.Item label="VIP等级" name="vip_level" rules={[{ required: true }]}>
            <Select>
              {[0, 1, 2, 3, 4, 5, 10, 50, 99].map(level => (
                <Select.Option key={level} value={level}>VIP {level}</Select.Option>
              ))}
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
