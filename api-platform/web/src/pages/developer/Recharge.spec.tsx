/**
 * 充值中心（developer/Recharge.tsx，2001 行 —— 全前端最大文件）测试
 *
 * 为什么是资金链路里必须锁死的一页：
 *   1. **到账金额计算**（`price + bonus_amount + price * bonus_ratio / 100`）——
 *      两种赠送方式（固定金额 / 比例）走的是**同一条式子**，算错就是真金白银；
 *      而页面上"支付金额"与"实际到账"两行都渲染出来，肉眼很容易只看前者。
 *   2. **自定义金额的上下限校验** —— 超界必须**拦在请求之前**（不是发出去等后端拒）。
 *   3. **套餐与自定义互斥** —— 两者同时生效会导致"用套餐价买自定义金额"这类错单。
 *
 * 实现要点（决定测试手法）：
 *   - 初始化是 `Promise.all([fetchPackages, fetchConfig, fetchBalance])`；
 *   - `fetchPackages` 会**过滤掉 `is_active !== true`** 的套餐；
 *   - loading 期间整页只渲染 `<Spin>`，所以断言前必须先 `findByText` 等到列表出现；
 *   - 下单成功后会启动轮询 / 写 sessionStorage，因此测试间需清理 sessionStorage。
 *
 * 用例编号：TC-FE-RECHARGE-001 ~ TC-FE-RECHARGE-008
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { screen, waitFor, fireEvent, act } from '@testing-library/react'

const mocks = vi.hoisted(() => ({
  showError: vi.fn(),
}))

vi.mock('../../api/payment', () => ({
  paymentApi: {
    getPackages: vi.fn(),
    getConfig: vi.fn(),
    getPaymentStatus: vi.fn(),
    createPayment: vi.fn(),
    createCustomRecharge: vi.fn(),
    refreshQrCode: vi.fn(),
    cancelPayment: vi.fn(),
    mockPaymentCallback: vi.fn(),
    clientLog: vi.fn().mockResolvedValue(undefined),
  },
}))

vi.mock('../../api/billing', () => ({
  billingApi: { getAccount: vi.fn() },
}))

vi.mock('../../api/auth', () => ({ authApi: {} }))

vi.mock('../../components/ErrorModal', () => ({
  useErrorModal: () => ({
    showError: mocks.showError,
    closeError: vi.fn(),
    ErrorModal: () => null,
  }),
}))

import DeveloperRecharge from './Recharge'
import { paymentApi } from '../../api/payment'
import { billingApi } from '../../api/billing'
import { useAuthStore } from '../../stores/auth'
import { renderWithProviders } from '../../test/renderWithProviders'

/**
 * 套餐数据刻意覆盖三种赠送形态：
 *   入门包 —— 无赠送（bonus_amount=0 且 bonus_ratio=0）
 *   超值包 —— **固定金额**赠送 +20
 *   比例包 —— **比例**赠送 10%
 *   下架包 —— is_active=false，必须被过滤掉
 */
const packageList = [
  {
    id: 'p1',
    name: '入门包',
    price: 10,
    bonus_amount: 0,
    bonus_ratio: 0,
    is_active: true,
    is_featured: false,
    description: '体验用',
  },
  {
    id: 'p2',
    name: '超值包',
    price: 100,
    bonus_amount: 20,
    bonus_ratio: 0,
    is_active: true,
    is_featured: true,
    description: '送 20 元',
  },
  {
    id: 'p4',
    name: '比例包',
    price: 100,
    bonus_amount: 0,
    bonus_ratio: 10,
    is_active: true,
    is_featured: false,
    description: '送 10%',
  },
  {
    id: 'p3',
    name: '已下架包',
    price: 999,
    bonus_amount: 0,
    bonus_ratio: 0,
    is_active: false,
    is_featured: false,
  },
]

/**
 * 点击「立即充值」下单按钮。
 *
 * ⚠️ 两个坑（都实测踩过）：
 *   1. **必须等按钮 enabled**：选中套餐 / 填自定义金额都是 React 状态更新（异步批处理），
 *      `fireEvent` 之后同步取按钮会拿到旧的 `disabled` DOM，点击被忽略 → API 调用数为 0。
 *   2. **点击前必须重新查询元素**：`waitFor` 期间组件可能已重新渲染（antd Button 会换节点），
 *      拿着旧引用去 `fireEvent.click` 同样无效 —— 表现为「按钮明明已启用，但点了没反应」。
 */
