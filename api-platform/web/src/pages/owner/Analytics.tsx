/**
 * 数据分析页面
 */

import { useState, useEffect, useCallback } from 'react'
import { Card, Row, Col, Typography, Statistic, Spin, Empty } from 'antd'
import { BarChartOutlined, RiseOutlined, ApiOutlined, DollarOutlined, InboxOutlined } from '@ant-design/icons'
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import { analyticsApi, OverviewStats, WeeklyStats, HourlyStats, SourceStats } from '../../api/analytics'
import styles from './Analytics.module.css'

const { Title } = Typography

const COLORS = ['#1677ff', '#52c41a', '#faad14', '#ff4d4f', '#722ed1']

export default function OwnerAnalytics() {
  const [loading, setLoading] = useState(true)
  const [overview, setOverview] = useState<OverviewStats | null>(null)
  const [weeklyData, setWeeklyData] = useState<WeeklyStats[]>([])
  const [hourlyData, setHourlyData] = useState<HourlyStats[]>([])
  const [sourceData, setSourceData] = useState<SourceStats[]>([])

  // 获取所有统计数据
  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const [overviewData, weekly, hourly, sources] = await Promise.all([
        analyticsApi.getOverview(),
        analyticsApi.getWeeklyStats(1),
        analyticsApi.getHourlyStats(),
        analyticsApi.getSourceStats()
      ])
      
      setOverview(overviewData)
      setWeeklyData(weekly)
      setHourlyData(hourly)
      setSourceData(sources)
    } catch (error: any) {
      console.error('获取统计数据失败:', error)
      message.error('获取统计数据失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  // 格式化周数据用于显示
  const formatWeeklyData = weeklyData.map(item => ({
    ...item,
    date: item.date.split('-').slice(1).join('/') // 2026-04-19 -> 04/19
  }))

  // 检查是否有任何数据
  const hasData = overview && (overview.total_calls > 0 || overview.total_revenue > 0 || overview.total_repos > 0)

  // 渲染空图表
  const renderEmptyChart = (height: number = 300) => (
    <div style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>
      <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无数据" />
    </div>
  )

  if (loading) {
    return (
      <div className={styles.container}>
        <Title level={4}>数据分析</Title>
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 400 }}>
          <Spin size="large" tip="加载统计数据..." />
        </div>
      </div>
    )
  }

  return (
    <div className={styles.container}>
      <Title level={4}>数据分析</Title>

      {/* 统计卡片 - 移动端单列，平板双列，桌面四列 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card className={styles.statCard}>
            <Statistic
              title="总调用量"
              value={overview?.total_calls || 0}
              prefix={<ApiOutlined style={{ color: '#1677ff' }} />}
              valueStyle={{ color: '#1677ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className={styles.statCard}>
            <Statistic
              title="本月调用"
              value={overview?.month_calls || 0}
              prefix={<RiseOutlined style={{ color: '#52c41a' }} />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className={styles.statCard}>
            <Statistic
              title="总收益"
              value={overview?.total_revenue || 0}
              prefix={<DollarOutlined style={{ color: '#faad14' }} />}
              precision={2}
              valueStyle={{ color: '#faad14' }}
              suffix="元"
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className={styles.statCard}>
            <Statistic
              title="活跃仓库"
              value={overview?.total_repos || 0}
              prefix={<BarChartOutlined style={{ color: '#722ed1' }} />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={16}>
          <Card title="调用趋势（本周）" className={styles.chartCard}>
            {formatWeeklyData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={formatWeeklyData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis yAxisId="left" orientation="left" stroke="#1677ff" />
                  <YAxis yAxisId="right" orientation="right" stroke="#52c41a" />
                  <Tooltip />
                  <Bar yAxisId="left" dataKey="calls" fill="#1677ff" name="调用量" />
                  <Line yAxisId="right" type="monotone" dataKey="revenue" stroke="#52c41a" name="收益" />
                </BarChart>
              </ResponsiveContainer>
            ) : renderEmptyChart()}
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="调用来源分布" className={styles.chartCard}>
            {sourceData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={sourceData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={100}
                    label={({ name, percentage }) => `${name} ${percentage}%`}
                  >
                    {sourceData.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            ) : renderEmptyChart()}
          </Card>
        </Col>
      </Row>

      <Card title="24小时调用分布" className={styles.chartCard}>
        {hourlyData.some(h => h.calls > 0) ? (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={hourlyData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="hour" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="calls" fill="#1677ff" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        ) : renderEmptyChart()}
      </Card>
    </div>
  )
}
