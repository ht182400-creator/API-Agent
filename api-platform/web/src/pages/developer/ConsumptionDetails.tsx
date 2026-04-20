import React, { useState, useEffect } from 'react'
import {
  Card,
  Table,
  Space,
  DatePicker,
  Select,
  Button,
  Statistic,
  Row,
  Col,
  message,
  Tag,
  Typography,
} from 'antd'
import {
  BarChartOutlined,
  DollarOutlined,
  ApartmentOutlined,
  SearchOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { billingApi, ConsumptionDetail } from '../../api/billing'
import styles from './ConsumptionDetails.module.css'

const { RangePicker } = DatePicker
const { Text } = Typography

const ConsumptionDetails: React.FC = () => {
  const [loading, setLoading] = useState(false)
  const [details, setDetails] = useState<ConsumptionDetail[]>([])
  const [pagination, setPagination] = useState({
    page: 1,
    page_size: 20,
    total: 0,
  })
  const [dateRange, setDateRange] = useState<[string | null, string | null]>([null, null])
  const [summaryStats, setSummaryStats] = useState({
    total_calls: 0,
    total_tokens: 0,
    total_cost: 0,
  })

  // Load consumption details
  const loadDetails = async () => {
    setLoading(true)
    try {
      const params: any = {
        page: pagination.page,
        page_size: pagination.page_size,
      }

      if (dateRange[0]) params.start_date = dateRange[0]
      if (dateRange[1]) params.end_date = dateRange[1]

      const response = await billingApi.getConsumptionDetails(params)
      if (response) {
        setDetails(response.items || [])
        setPagination({
          ...pagination,
          total: response.pagination?.total || 0,
        })

        // Calculate summary
        const items = response.items || []
        const summary = {
          total_calls: items.length,
          total_tokens: items.reduce((sum, item) => sum + (item.tokens_used || 0), 0),
          total_cost: items.reduce((sum, item) => sum + (item.cost || 0), 0),
        }
        setSummaryStats(summary)
      }
    } catch (error) {
      message.error('Failed to load consumption details')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadDetails()
  }, [pagination.page, pagination.page_size])

  // Table columns
  const columns: ColumnsType<ConsumptionDetail> = [
    {
      title: 'Time',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (time: string) => {
        const date = new Date(time)
        return (
          <span>
            {date.toLocaleDateString()} {date.toLocaleTimeString()}
          </span>
        )
      },
    },
    {
      title: 'Repo',
      dataIndex: 'repo_name',
      key: 'repo_name',
      width: 150,
      ellipsis: true,
      render: (name: string) => <Tag color="blue">{name || 'Unknown'}</Tag>,
    },
    {
      title: 'Endpoint',
      dataIndex: 'endpoint',
      key: 'endpoint',
      ellipsis: true,
      render: (endpoint: string) => (
        <Text code style={{ fontSize: 11 }}>
          {endpoint || '-'}
        </Text>
      ),
    },
    {
      title: 'Tokens Used',
      dataIndex: 'tokens_used',
      key: 'tokens_used',
      width: 120,
      align: 'right',
      render: (tokens: number) => tokens?.toLocaleString() || 0,
    },
    {
      title: 'Cost',
      dataIndex: 'cost',
      key: 'cost',
      width: 100,
      align: 'right',
      render: (cost: number) => (
        <Text type={cost > 0 ? 'danger' : 'secondary'}>
          ¥{(cost || 0).toFixed(4)}
        </Text>
      ),
    },
  ]

  // Handle date range change
  const handleDateChange = (dates: any, dateStrings: [string, string]) => {
    setDateRange(dateStrings)
  }

  // Handle search
  const handleSearch = () => {
    setPagination({ ...pagination, page: 1 })
    loadDetails()
  }

  // Handle reset
  const handleReset = () => {
    setDateRange([null, null])
    setPagination({ ...pagination, page: 1 })
    loadDetails()
  }

  return (
    <div className={styles.container}>
      <Card
        title={
          <Space>
            <BarChartOutlined />
            <span>Consumption Details</span>
          </Space>
        }
      >
        {/* Summary Statistics */}
        <Row gutter={16} className={styles.statsRow}>
          <Col span={8}>
            <Card className={styles.statCard}>
              <Statistic
                title="Total API Calls"
                value={summaryStats.total_calls}
                prefix={<ApartmentOutlined />}
              />
            </Card>
          </Col>
          <Col span={8}>
            <Card className={styles.statCard}>
              <Statistic
                title="Total Tokens"
                value={summaryStats.total_tokens}
                prefix={<BarChartOutlined />}
              />
            </Card>
          </Col>
          <Col span={8}>
            <Card className={styles.statCard}>
              <Statistic
                title="Total Cost"
                value={summaryStats.total_cost}
                precision={4}
                prefix={<DollarOutlined />}
                valueStyle={{ color: '#cf1322' }}
              />
            </Card>
          </Col>
        </Row>

        {/* Filters */}
        <div className={styles.filters}>
          <Space>
            <RangePicker onChange={handleDateChange} />
            <Button type="primary" icon={<SearchOutlined />} onClick={handleSearch}>
              Search
            </Button>
            <Button icon={<ReloadOutlined />} onClick={handleReset}>
              Reset
            </Button>
          </Space>
        </div>

        {/* Table */}
        <Table
          columns={columns}
          dataSource={details}
          rowKey="id"
          loading={loading}
          pagination={{
            current: pagination.page,
            pageSize: pagination.page_size,
            total: pagination.total,
            showSizeChanger: true,
            showTotal: (total) => `Total ${total}`,
            onChange: (page, pageSize) => setPagination({ ...pagination, page, page_size: pageSize }),
          }}
        />
      </Card>
    </div>
  )
}

export default ConsumptionDetails