async function clickRechargeButton(): Promise<void> {
  const pick = () =>
    screen
      .getAllByRole('button', { name: /立即充值/ })
      .filter((b) => !(b as HTMLButtonElement).disabled)

  await waitFor(() => expect(pick().length).toBeGreaterThan(0))
  // ⚠️ 用**原生 DOM click()** 而非 fireEvent.click：本页在 render 中反复重建按钮节点
  //    （loading / 条件渲染），fireEvent 点到的引用可能已脱离 DOM → React 事件委托收不到
  //    → onClick 不执行（表现为「按钮已启用，但 API 调用数 0」）。实测踩过。
  //    同时遍历所有可用按钮，兼容桌面/移动两套结构。
  for (const btn of pick()) (btn as HTMLButtonElement).click()
}

/** 在自定义金额输入框填值（antd InputNumber 受控，需 blur 才提交） */
async function fillCustomAmount(value: string): Promise<void> {
  const input = await screen.findByPlaceholderText('10 - 1000')
  fireEvent.change(input, { target: { value } })
  fireEvent.blur(input)
}

beforeEach(() => {
  sessionStorage.clear()
  // ⚠️ 必须在这里**重新**给 clientLog 装上实现：vitest 的 mock 重置策略会清掉
  //    在 `vi.mock` 工厂里写的 `mockResolvedValue`。而 Recharge 的 `paymentLogger` 是
  //    `paymentApi.clientLog(...).catch(...)` —— 一旦返回 undefined，
  //    会抛 `TypeError: Cannot read properties of undefined (reading 'catch')`，
  //    **把整个下单流程打断在后端请求之前**（表现为"点了按钮但 API 调用数 0"，实测踩过）。
  vi.mocked(paymentApi.clientLog).mockResolvedValue(undefined as never)
  vi.mocked(paymentApi.getPackages).mockResolvedValue(packageList as never)
  vi.mocked(paymentApi.getConfig).mockResolvedValue({
    min_amount: 10,
    max_amount: 1000,
    default_bonus_ratio: 0.05,
  } as never)
  vi.mocked(billingApi.getAccount).mockResolvedValue({ balance: 88.5 } as never)
  vi.mocked(paymentApi.getPaymentStatus).mockResolvedValue({
    status: 'pending',
    payment_no: 'PAY1',
    created_at: new Date().toISOString(),
    expires_in: 600,
  } as never)
  vi.mocked(paymentApi.createPayment).mockResolvedValue({
    payment_no: 'PAY-NEW',
    order_no: 'ORD-NEW',
    amount: 10,
    status: 'pending',
    expires_in: 600,
  } as never)
  vi.mocked(paymentApi.createCustomRecharge).mockResolvedValue({
    payment_no: 'PAY-CUSTOM',
    order_no: 'ORD-CUSTOM',
    amount: 200,
    status: 'pending',
    expires_in: 600,
  } as never)

  useAuthStore.setState({
    user: {
      id: 'u1',
      email: 'dev@example.com',
      user_type: 'developer',
      role: 'developer',
      permissions: [],
      user_status: 'active',
      email_verified: true,
      vip_level: 0,
      created_at: '2026-01-01T00:00:00Z',
    },
    accessToken: 'tok',
    refreshToken: 'rt',
    isAuthenticated: true,
  })
})

afterEach(() => {
  sessionStorage.clear()
  vi.unstubAllGlobals()
})

/** stub /health（useEnvInfo 用原生 fetch，不走 axios） */
function stubHealth(billingEnv: string, isProduction: boolean) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        environment: 'development',
        billing_environment: billingEnv,
        is_production: isProduction,
      }),
    })
  )
}

describe('环境与支付通道标签', () => {
  it('TC-FE-RECHARGE-017: 测试环境显示「测试支付通道」，不得出现「真实支付通道」', async () => {
    stubHealth('simulation', false)
    renderWithProviders(<DeveloperRecharge />, { route: '/developer/recharge' })
    await screen.findByText('入门包')

    // 与顶栏「测试环境 · SIMULATION」一致（用户实测：原标签读 mock_mode 显示「真实支付通道」）
    // ⚠️ Tag 文本带 emoji 前缀（🧪）→ 用正则部分匹配
    expect(await screen.findByText(/测试支付通道/)).toBeInTheDocument()
    expect(screen.queryByText(/真实支付通道/)).not.toBeInTheDocument()
  })

  it('TC-FE-RECHARGE-018: 生产环境显示「真实支付通道」', async () => {
    stubHealth('production', true)
    renderWithProviders(<DeveloperRecharge />, { route: '/developer/recharge' })
    await screen.findByText('入门包')

    expect(await screen.findByText(/真实支付通道/)).toBeInTheDocument()
    expect(screen.queryByText(/测试支付通道/)).not.toBeInTheDocument()
  })
})

