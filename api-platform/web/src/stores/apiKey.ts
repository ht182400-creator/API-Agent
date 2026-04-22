/**
 * API Key 状态管理
 * 用于 API 测试工具的访问密钥配置
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface ApiKeyState {
  apiKey: string | null
  setApiKey: (key: string | null) => void
  clearApiKey: () => void
}

export const useApiKeyStore = create<ApiKeyState>()(
  persist(
    (set) => ({
      apiKey: null,
      
      setApiKey: (key) => {
        set({ apiKey: key || null })
      },
      
      clearApiKey: () => {
        set({ apiKey: null })
      },
    }),
    {
      name: 'api-key-storage',
    }
  )
)
