/**
 * 管理员分析报表页面
 * 功能：全局统计概览、调用/收入趋势图、仓库明细排行榜
 * V1.0 - 初始版本
 */

import { useState, useEffect } from 'react'
import {
  Card,
  Row,
  Col,
  Statistic,
  Table,
  Select,
  Button,
  Space,
  Tag,
  Spin,
  Tabs,
  Typography,
  message,
  Modal,
  Descriptions,
  Divider,
  Progress
} from 'antd'
import {
  ApiOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  UserOutlined,
  DollarOutlined,
  LineChartOutlined,
  TableOutlined,
  SyncOutlined,
  ThunderboltOutlined
} from '@ant-design/icons'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  Legend
} from 'recharts'
import { adminAnalyticsApi, AdminOverview, TrendData, RepoDetailItem, RepoTrendData } from '../../api/adminAnalytics'
import { useNavigate } from 'react-router-dom'
import styles from './Analytics.module.css'

const { Title, Text } = Typography
const { TabPane } = Tabs

// 状态颜色映射
const statusColors: Record<string, string> = {
  online: 'green',
  pending: 'orange',
  approved: 'blue',
  rejected: 'red',
  offline: 'default'
}

// 状态文本映射
const statusText: Record<string, string> = {
  online: '已上线',
  pending: '待审核',
  approved: '已审核',
  rejected: '已拒绝',
  offline: '已下线'
}

