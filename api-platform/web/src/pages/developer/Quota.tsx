/**
 * 配额使用页面
 */

import { useState, useEffect } from 'react'
import { Row, Col, Card, Progress, Table, Select, Typography, Space, Statistic, Empty, Button } from 'antd'
import { PieChartOutlined, BarChartOutlined, PlusOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { quotaApi, APIKey, QuotaInfo } from '../../api/quota'
import { useErrorModal } from '../../components/ErrorModal'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import dayjs from 'dayjs'
import styles from './Quota.module.css'

const { Title, Text } = Typography

export default function DeveloperQuota() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [keys, setKeys] = useState<APIKey[]>([])
  const [selectedKey, setSelectedKey] = useState<string>('')
  const [quota, setQuota] = useState<QuotaInfo | null>(null)
  const [usageHistory, setUsageHistory] = useState<any[]>([])
  const [topRepos, setTopRepos] = useState<any[]>([])

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
      // api.get 已返回 res.data，所以直接是 PaginatedResponse
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

  const COLORS = ['#1677ff', '#52c41a', '#faad14', '#ff4d4f', '#722ed1', '#13c2c2']

  return (
    <div className={styles.container}>
      {/* 统一的错误提示组件 */}
      <ErrorModalComponent />

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
          {/* 配额概览 */}
          <Row gutter={[16, 16]}>
            <Col xs={24} md={12}>
              <Card className={styles.card}>
                <div className={styles.quotaHeader}>
                  <PieChartOutlined />
                  <Text strong>每日配额</Text>
                </div>
                <Progress
                  type="dashboard"
                  percent={quota.daily.limit ? Math.round((quota.daily.used / quota.daily.limit) * 100) : 0}
                  format={(p) => `${quota.daily.used}/${quota.daily.limit || '∞'}`}
                  strokeColor={getProgressColor(
                    quota.daily.limit ? (quota.daily.used / quota.daily.limit) * 100 : 0
                  )}
                />
                <div className={styles.quotaDetail}>
                  <Space direction="vertical">
                    <Text>已使用：{quota.daily.used}</Text>
                    <Text type="secondary">
                      剩余：{quota.daily.remaining ?? '无限制'}
                    </Text>
                  </Space>
                </div>
              </Card>
            </Col>
            <Col xs={24} md={12}>
              <Card className={styles.card}>
                <div className={styles.quotaHeader}>
                  <BarChartOutlined />
                  <Text strong>每月配额</Text>
                </div>
                <Progress
                  type="dashboard"
                  percent={quota.monthly.limit ? Math.round((quota.monthly.used / quota.monthly.limit) * 100) : 0}
                  format={(p) => `${quota.monthly.used}/${quota.monthly.limit || '∞'}`}
                  strokeColor={getProgressColor(
                    quota.monthly.limit ? (quota.monthly.used / quota.monthly.limit) * 100 : 0
                  )}
                />
                <div className={styles.quotaDetail}>
                  <Space direction="vertical">
                    <Text>已使用：{quota.monthly.used}</Text>
                    <Text type="secondary">
                      剩余：{quota.monthly.remaining ?? '无限制'}
                    </Text>
                  </Space>
                </div>
              </Card>
            </Col>
          </Row>

          {/* 使用趋势 */}
          <Card title="每日调用趋势（近14天）" className={styles.chartCard}>
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
                  <Tooltip 
                    labelFormatter={(val) => dayjs(val).format('YYYY-MM-DD')}
                    formatter={(value: number) => [`${value}次`, '调用次数']}
                  />
                  <Bar dataKey="call_count" fill="#1677ff" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </Card>

          {/* Top仓库 */}
          <Card title="调用量最高的仓库（近14天）" className={styles.tableCard}>
            <Table
              dataSource={topRepos}
              rowKey="repo_id"
              pagination={false}
              locale={{ emptyText: <Empty description="暂无仓库调用记录" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
              columns={[
                { 
                  title: '排名', 
                  key: 'rank',
                  render: (_: any, __: any, index: number) => index + 1
                },
                { title: '仓库名称', dataIndex: 'repo_name', key: 'repo_name' },
                { 
                  title: '调用次数', 
                  dataIndex: 'call_count', 
                  key: 'call_count',
                  sorter: (a: any, b: any) => a.call_count - b.call_count,
                },
                {
                  title: '用量占比',
                  key: 'percent',
                  render: (_: any, record: any) => {
                    const total = topRepos.reduce((acc, r) => acc + r.call_count, 0)
                    const percent = Math.round((record.call_count / total) * 100)
                    return (
                      <Progress
                        percent={percent}
                        size="small"
                        format={(p) => `${p}%`}
                      />
                    )
                  }
                },
              ]}
            />
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
            <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/developer/keys')}>
              创建API Key
            </Button>
          </Empty>
        </Card>
      )}
    </div>
  )
}
