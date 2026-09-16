/**
 * 「数据概览」Tab —— P1-4 巨型组件拆分（纯搬运，零行为改变）
 *
 * 由 `../Analytics.tsx` 抽出（原占约 185 行）。内容：
 *   ① 4 张统计卡片（仓库总数 / 今日调用 / 本周调用 / 总收入）
 *   ② 3 张快捷统计（活跃用户 / 本月调用 / 本月收入）
 *   ③ 趋势预览（周期/天数选择 + 双 Y 轴折线图）
 *
 * ⚠️ 第 ③ 块的折线图与「趋势分析」Tab、明细弹窗里的图表写法高度重复
 *    （同样的 YAxis/Tooltip/Line 组合），后续可再提为一个 `TrendChart` 组件共用。
 *
 * ⚠️ 本组件把 `trendPeriod` / `trendDays` 也作为受控 prop 传进来：
 *    概览页的周期选择与「趋势分析」Tab **共用同一份状态**（切换 Tab 后选择保持一致），
 *    这是既有行为，不能改成组件内部 state。
 */
import { Card, Col, Row, Spin, Statistic, Tag, Typography } from 'antd'
import {
  ApiOutlined,
  ThunderboltOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  LineChartOutlined,
  DollarOutlined,
  UserOutlined,
} from '@ant-design/icons'
import {
  Line,
  LineChart,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'
import type { AdminOverview, TrendData } from '../../../api/adminAnalytics'
import { buildTrendChartData } from './chartData'
import { TrendControls } from './TrendControls'
// ⚠️ 样式在 admin/ 下，本文件在 admin/analytics/ → 回退一级
import styles from '../Analytics.module.css'

const { Text } = Typography

export interface OverviewTabProps {
  overview: AdminOverview | null
  overviewLoading: boolean
  trendData: TrendData | null
  trendLoading: boolean
  /** 与「趋势分析」Tab 共用 */
  trendPeriod: 'hour' | 'day'
  trendDays: number
  onPeriodChange: (value: 'hour' | 'day') => void
  onDaysChange: (value: number) => void
}

export function OverviewTab({
  overview,
  overviewLoading,
  trendData,
  trendLoading,
  trendPeriod,
  trendDays,
  onPeriodChange,
  onDaysChange,
}: OverviewTabProps) {
  return (
    <Spin spinning={overviewLoading}>
      {/* 统计卡片 */}
      <Row gutter={[12, 12]} className={styles.statsRow}>
        <Col xs={24} sm={12} lg={6}>
          <Card className={styles.statCard}>
            <Statistic
              title="仓库总数"
              value={overview?.repos.total || 0}
              prefix={<ApiOutlined />}
              valueStyle={{ color: '#10b981' }}
            />
            <div className={styles.statSub}>
              <Tag color="green">{overview?.repos.online || 0} 已上线</Tag>
              <Tag color="orange">{overview?.repos.pending || 0} 待审核</Tag>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className={styles.statCard}>
            <Statistic
              title="今日调用"
              value={overview?.calls.today || 0}
              prefix={<ThunderboltOutlined />}
              valueStyle={{ color: '#059669' }}
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
        <Col xs={24} sm={12} lg={6}>
          <Card className={styles.statCard}>
            <Statistic
              title="本周调用"
              value={overview?.calls.week || 0}
              prefix={<LineChartOutlined />}
              valueStyle={{ color: '#10b981' }}
              suffix="次"
            />
            <div className={styles.statSub}>
              <Text type="secondary">本月: {(overview?.calls.month || 0).toLocaleString()} 次</Text>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className={styles.statCard}>
            <Statistic
              title="总收入"
              value={overview?.revenue.total || 0}
              prefix={<DollarOutlined />}
              valueStyle={{ color: '#faad14' }}
              precision={2}
            />
            <div className={styles.statSub}>
              <Text type="secondary">今日: ¥{(overview?.revenue.today || 0).toFixed(2)}</Text>
            </div>
          </Card>
        </Col>
      </Row>

      {/* 快捷统计 */}
      <Row gutter={[12, 12]} className={styles.quickStats}>
        <Col xs={24} sm={8}>
          <Card size="small">
            <Statistic
              title="活跃用户（本周）"
              value={overview?.active_users || 0}
              prefix={<UserOutlined />}
              valueStyle={{ color: '#059669' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card size="small">
            <Statistic
              title="本月调用"
              value={overview?.calls.month || 0}
              suffix="次"
              valueStyle={{ color: '#10b981' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
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
          // ⚠️ 与「趋势分析」Tab 共用同一个受控控件：原先两处各写了一份 options，
          //    文案还不一致（这里是「按天」，那边是「按天统计」）—— 见用例库
          //    FE-BUG-ANALYTICS-DUP-TREND-CARD，现已统一到 TrendControls
          <TrendControls
            period={trendPeriod}
            days={trendDays}
            onPeriodChange={onPeriodChange}
            onDaysChange={onDaysChange}
            compact
          />
        }
      >
        <Spin spinning={trendLoading}>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={buildTrendChartData(trendData)}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="time" tick={{ fontSize: 12 }} />
              <YAxis
                yAxisId="left"
                tick={{ fontSize: 12 }}
                tickFormatter={(v) => (v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v)}
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
                  name === 'calls' ? '调用次数' : '收入',
                ]}
              />
              <Legend />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="calls"
                stroke="#10b981"
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
}
