/**
 * 配额使用页面
 * V2.6 更新：现代化UI设计，支持多种配额类型显示
 */

import { useState, useEffect } from 'react'
import '../../styles/cyber-theme.css'
import { Row, Col, Card, Progress, Table, Select, Typography, Space, Statistic, Empty, Button, Alert, Tag, Tooltip, Badge } from 'antd'
import { 
  PieChartOutlined, 
  BarChartOutlined, 
  ThunderboltOutlined, 
  ClockCircleOutlined, 
  WarningOutlined,
  CheckCircleOutlined,
  CalendarOutlined,
  RiseOutlined,
  FallOutlined,
  RocketOutlined
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { quotaApi, APIKey, QuotaInfo } from '../../api/quota'
import { useErrorModal } from '../../components/ErrorModal'
import { useAuthStore } from '../../stores/auth'
import { useDevice } from '../../hooks/useDevice'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, Cell } from 'recharts'
import dayjs from 'dayjs'
import styles from './Quota.module.css'

const { Title, Text } = Typography

export default function DeveloperQuota() {
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const { isMobile } = useDevice()
  const [loading, setLoading] = useState(false)
  const [keys, setKeys] = useState<APIKey[]>([])
  const [selectedKey, setSelectedKey] = useState<string>('')
  const [quota, setQuota] = useState<QuotaInfo | null>(null)
  const [usageHistory, setUsageHistory] = useState<any[]>([])
  const [topRepos, setTopRepos] = useState<any[]>([])
  
  // 判断是否是普通用户
  const isNormalUser = user?.user_type === 'user'

  // 使用统一的错误提示
  const { showError, closeError, ErrorModal: ErrorModalComponent } = useErrorModal()

  useEffect(() => {
    fetchKeys()
  }, [])

  useEffect(() => {
    if (selectedKey) {
      fetchQuotaData(selectedKey)
    }
  }, [selectedKey])

  const fetchKeys = async () => {
    try {
      const data = await quotaApi.getKeys({ page_size: 100 })
      setKeys(data.items)
      if (data.items.length > 0) {
        setSelectedKey(data.items[0].id)
      }
    } catch (error: any) {
      showError(error, () => fetchKeys())
    }
  }

  const fetchQuotaData = async (keyId: string) => {
    setLoading(true)
    try {
      const [quotaRes, historyRes, reposRes] = await Promise.all([
        quotaApi.getQuota(keyId),
        quotaApi.getUsageHistory(keyId, 'daily', 14),
        quotaApi.getTopRepos(keyId, 10, 14),
      ])

      setQuota(quotaRes)
      setUsageHistory(historyRes)
      setTopRepos(reposRes)
    } catch (error: any) {
      showError(error, () => fetchQuotaData(keyId))
    } finally {
      setLoading(false)
    }
  }

  const getProgressColor = (percent: number) => {
    if (percent >= 90) return '#ff4d4f'
    if (percent >= 70) return '#faad14'
    return '#52c41a'
  }

  const getQuotaStatus = (used: number, limit: number | null) => {
    if (!limit) return { color: 'blue', text: '无限制', icon: <CheckCircleOutlined /> }
    const percent = (used / limit) * 100
    if (percent >= 100) return { color: 'red', text: '已用完', icon: <WarningOutlined /> }
    if (percent >= 90) return { color: 'orange', text: '即将用完', icon: <WarningOutlined /> }
    if (percent >= 70) return { color: 'gold', text: '使用中', icon: <ClockCircleOutlined /> }
    return { color: 'green', text: '正常', icon: <CheckCircleOutlined /> }
  }

  // 每日配额数据
  const dailyData = quota ? getQuotaData(quota.daily) : null
  // 每月配额数据
  const monthlyData = quota ? getQuotaData(quota.monthly) : null

  function getQuotaData(data: { used: number; limit: number | null; remaining: number | null }) {
    const percent = data.limit ? Math.min(100, Math.round((data.used / data.limit) * 100)) : 0
    const status = getQuotaStatus(data.used, data.limit)
    return {
      used: data.used,
      limit: data.limit,
      remaining: data.remaining ?? (data.limit ? data.limit - data.used : null),
      percent,
      status
    }
  }

  const COLORS = ['#1677ff', '#52c41a', '#faad14', '#ff4d4f', '#722ed1', '#13c2c2']

  return (
    <div className={`${styles.container} bamboo-bg-pattern`}>
      <ErrorModalComponent />
      
      {/* 普通用户升级引导 */}
      {isNormalUser && (
        <Alert
          type="info"
          showIcon
          icon={<RocketOutlined />}
          message="升级为开发者，解锁更多功能"
          description="成为开发者后，您可以创建API Keys、查看完整的配额使用统计等功能。"
          action={
            <Button type="primary" size="small" onClick={() => navigate('/user')}>
              前往升级
            </Button>
          }
          style={{ marginBottom: 16 }}
        />
      )}

      <div className={styles.header}>
        <Title level={4}>配额使用情况</Title>
        <Select
          value={selectedKey}
          onChange={setSelectedKey}
          style={{ width: 300 }}
          placeholder="选择API Key"
        >
          {keys.map((key) => (
            <Select.Option key={key.id} value={key.id}>
              {key.key_name} ({key.key_prefix}...)
            </Select.Option>
          ))}
        </Select>
      </div>

      {quota && (
        <>
          {/* 配额概览 - 现代化卡片设计 */}
          <Row gutter={[16, 16]} className="mb-4">
            {/* 每日配额 */}
            <Col xs={24} md={12} lg={6}>
              <Card 
                className={styles.quotaCard}
                loading={loading}
                style={{ borderTop: '3px solid #1677ff' }}
              >
                <div className={styles.quotaCardHeader}>
                  <div className={styles.quotaCardIcon} style={{ backgroundColor: '#e6f4ff' }}>
                    <CalendarOutlined style={{ color: '#1677ff', fontSize: 20 }} />
                  </div>
                  <Tag color={dailyData?.status.color}>{dailyData?.status.text}</Tag>
                </div>
                <div className={styles.quotaCardTitle}>每日配额</div>
                <div className={styles.quotaCardValue}>
                  <span className={styles.quotaUsed}>{dailyData?.used ?? 0}</span>
                  <span className={styles.quotaDivider}>/</span>
                  <span className={styles.quotaLimit}>{dailyData?.limit ?? '∞'}</span>
                </div>
                <Progress 
                  percent={dailyData?.percent ?? 0}
                  strokeColor={getProgressColor(dailyData?.percent ?? 0)}
                  showInfo={false}
                  size="small"
                />
                <div className={styles.quotaCardFooter}>
                  <span>剩余: <Text strong>{dailyData?.remaining ?? '无限制'}</Text></span>
                </div>
              </Card>
            </Col>

            {/* 每月配额 */}
            <Col xs={24} md={12} lg={6}>
              <Card 
                className={styles.quotaCard}
                loading={loading}
                style={{ borderTop: '3px solid #722ed1' }}
              >
                <div className={styles.quotaCardHeader}>
                  <div className={styles.quotaCardIcon} style={{ backgroundColor: '#f9f0ff' }}>
                    <BarChartOutlined style={{ color: '#722ed1', fontSize: 20 }} />
                  </div>
                  <Tag color={monthlyData?.status.color}>{monthlyData?.status.text}</Tag>
                </div>
                <div className={styles.quotaCardTitle}>每月配额</div>
                <div className={styles.quotaCardValue}>
                  <span className={styles.quotaUsed}>{monthlyData?.used ?? 0}</span>
                  <span className={styles.quotaDivider}>/</span>
                  <span className={styles.quotaLimit}>{monthlyData?.limit ?? '∞'}</span>
                </div>
                <Progress 
                  percent={monthlyData?.percent ?? 0}
                  strokeColor={getProgressColor(monthlyData?.percent ?? 0)}
                  showInfo={false}
                  size="small"
                />
                <div className={styles.quotaCardFooter}>
                  <span>剩余: <Text strong>{monthlyData?.remaining ?? '无限制'}</Text></span>
                </div>
              </Card>
            </Col>

            {/* RPM 限制 */}
            <Col xs={24} md={12} lg={6}>
              <Card 
                className={styles.quotaCard}
                loading={loading}
                style={{ borderTop: '3px solid #faad14' }}
              >
                <div className={styles.quotaCardHeader}>
                  <div className={styles.quotaCardIcon} style={{ backgroundColor: '#fffbe6' }}>
                    <ThunderboltOutlined style={{ color: '#faad14', fontSize: 20 }} />
                  </div>
                  <Badge 
                    status={quota.rpm_used >= (quota.rpm_limit || 1000) ? 'error' : 'processing'}
                    text={quota.rpm_used >= (quota.rpm_limit || 1000) ? '已达限' : '正常'}
                  />
                </div>
                <div className={styles.quotaCardTitle}>每分钟请求 (RPM)</div>
                <div className={styles.quotaCardValue}>
                  <span className={styles.quotaUsed} style={{ color: quota.rpm_used >= (quota.rpm_limit || 1000) ? '#ff4d4f' : '#faad14' }}>
                    {quota.rpm_used ?? 0}
                  </span>
                  <span className={styles.quotaDivider}>/</span>
                  <span className={styles.quotaLimit}>{quota.rpm_limit || 1000}</span>
                </div>
                <Progress 
                  percent={quota.rpm_limit ? Math.min(100, Math.round((quota.rpm_used / quota.rpm_limit) * 100)) : 0}
                  strokeColor={quota.rpm_used >= (quota.rpm_limit || 1000) ? '#ff4d4f' : '#faad14'}
                  showInfo={false}
                  size="small"
                />
                <div className={styles.quotaCardFooter}>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    限制: {quota.rpm_limit || 1000} 次/分钟
                  </Text>
                </div>
              </Card>
            </Col>

            {/* RPH 限制 */}
            <Col xs={24} md={12} lg={6}>
              <Card 
                className={styles.quotaCard}
                loading={loading}
                style={{ borderTop: '3px solid #52c41a' }}
              >
                <div className={styles.quotaCardHeader}>
                  <div className={styles.quotaCardIcon} style={{ backgroundColor: '#f6ffed' }}>
                    <ClockCircleOutlined style={{ color: '#52c41a', fontSize: 20 }} />
                  </div>
                  <Badge 
                    status={quota.rph_used >= (quota.rph_limit || 10000) ? 'error' : 'processing'}
                    text={quota.rph_used >= (quota.rph_limit || 10000) ? '已达限' : '正常'}
                  />
                </div>
                <div className={styles.quotaCardTitle}>每小时请求 (RPH)</div>
                <div className={styles.quotaCardValue}>
                  <span className={styles.quotaUsed} style={{ color: quota.rph_used >= (quota.rph_limit || 10000) ? '#ff4d4f' : '#52c41a' }}>
                    {quota.rph_used ?? 0}
                  </span>
                  <span className={styles.quotaDivider}>/</span>
                  <span className={styles.quotaLimit}>{quota.rph_limit || 10000}</span>
                </div>
                <Progress 
                  percent={quota.rph_limit ? Math.min(100, Math.round((quota.rph_used / quota.rph_limit) * 100)) : 0}
                  strokeColor={quota.rph_used >= (quota.rph_limit || 10000) ? '#ff4d4f' : '#52c41a'}
                  showInfo={false}
                  size="small"
                />
                <div className={styles.quotaCardFooter}>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    限制: {quota.rph_limit || 10000} 次/小时
                  </Text>
                </div>
              </Card>
            </Col>
          </Row>

          {/* 余额警告 */}
          {quota.balance_enabled && quota.balance !== undefined && (
            <Alert
              type={quota.balance < 1 ? 'error' : 'warning'}
              message={
                <Space>
                  <span>
                    余额提醒：当前余额 <Text strong>¥{quota.balance.toFixed(2)}</Text>
                    {quota.balance < 1 && '，余额不足，请及时充值'}
                  </span>
                  <Tag color={quota.balance < 1 ? 'red' : 'orange'}>
                    余额扣费已启用
                  </Tag>
                </Space>
              }
              showIcon
              icon={<WarningOutlined />}
              action={
                <Button size="small" type="primary" onClick={() => navigate('/developer/recharge')}>
                  立即充值
                </Button>
              }
              style={{ marginBottom: 16 }}
            />
          )}

          {/* 使用趋势 */}
          <Card 
            title={
              <Space>
                <RiseOutlined />
                <span>每日调用趋势（近14天）</span>
              </Space>
            } 
            className={styles.chartCard}
            extra={
              <Text type="secondary">
                总调用: {usageHistory.reduce((acc, r) => acc + r.call_count, 0)} 次
              </Text>
            }
          >
            {usageHistory.length === 0 ? (
              <div style={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Empty description="暂无调用记录，开始使用API后将显示趋势图" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={usageHistory}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    dataKey="date"
                    tickFormatter={(val) => dayjs(val).format('MM-DD')}
                  />
                  <YAxis />
                  <RechartsTooltip 
                    labelFormatter={(val) => dayjs(val).format('YYYY-MM-DD')}
                    formatter={(value: number) => [`${value}次`, '调用次数']}
                  />
                  <Bar dataKey="call_count" fill="#1677ff" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </Card>

          {/* Top仓库 */}
          <Card 
            title={
              <Space>
                <FallOutlined />
                <span>调用量最高的仓库（近14天）</span>
              </Space>
            }
            className={styles.tableCard}
          >
            {isMobile ? (
              // 移动端：卡片列表
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {topRepos.map((repo, index) => {
                  const total = topRepos.reduce((acc, r) => acc + r.call_count, 0)
                  const percent = total > 0 ? Math.round((repo.call_count / total) * 100) : 0
                  return (
                    <Card key={repo.repo_id} size="small" style={{ borderRadius: 8, boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }} bodyStyle={{ padding: 12 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
                        <Badge count={index + 1} style={{ backgroundColor: index < 3 ? '#1677ff' : '#d9d9d9' }} />
                        <Tag color="blue" style={{ marginInlineEnd: 0 }}>{repo.repo_name || '未知仓库'}</Tag>
                      </div>
                      <div style={{ fontSize: 12, color: '#666', marginBottom: 8 }}>
                        <div>调用次数：<Text strong>{repo.call_count?.toLocaleString()}</Text> 次</div>
                        <div style={{ marginTop: 8 }}>
                          <Progress percent={percent} size="small" format={() => `${percent}%`} strokeColor={percent > 50 ? '#1677ff' : '#52c41a'} />
                        </div>
                      </div>
                    </Card>
                  )
                })}
              </div>
            ) : (
              // 桌面端：表格
              <Table
                dataSource={topRepos}
                rowKey="repo_id"
                pagination={false}
                locale={{ emptyText: <Empty description="暂无仓库调用记录" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
                columns={[
                  { 
                    title: '排名', 
                    key: 'rank',
                    width: 80,
                    render: (_: any, __: any, index: number) => (
                      <Badge count={index + 1} style={{ backgroundColor: index < 3 ? '#1677ff' : '#d9d9d9' }} />
                    )
                  },
                  { 
                    title: '仓库名称', 
                    dataIndex: 'repo_name', 
                    key: 'repo_name',
                    render: (name: string) => <Tag color="blue">{name || '未知仓库'}</Tag>
                  },
                  { 
                    title: '调用次数', 
                    dataIndex: 'call_count', 
                    key: 'call_count',
                    sorter: (a: any, b: any) => a.call_count - b.call_count,
                    render: (count: number) => count?.toLocaleString()
                  },
                  {
                    title: '用量占比',
                    key: 'percent',
                    width: 200,
                    render: (_: any, record: any) => {
                      const total = topRepos.reduce((acc, r) => acc + r.call_count, 0)
                      const percent = total > 0 ? Math.round((record.call_count / total) * 100) : 0
                      return (
                        <Tooltip title={`${record.call_count} / ${total} 次`}>
                          <Progress
                            percent={percent}
                            size="small"
                            format={(p) => `${p}%`}
                            strokeColor={percent > 50 ? '#1677ff' : '#52c41a'}
                          />
                        </Tooltip>
                      )
                    }
                  },
                ]}
              />
            )}
          </Card>
        </>
      )}

      {/* 无API Key时的提示 */}
      {keys.length === 0 && (
        <Card className={styles.card}>
          <Empty 
            description="暂无API Key，请先创建API Key"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          >
            <Button type="primary" icon={<CheckCircleOutlined />} onClick={() => navigate('/developer/keys')}>
              创建API Key
            </Button>
          </Empty>
        </Card>
      )}
    </div>
  )
}
