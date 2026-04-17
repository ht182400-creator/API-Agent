/**
 * 应用状态管理
 */

import { create } from 'zustand'

interface AppState {
  // 侧边栏折叠状态
  collapsed: boolean
  setCollapsed: (collapsed: boolean) => void
  toggleCollapsed: () => void
  
  // 加载状态
  loading: boolean
  setLoading: (loading: boolean) => void
  
  // 消息提示
  message: {
    type: 'success' | 'error' | 'warning' | 'info'
    content: string
  } | null
  showMessage: (type: 'success' | 'error' | 'warning' | 'info', content: string) => void
  clearMessage: () => void
}

export const useAppStore = create<AppState>((set) => ({
  collapsed: false,
  setCollapsed: (collapsed) => set({ collapsed }),
  toggleCollapsed: () => set((state) => ({ collapsed: !state.collapsed })),
  
  loading: false,
  setLoading: (loading) => set({ loading }),
  
  message: null,
  showMessage: (type, content) => set({ message: { type, content } }),
  clearMessage: () => set({ message: null }),
}))
