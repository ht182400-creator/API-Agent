/**
 * 主布局（Layout.tsx）测试 —— 菜单可见性
 *
 * 为什么优先测它（P0）：
 *   Layout 决定「用户能看到哪些菜单入口」，这是**越权可见性**的展示层防线。
 *   菜单配错既不会报错也不会白屏 —— 只会让无权用户看到不该有的入口（或反之），
 *   靠人工点很难覆盖全部角色组合。其核心 `getMenuItems(userType)` 是纯函数，最适合单测。
 *
 * ✅ 相关死代码已清理（用例库 FE-BUG-LAYOUT-DEAD-MENU）：`developerWithoutReposMenu`
 *   （已无引用）与 `getMenuItems` 的 `userHasRepos` 参数（不再影响任何分支）均已移除，
 *   连带删除只为该参数服务的 `hasRepos` 状态与 `/user/has-repos` 请求（少一次无谓请求）。
 *
 * 用例编号：TC-FE-LAYOUT-001 ~ TC-FE-LAYOUT-006
 * （组件级渲染/登出用例见用例库 planned：TC-FE-LAYOUT-007~008）
 */
import { describe, it, expect, vi } from 'vitest'

vi.mock('../../api/auth', () => ({
  authApi: { logout: vi.fn(), me: vi.fn() },
}))
vi.mock('../../api/notification', () => ({
  notificationApi: {
    getUnreadCount: vi.fn().mockResolvedValue(0),
    getList: vi.fn().mockResolvedValue({ items: [] }),
  },
}))

import { getMenuItems } from './Layout'

/**
 * 把 antd 菜单树拍平成 key 列表。
 * 说明：菜单是嵌套结构（含 `type: 'divider'` 这类无 key 项），断言"有哪些入口"前必须先拍平。
 */
function flatKeys(items: unknown): string[] {
  const out: string[] = []
  const walk = (list: unknown): void => {
    if (!Array.isArray(list)) return
    list.forEach((item) => {
      if (!item || typeof item !== 'object') return
      const node = item as { key?: unknown; children?: unknown }
      if (typeof node.key === 'string') out.push(node.key)
      if (node.children) walk(node.children)
    })
  }
  walk(items)
  return out
}

describe('getMenuItems（用户类型 → 菜单可见性）', () => {
  it('TC-FE-LAYOUT-001: super_admin 只看到超级管理入口', () => {
    const keys = flatKeys(getMenuItems('super_admin'))

    expect(keys).toContain('/superadmin')
    expect(keys).toContain('/superadmin/audit')
    // 不得出现 admin / developer / owner 的入口
    expect(keys.filter((k) => k.startsWith('/admin'))).toEqual([])
    expect(keys.filter((k) => k.startsWith('/developer'))).toEqual([])
    expect(keys).not.toContain('/owner/repos')
  })

  it('TC-FE-LAYOUT-002: admin 含财务对账与计费配置子菜单，且无超管入口', () => {
    const keys = flatKeys(getMenuItems('admin'))

    expect(keys).toContain('/admin/reconciliation')
    expect(keys).toContain('/admin/recharge-records')
    expect(keys).toContain('/admin/pricing-config')
    expect(keys).toContain('/admin/monthly-bills')
    // 越权可见性：管理员不应看到超级管理员专属入口
    expect(keys.filter((k) => k.startsWith('/superadmin'))).toEqual([])
  })

  it('TC-FE-LAYOUT-003: developer 含仓库市场与仓库管理，且无 admin/superadmin 入口', () => {
    const keys = flatKeys(getMenuItems('developer'))

    expect(keys).toContain('/developer/repos') // 仓库市场（可预览所有仓库）
    expect(keys).toContain('/owner/repos') // 仓库管理（仅自己的）
    expect(keys).toContain('/developer/keys')
    expect(keys.filter((k) => k.startsWith('/admin'))).toEqual([])
    expect(keys.filter((k) => k.startsWith('/superadmin'))).toEqual([])
  })

  it('TC-FE-LAYOUT-004: 普通用户只能看到 /user/*，且绝不出现 API Keys 入口', () => {
    const keys = flatKeys(getMenuItems('user'))

    expect(keys).toContain('/user/repos')
    expect(keys.length).toBeGreaterThan(0)
    // 全部入口都在 /user 命名空间下（普通用户只读，不能建 Key / 调 API）
    expect(keys.every((k) => k.startsWith('/user'))).toBe(true)
    expect(keys).not.toContain('/developer/keys')
  })

  it('TC-FE-LAYOUT-005: owner 含 owner 专属的数据分析与收益结算', () => {
    const keys = flatKeys(getMenuItems('owner'))

    expect(keys).toContain('/owner/analytics')
    expect(keys).toContain('/owner/settlement')
    expect(keys).toContain('/owner/repos')
  })

  it('TC-FE-LAYOUT-006: 未知 userType 兜底为普通用户菜单（不泄露任何管理入口）', () => {
    const keys = flatKeys(getMenuItems('ghost-type'))

    expect(keys.every((k) => k.startsWith('/user'))).toBe(true)
    expect(keys).not.toContain('/admin')
    expect(keys).not.toContain('/developer/keys')
    // 缺省参数路径同样安全
    expect(flatKeys(getMenuItems(''))).toEqual(keys)
  })
})
