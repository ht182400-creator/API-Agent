import React, { useState, useEffect } from 'react'
import {
  Card,
  Row,
  Col,
  Statistic,
  Progress,
  Table,
  Space,
  Typography,
  message,
  Spin,
  Tag,
} from 'antd'
import {
  ApartmentOutlined,
  DollarOutlined,
  BarChartOutlined,
  RocketOutlined,
  PieChartOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { billingApi, UserUsage } from '../../api/billing'
import styles from './Usage.module.css'

const { Text } = Typography

interface RepoUsage {
  repo_id: string
  repo_name: string
  call_count: number
  total_tokens: number
  total_cost: number
}

const Usage: React.FC = () => {
  const [loading, setLoading] = useState(true)
  const [usageData, setUsageData] = useState<UserUsage | null>(null)

  // Load usage data
  const loadUsage = async () => {
    setLoading(true)
    try {
      const response = await billingApi.getUsage()
      if (response) {
        setUsageData(response)
      }
    } catch (error) {
      message.error('Failed to load usage data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadUsage()
  }, [])

  // Table columns for repo usage
  const repoColumns: ColumnsType<RepoUsage> = [
    {
      title: 'Repository',
      dataIndex: 'repo_name',
      key: 'repo_name',
      render: (name: string, record) => (
        <Space>
          <Tag color="blue">{name || 'Unknown'}</Tag>
          <Text type="secondary" style={{ fontSize: 11 }}>
            {record.repo_id?.substring(0, 8)}...
          </Text>
        </Space>
      ),
    },
    {
      title: 'API Calls',
      dataIndex: 'call_count',
      key: 'call_count',
      align: 'right',
      sorter: (a, b) => a.call_count - b.call_count,
      render: (count: number) => count?.toLocaleString() || 0,
    },
    {
      title: 'Total Tokens',
      dataIndex: 'total_tokens',
      key: 'total_tokens',
      align: 'right',
      sorter: (a, b) => a.total_tokens - b.total_tokens,
      render: (tokens: number) => tokens?.toLocaleString() || 0,
    },
    {
      title: 'Total Cost',
      dataIndex: 'total_cost',
      key: 'total_cost',
      align: 'right',
      sorter: (a, b) => a.total_cost - b.total_cost,
      render: (cost: number) => (
        <Text type="danger" strong>
          ¥{(cost || 0).toFixed(4)}
        </Text>
      ),
    },
    {
      title: 'Usage %',
      key: 'usage_percent',
      width: 150,
      render: (_, record) => {
        const totalCalls = usageData?.call_count || 1
        const percent = (record.call_count / totalCalls) * 100
        return <Progress percent={percent} size="small" format={() => `${percent.toFixed(1)}%`} />
      },
    },
  ]

  if (loading) {
    return (
      <div className={styles.loading}>
        <Spin size="large" tip="Loading usage data..." />
      </div>
    )
  }

  const byRepository: RepoUsage[] = usageData?.by_repository || []

  return (
    <div className={styles.container}>
      <Card
        title={
          <Space>
            <PieChartOutlined />
            <span>API Usage Overview</span>
          </Space>
        }
      >
        {/* Summary Statistics */}
        <Row gutter={16} className={styles.statsRow}>
          <Col span={6}>
            <Card className={styles.statCard}>
              <Statistic
                title="Total API Calls"
                value={usageData?.call_count || 0}
                prefix={<RocketOutlined />}
                valueStyle={{ color: '#1890ff' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card className={styles.statCard}>
              <Statistic
                title="Total Tokens"
                value={usageData?.total_tokens || 0}
                prefix={<BarChartOutlined />}
                valueStyle={{ color: '#722ed1' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card className={styles.statCard}>
              <Statistic
                title="Total Cost"
                value={usageData?.total_cost || 0}
                precision={4}
                prefix={<DollarOutlined />}
                valueStyle={{ color: '#cf1322' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card className={styles.statCard}>
              <Statistic
                title="Repositories"
                value={byRepository.length}
                prefix={<ApartmentOutlined />}
                valueStyle={{ color: '#52c41a' }}
              />
            </Card>
          </Col>
        </Row>

        {/* Usage by Repository */}
        <div className={styles.section}>
          <h4>Usage by Repository</h4>
          {byRepository.length > 0 ? (
            <Table
              columns={repoColumns}
              dataSource={byRepository}
              rowKey="repo_id"
              pagination={false}
              size="small"
            />
          ) : (
            <div className={styles.empty}>
              <Text type="secondary">No usage data yet</Text>
            </div>
          )}
        </div>
      </Card>
    </div>
  )
}

export default Usage
