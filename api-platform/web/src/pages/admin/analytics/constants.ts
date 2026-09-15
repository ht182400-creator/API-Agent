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
