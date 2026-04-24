/**
 * 开发工具页面 - 日志查看器
 */

import { useState } from 'react'
import '../../styles/cyber-theme.css'
import { Card, Table, Button, Space, Select, Tag, Empty, Popconfirm, message } from 'antd'
import { ReloadOutlined, DeleteOutlined, DownloadOutlined } from '@ant-design/icons'
import { log } from '../../utils/logger'

interface LogEntry {
  timestamp: string
  level: string
  message: string
}

const levelColors: Record<string, string> = {
  DEBUG: 'default',
  INFO: 'blue',
  WARN: 'orange',
  ERROR: 'red',
}

export default function DevTools() {
  const [logs, setLogs] = useState<LogEntry[]>(() => log.getLogs())
  const [levelFilter, setLevelFilter] = useState<string>('all')

  const filteredLogs = levelFilter === 'all' 
    ? logs 
    : logs.filter(l => l.level === levelFilter)

  const handleRefresh = () => {
    setLogs(log.getLogs())
  }

  const handleClear = () => {
    log.clear()
    setLogs([])
    message.success('日志已清除')
  }

  const handleExport = () => {
    const content = log.export()
    const blob = new Blob([content], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `app-logs-${new Date().toISOString().slice(0, 10)}.txt`
    a.click()
    URL.revokeObjectURL(url)
    message.success('日志已导出')
  }

  const columns = [
    {
      title: '时间',
      dataIndex: 'timestamp',
      key: 'timestamp',
      width: 200,
      render: (text: string) => (
        <span style={{ fontSize: 12, color: '#666' }}>
          {new Date(text).toLocaleString()}
        </span>
      ),
    },
    {
      title: '级别',
      dataIndex: 'level',
      key: 'level',
      width: 80,
      render: (level: string) => (
        <Tag color={levelColors[level]}>{level}</Tag>
      ),
    },
    {
      title: '消息',
      dataIndex: 'message',
      key: 'message',
      ellipsis: true,
      render: (text: string) => (
        <span style={{ fontFamily: 'monospace', fontSize: 12 }}>{text}</span>
      ),
    },
  ]

  return (
    <div style={{ padding: 24 }} className="bamboo-bg-pattern">
      <Card
        title="📋 应用日志"
        extra={
          <Space>
            <Select
              value={levelFilter}
              onChange={setLevelFilter}
              style={{ width: 100 }}
              options={[
                { value: 'all', label: '全部' },
                { value: 'DEBUG', label: 'DEBUG' },
                { value: 'INFO', label: 'INFO' },
                { value: 'WARN', label: 'WARN' },
                { value: 'ERROR', label: 'ERROR' },
              ]}
            />
            <Button icon={<ReloadOutlined />} onClick={handleRefresh}>
              刷新
            </Button>
            <Popconfirm title="确定清除所有日志？" onConfirm={handleClear}>
              <Button icon={<DeleteOutlined />}>清除</Button>
            </Popconfirm>
            <Button icon={<DownloadOutlined />} onClick={handleExport}>
              导出
            </Button>
          </Space>
        }
      >
        {filteredLogs.length === 0 ? (
          <Empty description="暂无日志" />
        ) : (
          <Table
            dataSource={[...filteredLogs].reverse()}
            columns={columns}
            rowKey={(record, index) => `${record.timestamp}-${index}`}
            size="small"
            pagination={{ pageSize: 20 }}
            scroll={{ y: 500 }}
          />
        )}
      </Card>
    </div>
  )
}
