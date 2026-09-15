/**
 * 仓库状态 → antd Tag 颜色 / 中文文案（全站唯一来源）
 *
 * ⚠️ **admin 与 owner 两个变体是有意区分的**，不要"顺手统一"成一个：
 *   - `admin` 视角：approved = 「已审核」（管理员关心"审没审过"）；
 *   - `owner` 视角：approved = 「已审核（待上线）」（提醒所有者"还差你上线"）。
 * 实测踩点：三处重复的 statusMap 中 owner 侧文案与 admin 侧不同，属于**业务语义**差异。
 *
 * 本文件只导出纯数据与纯函数（不含 JSX）—— 各调用点保留自己的渲染方式
 * （Tag / fallback 逻辑），只把 map 引用收敛到这里。
 */
export type RepoStatusVariant = 'admin' | 'owner'

export type RepoStatusConfig = { color: string; text: string }

export const REPO_STATUS_MAPS: Record<RepoStatusVariant, Record<string, RepoStatusConfig>> = {
  admin: {
    pending: { color: 'orange', text: '待审核' },
    approved: { color: 'blue', text: '已审核' },
    rejected: { color: 'red', text: '已拒绝' },
    online: { color: 'green', text: '已上线' },
    offline: { color: 'default', text: '已下线' },
  },
  owner: {
    pending: { color: 'orange', text: '待审核' },
    approved: { color: 'blue', text: '已审核（待上线）' },
    rejected: { color: 'red', text: '已拒绝' },
    online: { color: 'green', text: '已上线' },
    offline: { color: 'default', text: '已下线' },
  },
}

/**
 * 取状态对应的颜色与文案；未命中时回退为「默认灰 + 原始状态值」。
 * 需要自定义 fallback 文案（如 owner/Dashboard 的 `status || '未知'`）的调用方，
 * 先自行兜底再传入。
 */
export function repoStatusConfig(status: string, variant: RepoStatusVariant): RepoStatusConfig {
  const map = REPO_STATUS_MAPS[variant]
  return map[status] || { color: 'default', text: status }
}