describe('初始化', () => {
  it('TC-FE-RECHARGE-001: 并行加载套餐/配置/余额，并过滤掉未启用的套餐', async () => {
    renderWithProviders(<DeveloperRecharge />, { route: '/developer/recharge' })

    await waitFor(() => expect(paymentApi.getPackages).toHaveBeenCalled())
    expect(paymentApi.getConfig).toHaveBeenCalled()
    expect(billingApi.getAccount).toHaveBeenCalled()

    // 启用的套餐渲染出来
    expect(await screen.findByText('入门包')).toBeInTheDocument()
    expect(screen.getByText('超值包')).toBeInTheDocument()
    // ⚠️ is_active=false 的套餐不得出现（会被 fetchPackages 过滤）
    expect(screen.queryByText('已下架包')).not.toBeInTheDocument()
  })

  it('TC-FE-RECHARGE-006: 套餐与自定义金额互斥（选一即取消另一）', async () => {
    renderWithProviders(<DeveloperRecharge />, { route: '/developer/recharge' })
    await screen.findByText('入门包')

    // 先选套餐 → 摘要区「充值方式」显示套餐名
    fireEvent.click(screen.getByText('入门包'))
    await waitFor(() => expect(screen.getByText('充值方式')).toBeInTheDocument())
    // ⚠️ ¥10.00 在「套餐卡价格」「摘要-支付金额」「下单按钮」三处都会出现 → 不能用 getByText
    expect(screen.getAllByText('¥10.00').length).toBeGreaterThan(0)

    // 切到自定义金额 → 摘要区不再显示该套餐名
    fireEvent.click(screen.getByText('自定义金额'))
    await waitFor(() => expect(screen.queryByText('支付金额')).not.toBeInTheDocument())
    expect(screen.getByText('充值金额')).toBeInTheDocument()
  })
})

describe('到账金额计算', () => {
  it('TC-FE-RECHARGE-002: 套餐到账 = 价格 + 固定赠送 + 价格×比例', async () => {
    renderWithProviders(<DeveloperRecharge />, { route: '/developer/recharge' })
    await screen.findByText('超值包')

    // 固定金额赠送：100 + 20 = 120.00
    fireEvent.click(screen.getByText('超值包'))
    expect((await screen.findAllByText('¥120.00')).length).toBeGreaterThan(0)

    // 比例赠送：100 + 100×10% = 110.00
    fireEvent.click(screen.getByText('比例包'))
    expect((await screen.findAllByText('¥110.00')).length).toBeGreaterThan(0)
  })

  it('TC-FE-RECHARGE-008: 自定义金额到账 = 金额 ×(1 + 默认比例)', async () => {
    renderWithProviders(<DeveloperRecharge />, { route: '/developer/recharge' })
    await screen.findByText('入门包')

    fireEvent.click(screen.getByText('自定义金额'))
    const input = await screen.findByPlaceholderText('10 - 1000')
    fireEvent.change(input, { target: { value: '200' } })

    // default_bonus_ratio = 0.05 → 200 × 1.05 = 210.00
    await waitFor(() => expect(screen.getByText('¥210.00')).toBeInTheDocument())
  })
})

