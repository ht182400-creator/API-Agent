/**
 * 用户管理页面
 */

import { useState } from 'react'
import { Table, Button, Input, Select, Tag, Space, Modal, message, Typography } from 'antd'
import { SearchOutlined, UserOutlined, LockOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import dayjs from 'dayjs'
import styles from './Users.module.css'

const { Title, Text } = Typography

export default function AdminUsers() {
  const navigate = useNavigate()
  const [loading] = useState(false)
  const [searchText, setSearchText] = useState('')

  // 示例数据
  const users = [
    { id: '1', email: 'admin@example.com', user_type: 'admin', user_status: 'active', vip_level: 99, created_at: '2024-01-01' },
    { id: '2', email: 'owner@example.com', user_type: 'owner', user_status: 'active', vip_level: 5, created_at: '2024-01-15' },
    { id: '3', email: 'developer@example.com', user_type: 'developer', user_status: 'active', vip_level: 0, created_at: '2024-02-01' },
  ]

  const columns = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 200, ellipsis: true },
    { title: '邮箱', dataIndex: 'email', key: 'email' },
    { title: '类型', dataIndex: 'user_type', key: 'user_type', render: (t: string) => <Tag color={t === 'admin' ? 'red' : t === 'owner' ? 'blue' : 'default'}>{t}</Tag> },
    { title: '状态', dataIndex: 'user_status', key: 'user_status', render: (s: string) => <Tag color={s === 'active' ? 'green' : 'red'}>{s}</Tag> },
    { title: 'VIP等级', dataIndex: 'vip_level', key: 'vip_level', render: (l: number) => l > 0 ? <Tag color="gold">VIP {l}</Tag> : '-' },
    { title: '注册时间', dataIndex: 'created_at', key: 'created_at' },
    {
      title: '操作',
      key: 'action',
      render: () => (
        <Space>
          <Button type="text" size="small" icon={<LockOutlined />}>禁用</Button>
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
            placeholder="搜索邮箱..."
            prefix={<SearchOutlined />}
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            style={{ width: 200 }}
          />
          <Select placeholder="用户类型" style={{ width: 120 }} allowClear>
            <Select.Option value="admin">管理员</Select.Option>
            <Select.Option value="owner">仓库所有者</Select.Option>
            <Select.Option value="developer">开发者</Select.Option>
          </Select>
        </Space>
      </div>

      <Table
        dataSource={users}
        columns={columns}
        rowKey="id"
        loading={loading}
        pagination={{ pageSize: 20 }}
      />
    </div>
  )
}
