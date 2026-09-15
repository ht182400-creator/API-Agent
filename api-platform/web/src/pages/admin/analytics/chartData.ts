/**
 * 管理员分析报表页 —— 图表数据整形（纯函数）
 *
 * 由 `../Analytics.tsx` 提取（P1-4 巨型组件拆分，**纯搬运，零行为改变**）。
 * 提取理由：这些是"接口数据 → recharts/Table 行数组"的纯转换，与组件状态无关；
 * 抽成独立函数后可单测（原实现内联在组件里，无法直接测）。
 */
import type { RepoTrendData, TrendData } from '../../../api/adminAnalytics'

/** 趋势图/趋势明细表的一行 */
export interface TrendRow {
  time: string
  calls: number
  revenue: number
}

/** 仓库趋势图的一行（比趋势多一个时延维度） */
export interface RepoTrendRow extends TrendRow {
  avgLatency: number
}

/**
 * 全局趋势数据 → 行数组（缺失值补 0，保持与 labels 等长对齐）。
 *
 * 对应原组件内 `getTrendChartData()`。
 */
export function buildTrendChartData(trendData: TrendData | null): TrendRow[] {
  if (!trendData) return []
  return trendData.labels.map((label, index) => ({
    time: label,
    calls: trendData.series.calls[index] || 0,
    revenue: trendData.series.revenue[index] || 0,
  }))
}

/**
 * 单仓库趋势数据 → 行数组（含平均时延；缺失值补 0）。
 *
 * 对应原组件内弹窗图表处的 `repoTrendData.labels.map(...)`；
 * 返回 null 时给空数组，便于直接作为图表 data 使用。
 */
export function buildRepoTrendChartData(repoTrendData: RepoTrendData | null): RepoTrendRow[] {
  if (!repoTrendData) return []
  return repoTrendData.labels.map((label, index) => ({
    time: label,
    calls: repoTrendData.series.calls[index] || 0,
    revenue: repoTrendData.series.revenue[index] || 0,
    avgLatency: repoTrendData.series.avg_latency[index] || 0,
  }))
}
