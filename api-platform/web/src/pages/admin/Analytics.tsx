/**
 * 管理员分析报表页面
 * 功能：全局统计概览、调用/收入趋势图、仓库明细排行榜
 * V1.0 - 初始版本
 */

import { useState, useEffect } from 'react'
import '../../styles/cyber-theme.css'
import {
  Card,
  Row,
  Col,
  Statistic,
  Table,
  Select,
  Button,
  Space,
  Spin,
  Tabs,
  Typography,
  message
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
// 【P1-4 拆分】状态映射与图表数据整形已抽到同目录 `analytics/`（纯数据 / 纯函数，均已单测）
import { statusColors, statusText } from './analytics/constants'
import { createRepoDetailColumns } from './analytics/repoDetailColumns'
import { OverviewTab } from './analytics/OverviewTab'
import { RepoDetailModal } from './analytics/RepoDetailModal'
import { buildRepoTrendChartData, buildTrendChartData } from './analytics/chartData'

const { Title, Text } = Typography
const { TabPane } = Tabs

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
  // 【2026-09-15 修复】原先这里也调用了 loadTrend()，但紧随其后的
  // `[trendPeriod, trendDays]` effect 在挂载时同样会执行（初始 activeTab='overview' 满足其条件）
  // → 首屏会**重复请求**一次趋势数据（实测 2 次）。此处去掉，行为等价且少一次查询。
  useEffect(() => {
    loadOverview()
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

  // 趋势图表数据改由 `analytics/chartData.ts` 的 buildTrendChartData(trendData) 生成（纯函数，已单测）

  // 仓库明细表格列
  // 「仓库明细」表格列定义已抽至 ./analytics/repoDetailColumns（工厂函数，需传入两个动作回调）
  const repoDetailColumns = createRepoDetailColumns({
    onViewDetail: openRepoDetail,
    onOpenRepo: (slug) => navigate(`/admin/repos/${slug}`),
  })

  return (
    <div className={`${styles.container} bamboo-bg-pattern`}>
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
              // 概览内容已抽为 ./analytics/OverviewTab
              <OverviewTab
                overview={overview}
                overviewLoading={overviewLoading}
                trendData={trendData}
                trendLoading={trendLoading}
                trendPeriod={trendPeriod}
                trendDays={trendDays}
                onPeriodChange={setTrendPeriod}
                onDaysChange={setTrendDays}
              />
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
                    <LineChart data={buildTrendChartData(trendData)}>
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
                        stroke="#10b981" 
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
                    dataSource={buildTrendChartData(trendData)}
                    rowKey="time"
                    pagination={false}
                    size="small"
                    tableLayout="fixed"
                    columns={[
                      { title: '时间', dataIndex: 'time', key: 'time', width: 150 },
                      { 
                        title: '调用次数', 
                        dataIndex: 'calls', 
                        key: 'calls',
                        width: 120,
                        render: (v) => v.toLocaleString()
                      },
                      { 
                        title: '收入', 
                        dataIndex: 'revenue', 
                        key: 'revenue',
                        width: 100,
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
                    scroll={{ x: 'max-content' }}
                    size="small"
                    tableLayout="fixed"
                  />
                </Card>
              </Spin>
            )
          }
        ]}
      />

      {/* 【V1.1新增】仓库明细弹窗 —— 内容已抽为 ./analytics/RepoDetailModal */}
      <RepoDetailModal
        open={detailModalVisible}
        onClose={closeRepoDetail}
        loading={detailModalLoading}
        repo={detailModalRepo}
        trendData={repoTrendData}
        days={detailDays}
        onDaysChange={handleDetailDaysChange}
      />

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
