/**
 * 配额使用页面
 * V2.5 更新：添加 RPM/RPH 限制展示
 */

import { useState, useEffect } from 'react'
import { Row, Col, Card, Progress, Table, Select, Typography, Space, Statistic, Empty, Button, Alert, Tag } from 'antd'
import { PieChartOutlined, BarChartOutlined, PlusOutlined, ThunderboltOutlined, ClockCircleOutlined, WarningOutlined } from '@ant-design/icons'
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

          {/* RPM/RPH 限流信息 V2.5 新增 */}
          <Row gutter={[16, 16]}>
            <Col xs={24} md={12}>
              <Card 
                className={styles.card}
                title={
                  <Space>
                    <ThunderboltOutlined />
                    <span>每分钟请求限制 (RPM)</span>
                  </Space>
                }
              >
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Row gutter={16}>
                    <Col span={12}>
                      <Statistic 
                        title="RPM 限制" 
                        value={quota.rpm_limit || 1000} 
                        suffix="次/分钟" 
                      />
                    </Col>
                    <Col span={12}>
                      <Statistic 
                        title="最近1分钟" 
                        value={quota.rpm_used || 0} 
                        valueStyle={{ color: quota.rpm_used >= (quota.rpm_limit || 1000) ? '#ff4d4f' : undefined }}
                      />
                    </Col>
                  </Row>
                  <Progress 
                    percent={quota.rpm_limit ? Math.min(100, Math.round((quota.rpm_used / quota.rpm_limit) * 100)) : 0}
                    strokeColor={getProgressColor(
                      quota.rpm_limit ? Math.min(100, (quota.rpm_used / quota.rpm_limit) * 100) : 0
                    )}
                    format={(p) => `${p}%`}
                    showInfo
                  />
                  {quota.rpm_used >= (quota.rpm_limit || 1000) && (
                    <Alert 
                      type="warning" 
                      message="RPM 限制已达上限，请稍后再试" 
                      showIcon 
                      icon={<WarningOutlined />}
                    />
                  )}
                </Space>
              </Card>
            </Col>
            <Col xs={24} md={12}>
              <Card 
                className={styles.card}
                title={
                  <Space>
                    <ClockCircleOutlined />
                    <span>每小时请求限制 (RPH)</span>
                  </Space>
                }
              >
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Row gutter={16}>
                    <Col span={12}>
                      <Statistic 
                        title="RPH 限制" 
                        value={quota.rph_limit || 10000} 
                        suffix="次/小时" 
                      />
                    </Col>
                    <Col span={12}>
                      <Statistic 
                        title="最近1小时" 
                        value={quota.rph_used || 0} 
                        valueStyle={{ color: quota.rph_used >= (quota.rph_limit || 10000) ? '#ff4d4f' : undefined }}
                      />
                    </Col>
                  </Row>
                  <Progress 
                    percent={quota.rph_limit ? Math.min(100, Math.round((quota.rph_used / quota.rph_limit) * 100)) : 0}
                    strokeColor={getProgressColor(
                      quota.rph_limit ? Math.min(100, (quota.rph_used / quota.rph_limit) * 100) : 0
                    )}
                    format={(p) => `${p}%`}
                    showInfo
                  />
                  {quota.rph_used >= (quota.rph_limit || 10000) && (
                    <Alert 
                      type="warning" 
                      message="RPH 限制已达上限，请稍后再试" 
                      showIcon 
                      icon={<WarningOutlined />}
                    />
                  )}
                </Space>
              </Card>
            </Col>
          </Row>

          {/* 余额警告 V2.5 新增 */}
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
              action={
                <Button size="small" type="primary" onClick={() => navigate('/developer/recharge')}>
                  立即充值
                </Button>
              }
              style={{ marginBottom: 16 }}
            />
          )}

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
