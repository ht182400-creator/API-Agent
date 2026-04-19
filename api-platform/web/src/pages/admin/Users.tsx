/**
 * 用户管理页面
 */

import { useState, useEffect } from 'react'
import { Table, Button, Input, Select, Tag, Space, Modal, message, Typography, Popconfirm } from 'antd'
import { SearchOutlined, LockOutlined, DeleteOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { adminUserApi } from '../../api/admin'
import { UserListItem } from '../../api/superadmin'
import styles from './Users.module.css'

const { Title } = Typography

// 用户类型映射
const userTypeMap: Record<string, { label: string; color: string }> = {
  super_admin: { label: '超级管理员', color: 'red' },
  admin: { label: '管理员', color: 'orange' },
  owner: { label: '仓库所有者', color: 'blue' },
  developer: { label: '开发者', color: 'green' },
  user: { label: '普通用户', color: 'default' },
}

// 用户状态映射
const userStatusMap: Record<string, { label: string; color: string }> = {
  active: { label: '正常', color: 'green' },
  inactive: { label: '未激活', color: 'orange' },
  suspended: { label: '已禁用', color: 'red' },
  deleted: { label: '已删除', color: 'default' },
}

export default function AdminUsers() {
  const [loading, setLoading] = useState(false)
  const [users, setUsers] = useState<UserListItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [searchText, setSearchText] = useState('')
  const [userTypeFilter, setUserTypeFilter] = useState<string | undefined>(undefined)
  const [userStatusFilter, setUserStatusFilter] = useState<string | undefined>(undefined)

  // 加载用户列表
  const loadUsers = async () => {
    setLoading(true)
    try {
      const res = await adminUserApi.list({
        page,
        page_size: pageSize,
        keyword: searchText || undefined,
        user_type: userTypeFilter,
        user_status: userStatusFilter,
      })
      setUsers(res.items || [])
      setTotal(res.total || 0)
    } catch (err: any) {
      console.error('加载用户列表失败', err)
      message.error(err.userMessage || err.message || '加载失败')
    } finally {
      setLoading(false)
    }
  }

  // 初始加载和分页/筛选变化时重新加载
  useEffect(() => {
    loadUsers()
  }, [page, pageSize, userTypeFilter, userStatusFilter])

  // 搜索处理（防抖）
  useEffect(() => {
    const timer = setTimeout(() => {
      if (page !== 1) {
        setPage(1)
      } else {
        loadUsers()
      }
    }, 300)
    return () => clearTimeout(timer)
  }, [searchText])

  // 处理禁用用户
  const handleToggleStatus = async (user: UserListItem) => {
    try {
      const newStatus = user.user_status === 'active' ? 'suspended' : 'active'
      await adminUserApi.update(user.id, { user_status: newStatus })
      message.success(newStatus === 'active' ? '已启用该用户' : '已禁用该用户')
      loadUsers()
    } catch (err: any) {
      message.error(err.userMessage || err.message || '操作失败')
    }
  }

  // 处理删除用户
  const handleDeleteUser = async (userId: string) => {
    try {
      await adminUserApi.delete(userId)
      message.success('用户已删除')
      loadUsers()
    } catch (err: any) {
      message.error(err.userMessage || err.message || '删除失败')
    }
  }

  const columns = [
    { title: '用户名', dataIndex: 'username', key: 'username', width: 120 },
    { title: 'ID', dataIndex: 'id', key: 'id', width: 220, ellipsis: true },
    { title: '邮箱', dataIndex: 'email', key: 'email' },
    { 
      title: '类型', 
      dataIndex: 'user_type', 
      key: 'user_type', 
      width: 100,
      render: (t: string) => {
        const config = userTypeMap[t] || { label: t, color: 'default' }
        return <Tag color={config.color}>{config.label}</Tag>
      }
    },
    { 
      title: '状态', 
      dataIndex: 'user_status', 
      key: 'user_status',
      width: 80,
      render: (s: string) => {
        const config = userStatusMap[s] || { label: s, color: 'default' }
        return <Tag color={config.color}>{config.label}</Tag>
      }
    },
    { 
      title: 'VIP等级', 
      dataIndex: 'vip_level', 
      key: 'vip_level',
      width: 80,
      render: (l: number) => l > 0 ? <Tag color="gold">VIP {l}</Tag> : '-'
    },
    { 
      title: '注册时间', 
      dataIndex: 'created_at', 
      key: 'created_at',
      width: 160,
      render: (d: string) => d ? dayjs(d).format('YYYY-MM-DD HH:mm') : '-'
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_: any, record: UserListItem) => (
        <Space size="small">
          <Popconfirm
            title="确认禁用？"
            description="禁用后该用户将无法登录"
            onConfirm={() => handleToggleStatus(record)}
            okText="确认"
            cancelText="取消"
          >
            <Button 
              type="text" 
              size="small" 
              icon={<LockOutlined />}
              danger={record.user_status === 'active'}
            >
              {record.user_status === 'active' ? '禁用' : '启用'}
            </Button>
          </Popconfirm>
          <Popconfirm
            title="确认删除？"
            description="删除后数据无法恢复"
            onConfirm={() => handleDeleteUser(record.id)}
            okText="确认"
            cancelText="取消"
            okButtonProps={{ danger: true }}
          >
            <Button 
              type="text" 
              size="small" 
              icon={<DeleteOutlined />}
              danger
            >
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <Title level={4}>用户管理</Title>
        <Space>
          <Input
            placeholder="搜索用户名/邮箱..."
            prefix={<SearchOutlined />}
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            style={{ width: 200 }}
            allowClear
          />
          <Select 
            placeholder="用户类型" 
            style={{ width: 120 }} 
            allowClear
            value={userTypeFilter}
            onChange={(v) => {
              setUserTypeFilter(v)
              setPage(1)
            }}
          >
            <Select.Option value="owner">仓库所有者</Select.Option>
            <Select.Option value="developer">开发者</Select.Option>
            <Select.Option value="user">普通用户</Select.Option>
          </Select>
          <Select 
            placeholder="用户状态" 
            style={{ width: 100 }} 
            allowClear
            value={userStatusFilter}
            onChange={(v) => {
              setUserStatusFilter(v)
              setPage(1)
            }}
          >
            <Select.Option value="active">正常</Select.Option>
            <Select.Option value="inactive">未激活</Select.Option>
            <Select.Option value="suspended">已禁用</Select.Option>
          </Select>
        </Space>
      </div>

      <Table
        dataSource={users}
        columns={columns}
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
    </div>
  )
}
