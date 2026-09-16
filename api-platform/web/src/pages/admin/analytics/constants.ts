/**
 * 管理员分析报表页 —— 常量映射表
 *
 * 由 `../Analytics.tsx` 提取（P1-4 巨型组件拆分，**纯搬运，零行为改变**）。
 * 提取理由：这两个映射与组件状态无关，是纯数据；抽走后可被页面内多个子组件
 * （概览卡片、明细表格、趋势弹窗）共用，也便于单测。
 */

/** 仓库状态 → antd Tag 颜色 */
export const statusColors: Record<string, string> = {
  online: 'green',
  pending: 'orange',
  approved: 'blue',
  rejected: 'red',
  offline: 'default',
}

/** 仓库状态 → 中文文案（未命中时由调用方回退为原始状态值） */
export const statusText: Record<string, string> = {
  online: '已上线',
  pending: '待审核',
  approved: '已审核',
  rejected: '已拒绝',
  offline: '已下线',
}

/**
 * 趋势「周期」/「天数」选择器的 option 常量（P1-4 拆分 B 轮新增）。
 *
 * ⚠️ 为什么要有这组常量：同一页原先**三处**各写了一份 options
 *    （概览卡片 / 趋势 Tab / 明细弹窗），而且前两处的周期文案并不一致 ——
 *    概览是「按天」/「按小时」，趋势 Tab 是「按天统计」/「按小时统计」。
 *    现统一为同一份数据源（取更明确的「按小时统计」/「按天统计」）。
 *    对应用例库缺陷条目：`FE-BUG-ANALYTICS-DUP-TREND-CARD`。
 */
export const TREND_PERIOD_OPTIONS: Array<{ label: string; value: 'hour' | 'day' }> = [
  { label: '按小时统计', value: 'hour' },
  { label: '按天统计', value: 'day' },
]

export const TREND_DAYS_OPTIONS: Array<{ label: string; value: number }> = [
  { label: '近7天', value: 7 },
  { label: '近30天', value: 30 },
  { label: '近90天', value: 90 },
]
