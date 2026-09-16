/**
 * 趋势「周期 + 天数」选择器 —— P1-4 巨型组件拆分（B 轮）抽出。
 *
 * 为什么值得单独抽：
 *   同一页原先有**三处**几乎相同的写法（概览 Tab 卡片、趋势 Tab 卡片、明细弹窗），
 *   其中前两处共用同一份状态（`trendPeriod` / `trendDays`）却各写了一套 option 文案 ——
 *   概览是「按天」/「按小时」，趋势 Tab 是「按天统计」/「按小时统计」，用户看到的措辞不一致
 *   （用例库缺陷 `FE-BUG-ANALYTICS-DUP-TREND-CARD`，就是写 ANA-009 时发现的）。
 *   抽成一个组件 + 一份 option 常量后，这种"改一处忘另一处"不可能再发生。
 *
 * ⚠️ 本组件**完全受控**：概览与趋势两个 Tab 共用同一份状态，周期/天数在切换 Tab 后必须保持一致，
 *    所以不能把状态收进组件内部。
 */
import { Select, Space } from 'antd'
import { TREND_DAYS_OPTIONS, TREND_PERIOD_OPTIONS } from './constants'

export interface TrendControlsProps {
  period: 'hour' | 'day'
  days: number
  onPeriodChange: (value: 'hour' | 'day') => void
  onDaysChange: (value: number) => void
  /** 概览卡片是窄容器，用略小的宽度（文案统一后比原先的 90 稍宽一点） */
  compact?: boolean
}

export function TrendControls({
  period,
  days,
  onPeriodChange,
  onDaysChange,
  compact = false,
}: TrendControlsProps) {
  const width = compact ? 110 : 120
  return (
    <Space wrap size="small">
      <Select
        value={period}
        onChange={onPeriodChange}
        style={{ width }}
        options={TREND_PERIOD_OPTIONS}
      />
      {/* 天数只在「按天统计」下有意义（按小时统计本身就是当天分时） */}
      {period === 'day' && (
        <Select
          value={days}
          onChange={onDaysChange}
          style={{ width }}
          options={TREND_DAYS_OPTIONS}
        />
      )}
    </Space>
  )
}
