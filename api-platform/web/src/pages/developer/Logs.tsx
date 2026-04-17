/**
 * 调用日志页面
 */

import { useState, useEffect } from 'react'
import { Table, Card, Select, DatePicker, Button, Typography, Tag, Space } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import { quotaApi, APICallLog } from '../../api/quota'
import dayjs from 'dayjs'
import styles from './Logs.module.css'

const { Title, Text } = Typography
const { RangePicker } = DatePicker

export default function DeveloperLogs() {
  const [loading, setLoading] = useState(false)
  const [logs, setLogs] = useState<APICallLog[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [filters, setFilters] = useState({
    key_id: undefined as string | undefined,
    repo_id: undefined as string | undefined,
    start_date: undefined as string | undefined,
    end_date: undefined as string | undefined,
  })

  useEffect(() => {
    fetchLogs()
  }, [page, pageSize, filters])

  const fetchLogs = async () => {
    setLoading(true)
    try {
      const { data } = await quotaApi.getLogs({
        page,
        page_size: pageSize,
        ...filters,
      })
      setLogs(data.items)
      setTotal(data.total)
    } catch (error) {
      console.error('获取日志失败:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleFilterChange = (key: string, value: any) => {
    setFilters((prev) => ({ ...prev, [key]: value }))
    setPage(1)
  }

  const handleDateChange = (dates: any) => {
    if (dates) {
      setFilters((prev) => ({
        ...prev,
        start_date: dates[0].format('YYYY-MM-DD'),
        end_date: dates[1].format('YYYY-MM-DD'),
      }))
    } else {
      setFilters((prev) => ({
        ...prev,
        start_date: undefined,
        end_date: undefined,
      }))
    }
    setPage(1)
  }

  const getStatusColor = (status: number) => {
    if (status >= 200 && status < 300) return 'success'
    if (status >= 400 && status < 500) return 'warning'
    if (status >= 500) return 'error'
    return 'default'
  }

  const columns = [
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (date: string) => dayjs(date).format('YYYY-MM-DD HH:mm:ss'),
    },
    {
      title: '仓库',
      dataIndex: 'repo_name',
      key: 'repo_name',
      width: 120,
    },
    {
      title: '接口',
      dataIndex: 'endpoint',
      key: 'endpoint',
      ellipsis: true,
    },
    {
      title: '方法',
      dataIndex: 'method',
      key: 'method',
      width: 80,
      render: (method: string) => (
        <Tag color={method === 'GET' ? 'blue' : method === 'POST' ? 'green' : 'orange'}>
          {method}
        </Tag>
      ),
    },
    {
      title: '状态',
      dataIndex: 'response_status',
      key: 'response_status',
      width: 100,
      render: (status: number) => (
        <Tag color={getStatusColor(status)}>{status}</Tag>
      ),
    },
    {
      title: '响应时间',
      dataIndex: 'response_time',
      key: 'response_time',
      width: 100,
      render: (time: number) => (
        <Text type={time > 1000 ? 'danger' : time > 500 ? 'warning' : undefined}>
          {time}ms
        </Text>
      ),
    },
    {
      title: 'IP地址',
      dataIndex: 'ip_address',
      key: 'ip_address',
      width: 140,
    },
    {
      title: '请求ID',
      dataIndex: 'id',
      key: 'id',
      width: 200,
      ellipsis: true,
      render: (id: string) => <Text copyable={{ text: id }}>{id.substring(0, 16)}...</Text>,
    },
  ]

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <Title level={4}>调用日志</Title>
        <Button icon={<ReloadOutlined />} onClick={fetchLogs}>
          刷新
        </Button>
      </div>

      <Card className={styles.filterCard}>
        <Space wrap>
          <Select
            placeholder="选择API Key"
            allowClear
            style={{ width: 200 }}
            onChange={(value) => handleFilterChange('key_id', value)}
          >
            <Select.Option value="all">全部 Keys</Select.Option>
          </Select>
          <RangePicker onChange={handleDateChange} />
        </Space>
      </Card>

      <Table
        dataSource={logs}
        columns={columns}
        rowKey="id"
        loading={loading}
        pagination={{
          current: page,
          pageSize,
          total,
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (total) => `共 ${total} 条`,
          onChange: (p, ps) => {
            setPage(p)
            setPageSize(ps)
          },
        }}
        scroll={{ x: 1200 }}
      />
    </div>
  )
}
