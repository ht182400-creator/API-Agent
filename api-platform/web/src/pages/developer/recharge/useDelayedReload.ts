/**
 * 结算成功后的"延迟刷新页面"（M3-c₁）。
 *
 * ## 改造前：同一段逻辑抄了 3 遍，而且每遍都有同一个毛病
 *
 * ```ts
 * setTimeout(() => {
 *   if (paymentStateRef.current.paySuccess) window.location.reload()
 * }, 5000)
 * ```
 *
 * 三个问题：
 *
 * ① **重复 3 份**（支付宝回调 / 扫码轮询成功 / 手动刷新确认成功），各处延迟还不一样；
 * ② **从不清理**：这是个"发射后不管"的定时器 —— 组件已卸载、甚至整页测试已结束它仍会触发。
 *    它正是"卸载后仍有副作用"这类噪声（含 `act` 警告与 jsdom teardown 报错）来源之一。
 * ③ 那个 `paySuccess` 守卫**现在是多余的**：调用点只出现在"**已确认结算成功之后**"，
 *    而终态不可逆（`succeeded` 不会再变回未支付）→ 守卫恒为真。
 *    它存在的唯一后果是逼着我们维护一份 `paymentStateRef` 状态快照 ——
 *    而"第二份真相"正是这次重构要消灭的东西。
 *
 * ## 现在
 *
 * 一个 hook：**重复调度只保留最后一次**、**卸载即取消**、并允许注入 `reload` 以便单测
 * （jsdom 里 `window.location.reload` 不可 mock）。
 */
import { useCallback, useEffect, useRef } from 'react'

/** 默认延迟：5 秒（与改造前一致，留给用户看清"支付成功"的提示） */
export const DEFAULT_RELOAD_DELAY_MS = 5000

/** 默认刷新实现（单测时注入假实现；jsdom 下真实的 location.reload 不可 mock） */
const defaultReload = () => window.location.reload()

export function useDelayedReload(
  reload: () => void = defaultReload,
  defaultDelayMs: number = DEFAULT_RELOAD_DELAY_MS
): (delayMs?: number) => void {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const reloadRef = useRef(reload)
  reloadRef.current = reload

  // 卸载即取消：不再有"页面/测试都结束了才导航"的悬空定时器
  useEffect(
    () => () => {
      if (timerRef.current) clearTimeout(timerRef.current)
      timerRef.current = null
    },
    []
  )

  return useCallback(
    (delayMs: number = defaultDelayMs) => {
      // 重复调度只保留最后一次（例如"手动刷新"与"轮询"同时确认成功，不应刷两次）
      if (timerRef.current) clearTimeout(timerRef.current)
      timerRef.current = setTimeout(() => {
        timerRef.current = null
        reloadRef.current()
      }, delayMs)
    },
    [defaultDelayMs]
  )
}