describe('下单', () => {
  it('TC-FE-RECHARGE-003: 选中套餐后下单，参数含 package_id/payment_method/payment_type', async () => {
    renderWithProviders(<DeveloperRecharge />, { route: '/developer/recharge' })
    await screen.findByText('入门包')

    fireEvent.click(screen.getByText('入门包'))
    await clickRechargeButton()

    // 不应走错误分支（若走错，说明下单在请求后端之前就抛错了）
    expect(mocks.showError).not.toHaveBeenCalled()
    await waitFor(() =>
      expect(paymentApi.createPayment).toHaveBeenCalledWith({
        package_id: 'p1',
        payment_method: 'alipay', // 默认值
        payment_type: 'qrcode', // 默认值：扫码
      })
    )
  })

  it('TC-FE-RECHARGE-004: 自定义金额输入框按后端配置限制上下限（UI 层先拦一道）', async () => {
    renderWithProviders(<DeveloperRecharge />, { route: '/developer/recharge' })
    await screen.findByText('入门包')

    fireEvent.click(screen.getByText('自定义金额'))
    const input = await screen.findByPlaceholderText('10 - 1000')

    // ⚠️ 上下限来自 rechargeConfig（mock 为 10 / 1000）→ 输入框本身即拒绝越界值，
    //    所以"越界不请求"是 UI 层的功劳，业务层校验（handleCreateOrder 里的比较）
    //    实际只在"值绕过 InputNumber 被设入"时才会走到。
    expect(input).toHaveAttribute('aria-valuemin', '10')
    expect(input).toHaveAttribute('aria-valuemax', '1000')
  })

  it('TC-FE-RECHARGE-005: 自定义金额下单成功 —— createCustomRecharge 带金额与支付参数', async () => {
    renderWithProviders(<DeveloperRecharge />, { route: '/developer/recharge' })
    await screen.findByText('入门包')

    fireEvent.click(screen.getByText('自定义金额'))
    await fillCustomAmount('200') // 落在 [10, 1000] 内

    await clickRechargeButton()

    await waitFor(() =>
      expect(paymentApi.createCustomRecharge).toHaveBeenCalledWith({
        amount: 200,
        payment_method: 'alipay', // 默认值
        payment_type: 'qrcode', // 默认扫码
      })
    )
  })

  it('TC-FE-RECHARGE-007: 下单失败不白屏（页面骨架保留，用户可重试）', async () => {
    vi.mocked(paymentApi.createPayment).mockRejectedValue(new Error('网关超时'))

    renderWithProviders(<DeveloperRecharge />, { route: '/developer/recharge' })
    await screen.findByText('入门包')

    fireEvent.click(screen.getByText('入门包'))
    await clickRechargeButton()

    await waitFor(() => expect(paymentApi.createPayment).toHaveBeenCalled())
    // ⚠️ 提示走哪条分支取决于 `isPaymentError`：支付类错误进"支付异常"弹窗（setPayError），
    //    仅非支付类才走 showError —— 故此处不锁具体提示，只锁"没白屏、仍可重试"。
    expect(screen.getAllByText('入门包').length).toBeGreaterThan(0)
    expect(screen.getByRole('button', { name: /立即充值/ })).toBeInTheDocument()
  })

  it('TC-FE-RECHARGE-009: 日志上报异常不得拦截下单（回归防线）', async () => {
    // 模拟日志服务不可用：同步抛错 + 返回非 Promise 两种坏形态都要能扛住
    vi.mocked(paymentApi.clientLog).mockImplementation(() => {
      throw new Error('日志服务不可用')
    })

    renderWithProviders(<DeveloperRecharge />, { route: '/developer/recharge' })
    await screen.findByText('入门包')

    fireEvent.click(screen.getByText('入门包'))
    await clickRechargeButton()

    // ⚠️ 关键：日志崩了也必须把订单创建出去。
    //    修复前 paymentLogger 里是 `clientLog(...).catch(...)`，一旦 clientLog 抛错/返回非 Promise，
    //    异常会被 handleCreateOrder 的 try/catch 吞掉 → 后端请求根本没发出，
    //    用户只看到"点了没反应"（详见该文件顶部 sendPaymentLog 的注释）。
    await waitFor(() => expect(paymentApi.createPayment).toHaveBeenCalled())
    expect(mocks.showError).not.toHaveBeenCalled()
  })

  /**
   * ⚠️ 这条覆盖 **原缺陷的真实触发形态**，与 TC-FE-RECHARGE-009 互补、缺一不可：
   *
   *   - 009：clientLog **同步抛错**   → 源码的 `try/catch` 能兜住；
   *   - 本条：clientLog **返回 undefined**（非 Promise）→ 源码的 `.catch(...)` 直接抛
   *     `TypeError: Cannot read properties of undefined (reading 'catch')`，
   *     这才是当初"点充值完全没反应"的真正原因。
   *
   * （差异由变异检验暴露：只保留 009 时，去掉 `Promise.resolve` 包壳后用例仍然通过。）
   */
  it('TC-FE-RECHARGE-016: 日志接口返回非 Promise（undefined）时也不得中断下单', async () => {
    vi.mocked(paymentApi.clientLog).mockReturnValue(undefined as never)

    renderWithProviders(<DeveloperRecharge />, { route: '/developer/recharge' })
    await screen.findByText('入门包')

    fireEvent.click(screen.getByText('入门包'))
    await clickRechargeButton()

    await waitFor(() => expect(paymentApi.createPayment).toHaveBeenCalled())
    expect(mocks.showError).not.toHaveBeenCalled()
  })
})

