/**
 * 仓库管理页面
 */

import { Table, Tag, Typography } from 'antd'
import { useState } from 'react'
import styles from './Repos.module.css'

const { Title } = Typography

export default function AdminRepos() {
  const [loading] = useState(false)

  // 示例数据
  const repos = [
    { id: '1', name: 'psychology-api', owner: 'owner@example.com', category: 'ai', status: 'active', calls: 12500 },
    { id: '2', name: 'translate-api', owner: 'owner@example.com', category: 'translate', status: 'active', calls: 8500 },
    { id: '3', name: 'vision-api', owner: 'owner2@example.com', category: 'vision', status: 'inactive', calls: 0 },
  ]

  const columns = [
    { title: '仓库名称', dataIndex: 'name', key: 'name' },
    { title: '所有者', dataIndex: 'owner', key: 'owner' },
    { title: '分类', dataIndex: 'category', key: 'category', render: (c: string) => <Tag>{c}</Tag> },
    { title: '状态', dataIndex: 'status', key: 'status', render: (s: string) => <Tag color={s === 'active' ? 'green' : 'orange'}>{s}</Tag> },
    { title: '总调用', dataIndex: 'calls', key: 'calls', render: (c: number) => c.toLocaleString() },
  ]

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <Title level={4}>仓库管理</Title>
      </div>

      <Table
        dataSource={repos}
        columns={columns}
        rowKey="id"
        loading={loading}
        pagination={{ pageSize: 20 }}
      />
    </div>
  )
}
