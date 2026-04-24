/**
 * 调用日志页面
 * V2.6 更新：现代化UI设计，改进数据展示
 */

import { useState, useEffect } from 'react'
import '../../styles/cyber-theme.css'
import { Table, Card, Select, DatePicker, Button, Typography, Tag, Space, Empty, Tooltip, Badge } from 'antd'
import { ReloadOutlined, FilterOutlined, ClockCircleOutlined } from '@ant-design/icons'
import { quotaApi, APICallLog, APIKey } from '../../api/quota'
import { useErrorModal } from '../../components/ErrorModal'
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
  const [keys, setKeys] = useState<APIKey[]>([])
  const [filters, setFilters] = useState({
    key_id: undefined as string | undefined,
    repo_id: undefined as string | undefined,
    start_date: undefined as string | undefined,
    end_date: undefined as string | undefined,
  })

  const { showError, closeError, ErrorModal: ErrorModalComponent } = useErrorModal()

  // 加载 API Key 列表
  useEffect(() => {
    const fetchKeys = async () => {
      try {
        const data = await quotaApi.getKeys({ page_size: 100 })
        setKeys(data.items)
      } catch (error: any) {
        // 忽略错误，不影响页面显示
      }
    }
    fetchKeys()
  }, [])

  useEffect(() => {
    fetchLogs()
  }, [page, pageSize, filters])

  const fetchLogs = async () => {
    setLoading(true)
    try {
      const data = await quotaApi.getLogs({
        page,
        page_size: pageSize,
        ...filters,
      })
      setLogs(data.items)
      setTotal(data.pagination.total)
    } catch (error: any) {
      showError(error, () => fetchLogs())
    } finally {
      setLoading(false)
    }
  }

  const handleFilterChange = (key: string, value: any) => {
    if (value === 'all') {
      value = undefined
    }
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

  const getStatusColor = (status: number | undefined) => {
    if (!status) return 'default'
    if (status >= 200 && status < 300) return 'success'
    if (status >= 400 && status < 500) return 'warning'
    if (status >= 500) return 'error'
    return 'default'
  }

  const getStatusText = (status: number | undefined) => {
    if (!status) return '未知'
    if (status >= 200 && status < 300) return `${status} 成功`
    if (status >= 400 && status < 500) return `${status} 客户端错误`
    if (status >= 500) return `${status} 服务端错误`
    return status.toString()
  }

  const getResponseTimeColor = (time: number | undefined) => {
    if (!time) return undefined
    if (time > 2000) return 'error'
    if (time > 1000) return 'warning'
    if (time > 500) return 'gold'
    return 'processing'
  }

  const columns = [
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 170,
      render: (date: string) => (
        <Tooltip title={dayjs(date).format('YYYY-MM-DD HH:mm:ss')}>
          <Space>
            <ClockCircleOutlined style={{ color: '#8c8c8c' }} />
            <Text>{dayjs(date).format('MM-DD HH:mm:ss')}</Text>
          </Space>
        </Tooltip>
      ),
    },
    {
      title: '仓库',
      dataIndex: 'repo_name',
      key: 'repo_name',
      width: 130,
      render: (name: string) => (
        <Tag color="blue">{name || '未知'}</Tag>
      ),
    },
    {
      title: '接口',
      dataIndex: 'endpoint',
      key: 'endpoint',
      ellipsis: true,
      render: (endpoint: string) => (
        <Tooltip title={endpoint}>
          <Text code style={{ fontSize: 12 }}>
            {endpoint?.length > 30 ? endpoint.substring(0, 30) + '...' : endpoint}
          </Text>
        </Tooltip>
      ),
    },
    {
      title: '方法',
      dataIndex: 'method',
      key: 'method',
      width: 80,
      render: (method: string) => {
        const colorMap: Record<string, string> = {
          GET: 'blue',
          POST: 'green',
          PUT: 'orange',
          DELETE: 'red',
          PATCH: 'purple',
        }
        return <Tag color={colorMap[method] || 'default'}>{method}</Tag>
      },
    },
    {
      title: '状态',
      dataIndex: 'response_status',
      key: 'response_status',
      width: 130,
      render: (status: number) => (
        <Badge status={getStatusColor(status) as any} text={getStatusText(status)} />
      ),
    },
    {
      title: '响应时间',
      dataIndex: 'response_time',
      key: 'response_time',
      width: 110,
      align: 'right' as const,
      render: (time: number | undefined) => (
        <Tooltip title={time ? `响应耗时: ${time}ms` : '未知'}>
          <Badge status={getResponseTimeColor(time) as any} text={time ? `${time}ms` : '-'} />
        </Tooltip>
      ),
    },
    {
      title: 'IP地址',
      dataIndex: 'ip_address',
      key: 'ip_address',
      width: 130,
      render: (ip: string) => (
        <Text type="secondary" style={{ fontSize: 12 }}>{ip || '-'}</Text>
      ),
    },
    {
      title: '请求ID',
      dataIndex: 'request_id',
      key: 'request_id',
      width: 140,
      render: (requestId: string | null, record: any) => {
        // 优先显示 request_id，没有则降级到 id
        const displayId = requestId || record.id
        return (
          <Tooltip title={displayId}>
            <Text copyable={{ text: displayId, tooltips: '复制ID' }} style={{ fontSize: 11 }}>
              {displayId?.substring(0, 16)}...
            </Text>
          </Tooltip>
        )
      },
    },
  ]

  return (
    <div className={`${styles.container} bamboo-bg-pattern`}>
      <ErrorModalComponent />

      <div className={styles.header}>
        <Title level={4}>调用日志</Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchLogs} loading={loading}>
            刷新
          </Button>
        </Space>
      </div>

      <Card className={styles.filterCard}>
        <Space wrap align="center">
          <Space>
            <FilterOutlined style={{ color: '#8c8c8c' }} />
            <Text type="secondary">筛选条件</Text>
          </Space>
          <Select
            placeholder="选择API Key"
            allowClear
            style={{ width: 200 }}
            value={filters.key_id}
            onChange={(value) => handleFilterChange('key_id', value)}
          >
            <Select.Option value="all">全部 Keys</Select.Option>
            {keys.map(key => (
              <Select.Option key={key.id} value={key.id}>
                {key.key_name || key.key_prefix}
              </Select.Option>
            ))}
          </Select>
          <RangePicker onChange={handleDateChange} />
          {filters.start_date && (
            <Button size="small" onClick={() => {
              setFilters({ key_id: undefined, repo_id: undefined, start_date: undefined, end_date: undefined })
              setPage(1)
            }}>
              清除筛选
            </Button>
          )}
        </Space>
      </Card>

      <Card className={styles.tableCard}>
        <div className={styles.tableHeader}>
          <Space>
            <Text type="secondary">共</Text>
            <Text strong>{total.toLocaleString()}</Text>
            <Text type="secondary">条记录</Text>
          </Space>
        </div>
        
        <Table
          dataSource={logs}
          columns={columns}
          rowKey="id"
          loading={loading}
          scroll={{ x: 1100 }}
          locale={{ 
            emptyText: (
              <Empty 
                description={
                  <Space direction="vertical">
                    <Text>暂无调用日志</Text>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      开始使用API后将自动记录调用日志
                    </Text>
                  </Space>
                } 
                image={Empty.PRESENTED_IMAGE_SIMPLE} 
              />
            )
          }}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 条`,
            pageSizeOptions: ['10', '20', '50', '100'],
            onChange: (p, ps) => {
              setPage(p)
              setPageSize(ps)
            },
          }}
        />
      </Card>
    </div>
  )
}
