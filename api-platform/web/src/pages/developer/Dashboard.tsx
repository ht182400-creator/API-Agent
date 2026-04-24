/**
 * 开发者工作台
 */

import { useState, useEffect } from 'react'
import '../../styles/cyber-theme.css'
import { Row, Col, Card, Statistic, Table, Progress, Typography, Space, Tag, Empty, Alert, Button } from 'antd'
import {
  RiseOutlined,
  FallOutlined,
  KeyOutlined,
  PieChartOutlined,
  FileTextOutlined,
  WalletOutlined,
  DollarOutlined,
  WarningOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { quotaApi, APIKey, QuotaInfo } from '../../api/quota'
import { billingApi, UserAccount } from '../../api/billing'
import { repoApi, Repository } from '../../api/repo'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import dayjs from 'dayjs'
import styles from './Dashboard.module.css'

const { Title, Text } = Typography

export default function DeveloperDashboard() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [account, setAccount] = useState<UserAccount | null>(null)
  const [keys, setKeys] = useState<APIKey[]>([])
  const [quotaOverview, setQuotaOverview] = useState<QuotaInfo[]>([])
  const [topRepos, setTopRepos] = useState<any[]>([])
  const [recentLogs, setRecentLogs] = useState<any[]>([])
  const [consumptionTrend, setConsumptionTrend] = useState<any[]>([])

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    setLoading(true)
    try {
      // 先获取 keys，再并行获取其他数据
      const keysRes = await quotaApi.getKeys({ page_size: 5 })

      const [accountRes, quotaRes, consumptionRes] = await Promise.all([
        billingApi.getAccount(),
        quotaApi.getQuotaOverview(),
        quotaApi.getConsumptionTrend(7),  // 使用 quota API 的趋势统计（基于调用记录）
      ])

      // 获取第一个 key 的 top repos
      const topReposRes = keysRes?.items?.[0]?.id 
        ? await quotaApi.getTopRepos(keysRes.items[0].id, 5, 14)
        : []

      setAccount(accountRes)
      setKeys(keysRes?.items || [])
      setQuotaOverview(quotaRes || [])
      setConsumptionTrend(consumptionRes || [])
      setTopRepos(topReposRes || [])
    } catch (error) {
      console.error('获取数据失败:', error)
      // 失败时设置默认值，避免界面异常
      setAccount(null)
      setKeys([])
      setQuotaOverview([])
      setConsumptionTrend([])
      setTopRepos([])
    } finally {
      setLoading(false)
    }
  }

  // 计算统计数据
  const totalQuota = quotaOverview.reduce((acc, q) => {
    const dailyUsed = q.daily.used || 0
    const monthlyUsed = q.monthly.used || 0
    return {
      daily: acc.daily + dailyUsed,
      monthly: acc.monthly + monthlyUsed,
    }
  }, { daily: 0, monthly: 0 })

  const columns = [
    { title: 'Key名称', dataIndex: 'key_name', key: 'key_name' },
    { 
      title: '状态', 
      dataIndex: 'status', 
      key: 'status',
      render: (status: string) => (
        <Tag color={status === 'active' ? 'green' : 'red'}>
          {status === 'active' ? '正常' : '禁用'}
        </Tag>
      )
    },
    { 
      title: '创建时间', 
      dataIndex: 'created_at', 
      key: 'created_at',
      render: (date: string) => dayjs(date).format('YYYY-MM-DD')
    },
  ]

  return (
    <div className={`${styles.dashboard} bamboo-bg-pattern`}>
      <Title level={4}>开发者工作台</Title>

      {/* 【V4.1 新增】余额为0或获取失败时的引导提示 */}
      {account && account.balance === 0 && !loading && (
        <Alert
          message="账户余额为0"
          description={
            <span>
              您需要充值后才能调用付费API。
              <Button 
                type="link" 
                icon={<DollarOutlined />}
                onClick={() => navigate('/developer/recharge')}
                style={{ padding: 0, marginLeft: 8 }}
              >
                立即充值
              </Button>
            </span>
          }
          type="warning"
          showIcon
          icon={<WarningOutlined />}
          style={{ marginBottom: 16 }}
        />
      )}

      {/* 统计卡片 */}
      <Row gutter={[16, 16]} className={styles.stats}>
        <Col xs={24} sm={12} lg={6}>
          <Card className={styles.statCard}>
            <Statistic
              title={
                <Space>
                  <span>账户余额</span>
                  <Tag color={account?.mock_mode !== false ? 'orange' : 'green'} style={{ marginLeft: 8 }}>
                    {account?.mock_mode !== false ? '模拟' : '真实'}
                  </Tag>
                </Space>
              }
              value={account?.balance || 0}
              prefix={<WalletOutlined />}
              precision={2}
              suffix="元"
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className={styles.statCard}>
            <Statistic
              title="今日API调用"
              value={totalQuota.daily}
              prefix={<FileTextOutlined />}
              suffix="次"
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className={styles.statCard}>
            <Statistic
              title="本月API调用"
              value={totalQuota.monthly}
              prefix={<PieChartOutlined />}
              suffix="次"
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className={styles.statCard}>
            <Statistic
              title="API Keys"
              value={keys.length}
              prefix={<KeyOutlined />}
              valueStyle={{ color: '#1677ff' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 消费趋势 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={16}>
          <Card title="消费趋势（近7天）" className={styles.chartCard}>
            {consumptionTrend.length === 0 ? (
              <div style={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Empty description="暂无消费数据，开始调用API后将在此处显示趋势" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={consumptionTrend}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    dataKey="date" 
                    tickFormatter={(val) => dayjs(val).format('MM-DD')}
                  />
                  <YAxis />
                  <Tooltip 
                    labelFormatter={(val) => dayjs(val).format('YYYY-MM-DD')}
                    formatter={(value: number) => [`¥${value.toFixed(2)}`, '消费']}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="amount" 
                    stroke="#1677ff" 
                    strokeWidth={2}
                    dot={{ fill: '#1677ff' }}
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </Card>
        </Col>

        <Col xs={24} lg={8}>
          <Card title="配额使用情况" className={styles.quotaCard}>
            {quotaOverview.length === 0 ? (
              <Empty description="暂无配额数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            ) : (
              quotaOverview.slice(0, 3).map((q, index) => {
                const dailyPercent = q.daily.limit 
                  ? Math.round((q.daily.used / q.daily.limit) * 100) 
                  : 0
                const monthlyPercent = q.monthly.limit 
                  ? Math.round((q.monthly.used / q.monthly.limit) * 100) 
                  : 0
                
                return (
                  <div key={index} className={styles.quotaItem}>
                    <Text>Key {index + 1}</Text>
                    <Progress
                      percent={dailyPercent}
                      size="small"
                      format={(p) => `${p}%`}
                      status={dailyPercent > 80 ? 'exception' : 'active'}
                    />
                  </div>
                )
              })
            )}
          </Card>
        </Col>
      </Row>

      {/* API Keys列表 */}
      <Card 
        title="我的API Keys" 
        className={styles.tableCard}
        extra={
          <a onClick={() => navigate('/developer/keys')}>查看全部</a>
        }
      >
        <Table
          dataSource={keys}
          columns={columns}
          rowKey="id"
          pagination={false}
          loading={loading}
        />
      </Card>
    </div>
  )
}
