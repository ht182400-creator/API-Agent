/**
 * 仓库详情页面
 * 展示仓库的端点列表、限流配置、定价信息
 */

import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { Card, Descriptions, Table, Tag, Button, Space, Typography, Row, Col, Statistic, Alert, Spin, Breadcrumb, Tooltip } from 'antd'
import { 
  ApiOutlined, 
  SafetyCertificateOutlined, 
  DollarOutlined, 
  ThunderboltOutlined,
  ArrowLeftOutlined,
  GlobalOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined
} from '@ant-design/icons'
import { repoApi, Repository, RepositoryEndpoint, RepositoryLimits } from '../../api/repo'
import { useError } from '../../contexts/ErrorContext'
import styles from './RepoDetail.module.css'

const { Title, Text, Paragraph } = Typography

export default function RepoDetail() {
  const { slug } = useParams<{ slug: string }>()
  const [repo, setRepo] = useState<Repository | null>(null)
  const [loading, setLoading] = useState(true)
  const { showError } = useError()

  useEffect(() => {
    if (slug) {
      fetchRepoDetail(slug)
    }
  }, [slug])

  const fetchRepoDetail = async (repoSlug: string) => {
    setLoading(true)
    try {
      const data = await repoApi.get(repoSlug)
      setRepo(data)
    } catch (error: any) {
      showError(error, () => fetchRepoDetail(repoSlug))
    } finally {
      setLoading(false)
    }
  }

  // 获取HTTP方法对应的颜色
  const getMethodColor = (method: string) => {
    const colors: Record<string, string> = {
      GET: 'green',
      POST: 'blue',
      PUT: 'orange',
      DELETE: 'red',
      PATCH: 'purple'
    }
    return colors[method] || 'default'
  }

  // 端点列定义
  const endpointColumns = [
    {
      title: '方法',
      dataIndex: 'method',
      key: 'method',
      width: 100,
      render: (method: string) => (
        <Tag color={getMethodColor(method)}>{method}</Tag>
      )
    },
    {
      title: '路径',
      dataIndex: 'path',
      key: 'path',
      render: (path: string) => (
        <Text code style={{ fontSize: 13 }}>{path}</Text>
      )
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (desc: string) => desc || '-'
    },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      width: 120,
      render: (category: string) => category ? <Tag>{category}</Tag> : '-'
    }
  ]

  if (loading) {
    return (
      <div className={styles.loading}>
        <Spin size="large" tip="加载中..." />
      </div>
    )
  }

  if (!repo) {
    return (
      <Alert
        message="仓库不存在"
        description="无法找到该仓库，请检查URL是否正确"
        type="error"
        showIcon
      />
    )
  }

  return (
    <div className={styles.container}>
      {/* 面包屑导航 */}
      <Breadcrumb
        items={[
          { title: <Link to="/developer/repos">仓库市场</Link> },
          { title: repo.display_name || repo.name }
        ]}
        style={{ marginBottom: 16 }}
      />

      {/* 仓库基本信息卡片 */}
      <Card className={styles.basicInfoCard}>
        <Row gutter={24} align="middle">
          <Col flex="none">
            <div className={styles.repoLogo}>
              {repo.display_name?.charAt(0) || repo.name.charAt(0).toUpperCase()}
            </div>
          </Col>
          <Col flex="auto">
            <Title level={3} style={{ marginBottom: 8 }}>
              {repo.display_name || repo.name}
            </Title>
            <Space size="large">
              <Tag color={repo.status === 'online' ? 'green' : 'orange'}>
                {repo.status === 'online' ? '已上线' : '未上线'}
              </Tag>
              <Text type="secondary">{repo.type}</Text>
              <Text type="secondary">{repo.protocol?.toUpperCase()}</Text>
              {repo.docs_url && (
                <Button 
                  type="link" 
                  icon={<ApiOutlined />}
                  href={repo.docs_url}
                  target="_blank"
                >
                  查看API文档
                </Button>
              )}
            </Space>
          </Col>
        </Row>
        
        {repo.description && (
          <Paragraph className={styles.description}>
            {repo.description}
          </Paragraph>
        )}

        {/* SLA信息 */}
        {repo.sla && (repo.sla.uptime || repo.sla.latency_p99) && (
          <div className={styles.slaInfo}>
            <Text type="secondary">SLA承诺：</Text>
            {repo.sla.uptime && (
              <Text>
                可用性 {typeof repo.sla.uptime === 'string' ? repo.sla.uptime : `${repo.sla.uptime}%`}
              </Text>
            )}
            {repo.sla.uptime && repo.sla.latency_p99 && <Text> | </Text>}
            {repo.sla.latency_p99 && <Text>P99延迟 {repo.sla.latency_p99}ms</Text>}
          </div>
        )}
      </Card>

      {/* 统计信息 */}
      <Row gutter={16} className={styles.statsRow}>
        <Col span={6}>
          <Card>
            <Statistic
              title="API端点"
              value={repo.endpoints?.length || 0}
              prefix={<ApiOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="每分钟限制"
              value={repo.limits?.rpm || 1000}
              suffix="次"
              prefix={<ThunderboltOutlined />}
              valueStyle={{ color: '#fa8c16' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="每小时限制"
              value={repo.limits?.rph || 10000}
              suffix="次"
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="每日限制"
              value={repo.limits?.daily || 100000}
              suffix="次"
              prefix={<GlobalOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 详细信息 */}
      <Row gutter={16}>
        {/* API端点列表 */}
        <Col span={16}>
          <Card 
            title={
              <Space>
                <ApiOutlined />
                <span>API端点列表</span>
                <Tag>{repo.endpoints?.length || 0} 个</Tag>
              </Space>
            }
            className={styles.endpointsCard}
          >
            {repo.endpoints && repo.endpoints.length > 0 ? (
              <Table
                dataSource={repo.endpoints}
                columns={endpointColumns}
                rowKey={(record) => `${record.method}-${record.path}`}
                pagination={false}
                size="middle"
              />
            ) : (
              <Alert message="暂无API端点信息" type="info" showIcon />
            )}
          </Card>
        </Col>

        {/* 限流配置 */}
        <Col span={8}>
          <Card 
            title={
              <Space>
                <SafetyCertificateOutlined />
                <span>限流配置</span>
              </Space>
            }
            className={styles.limitsCard}
          >
            <Descriptions column={1} size="small">
              <Descriptions.Item label="每分钟请求 (RPM)">
                <Text strong>{repo.limits?.rpm || 1000}</Text> 次
              </Descriptions.Item>
              <Descriptions.Item label="每小时请求 (RPH)">
                <Text strong>{repo.limits?.rph || 10000}</Text> 次
              </Descriptions.Item>
              <Descriptions.Item label="每日请求 (RPD)">
                <Text strong>{repo.limits?.daily || 100000}</Text> 次
              </Descriptions.Item>
              {repo.limits?.burst_limit && (
                <Descriptions.Item label="突发限制">
                  <Text strong>{repo.limits.burst_limit}</Text> 次
                </Descriptions.Item>
              )}
              {repo.limits?.concurrent_limit && (
                <Descriptions.Item label="并发限制">
                  <Text strong>{repo.limits.concurrent_limit}</Text> 个
                </Descriptions.Item>
              )}
              {repo.limits?.request_timeout && (
                <Descriptions.Item label="请求超时">
                  <Text strong>{repo.limits.request_timeout}</Text> 秒
                </Descriptions.Item>
              )}
            </Descriptions>
          </Card>

          {/* 定价信息 */}
          {repo.pricing && (
            <Card 
              title={
                <Space>
                  <DollarOutlined />
                  <span>定价信息</span>
                </Space>
              }
              className={styles.pricingCard}
            >
              <Descriptions column={1} size="small">
                <Descriptions.Item label="计费模式">
                  <Tag color="blue">
                    {repo.pricing.type === 'per_call' && '按次计费'}
                    {repo.pricing.type === 'token' && '按Token计费'}
                    {repo.pricing.type === 'flow' && '按流量计费'}
                    {repo.pricing.type === 'subscription' && '订阅计费'}
                    {repo.pricing.type === 'free' && '免费'}
                  </Tag>
                </Descriptions.Item>
                {repo.pricing.price_per_call && (
                  <Descriptions.Item label="每次调用">
                    ¥{repo.pricing.price_per_call.toFixed(4)}
                  </Descriptions.Item>
                )}
                {repo.pricing.price_per_token && (
                  <Descriptions.Item label="每Token">
                    ¥{repo.pricing.price_per_token.toFixed(6)}
                  </Descriptions.Item>
                )}
                {repo.pricing.monthly_price && (
                  <Descriptions.Item label="月订阅">
                    ¥{repo.pricing.monthly_price}
                  </Descriptions.Item>
                )}
                {repo.pricing.free_calls !== undefined && repo.pricing.free_calls > 0 && (
                  <Descriptions.Item label="免费调用">
                    <Text type="success">
                      <CheckCircleOutlined /> {repo.pricing.free_calls} 次
                    </Text>
                  </Descriptions.Item>
                )}
                {repo.pricing.free_tokens !== undefined && repo.pricing.free_tokens > 0 && (
                  <Descriptions.Item label="免费Token">
                    <Text type="success">
                      <CheckCircleOutlined /> {repo.pricing.free_tokens} Tokens
                    </Text>
                  </Descriptions.Item>
                )}
              </Descriptions>
            </Card>
          )}
        </Col>
      </Row>

      {/* 所有者信息 */}
      <Card className={styles.ownerCard}>
        <Descriptions title="仓库信息">
          <Descriptions.Item label="仓库名称">{repo.name}</Descriptions.Item>
          <Descriptions.Item label="仓库类型">{repo.type}</Descriptions.Item>
          <Descriptions.Item label="协议类型">{repo.protocol?.toUpperCase()}</Descriptions.Item>
          {repo.owner && <Descriptions.Item label="所有者">{repo.owner.name}</Descriptions.Item>}
          {repo.api_docs_url && <Descriptions.Item label="API文档地址">{repo.api_docs_url}</Descriptions.Item>}
          <Descriptions.Item label="创建时间">{repo.created_at}</Descriptions.Item>
          {repo.online_at && <Descriptions.Item label="上线时间">{repo.online_at}</Descriptions.Item>}
        </Descriptions>
      </Card>
    </div>
  )
}
