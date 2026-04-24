/**
 * 超级管理员 - 用户管理页面
 * 数据从数据库获取
 */

import { useState, useEffect } from 'react'
import '../../styles/cyber-theme.css'
import { Table, Tag, Button, Space, Modal, Form, Select, Input, message, Popconfirm } from 'antd'
import { UserOutlined, EditOutlined, DeleteOutlined, SafetyOutlined, SearchOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { userApi, userTypeLabels, userTypeColors, roleLabels, UserListItem } from '../../api/superadmin'

export default function SuperAdminUsers() {
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
    { title: '用户名', dataIndex: 'username', key: 'username' },
    { title: '邮箱', dataIndex: 'email', key: 'email', ellipsis: true },
    { title: '手机', dataIndex: 'phone', key: 'phone' },
    { 
      title: '用户类型', 
      dataIndex: 'user_type', 
      key: 'user_type',
      render: (type: string) => <Tag color={userTypeColors[type]}>{userTypeLabels[type] || type}</Tag>
    },
    { 
      title: '角色', 
      dataIndex: 'role', 
      key: 'role',
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

      <Table 
        columns={columns} 
        dataSource={users} 
        rowKey="id"
        loading={loading}
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
