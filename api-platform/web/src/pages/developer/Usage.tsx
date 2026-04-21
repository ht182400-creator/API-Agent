/**
 * API 使用概览页面
 * V2.6 更新：支持多种计费模式显示（按次数/按Token/包月）
 */

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
  Empty,
  Tooltip,
} from 'antd'
import {
  ApartmentOutlined,
  DollarOutlined,
  BarChartOutlined,
  RocketOutlined,
  PieChartOutlined,
  CrownOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { billingApi, UserUsage } from '../../api/billing'
import styles from './Usage.module.css'

const { Text } = Typography

// 计费模式枚举
type BillingModel = 'per_call' | 'per_token' | 'subscription'

// 计费模式配置
const BILLING_MODEL_CONFIG = {
  per_call: {
    label: '按次计费',
    icon: <ThunderboltOutlined />,
    color: '#1677ff',
    unit: '次',
  },
  per_token: {
    label: '按Token计费',
    icon: <BarChartOutlined />,
    color: '#722ed1',
    unit: 'Tokens',
  },
  subscription: {
    label: '包月/包年',
    icon: <CrownOutlined />,
    color: '#faad14',
    unit: '月',
  },
}

interface RepoUsage {
  repo_id: string
  repo_name: string
  billing_model: BillingModel
  call_count: number
  total_tokens: number
  total_cost: number
}

const Usage: React.FC = () => {
  const [loading, setLoading] = useState(true)
  const [usageData, setUsageData] = useState<UserUsage | null>(null)
  const [billingModel, setBillingModel] = useState<BillingModel>('per_call')

  // 加载使用量数据
  const loadUsage = async () => {
    setLoading(true)
    try {
      const response = await billingApi.getUsage()
      if (response) {
        setUsageData(response)
        // 根据数据特征自动判断计费模式
        if (response.total_tokens > 0 && response.call_count > 0) {
          // 如果有token使用，可能是per_token模式
          setBillingModel('per_token')
        } else if (response.total_cost > 0) {
          setBillingModel('per_call')
        }
      }
    } catch (error) {
      message.error('加载使用量数据失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadUsage()
  }, [])

  // Table columns for repo usage - 根据计费模式动态显示
  const repoColumns: ColumnsType<RepoUsage> = [
    {
      title: '仓库',
      dataIndex: 'repo_name',
      key: 'repo_name',
      render: (name: string, record) => (
        <Space direction="vertical" size={0}>
          <Space>
            <Tag color="blue">{name || '未知'}</Tag>
            <Tag icon={BILLING_MODEL_CONFIG[record.billing_model || 'per_call'].icon} 
                 color={BILLING_MODEL_CONFIG[record.billing_model || 'per_call'].color === '#1677ff' ? 'blue' : 
                        BILLING_MODEL_CONFIG[record.billing_model || 'per_call'].color === '#722ed1' ? 'purple' : 'gold'}>
              {BILLING_MODEL_CONFIG[record.billing_model || 'per_call'].label}
            </Tag>
          </Space>
          <Text type="secondary" style={{ fontSize: 11 }}>
            ID: {record.repo_id?.substring(0, 8)}...
          </Text>
        </Space>
      ),
    },
    {
      title: 'API 调用次数',
      dataIndex: 'call_count',
      key: 'call_count',
      align: 'right',
      sorter: (a, b) => a.call_count - b.call_count,
      render: (count: number) => (
        <Text strong>{count?.toLocaleString() || 0}</Text>
      ),
    },
    // 根据计费模式显示/隐藏Token列
    ...(billingModel === 'per_token' ? [{
      title: '总 Tokens',
      dataIndex: 'total_tokens',
      key: 'total_tokens',
      align: 'right',
      sorter: (a: RepoUsage, b: RepoUsage) => a.total_tokens - b.total_tokens,
      render: (tokens: number) => (
        <Tooltip title={`${tokens?.toLocaleString() || 0} Tokens`}>
          <Text style={{ color: '#722ed1' }}>
            {(tokens || 0).toLocaleString()}
          </Text>
        </Tooltip>
      ),
    }] : []),
    {
      title: '总费用',
      dataIndex: 'total_cost',
      key: 'total_cost',
      align: 'right',
      sorter: (a, b) => a.total_cost - b.total_cost,
      render: (cost: number) => (
        <Text type="danger" strong>
          ¥{(cost || 0).toFixed(billingModel === 'per_token' ? 4 : 2)}
        </Text>
      ),
    },
    {
      title: '使用占比',
      key: 'usage_percent',
      width: 150,
      render: (_, record) => {
        const totalCalls = usageData?.call_count || 1
        const percent = (record.call_count / totalCalls) * 100
        return (
          <Progress 
            percent={percent} 
            size="small" 
            format={() => `${percent.toFixed(1)}%`}
            strokeColor={percent > 50 ? '#1677ff' : '#52c41a'}
          />
        )
      },
    },
  ]

  if (loading) {
    return (
      <div className={styles.loading}>
        <Spin size="large" tip="正在加载使用量数据..." />
      </div>
    )
  }

  const byRepository: RepoUsage[] = (usageData?.by_repository || []).map(r => ({
    ...r,
    billing_model: r.total_tokens > 0 ? 'per_token' as BillingModel : 'per_call' as BillingModel,
  }))

  // 统计卡片配置
  const statCards = [
    {
      title: 'API 调用次数',
      value: usageData?.call_count || 0,
      icon: <RocketOutlined />,
      color: '#1677ff',
      bgColor: '#e6f4ff',
      suffix: '次',
    },
    ...(billingModel === 'per_token' ? [{
      title: '总 Tokens',
      value: usageData?.total_tokens || 0,
      icon: <BarChartOutlined />,
      color: '#722ed1',
      bgColor: '#f9f0ff',
      suffix: '',
    }] : []),
    {
      title: '总费用',
      value: usageData?.total_cost || 0,
      icon: <DollarOutlined />,
      color: '#ff4d4f',
      bgColor: '#fff1f0',
      suffix: '元',
    },
    {
      title: '仓库数',
      value: byRepository.length,
      icon: <ApartmentOutlined />,
      color: '#52c41a',
      bgColor: '#f6ffed',
      suffix: '个',
    },
  ]

  return (
    <div className={styles.container}>
      <Card
        title={
          <Space>
            <PieChartOutlined />
            <span>API 使用概览</span>
          </Space>
        }
        extra={
          <Space>
            <Text type="secondary">计费模式：</Text>
            <Tag icon={BILLING_MODEL_CONFIG[billingModel].icon} 
                 color={billingModel === 'per_call' ? 'blue' : 
                        billingModel === 'per_token' ? 'purple' : 'gold'}>
              {BILLING_MODEL_CONFIG[billingModel].label}
            </Tag>
          </Space>
        }
      >
        {/* Summary Statistics - 现代化卡片 */}
        <Row gutter={16} className={styles.statsRow}>
          {statCards.map((stat, index) => (
            <Col span={billingModel === 'per_token' ? 6 : 8} key={index}>
              <Card className={styles.statCard} style={{ borderTop: `3px solid ${stat.color}` }}>
                <div className={styles.statCardIcon} style={{ backgroundColor: stat.bgColor }}>
                  <span style={{ color: stat.color }}>{stat.icon}</span>
                </div>
                <Statistic
                  title={stat.title}
                  value={stat.value}
                  precision={stat.value > 10000 ? 0 : 2}
                  suffix={stat.suffix}
                  valueStyle={{ color: stat.color, fontSize: 22 }}
                />
              </Card>
            </Col>
          ))}
        </Row>

        {/* 费用说明 */}
        <div className={styles.billingInfo}>
          <Text type="secondary">
            {billingModel === 'per_call' && '💡 按次计费：每次API调用计费，与Token使用量无关'}
            {billingModel === 'per_token' && '💡 按Token计费：根据实际使用的Token数量计费'}
            {billingModel === 'subscription' && '💡 包月/包年：在有效期内不限次数使用'}
          </Text>
        </div>

        {/* Usage by Repository */}
        <div className={styles.section}>
          <h4>按仓库使用量</h4>
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
              <Empty description="暂无使用数据，开始调用API后将显示详细统计" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            </div>
          )}
        </div>
      </Card>
    </div>
  )
}

export default Usage
