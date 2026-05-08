/**
 * 认证状态管理
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { User } from '../api/auth'
import { logger } from '../utils/logger'

interface AuthState {
  user: User | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  
  // Actions
  setAuth: (user: User, accessToken: string, refreshToken: string) => void
  setUser: (user: User) => void
  setTokens: (accessToken: string, refreshToken: string) => void
  logout: () => void
  
  // 【V6.0 新增】强制刷新用户状态，确保 localStorage 同步
  forceRefreshUser: () => Promise<User>
}

// 获取 persist 中间件的 storage 对象引用
const getPersistedStorage = () => {
  // 直接操作 localStorage，确保同步更新
  const storage = localStorage.getItem('auth-storage')
  return storage ? JSON.parse(storage) : null
}

// 【V6.0 新增】同步更新 localStorage
const syncToLocalStorage = (state: Partial<AuthState>) => {
  try {
    const currentStorage = getPersistedStorage()
    if (currentStorage) {
      const newState = {
        ...currentStorage.state,
        ...state,
      }
      localStorage.setItem('auth-storage', JSON.stringify({
        ...currentStorage,
        state: newState,
      }))
    }
  } catch (error) {
    console.error('[Auth] 同步 localStorage 失败:', error)
  }
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      
      setAuth: (user, accessToken, refreshToken) => {
        set({
          user,
          accessToken,
          refreshToken,
          isAuthenticated: true,
        })
        // 【V6.0 新增】同步更新 localStorage
        syncToLocalStorage({ user, accessToken, refreshToken, isAuthenticated: true })
        // 设置日志用户ID
        logger.setUserId(user.id)
        logger.info('[Auth] User authenticated', { userId: user.id, userType: user.user_type })
      },
      
      setUser: (user) => {
        set({ user })
        // 【V6.0 新增】同步更新 localStorage，确保用户类型变化能立即持久化
        syncToLocalStorage({ user })
        logger.setUserId(user.id)
        console.log('[Auth] setUser 更新:', { userId: user.id, userType: user.user_type })
      },
      
      setTokens: (accessToken, refreshToken) => {
        set({ accessToken, refreshToken })
        // 【V6.0 新增】同步更新 localStorage
        syncToLocalStorage({ accessToken, refreshToken })
      },
      
      logout: () => {
        const currentUserId = useAuthStore.getState().user?.id
        
        // 清除所有敏感数据
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
        })
        
        // 清除日志用户ID
        logger.clearUserId()
        
        // 清除 localStorage 中的认证数据
        try {
          localStorage.removeItem('auth-storage')
        } catch (e) {
          // 忽略错误
        }
        
        logger.info('[Auth] User logged out', { userId: currentUserId })
      },
      
      // 【V6.0 新增】强制刷新用户状态，确保从后端获取最新数据并同步到 localStorage
      forceRefreshUser: async () => {
        const { accessToken } = get()
        if (!accessToken) {
          throw new Error('未登录')
        }
        
        // 从后端获取最新用户信息
        const response = await fetch('/api/v1/auth/me', {
          headers: {
            'Authorization': `Bearer ${accessToken}`,
          },
        })
        
        if (!response.ok) {
          throw new Error('获取用户信息失败')
        }
        
        const result = await response.json()
        
        // 【V6.0 修复】后端返回的是 BaseResponse 格式，数据在 data 字段中
        const user = result.data
        
        if (!user || !user.user_type) {
          console.error('[Auth] forceRefreshUser 返回数据异常:', result)
          throw new Error('用户数据异常')
        }
        
        // 更新状态（会自动同步到 localStorage）
        set({ user })
        syncToLocalStorage({ user })
        
        console.log('[Auth] forceRefreshUser 更新:', { userId: user.id, userType: user.user_type })
        return user
      },
    }),
    {
      name: 'auth-storage',
      // 注意：这里只持久化必要的认证状态，不存储密码
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)
