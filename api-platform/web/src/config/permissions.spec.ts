/**
 * 前端权限配置单元测试
 *
 * 为什么优先测它：
 *   权限判断是"越权防护"的前端第一道门（`hasPermission` / `hasRole` 决定菜单与路由可见性），
 *   且是纯函数 —— 可用单测把语义完全锁死，避免重构时被悄悄改坏。
 *
 * 覆盖：
 *   1. hasPermission：通配 '*'、单权限、多权限（**every** 语义）、空数组边界
 *   2. hasRole：等级比较、数组（**some** 语义）、非法角色（等级 0）
 *   3. 配置一致性：角色/用户类型映射、角色权限矩阵、路由表（路径唯一、userTypes 合法非空）
 *
 * 用例编号：TC-FE-PERM-001 ~ TC-FE-PERM-013
 */
import { describe, it, expect } from 'vitest'
import {
  Permission,
  RolePermissions,
  UserTypeDefaultRole,
  RoutePermissions,
  hasPermission,
  hasRole,
  type PermissionKey,
  type Role,
  type UserType,
} from './permissions'

const ALL_ROLES: Role[] = ['super_admin', 'admin', 'developer', 'user']
const ALL_USER_TYPES: UserType[] = ['super_admin', 'admin', 'owner', 'developer', 'user']

describe('hasPermission —— 权限判定', () => {
  it('TC-FE-PERM-001 通配权限 * 放行任何要求', () => {
    const perms: PermissionKey[] = ['*']
    expect(hasPermission(perms, Permission.SYSTEM_SETTINGS)).toBe(true)
    expect(hasPermission(perms, [Permission.USER_MANAGE, Permission.REPO_MANAGE])).toBe(true)
  })

  it('TC-FE-PERM-002 持有要求的权限 → true', () => {
    expect(hasPermission([Permission.DEV_API_KEYS], Permission.DEV_API_KEYS)).toBe(true)
  })

  it('TC-FE-PERM-003 未持有要求的权限 → false', () => {
    expect(hasPermission([Permission.DEV_QUOTA], Permission.DEV_API_KEYS)).toBe(false)
  })

  it('TC-FE-PERM-004 多个要求必须**全部**满足（every 语义）', () => {
    const perms: PermissionKey[] = [Permission.DEV_API_KEYS, Permission.DEV_QUOTA]
    expect(hasPermission(perms, [Permission.DEV_API_KEYS, Permission.DEV_QUOTA])).toBe(true)
    // 只满足其中一个 → 拒绝（多要求是"与"而非"或"）
    expect(hasPermission(perms, [Permission.DEV_API_KEYS, Permission.SYSTEM_LOGS])).toBe(false)
  })

  it('TC-FE-PERM-005 空权限列表一律拒绝（边界）', () => {
    expect(hasPermission([], Permission.DEV_QUOTA)).toBe(false)
    expect(hasPermission([], [Permission.DEV_QUOTA])).toBe(false)
  })

  it('TC-FE-PERM-006 空要求列表视为满足（every 空集语义，边界）', () => {
    // 说明：这是当前实现语义（`[].every(...) === true`）。
    //       若将来改为"空要求也拒绝"，必须同步更新本用例与调用方预期。
    expect(hasPermission([], [])).toBe(true)
  })

  it('TC-FE-PERM-007 角色默认权限矩阵关键断言', () => {
    // 超级管理员：通配
    expect(RolePermissions.super_admin).toEqual(['*'])

    // 管理员：拥有用户管理与审核权限，但不含充值/开发者私有权限
    expect(RolePermissions.admin).toContain(Permission.USER_MANAGE)
    expect(RolePermissions.admin).toContain(Permission.REPO_APPROVE)
    expect(RolePermissions.admin).not.toContain(Permission.BILLING_RECHARGE)
    expect(RolePermissions.admin).not.toContain(Permission.DEV_API_KEYS)

    // 开发者：可管理自己的 Key/配额/仓库，但不能审核仓库
    expect(RolePermissions.developer).toContain(Permission.DEV_API_KEYS)
    expect(RolePermissions.developer).toContain(Permission.OWNER_REPO)
    expect(RolePermissions.developer).not.toContain(Permission.REPO_APPROVE)

    // 普通用户：只读 + 充值相关，不含开发者私有权限
    expect(RolePermissions.user).toContain(Permission.REPO_READ)
    expect(RolePermissions.user).not.toContain(Permission.DEV_API_KEYS)

    // 每个角色的权限列表都非空
    ALL_ROLES.forEach((role) => {
      expect(RolePermissions[role].length).toBeGreaterThan(0)
    })
  })
})

describe('hasRole —— 角色等级判定', () => {
  it('TC-FE-PERM-008 高等级满足低等级要求', () => {
    expect(hasRole('admin', 'developer')).toBe(true)
    expect(hasRole('super_admin', 'admin')).toBe(true)
  })

  it('TC-FE-PERM-009 低等级不满足高等级要求', () => {
    expect(hasRole('developer', 'admin')).toBe(false)
    expect(hasRole('user', 'developer')).toBe(false)
  })

  it('TC-FE-PERM-010 同等级满足', () => {
    ALL_ROLES.forEach((role) => {
      expect(hasRole(role, role)).toBe(true)
    })
  })

  it('TC-FE-PERM-011 数组要求满足**任一**即可（some 语义）', () => {
    expect(hasRole('developer', ['admin', 'developer'])).toBe(true)
    expect(hasRole('user', ['admin', 'developer'])).toBe(false)
  })

  it('TC-FE-PERM-012 非法/未知角色按等级 0 处理 → 拒绝（异常输入）', () => {
    expect(hasRole('ghost' as Role, 'user')).toBe(false)
  })
})

describe('配置一致性', () => {
  it('TC-FE-PERM-013 用户类型→角色映射完备，且路由表结构合法', () => {
    // 1) 每个 user_type 都能映射到合法 role（owner 映射为 developer，是业务约定）
    ALL_USER_TYPES.forEach((userType) => {
      const role = UserTypeDefaultRole[userType]
      expect(ALL_ROLES).toContain(role)
    })
    expect(UserTypeDefaultRole.owner).toBe('developer')

    // 2) 路由表：路径唯一（重复会导致权限匹配歧义）
    const paths = RoutePermissions.map((r) => r.path)
    expect(new Set(paths).size).toBe(paths.length)

    // 3) 每个路由的 userTypes 非空且合法；requiredPermissions 若存在则非空
    RoutePermissions.forEach((route) => {
      expect(route.userTypes.length).toBeGreaterThan(0)
      route.userTypes.forEach((t) => expect(ALL_USER_TYPES).toContain(t))
      if (route.requiredPermissions) {
        expect(route.requiredPermissions.length).toBeGreaterThan(0)
      }
    })

    // 4) 关键路由存在性（防误删导致入口消失）
    const needed = ['/', '/developer/keys', '/owner/repos', '/admin/users', '/superadmin/roles']
    needed.forEach((p) => {
      expect(paths).toContain(p)
    })
  })
})
