/**
 * 数据分析页面 - 竹韵赛博风主题
 */

import { useState, useEffect, useCallback } from 'react'
import '../../styles/cyber-theme.css'
import { Spin } from 'antd'
import { 
  ApiOutlined, 
  RiseOutlined, 
  DollarOutlined, 
  BarChartOutlined,
  LineChartOutlined,
  PieChartOutlined,
  SyncOutlined,
  ThunderboltOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined
} from '@ant-design/icons'
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer, 
  PieChart, 
  Pie, 
  Cell,
  Area,
  AreaChart,
  Legend
} from 'recharts'
import { analyticsApi, OverviewStats, WeeklyStats, HourlyStats, SourceStats } from '../../api/analytics'
import styles from './Analytics.module.css'

// 竹韵主题配色
const COLORS = ['#059669', '#10b981', '#34d399', '#6ee7b7', '#a7f3d0', '#d1fae5']

// 自定义 Tooltip 组件
const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className={styles.customTooltip}>
        <div className={styles.customTooltipLabel}>{label}</div>
        {payload.map((entry: any, index: number) => (
          <div key={index} className={styles.customTooltipItem}>
            <span 
              className={styles.customTooltipDot} 
              style={{ backgroundColor: entry.color }}
            />
            {entry.name}: {typeof entry.value === 'number' ? entry.value.toLocaleString() : entry.value}
          </div>
        ))}
      </div>
    )
  }
  return null
}

// 格式化数字
const formatNumber = (num: number): string => {
  if (num >= 10000) {
    return (num / 10000).toFixed(1) + 'w'
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'k'
  }
  return num.toLocaleString()
}

// 获取问候语
const getGreeting = (): string => {
  const hour = new Date().getHours()
  if (hour < 6) return '凌晨好'
  if (hour < 9) return '早上好'
  if (hour < 12) return '上午好'
  if (hour < 14) return '中午好'
  if (hour < 18) return '下午好'
  if (hour < 22) return '晚上好'
  return '夜深了'
}

