/**
 * 「趋势分析」Tab —— P1-4 巨型组件拆分（B 轮，由 `../Analytics.tsx` 抽出）
 *
 * 内容：调用与收入趋势折线图（双 Y 轴）+ 趋势数据明细表。
 * 原实现把图表与明细表各自调用一次 `buildTrendChartData(trendData)` —— 现只算一次复用
 * （纯函数、结果相同，行为不变）。
 *
 * ⚠️ `trendPeriod` / `trendDays` 是**受控 prop**：与概览 Tab 共用同一份状态，不能收进组件内部。
 */
import { Card, Spin, Table } from 'antd'
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { TrendData } from '../../../api/adminAnalytics'
import { buildTrendChartData } from './chartData'
import { TrendControls } from './TrendControls'
// ⚠️ 样式在 admin/ 下，本文件在 admin/analytics/ → 回退一级
import styles from '../Analytics.module.css'

export interface TrendTabProps {
  trendData: TrendData | null
  trendLoading: boolean
  trendPeriod: 'hour' | 'day'
  trendDays: number
  onPeriodChange: (value: 'hour' | 'day') => void
  onDaysChange: (value: number) => void
}

export function TrendTab({
  trendData,
  trendLoading,
  trendPeriod,
  trendDays,
  onPeriodChange,
  onDaysChange,
}: TrendTabProps) {
  const chartData = buildTrendChartData(trendData)

  return (
    <Spin spinning={trendLoading}>
      <Card
        title="调用与收入趋势"
        extra={
          <TrendControls
            period={trendPeriod}
            days={trendDays}
            onPeriodChange={onPeriodChange}
            onDaysChange={onDaysChange}
          />
        }
      >
        <ResponsiveContainer width="100%" height={400}>
          <LineChart data={chartData}>
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
          dataSource={chartData}
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
              render: (v: number) => v.toLocaleString(),
            },
            {
              title: '收入',
              dataIndex: 'revenue',
              key: 'revenue',
              width: 100,
              render: (v: number) => `¥${v.toFixed(2)}`,
            },
          ]}
        />
      </Card>
    </Spin>
  )
}
