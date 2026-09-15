/**
 * 图表数据整形纯函数单测（P1-4 拆分产物）
 *
 * 为什么要测：这两个函数原本内联在 994 行的 `Analytics.tsx` 里（无法单独测），
 * 拆分后成为页面渲染的关键路径 —— 若 `labels` 与 `series` 的对齐逻辑被改错，
 * 图表会静默画错（不报错、不白屏），只有单测能挡住。
 *
 * 用例编号：TC-FE-ANA-DATA-001 ~ TC-FE-ANA-DATA-005
 */
import { describe, it, expect } from 'vitest'
import { buildRepoTrendChartData, buildTrendChartData } from './chartData'
import type { RepoTrendData, TrendData } from '../../../api/adminAnalytics'

const trend = (over: Partial<TrendData> = {}): TrendData => ({
  labels: ['09-14', '09-15'],
  series: { calls: [10, 20], revenue: [1.5, 2.5] },
  period: 'day',
  days: 7,
  repo_id: null,
  generated_at: '2026-09-15T00:00:00Z',
  ...over,
})

const repoTrend = (over: Partial<RepoTrendData> = {}): RepoTrendData => ({
  repo_id: 'r1',
  repo_name: '天气服务',
  labels: ['09-14', '09-15'],
  series: { calls: [3, 4], revenue: [0.3, 0.4], avg_latency: [120, 150] },
  days: 7,
  generated_at: '2026-09-15T00:00:00Z',
  ...over,
})

describe('buildTrendChartData', () => {
  it('TC-FE-ANA-DATA-001: 输入为 null 时返回空数组（图表不崩）', () => {
    expect(buildTrendChartData(null)).toEqual([])
  })

  it('TC-FE-ANA-DATA-002: 按 labels 逐项对齐 calls / revenue', () => {
    expect(buildTrendChartData(trend())).toEqual([
      { time: '09-14', calls: 10, revenue: 1.5 },
      { time: '09-15', calls: 20, revenue: 2.5 },
    ])
  })

  it('TC-FE-ANA-DATA-003: series 比 labels 短时缺失项补 0（保持等长）', () => {
    const rows = buildTrendChartData(
      trend({ labels: ['a', 'b', 'c'], series: { calls: [1], revenue: [] } })
    )
    expect(rows).toHaveLength(3)
    expect(rows).toEqual([
      { time: 'a', calls: 1, revenue: 0 },
      { time: 'b', calls: 0, revenue: 0 },
      { time: 'c', calls: 0, revenue: 0 },
    ])
  })
})

describe('buildRepoTrendChartData', () => {
  it('TC-FE-ANA-DATA-004: 输入为 null 时返回空数组', () => {
    expect(buildRepoTrendChartData(null)).toEqual([])
  })

  it('TC-FE-ANA-DATA-005: 带出 avgLatency（缺失补 0）', () => {
    expect(buildRepoTrendChartData(repoTrend())).toEqual([
      { time: '09-14', calls: 3, revenue: 0.3, avgLatency: 120 },
      { time: '09-15', calls: 4, revenue: 0.4, avgLatency: 150 },
    ])

    const rows = buildRepoTrendChartData(
      repoTrend({
        labels: ['a', 'b'],
        series: { calls: [1, 2], revenue: [0, 0], avg_latency: [9] },
      })
    )
    expect(rows[0].avgLatency).toBe(9)
    expect(rows[1].avgLatency).toBe(0)
  })
})