export default function AdminAnalytics() {
  const navigate = useNavigate()
  
  // 加载状态
  const [loading, setLoading] = useState(false)
  const [overviewLoading, setOverviewLoading] = useState(false)
  const [trendLoading, setTrendLoading] = useState(false)
  const [detailsLoading, setDetailsLoading] = useState(false)
  
  // 数据状态
  const [overview, setOverview] = useState<AdminOverview | null>(null)
  const [trendData, setTrendData] = useState<TrendData | null>(null)
  const [repoDetails, setRepoDetails] = useState<RepoDetailItem[]>([])
  const [repoPagination, setRepoPagination] = useState({
    page: 1,
    page_size: 10,
    total: 0
  })
  
  // 筛选状态
  const [trendPeriod, setTrendPeriod] = useState<'hour' | 'day'>('day')
  const [trendDays, setTrendDays] = useState(7)
  const [detailStatus, setDetailStatus] = useState<string | undefined>(undefined)
  const [detailSortBy, setDetailSortBy] = useState<'total_calls' | 'total_cost' | 'name'>('total_calls')
  const [detailSortOrder, setDetailSortOrder] = useState<'asc' | 'desc'>('desc')
  
  // Tab状态
  const [activeTab, setActiveTab] = useState('overview')

  // 【V1.1新增】仓库明细弹窗状态
  const [detailModalVisible, setDetailModalVisible] = useState(false)
  const [detailModalRepo, setDetailModalRepo] = useState<RepoDetailItem | null>(null)
  const [repoTrendData, setRepoTrendData] = useState<RepoTrendData | null>(null)
  const [detailModalLoading, setDetailModalLoading] = useState(false)
  const [detailDays, setDetailDays] = useState(7)

  /**
   * 打开仓库明细弹窗
   */
  const openRepoDetail = async (repo: RepoDetailItem) => {
    setDetailModalRepo(repo)
    setDetailModalVisible(true)
    setDetailModalLoading(true)
    try {
      const data = await adminAnalyticsApi.getRepoTrend(repo.repo_id, detailDays)
      setRepoTrendData(data)
    } catch (err: any) {
      console.error('加载仓库趋势失败', err)
      message.error(err.userMessage || err.message || '加载仓库趋势失败')
    } finally {
      setDetailModalLoading(false)
    }
  }

  /**
   * 关闭仓库明细弹窗
   */
  const closeRepoDetail = () => {
    setDetailModalVisible(false)
    setDetailModalRepo(null)
    setRepoTrendData(null)
  }

  /**
   * 切换明细天数时重新加载
   */
  const handleDetailDaysChange = async (days: number) => {
    setDetailDays(days)
    if (detailModalRepo) {
      setDetailModalLoading(true)
      try {
        const data = await adminAnalyticsApi.getRepoTrend(detailModalRepo.repo_id, days)
        setRepoTrendData(data)
      } catch (err: any) {
        message.error(err.userMessage || err.message || '加载仓库趋势失败')
      } finally {
        setDetailModalLoading(false)
      }
    }
  }

  // 加载概览数据
  const loadOverview = async () => {
    setOverviewLoading(true)
    try {
      const data = await adminAnalyticsApi.getOverview()
      setOverview(data)
    } catch (err: any) {
      console.error('加载概览失败', err)
      message.error(err.userMessage || err.message || '加载概览失败')
    } finally {
      setOverviewLoading(false)
    }
  }

  // 加载趋势数据
  const loadTrend = async () => {
    setTrendLoading(true)
    try {
      const data = await adminAnalyticsApi.getTrend({
        period: trendPeriod,
        days: trendDays
      })
      setTrendData(data)
    } catch (err: any) {
      console.error('加载趋势数据失败', err)
      message.error(err.userMessage || err.message || '加载趋势失败')
    } finally {
      setTrendLoading(false)
    }
  }

  // 加载仓库明细
  const loadRepoDetails = async () => {
    setDetailsLoading(true)
    try {
      const data = await adminAnalyticsApi.getRepoDetails({
        page: repoPagination.page,
        page_size: repoPagination.page_size,
        status: detailStatus,
        sort_by: detailSortBy,
        sort_order: detailSortOrder
      })
      setRepoDetails(data.items)
      setRepoPagination(prev => ({
        ...prev,
        total: data.pagination.total
      }))
    } catch (err: any) {
      console.error('加载仓库明细失败', err)
      message.error(err.userMessage || err.message || '加载明细失败')
    } finally {
      setDetailsLoading(false)
    }
  }

  // 初始化加载
  useEffect(() => {
    loadOverview()
    loadTrend()
    loadRepoDetails()
  }, [])

  // 趋势周期变化时重新加载
  useEffect(() => {
    if (activeTab === 'trend' || activeTab === 'overview') {
      loadTrend()
    }
  }, [trendPeriod, trendDays])

  // Tab切换时加载对应数据
  useEffect(() => {
    if (activeTab === 'details') {
      loadRepoDetails()
    }
  }, [activeTab, repoPagination.page, detailStatus, detailSortBy, detailSortOrder])

  // 准备趋势图表数据
  const getTrendChartData = () => {
    if (!trendData) return []
    return trendData.labels.map((label, index) => ({
      time: label,
      calls: trendData.series.calls[index] || 0,
      revenue: trendData.series.revenue[index] || 0
    }))
  }

  // 仓库明细表格列
  const repoDetailColumns = [
    {
      title: '仓库名称',
      dataIndex: 'name',
      key: 'name',
      width: 200,
      render: (text: string, record: RepoDetailItem) => (
        <div>
          <div style={{ fontWeight: 500 }}>{text}</div>
          <div style={{ color: '#999', fontSize: 12 }}>{record.slug}</div>
        </div>
      )
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => (
        <Tag color={statusColors[status] || 'default'}>
          {statusText[status] || status}
        </Tag>
      )
    },
    {
      title: '总调用',
      dataIndex: 'total_calls',
      key: 'total_calls',
      width: 120,
      sorter: true,
      render: (value: number) => (
        <span style={{ color: '#1890ff' }}>
          {value.toLocaleString()} 次
        </span>
      )
    },
    {
      title: '成功',
      dataIndex: 'success_calls',
      key: 'success_calls',
      width: 100,
      render: (value: number) => (
        <span style={{ color: '#52c41a' }}>
          {value.toLocaleString()}
        </span>
      )
    },
    {
      title: '失败',
      dataIndex: 'failed_calls',
      key: 'failed_calls',
      width: 100,
      render: (value: number) => (
        <span style={{ color: value > 0 ? '#ff4d4f' : '#999' }}>
          {value.toLocaleString()}
        </span>
      )
    },
    {
      title: '成功率',
      dataIndex: 'success_rate',
      key: 'success_rate',
      width: 100,
      render: (value: number) => (
        <span style={{ 
          color: value >= 99 ? '#52c41a' : value >= 95 ? '#faad14' : '#ff4d4f' 
        }}>
          {value.toFixed(1)}%
        </span>
      )
    },
    {
      title: '总收入',
      dataIndex: 'total_cost',
      key: 'total_cost',
      width: 120,
      sorter: true,
      render: (value: number) => (
        <span style={{ color: '#faad14', fontWeight: 500 }}>
          ¥{value.toFixed(2)}
        </span>
      )
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 170,
      render: (time: string) => time ? new Date(time).toLocaleString('zh-CN') : '-'
    },
    {
      title: '操作',
      key: 'action',
      width: 180,
      fixed: 'right' as const,
      render: (_: any, record: RepoDetailItem) => (
        <Space size="small">
          <Button
            type="primary"
            size="small"
            icon={<LineChartOutlined />}
            onClick={() => openRepoDetail(record)}
          >
            查看明细
          </Button>
          <Button
            type="link"
            size="small"
            onClick={() => navigate(`/admin/repos/${record.slug}`)}
          >
            详情
          </Button>
        </Space>
      )
    }
  ]

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <Title level={4}>
          <LineChartOutlined style={{ marginRight: 8 }} />
          数据分析
        </Title>
        <Button 
          icon={<SyncOutlined />} 
          onClick={() => {
            loadOverview()
            loadTrend()
            loadRepoDetails()
          }}
        >
          刷新数据
        </Button>
      </div>

      <Tabs 
        activeKey={activeTab} 
        onChange={setActiveTab}
        items={[
          // ==================== 概览 Tab ====================
          {
            key: 'overview',
            label: (
              <span><ApiOutlined />数据概览</span>
            ),
            children: (
              <Spin spinning={overviewLoading}>
                {/* 统计卡片 */}
                <Row gutter={16} className={styles.statsRow}>
                  <Col span={6}>
                    <Card className={styles.statCard}>
                      <Statistic
                        title="仓库总数"
                        value={overview?.repos.total || 0}
                        prefix={<ApiOutlined />}
                        valueStyle={{ color: '#1890ff' }}
                      />
                      <div className={styles.statSub}>
                        <Tag color="green">{overview?.repos.online || 0} 已上线</Tag>
                        <Tag color="orange">{overview?.repos.pending || 0} 待审核</Tag>
                      </div>
                    </Card>
                  </Col>
                  <Col span={6}>
                    <Card className={styles.statCard}>
                      <Statistic
                        title="今日调用"
                        value={overview?.calls.today || 0}
                        prefix={<ThunderboltOutlined />}
                        valueStyle={{ color: '#722ed1' }}
                        suffix="次"
                      />
                      <div className={styles.statSub}>
                        <Text type="success">
                          <ArrowUpOutlined /> {overview?.calls.today_success || 0} 成功
                        </Text>
                        <Text type="danger" style={{ marginLeft: 8 }}>
                          <ArrowDownOutlined /> {overview?.calls.today_failed || 0} 失败
                        </Text>
                      </div>
                    </Card>
                  </Col>
                  <Col span={6}>
                    <Card className={styles.statCard}>
                      <Statistic
                        title="本周调用"
                        value={overview?.calls.week || 0}
                        prefix={<LineChartOutlined />}
                        valueStyle={{ color: '#13c2c2' }}
                        suffix="次"
                      />
                      <div className={styles.statSub}>
                        <Text type="secondary">
                          本月: {(overview?.calls.month || 0).toLocaleString()} 次
                        </Text>
                      </div>
                    </Card>
                  </Col>
                  <Col span={6}>
                    <Card className={styles.statCard}>
                      <Statistic
                        title="总收入"
                        value={overview?.revenue.total || 0}
                        prefix={<DollarOutlined />}
                        valueStyle={{ color: '#faad14' }}
                        precision={2}
                        prefix="¥"
                      />
                      <div className={styles.statSub}>
                        <Text type="secondary">
                          今日: ¥{(overview?.revenue.today || 0).toFixed(2)}
                        </Text>
                      </div>
                    </Card>
                  </Col>
                </Row>

                {/* 快捷统计 */}
                <Row gutter={16} className={styles.quickStats}>
                  <Col span={8}>
                    <Card size="small">
                      <Statistic
                        title="活跃用户（本周）"
                        value={overview?.active_users || 0}
                        prefix={<UserOutlined />}
                        valueStyle={{ color: '#eb2f96' }}
                      />
                    </Card>
                  </Col>
                  <Col span={8}>
                    <Card size="small">
                      <Statistic
                        title="本月调用"
                        value={overview?.calls.month || 0}
                        suffix="次"
                        valueStyle={{ color: '#13c2c2' }}
                      />
                    </Card>
                  </Col>
                  <Col span={8}>
                    <Card size="small">
                      <Statistic
                        title="本月收入"
                        value={overview?.revenue.month || 0}
                        prefix="¥"
                        precision={2}
                        valueStyle={{ color: '#faad14' }}
                      />
                    </Card>
                  </Col>
                </Row>

                {/* 趋势预览（简化版） */}
                <Card 
                  title="调用与收入趋势" 
                  className={styles.chartCard}
                  extra={
                    <Space>
                      <Select 
                        value={trendPeriod} 
                        onChange={setTrendPeriod}
                        style={{ width: 100 }}
                        options={[
                          { label: '按小时', value: 'hour' },
                          { label: '按天', value: 'day' }
                        ]}
                      />
                      {trendPeriod === 'day' && (
                        <Select 
                          value={trendDays} 
                          onChange={setTrendDays}
                          style={{ width: 100 }}
                          options={[
                            { label: '近7天', value: 7 },
                            { label: '近30天', value: 30 },
                            { label: '近90天', value: 90 }
                          ]}
                        />
                      )}
                    </Space>
                  }
                >
                  <Spin spinning={trendLoading}>
                    <ResponsiveContainer width="100%" height={300}>
                      <LineChart data={getTrendChartData()}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                        <XAxis dataKey="time" tick={{ fontSize: 12 }} />
                        <YAxis 
                          yAxisId="left" 
                          tick={{ fontSize: 12 }}
                          tickFormatter={(v) => v >= 1000 ? `${(v/1000).toFixed(0)}k` : v}
                        />
                        <YAxis 
                          yAxisId="right" 
                          orientation="right" 
                          tick={{ fontSize: 12 }}
                          tickFormatter={(v) => `¥${v.toFixed(0)}`}
                        />
                        <RechartsTooltip 
                          formatter={(value: number, name: string) => [
                            name === 'calls' ? `${value.toLocaleString()} 次` : `¥${value.toFixed(2)}`,
                            name === 'calls' ? '调用次数' : '收入'
                          ]}
                        />
                        <Legend />
                        <Line 
                          yAxisId="left"
                          type="monotone" 
                          dataKey="calls" 
                          stroke="#722ed1" 
                          strokeWidth={2}
                          dot={{ r: 3 }}
                          activeDot={{ r: 5 }}
                          name="调用次数"
                        />
                        <Line 
                          yAxisId="right"
                          type="monotone" 
                          dataKey="revenue" 
                          stroke="#faad14" 
                          strokeWidth={2}
                          dot={{ r: 3 }}
                          activeDot={{ r: 5 }}
                          name="收入"
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </Spin>
                </Card>
              </Spin>
            )
          },
          
          // ==================== 趋势 Tab ====================
          {
            key: 'trend',
            label: (
              <span><LineChartOutlined />趋势分析</span>
            ),
            children: (
              <Spin spinning={trendLoading}>
                <Card 
                  title="调用与收入趋势"
                  extra={
                    <Space>
                      <Select 
                        value={trendPeriod} 
                        onChange={setTrendPeriod}
                        style={{ width: 120 }}
                        options={[
                          { label: '按小时统计', value: 'hour' },
                          { label: '按天统计', value: 'day' }
                        ]}
                      />
                      {trendPeriod === 'day' && (
                        <Select 
                          value={trendDays} 
                          onChange={setTrendDays}
                          style={{ width: 120 }}
                          options={[
                            { label: '近7天', value: 7 },
                            { label: '近30天', value: 30 },
                            { label: '近90天', value: 90 }
                          ]}
                        />
                      )}
                    </Space>
                  }
                >
                  <ResponsiveContainer width="100%" height={400}>
                    <LineChart data={getTrendChartData()}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                      <XAxis dataKey="time" tick={{ fontSize: 12 }} />
                      <YAxis 
                        yAxisId="left" 
                        tick={{ fontSize: 12 }}
                        tickFormatter={(v) => v >= 1000 ? `${(v/1000).toFixed(0)}k` : v}
                      />
                      <YAxis 
                        yAxisId="right" 
                        orientation="right" 
                        tick={{ fontSize: 12 }}
                        tickFormatter={(v) => `¥${v.toFixed(0)}`}
                      />
                      <RechartsTooltip 
                        formatter={(value: number, name: string) => [
                          name === 'calls' ? `${value.toLocaleString()} 次` : `¥${value.toFixed(2)}`,
                          name === 'calls' ? '调用次数' : '收入'
                        ]}
                      />
                      <Legend />
                      <Line 
                        yAxisId="left"
                        type="monotone" 
                        dataKey="calls" 
                        stroke="#722ed1" 
                        strokeWidth={2}
                        dot={{ r: 4 }}
                        activeDot={{ r: 6 }}
                        name="调用次数"
                      />
                      <Line 
                        yAxisId="right"
                        type="monotone" 
                        dataKey="revenue" 
                        stroke="#faad14" 
                        strokeWidth={2}
                        dot={{ r: 4 }}
                        activeDot={{ r: 6 }}
                        name="收入金额"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </Card>

                {/* 数据统计表 */}
                <Card title="趋势数据明细" className={styles.dataTable}>
                  <Table
                    dataSource={getTrendChartData()}
                    rowKey="time"
                    pagination={false}
                    size="small"
                    columns={[
                      { title: '时间', dataIndex: 'time', key: 'time' },
                      { 
                        title: '调用次数', 
                        dataIndex: 'calls', 
                        key: 'calls',
                        render: (v) => v.toLocaleString()
                      },
                      { 
                        title: '收入', 
                        dataIndex: 'revenue', 
                        key: 'revenue',
                        render: (v) => `¥${v.toFixed(2)}`
                      }
                    ]}
                  />
                </Card>
              </Spin>
            )
          },
          
          // ==================== 明细 Tab ====================
          {
            key: 'details',
            label: (
              <span><TableOutlined />仓库明细</span>
            ),
            children: (
              <Spin spinning={detailsLoading}>
                <Card 
                  title="仓库调用与收入明细"
                  extra={
                    <Space wrap>
                      <Select
                        placeholder="状态筛选"
                        allowClear
                        value={detailStatus}
                        onChange={(v) => setDetailStatus(v)}
                        style={{ width: 120 }}
                        options={[
                          { label: '全部状态', value: undefined },
                          { label: '已上线', value: 'online' },
                          { label: '待审核', value: 'pending' },
                          { label: '已下线', value: 'offline' },
                          { label: '已拒绝', value: 'rejected' }
                        ]}
                      />
                      <Select
                        value={detailSortBy}
                        onChange={setDetailSortBy}
                        style={{ width: 130 }}
                        options={[
                          { label: '按调用量排序', value: 'total_calls' },
                          { label: '按收入排序', value: 'total_cost' },
                          { label: '按名称排序', value: 'name' }
                        ]}
                      />
                      <Select
                        value={detailSortOrder}
                        onChange={setDetailSortOrder}
                        style={{ width: 100 }}
                        options={[
                          { label: '降序', value: 'desc' },
                          { label: '升序', value: 'asc' }
                        ]}
                      />
                    </Space>
                  }
                >
                  <Table
                    dataSource={repoDetails}
                    columns={repoDetailColumns}
                    rowKey="repo_id"
                    pagination={{
                      current: repoPagination.page,
                      pageSize: repoPagination.page_size,
                      total: repoPagination.total,
                      showSizeChanger: true,
                      showQuickJumper: true,
                      showTotal: (total) => `共 ${total} 条`,
                      onChange: (page, pageSize) => {
                        setRepoPagination(prev => ({ ...prev, page, page_size: pageSize }))
                      }
                    }}
                    scroll={{ x: 1200 }}
                    size="middle"
                  />
                </Card>
              </Spin>
            )
          }
        ]}
      />

      {/* 【V1.1新增】仓库明细弹窗 */}
      <Modal
        title={
          <Space>
            <LineChartOutlined />
            仓库收入与调用明细 - {detailModalRepo?.name}
          </Space>
        }
        open={detailModalVisible}
        onCancel={closeRepoDetail}
        footer={null}
        width={900}
        destroyOnClose
      >
        <Spin spinning={detailModalLoading}>
          {/* 基本信息 */}
          {detailModalRepo && (
            <Descriptions size="small" column={4} bordered style={{ marginBottom: 16 }}>
              <Descriptions.Item label="仓库ID">{detailModalRepo.repo_id}</Descriptions.Item>
              <Descriptions.Item label="Slug">{detailModalRepo.slug}</Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={statusColors[detailModalRepo.status] || 'default'}>
                  {statusText[detailModalRepo.status] || detailModalRepo.status}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="创建时间">
                {detailModalRepo.created_at ? new Date(detailModalRepo.created_at).toLocaleString('zh-CN') : '-'}
              </Descriptions.Item>
            </Descriptions>
          )}

          {/* 汇总统计 */}
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col span={6}>
              <Card size="small">
                <Statistic
                  title="总调用次数"
                  value={detailModalRepo?.total_calls || 0}
                  valueStyle={{ color: '#722ed1' }}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small">
                <Statistic
                  title="成功调用"
                  value={detailModalRepo?.success_calls || 0}
                  suffix={`/ ${detailModalRepo?.total_calls || 0}`}
                  valueStyle={{ color: '#52c41a' }}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small">
                <Statistic
                  title="失败调用"
                  value={detailModalRepo?.failed_calls || 0}
                  valueStyle={{ color: '#ff4d4f' }}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small">
                <Statistic
                  title="总收入"
                  value={detailModalRepo?.total_cost || 0}
                  prefix="¥"
                  precision={2}
                  valueStyle={{ color: '#faad14' }}
                />
              </Card>
            </Col>
          </Row>

          {/* 成功率 */}
          <Card size="small" style={{ marginBottom: 16 }}>
            <Space>
              <span>成功率：</span>
              <Progress
                percent={detailModalRepo?.success_rate || 0}
                format={(p) => `${p?.toFixed(1)}%`}
                strokeColor={{
                  '0%': '#ff4d4f',
                  '50%': '#faad14',
                  '100%': '#52c41a'
                }}
                style={{ width: 200 }}
              />
              <Text type="secondary">
                (成功 {detailModalRepo?.success_calls || 0} / 失败 {detailModalRepo?.failed_calls || 0})
              </Text>
            </Space>
          </Card>

          <Divider />

          {/* 趋势图表 */}
          <Card
            title="趋势分析"
            extra={
              <Select
                value={detailDays}
                onChange={handleDetailDaysChange}
                style={{ width: 120 }}
                options={[
                  { label: '近7天', value: 7 },
                  { label: '近30天', value: 30 },
                  { label: '近90天', value: 90 }
                ]}
              />
            }
          >
            {repoTrendData ? (
              <>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={
                    repoTrendData.labels.map((label, index) => ({
                      time: label,
                      calls: repoTrendData.series.calls[index] || 0,
                      revenue: repoTrendData.series.revenue[index] || 0,
                      avgLatency: repoTrendData.series.avg_latency[index] || 0
                    }))
                  }>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis dataKey="time" tick={{ fontSize: 12 }} />
                    <YAxis
                      yAxisId="left"
                      tick={{ fontSize: 12 }}
                      tickFormatter={(v) => v >= 1000 ? `${(v/1000).toFixed(0)}k` : v}
                    />
                    <YAxis
                      yAxisId="right"
                      orientation="right"
                      tick={{ fontSize: 12 }}
                      tickFormatter={(v) => `¥${v.toFixed(0)}`}
                    />
                    <RechartsTooltip
                      formatter={(value: number, name: string) => [
                        name === 'calls' ? `${value.toLocaleString()} 次` : name === 'revenue' ? `¥${value.toFixed(2)}` : `${value.toFixed(0)}ms`,
                        name === 'calls' ? '调用次数' : name === 'revenue' ? '收入' : '平均延迟'
                      ]}
                    />
                    <Legend />
                    <Line
                      yAxisId="left"
                      type="monotone"
                      dataKey="calls"
                      stroke="#722ed1"
                      strokeWidth={2}
                      dot={{ r: 3 }}
                      name="调用次数"
                    />
                    <Line
                      yAxisId="right"
                      type="monotone"
                      dataKey="revenue"
                      stroke="#faad14"
                      strokeWidth={2}
                      dot={{ r: 3 }}
                      name="收入"
                    />
                  </LineChart>
                </ResponsiveContainer>

                {/* 数据表格 */}
                <Table
                  dataSource={
                    repoTrendData.labels.map((label, index) => ({
                      key: index,
                      time: label,
                      calls: repoTrendData.series.calls[index] || 0,
                      revenue: repoTrendData.series.revenue[index] || 0
                    })).reverse()
                  }
                  columns={[
                    { title: '日期', dataIndex: 'time', key: 'time', width: 150 },
                    {
                      title: '调用次数',
                      dataIndex: 'calls',
                      key: 'calls',
                      render: (v: number) => v.toLocaleString()
                    },
                    {
                      title: '收入',
                      dataIndex: 'revenue',
                      key: 'revenue',
                      render: (v: number) => `¥${v.toFixed(2)}`
                    }
                  ]}
                  pagination={false}
                  size="small"
                  style={{ marginTop: 16 }}
                />
              </>
            ) : (
              <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
                暂无趋势数据
              </div>
            )}
          </Card>

          {/* 更新时间 */}
          {repoTrendData && (
            <div style={{ marginTop: 12, textAlign: 'right' }}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                数据更新时间: {new Date(repoTrendData.generated_at).toLocaleString('zh-CN')}
              </Text>
            </div>
          )}
        </Spin>
      </Modal>

      {/* 底部信息 */}
      {overview && (
        <div className={styles.footer}>
          <Text type="secondary">
            数据更新时间: {new Date(overview.generated_at).toLocaleString('zh-CN')}
          </Text>
        </div>
      )}
    </div>
  )
}