/**
 * 「不丢单」链路 —— 用户跳到支付宝 / 刷新页面回来后仍能确认结果。
 * 这三条是后续拆分支付流程 hook 的安全网。
 */
describe('待支付订单暂存（不丢单）', () => {
  const KEY = 'pending_payment'

  const statusOk = {
    status: 'pending',
    payment_no: 'PAY-OLD',
    created_at: new Date().toISOString(),
    expires_in: 600,
  }

  it('TC-FE-RECHARGE-010: 下单成功后写入 sessionStorage（含单号与金额）', async () => {
    renderWithProviders(<DeveloperRecharge />, { route: '/developer/recharge' })
    await screen.findByText('入门包')

    fireEvent.click(screen.getByText('入门包'))
    await clickRechargeButton()

    await waitFor(() => expect(paymentApi.createPayment).toHaveBeenCalled())

    await waitFor(() => {
      const raw = sessionStorage.getItem(KEY)
      expect(raw).toBeTruthy()
      const saved = JSON.parse(raw as string)
      expect(saved.payment_no).toBe('PAY-NEW')
      expect(saved.amount).toBe(10)
      expect(typeof saved.savedAt).toBe('number')
    })
  })

  it('TC-FE-RECHARGE-011: 页面挂载时恢复暂存的未完成支付并向后端确认', async () => {
    sessionStorage.setItem(
      KEY,
      JSON.stringify({
        payment_no: 'PAY-OLD',
        order_no: 'ORD-OLD',
        amount: 100,
        pay_url: '',
        savedAt: Date.now(),
      })
    )
    vi.mocked(paymentApi.getPaymentStatus).mockResolvedValue(statusOk as never)

    renderWithProviders(<DeveloperRecharge />, { route: '/developer/recharge' })

    // ⚠️ 关键：必须拿**暂存的单号**去问后端，而不是当作新页面什么都不做
    await waitFor(() => expect(paymentApi.getPaymentStatus).toHaveBeenCalledWith('PAY-OLD'))
  })

  it('TC-FE-RECHARGE-012: 超过 30 分钟的暂存视为作废并清理（不发确认请求）', async () => {
    sessionStorage.setItem(
      KEY,
      JSON.stringify({
        payment_no: 'PAY-EXPIRED',
        order_no: 'ORD-OLD',
        amount: 100,
        savedAt: Date.now() - 31 * 60 * 1000, // 31 分钟前
      })
    )

    renderWithProviders(<DeveloperRecharge />, { route: '/developer/recharge' })
    await screen.findByText('入门包')

    // 不得用过期单号去问后端
    expect(paymentApi.getPaymentStatus).not.toHaveBeenCalledWith('PAY-EXPIRED')
    // 且顺手清理掉
    expect(sessionStorage.getItem(KEY)).toBeNull()
  })
})

/**
 * 扫码轮询的"停止"语义。
 *
 * ⚠️ 这条是**暴露真实缺陷**的用例：`startQrcodePolling` 的循环条件是局部变量 `isPolling`，
 *    而 `stopQrcodePolling()` 只改 React state —— 两者根本不是同一个东西。
 *    结果：用户点「取消订单」后，轮询仍会跑满 8 次（约 32 秒），期间若后端返回 paid，
 *    还会触发 handleQrcodePaymentSuccess 把**已取消的订单**标记成支付成功。
 *    代码里那句注释「用户关闭弹窗时停止轮询」与实现不符。
 */
