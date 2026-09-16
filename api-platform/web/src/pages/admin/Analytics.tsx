/**
 * 管理员分析报表页面
 * 功能：全局统计概览、调用/收入趋势图、仓库明细排行榜
 * V1.0 - 初始版本
 *
 * 【P1-4 拆分 · B 轮收尾】本文件原 964 行，现按 Tab 拆成子组件（同目录 `analytics/`）：
 *   · OverviewTab / TrendTab / RepoDetailsTab —— 三个 Tab 的内容
 *   · RepoDetailModal  —— 单个仓库明细弹窗
 *   · TrendControls    —— 概览与趋势共用的周期/天数控件（本轮抽出；原先两处各写一份、
 *                          文案还不一致「按天」vs「按天统计」，见用例库 FE-BUG-ANALYTICS-DUP-TREND-CARD）
 *   · chartData / repoDetailColumns / constants —— 纯函数与常量（均已单测）
 * 本文件只保留：状态、数据加载、Tab 组合。**拆分是纯搬运，零行为改变**。
 */

import { useState, useEffect } from 'react'
import '../../styles/cyber-theme.css'
import { Button, Tabs, Typography, message } from 'antd'
import { ApiOutlined, LineChartOutlined, SyncOutlined, TableOutlined } from '@ant-design/icons'
import { adminAnalyticsApi, AdminOverview, TrendData, RepoDetailItem, RepoTrendData } from '../../api/adminAnalytics'
import { useNavigate } from 'react-router-dom'
import styles from './Analytics.module.css'
// 【P1-4 拆分】子组件与纯逻辑均在 ./analytics/ 下
import { createRepoDetailColumns } from './analytics/repoDetailColumns'
import { OverviewTab } from './analytics/OverviewTab'
import { TrendTab } from './analytics/TrendTab'
import { RepoDetailsTab } from './analytics/RepoDetailsTab'
import { RepoDetailModal } from './analytics/RepoDetailModal'

const { Title, Text } = Typography

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
              // B 轮抽出：图表 + 趋势明细表（周期/天数用共享的 TrendControls）
              <TrendTab
                trendData={trendData}
                trendLoading={trendLoading}
                trendPeriod={trendPeriod}
                trendDays={trendDays}
                onPeriodChange={setTrendPeriod}
                onDaysChange={setTrendDays}
              />
            )
          },
          
          // ==================== 明细 Tab ====================
          {
            key: 'details',
            label: (
              <span><TableOutlined />仓库明细</span>
            ),
            children: (
              // B 轮抽出：筛选 + 表格 + 服务端分页
              <RepoDetailsTab
                loading={detailsLoading}
                items={repoDetails}
                columns={repoDetailColumns}
                pagination={repoPagination}
                onPageChange={(page, pageSize) =>
                  setRepoPagination(prev => ({ ...prev, page, page_size: pageSize }))
                }
                status={detailStatus}
                onStatusChange={setDetailStatus}
                sortBy={detailSortBy}
                onSortByChange={(v) => setDetailSortBy(v as 'total_calls' | 'total_cost' | 'name')}
                sortOrder={detailSortOrder}
                onSortOrderChange={(v) => setDetailSortOrder(v as 'asc' | 'desc')}
              />
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