export default function OwnerAnalytics() {
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [overview, setOverview] = useState<OverviewStats | null>(null)
  const [weeklyData, setWeeklyData] = useState<WeeklyStats[]>([])
  const [hourlyData, setHourlyData] = useState<HourlyStats[]>([])
  const [sourceData, setSourceData] = useState<SourceStats[]>([])
  const [chartView, setChartView] = useState<'bar' | 'area'>('area')

  // 获取所有统计数据
  const fetchData = useCallback(async (isRefresh = false) => {
    if (isRefresh) {
      setRefreshing(true)
    } else {
      setLoading(true)
    }
    
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
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  // 刷新数据
  const handleRefresh = () => {
    fetchData(true)
  }

  // 格式化周数据
  const formatWeeklyData = (weeklyData || []).map(item => ({
    ...item,
    dateLabel: item.date.split('-').slice(1).join('/'),
    date: item.date
  }))

  // 计算峰值
  const peakHour = hourlyData.length > 0 
    ? hourlyData.reduce((max, item) => item.calls > max.calls ? item : max, hourlyData[0])
    : null

  // 计算活跃时间
  const activeHours = hourlyData.filter(h => h.calls > 0).length

  if (loading) {
    return (
      <div className={styles.loadingContainer}>
        <div className={styles.loadingContent}>
          <div className={styles.loadingSpinner} />
          <div className={styles.loadingText}>正在加载数据分析...</div>
        </div>
      </div>
    )
  }

  return (
    <div className={`${styles.container} bamboo-bg-pattern`}>
      {/* 竹韵背景装饰 */}
      <div className={styles.bambooDecoration} />

      {/* 内容区域 */}
      <div className={styles.content}>
        {/* 头部 */}
        <div className={`${styles.header} ${styles.animateSlideUp}`} style={{ flexWrap: 'wrap', gap: 12 }}>
          <div className={styles.headerLeft}>
            <h1 style={{ fontSize: 20, marginBottom: 4 }}>{getGreeting()}，数据分析师</h1>
            <p style={{ fontSize: 12 }}>以下是您的 API 调用数据概览</p>
          </div>
          <div className={styles.headerRight}>
            <button className={styles.refreshButton} onClick={handleRefresh} disabled={refreshing}>
              <SyncOutlined spin={refreshing} />
              {refreshing ? '刷新中...' : '刷新数据'}
            </button>
          </div>
        </div>

        {/* 统计卡片 - 竹韵主题 */}
        <div className={styles.statsGrid}>
          {/* 总调用量 - 竹韵绿 */}
          <div className={`${styles.statCard} ${styles.animateSlideUp} ${styles.animateDelay1}`} style={{ '--card-color': '#059669' } as React.CSSProperties}>
            <div className={styles.statIconWrapper} style={{ background: 'linear-gradient(135deg, #059669, #10b981)' }}>
              <ApiOutlined className={styles.statIcon} />
            </div>
            <div className={styles.statLabel}>总调用量</div>
            <div className={styles.statValue}>{formatNumber(overview?.total_calls || 0)}</div>
            <div className={styles.statTrend}>
              <RiseOutlined />
              <span>+{overview?.growth_rate || 0}% 较上月</span>
            </div>
          </div>

          {/* 本月调用 - 翡翠绿 */}
          <div className={`${styles.statCard} ${styles.animateSlideUp} ${styles.animateDelay2}`} style={{ '--card-color': '#10b981' } as React.CSSProperties}>
            <div className={styles.statIconWrapper} style={{ background: 'linear-gradient(135deg, #10b981, #34d399)' }}>
              <LineChartOutlined className={styles.statIcon} />
            </div>
            <div className={styles.statLabel}>本月调用</div>
            <div className={styles.statValue}>{formatNumber(overview?.month_calls || 0)}</div>
            <div className={styles.statMeta}>占总量的 {overview?.total_calls ? Math.round((overview.month_calls / overview.total_calls) * 100) : 0}%</div>
          </div>

          {/* 总收益 - 琥珀色 */}
          <div className={`${styles.statCard} ${styles.animateSlideUp} ${styles.animateDelay3}`} style={{ '--card-color': '#d97706' } as React.CSSProperties}>
            <div className={styles.statIconWrapper} style={{ background: 'linear-gradient(135deg, #d97706, #f59e0b)' }}>
              <DollarOutlined className={styles.statIcon} />
            </div>
            <div className={styles.statLabel}>总收益</div>
            <div className={styles.statValue}>¥{overview?.total_revenue?.toFixed(2) || '0.00'}</div>
            <div className={styles.statMeta}>持续增长中</div>
          </div>

          {/* 活跃仓库 - 深绿 */}
          <div className={`${styles.statCard} ${styles.animateSlideUp} ${styles.animateDelay4}`} style={{ '--card-color': '#047857' } as React.CSSProperties}>
            <div className={styles.statIconWrapper} style={{ background: 'linear-gradient(135deg, #047857, #059669)' }}>
              <BarChartOutlined className={styles.statIcon} />
            </div>
            <div className={styles.statLabel}>活跃仓库</div>
            <div className={styles.statValue}>{overview?.total_repos || 0}</div>
            <div className={styles.statMeta}>正在运行的 API</div>
          </div>
        </div>

        {/* 图表区域 */}
        <div className={`${styles.chartsGrid} ${styles.animateSlideUp}`} style={{ animationDelay: '0.5s', opacity: 0 }}>
          {/* 趋势图 */}
          <div className={styles.chartCard}>
            <div className={styles.chartHeader}>
              <h3 className={styles.chartTitle}>
                <div className={styles.chartTitleIcon}>
                  <LineChartOutlined />
                </div>
                调用趋势
              </h3>
              <div className={styles.chartTabs}>
                <button 
                  className={`${styles.chartTab} ${chartView === 'area' ? styles.active : ''}`}
                  onClick={() => setChartView('area')}
                >
                  面积图
                </button>
                <button 
                  className={`${styles.chartTab} ${chartView === 'bar' ? styles.active : ''}`}
                  onClick={() => setChartView('bar')}
                >
                  柱状图
                </button>
              </div>
            </div>
            
            {formatWeeklyData.length > 0 ? (
              <ResponsiveContainer width="100%" height={320}>
                {chartView === 'area' ? (
                  <AreaChart data={formatWeeklyData}>
                    <defs>
                      <linearGradient id="colorCalls" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#059669" stopOpacity={0.8}/>
                        <stop offset="95%" stopColor="#059669" stopOpacity={0}/>
                      </linearGradient>
                      <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#d97706" stopOpacity={0.8}/>
                        <stop offset="95%" stopColor="#d97706" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                    <XAxis dataKey="dateLabel" stroke="#64748b" fontSize={12} />
                    <YAxis yAxisId="left" stroke="#059669" fontSize={12} />
                    <YAxis yAxisId="right" orientation="right" stroke="#d97706" fontSize={12} />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend />
                    <Area 
                      yAxisId="left"
                      type="monotone" 
                      dataKey="calls" 
                      name="调用量"
                      stroke="#059669" 
                      fillOpacity={1} 
                      fill="url(#colorCalls)" 
                    />
                    <Area 
                      yAxisId="right"
                      type="monotone" 
                      dataKey="revenue" 
                      name="收益"
                      stroke="#d97706" 
                      fillOpacity={1} 
                      fill="url(#colorRevenue)" 
                    />
                  </AreaChart>
                ) : (
                  <BarChart data={formatWeeklyData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                    <XAxis dataKey="dateLabel" stroke="#64748b" fontSize={12} />
                    <YAxis yAxisId="left" orientation="left" stroke="#059669" fontSize={12} />
                    <YAxis yAxisId="right" orientation="right" stroke="#d97706" fontSize={12} />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend />
                    <Bar yAxisId="left" dataKey="calls" name="调用量" fill="#059669" radius={[4, 4, 0, 0]} />
                    <Bar yAxisId="right" dataKey="revenue" name="收益" fill="#d97706" radius={[4, 4, 0, 0]} />
                  </BarChart>
                )}
              </ResponsiveContainer>
            ) : (
              <div className={styles.emptyState}>
                <LineChartOutlined style={{ fontSize: 60, color: '#ccc' }} />
                <div className={styles.emptyTitle}>暂无趋势数据</div>
                <div className={styles.emptyDesc}>调用数据将在这里展示</div>
              </div>
            )}
          </div>

          {/* 来源分布 */}
          <div className={styles.chartCard}>
            <div className={styles.chartHeader}>
              <h3 className={styles.chartTitle}>
                <div className={styles.chartTitleIcon} style={{ background: 'linear-gradient(135deg, #10b981, #34d399)' }}>
                  <PieChartOutlined />
                </div>
                调用来源
              </h3>
              <div className={styles.realtimeIndicator}>
                <span className={styles.realtimeDot} />
                实时
              </div>
            </div>
            
            {sourceData.length > 0 ? (
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie
                    data={sourceData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={5}
                    label={({ name, percentage }) => `${name} ${percentage}%`}
                    labelLine={false}
                  >
                    {sourceData.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomTooltip />} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className={styles.emptyState}>
                <PieChartOutlined style={{ fontSize: 60, color: '#ccc' }} />
                <div className={styles.emptyTitle}>暂无来源数据</div>
                <div className={styles.emptyDesc}>来源数据将在这里展示</div>
              </div>
            )}
          </div>
        </div>

        {/* 24小时分布 */}
        <div className={`${styles.chartCard} ${styles.animateSlideUp}`} style={{ animationDelay: '0.6s', opacity: 0 }}>
          <div className={styles.chartHeader}>
            <h3 className={styles.chartTitle}>
              <div className={styles.chartTitleIcon} style={{ background: 'linear-gradient(135deg, #059669, #10b981)' }}>
                <ClockCircleOutlined />
              </div>
              24小时调用分布
            </h3>
            {peakHour && (
              <div className={styles.realtimeIndicator}>
                <ThunderboltOutlined />
                峰值: {peakHour.hour} ({peakHour.calls}次)
              </div>
            )}
          </div>
          
          {hourlyData.some(h => h.calls > 0) ? (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={hourlyData}>
                <defs>
                  <linearGradient id="colorHourly" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#059669" stopOpacity={1}/>
                    <stop offset="95%" stopColor="#059669" stopOpacity={0.3}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
                <XAxis 
                  dataKey="hour" 
                  stroke="#999" 
                  fontSize={11}
                  interval={2}
                />
                <YAxis stroke="#999" fontSize={12} />
                <Tooltip content={<CustomTooltip />} />
                <Bar 
                  dataKey="calls" 
                  name="调用量"
                  fill="url(#colorHourly)" 
                  radius={[4, 4, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className={styles.emptyState}>
              <ClockCircleOutlined style={{ fontSize: 60, color: '#ccc' }} />
              <div className={styles.emptyTitle}>暂无小时数据</div>
              <div className={styles.emptyDesc}>按小时的调用分布将在这里展示</div>
            </div>
          )}
        </div>

        {/* 底部统计 */}
        <div className={`${styles.bottomStats} ${styles.animateSlideUp}`} style={{ animationDelay: '0.7s', opacity: 0 }}>
          <div className={styles.bottomStatCard}>
            <div className={styles.bottomStatIcon} style={{ background: 'linear-gradient(135deg, #059669, #10b981)' }}>
              <CheckCircleOutlined />
            </div>
            <div className={styles.bottomStatInfo}>
              <div className={styles.bottomStatLabel}>服务可用性</div>
              <div className={styles.bottomStatValue}>99.9%</div>
            </div>
          </div>
          
          <div className={styles.bottomStatCard}>
            <div className={styles.bottomStatIcon} style={{ background: 'linear-gradient(135deg, #10b981, #34d399)' }}>
              <ClockCircleOutlined />
            </div>
            <div className={styles.bottomStatInfo}>
              <div className={styles.bottomStatLabel}>活跃时段</div>
              <div className={styles.bottomStatValue}>{activeHours} 小时</div>
            </div>
          </div>
          
          <div className={styles.bottomStatCard}>
            <div className={styles.bottomStatIcon} style={{ background: 'linear-gradient(135deg, #d97706, #f59e0b)' }}>
              <ThunderboltOutlined />
            </div>
            <div className={styles.bottomStatInfo}>
              <div className={styles.bottomStatLabel}>API 峰值</div>
              <div className={styles.bottomStatValue}>{peakHour ? `${peakHour.hour} (${peakHour.calls})` : '-'}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