describe('扫码轮询的停止', () => {
  it('TC-FE-RECHARGE-013: 取消订单后扫码轮询必须停止（不得再向后端查询）', async () => {
    vi.mocked(paymentApi.createPayment).mockResolvedValue({
      payment_no: 'PAY-QR',
      order_no: 'ORD-QR',
      amount: 10,
      status: 'pending',
      expires_in: 600,
      qr_code: 'data:image/png;base64,AAAA',
    } as never)
    vi.mocked(paymentApi.getPaymentStatus).mockResolvedValue({
      status: 'pending',
      payment_no: 'PAY-QR',
      created_at: new Date().toISOString(),
      expires_in: 600,
    } as never)
    vi.mocked(paymentApi.cancelPayment).mockResolvedValue({} as never)

    renderWithProviders(<DeveloperRecharge />, { route: '/developer/recharge' })
    await screen.findByText('入门包')

    fireEvent.click(screen.getByText('入门包'))
    await clickRechargeButton()

    // 带 qr_code + paymentType=qrcode → 自动启动扫码轮询（首次查询间隔 2s）
    await waitFor(
      () => expect(paymentApi.getPaymentStatus).toHaveBeenCalledWith('PAY-QR'),
      { timeout: 3500 }
    )

    // 用户取消订单（内部会调 stopQrcodePolling()）
    const cancelBtn = (await screen.findByText('取消订单')).closest('button')
    if (!cancelBtn) throw new Error('未找到「取消订单」按钮')
    fireEvent.click(cancelBtn)
    await waitFor(() => expect(paymentApi.cancelPayment).toHaveBeenCalled())

    const callsAtCancel = vi.mocked(paymentApi.getPaymentStatus).mock.calls.length

    // 等超过一个轮询间隔（2s）：期间**不得**再有查询。
    // ⚠️ 等待必须包在 act 里：这段时间内倒计时/轮询的 interval 会 fire 并 setState，
    //    裸 await 会让这些更新发生在 act 之外（实测贡献大量 act 警告）。
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 2600))
    })

    expect(vi.mocked(paymentApi.getPaymentStatus).mock.calls.length).toBe(callsAtCancel)
  }, 15000)

  it('TC-FE-RECHARGE-014: 组件卸载后定时器必须清理（不得继续轮询）', async () => {
    vi.mocked(paymentApi.createPayment).mockResolvedValue({
      payment_no: 'PAY-QR2',
      order_no: 'ORD-QR2',
      amount: 10,
      status: 'pending',
      expires_in: 600,
      qr_code: 'data:image/png;base64,BBBB',
    } as never)
    vi.mocked(paymentApi.getPaymentStatus).mockResolvedValue({
      status: 'pending',
      payment_no: 'PAY-QR2',
      created_at: new Date().toISOString(),
      expires_in: 600,
    } as never)

    const { unmount } = renderWithProviders(<DeveloperRecharge />, {
      route: '/developer/recharge',
    })
    await screen.findByText('入门包')

    fireEvent.click(screen.getByText('入门包'))
    await clickRechargeButton()

    // 等轮询真正跑起来（扫码轮询间隔 2s）
    await waitFor(
      () => expect(paymentApi.getPaymentStatus).toHaveBeenCalledWith('PAY-QR2'),
      { timeout: 3500 }
    )

    // 模拟用户直接切走页面（开着支付弹窗就离开）
    unmount()
    const callsAtUnmount = vi.mocked(paymentApi.getPaymentStatus).mock.calls.length

    // 等待超过所有轮询间隔（扫码 2s / 支付结果 3s）
    // ⚠️ 同 013：裸等待期间的一切 setState 都在 act 外 → 必须包裹
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 4200))
    })

    // ⚠️ 组件已卸载，不得再有任何后端查询（否则就是定时器泄漏）
    expect(vi.mocked(paymentApi.getPaymentStatus).mock.calls.length).toBe(callsAtUnmount)
  }, 20000)
})

/**
 * 自定义模式「赠送比例」的显示口径。
 *
 * ⚠️ 这条同样是**暴露真实缺陷**的用例：
 *    `default_bonus_ratio` 是**小数**（0.05），但页面写成 `+(customAmount * ratio)%`
 *    —— 算出来是**金额**却标了 `%`。数额越大越离谱：
 *      充 200 → 显示「+10%」（实际 5%，看着像对的，纯属巧合）
 *      充 500 → 显示「+25%」（实际仍是 5%）
 *
 * ⚠️ 注意与套餐的 `bonus_ratio` 区分：后者是**百分数**（10 表示 10%，
 *    见 calcArrivedAmount 里的 `bonus_ratio / 100`）。两个后端字段的语义不一致，
 *    这正是当初写错的原因。
 */
describe('自定义模式赠送比例的显示', () => {
  it('TC-FE-RECHARGE-015: 赠送比例按"百分比"显示，而不是拿金额冒充百分比', async () => {
    // beforeEach 里 default_bonus_ratio = 0.05（即 5%）
    renderWithProviders(<DeveloperRecharge />, { route: '/developer/recharge' })
    await screen.findByText('入门包')

    fireEvent.click(screen.getByText('自定义金额'))
    await fillCustomAmount('500')

    // 无论充多少，赠送比例都应显示 5%
    await waitFor(() => expect(screen.getByText('+5%')).toBeInTheDocument())
    // 修复前这里会是「+25%」（500 × 0.05），一个随金额变化、不可能正确的"百分比"
    expect(screen.queryByText('+25%')).not.toBeInTheDocument()
  })
})
