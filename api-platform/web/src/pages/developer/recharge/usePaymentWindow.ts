/**
 * 支付窗口管理（M4 余项：从 Recharge.tsx 抽出，纯搬运零行为改变）。
 *
 * 职责：**只管窗口的机械操作** —— 打开并监视关闭、主动关闭、停监视；
 * "检测到窗口关闭之后做什么"（如自动刷新支付状态）由页面通过 `onWindowClosed` 注入。
 *
 * ⚠️ 2026-09-17 语义修正（随迁移一并固化）：`close()` **不再调用 `window.close()` 自关当前窗口**
 *    （原缺陷 FE-BUG-CLOSE-PAY-WINDOW-CLOSE-SELF —— 关窗是支付返回页自己的职责）。
 * ⚠️ 卸载时**只停监视、不主动关窗**：用户可能还在支付页里操作。
 */
import { useCallback, useEffect, useRef } from 'react'

/** 打开支付窗口的特征参数（与改造前逐字一致） */
const WINDOW_FEATURES = 'width=900,height=700,scrollbars=yes'

export interface UsePaymentWindowOptions {
  /** 支付窗口被用户关闭时的回调（如自动刷新支付状态，不弹错误提示） */
  onWindowClosed: () => void
}

export function usePaymentWindow({ onWindowClosed }: UsePaymentWindowOptions) {
  const payWindowRef = useRef<Window | null>(null)
  const watchIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  // 回调用 ref 取最新：监视 interval 是长命闭包，页面每次渲染都可能是新函数
  const onWindowClosedRef = useRef(onWindowClosed)
  onWindowClosedRef.current = onWindowClosed

  /** 停止「监视窗口关闭」的轮询（不关窗） */
  const stopWatching = useCallback(() => {
    if (watchIntervalRef.current) {
      clearInterval(watchIntervalRef.current)
      watchIntervalRef.current = null
    }
  }, [])

  /** 关闭支付窗口（如有）：停监视 → 关窗 → 清引用。**不自关当前窗口**（见文件头） */
  const close = useCallback(() => {
    stopWatching()
    const win = payWindowRef.current
    if (win) {
      if (!win.closed) {
        try {
          win.close()
        } catch {
          // 跨域时可能失败，忽略
        }
      }
      payWindowRef.current = null
    }
  }, [stopWatching])

  /** 在新窗口打开支付页并开始监视其关闭；返回 false = 打开失败（被拦截） */
  const openAndWatch = useCallback(
    (url: string): boolean => {
      const win = window.open(url, '_blank', WINDOW_FEATURES)
      if (!win) return false
      payWindowRef.current = win
      stopWatching()
      watchIntervalRef.current = setInterval(() => {
        if (win.closed) {
          stopWatching()
          onWindowClosedRef.current()
        }
      }, 1000)
      return true
    },
    [stopWatching]
  )

  // 卸载：停监视（不主动关窗 —— 用户可能还在支付页里）
  useEffect(() => () => stopWatching(), [stopWatching])

  return { openAndWatch, close, stopWatching }
}
