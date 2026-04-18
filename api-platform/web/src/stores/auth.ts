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
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
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
        // 设置日志用户ID
        logger.setUserId(user.id)
        logger.info('[Auth] User authenticated', { userId: user.id, userType: user.user_type })
      },
      
      setUser: (user) => {
        set({ user })
        logger.setUserId(user.id)
      },
      
      setTokens: (accessToken, refreshToken) => {
        set({ accessToken, refreshToken })
      },
      
      logout: () => {
        const currentUserId = useAuthStore.getState().user?.id
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
        })
        // 清除日志用户ID
        logger.clearUserId()
        logger.info('[Auth] User logged out', { userId: currentUserId })
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)
