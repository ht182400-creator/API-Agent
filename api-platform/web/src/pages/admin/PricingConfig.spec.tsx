/**
 * 价格配置页（admin/PricingConfig.tsx）测试 —— 用例库 FE-ADMIN-PRICING
 *
 * 为什么值得优先测：这是**直接决定计费金额**的管理页 —— 配置错了就是资损。
 * 本文件锁住四件事：
 *   ① 列表的**派生文案**（价格 / 免费额度 / VIP 折扣的拼接，算错会误导运营）；
 *   ② 编辑回显：把配置灌回表单时数值要对，且 `packages` 必须被
 *      **序列化成 JSON 文本**（否则套餐类配置一打开编辑就坏）；
 *   ③ 计费模式的**联动必填**（选 call 就必须填每次调用价格）；
 *   ④ 保存成功后必须**重新拉取列表**（否则页面还显示旧价，运营以为没保存上）。
 *
 * ⚠️ 顺带修掉两笔"环境债"（补测试才会暴露）：
 *  - 本页原用 `Modal destroyOnClose`（antd v5 已废弃）。因该页**此前无任何测试渲染**，
 *    这条废弃警告从未出现过；补测试后它会顶穿 `test:budget` 的警告预算 → 已改 `destroyOnHidden`。
 *  - `renderWithProviders` 原先用 antd **默认英文** locale，与 `main.tsx` 的 `zhCN` 不一致
 *    → 弹窗按钮是 OK/Cancel。已对齐，故本文件断言的"确 定"与真实界面一致。
 *
 * ⚠️ antd Select 在 jsdom 下的交互（复用 Analytics.spec 踩过的结论）：
 *    打开下拉必须 `fireEvent.mouseDown(selector)`；option 弹层会停在 slide-up 动画帧、
 *    可访问性判定找不到 → 改为在弹层里按文本找 `.ant-select-item-option` 再 `fireEvent.click`。
 *
 * 用例编号：TC-FE-PRICING-001 ~ TC-FE-PRICING-004
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor, fireEvent, within } from '@testing-library/react'

const { messageSpies } = vi.hoisted(() => ({
  messageSpies: { success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn() },
}))

// ⚠️ 局部 mock antd 的 message（静态方法）：既能精确断言文案，
//    又规避 antd v5 静态 message 的 "can not consume context" 警告（基线外的新种类）。
vi.mock('antd', async (importOriginal) => {
  const actual = await importOriginal<typeof import('antd')>()
  return { ...actual, message: messageSpies }
})

// 组件唯一数据源 → 整体 mock，但保留 PRICING_TYPE_OPTIONS / STATUS_OPTIONS 等真实常量
vi.mock('../../api/adminPricingConfig', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../api/adminPricingConfig')>()
  return {
    ...actual,
    adminPricingConfigApi: {
      getConfigs: vi.fn(),
      getConfig: vi.fn(),
      getGlobalConfigs: vi.fn(),
      getConfigByRepo: vi.fn(),
      createConfig: vi.fn(),
      updateConfig: vi.fn(),
      deleteConfig: vi.fn(),
      enableConfig: vi.fn(),
      disableConfig: vi.fn(),
      calculateCost: vi.fn(),
    },
  }
})

import PricingConfigPage from './PricingConfig'
import { adminPricingConfigApi } from '../../api/adminPricingConfig'
import type { PricingConfig } from '../../api/adminPricingConfig'
import { renderWithProviders } from '../../test/renderWithProviders'

// ---------------- 测试数据（三种计费模式各一，覆盖所有派生文案分支）----------------

const callConfig: PricingConfig = {
  id: 'cfg-call-1111-2222-3333',
  repo_id: null,
  pricing_type: 'call',
  price_per_call: 0.02,
  free_calls: 100,
  priority: 100,
  status: 'active',
  description: '全局按调用',
  // 3 档 → 用于验证列表**只展示前 2 档**
  vip_discounts: { '1': 0.1, '2': 0.2, '3': 0.3 },
  created_at: '2026-09-01T00:00:00Z',
  updated_at: '2026-09-01T00:00:00Z',
}

const tokenConfig: PricingConfig = {
  id: 'cfg-token-4444-5555-6666',
  repo_id: 'repo-1',
  pricing_type: 'token',
  price_per_1k_input_tokens: 0.001,
  price_per_1k_output_tokens: 0.002,
  free_input_tokens: 1000,
  free_output_tokens: 500,
  priority: 50,
  status: 'inactive',
  created_at: '2026-09-02T00:00:00Z',
  updated_at: '2026-09-02T00:00:00Z',
}

const packageConfig: PricingConfig = {
  id: 'cfg-pkg-7777-8888-9999',
  repo_id: null,
  pricing_type: 'package',
  packages: [
    { id: 'free', name: 'Free', calls: 100, price: 0 },
    { id: 'pro', name: 'Pro', calls: 10000, price: 199 },
  ],
  priority: 10,
  status: 'active',
  created_at: '2026-09-03T00:00:00Z',
  updated_at: '2026-09-03T00:00:00Z',
}

const listResponse = {
  items: [callConfig, tokenConfig, packageConfig],
  total: 3,
  page: 1,
  page_size: 10,
  total_pages: 1,
}

function renderPage() {
  return renderWithProviders(<PricingConfigPage />, { route: '/admin/pricing-configs' })
}

/** input / textarea 的原始值（统一取字符串，避开 antd InputNumber 的类型差异） */
function valueOf(el: HTMLElement): string {
  return (el as HTMLInputElement | HTMLTextAreaElement).value
}

/** 按标题定位弹窗（比 role=dialog 稳：不依赖 antd 把 role 放在哪一层） */
function modalOf(title: string): HTMLElement {
  const el = screen.getByText(title).closest('.ant-modal')
  if (!el) throw new Error(`未找到弹窗：${title}`)
  return el as HTMLElement
}

/** antd Select：打开下拉（必须 mouseDown）→ 在弹层里点 option */
function pick(selector: HTMLElement, optionText: string): void {
  fireEvent.mouseDown(selector)
  const dd = [...document.querySelectorAll('.ant-select-dropdown')].find(
    (d) => !d.className.includes('hidden')
  )
  if (!dd) throw new Error('Select 下拉未打开')
  const opt = [...dd.querySelectorAll('.ant-select-item-option')].find(
    (o) => o.textContent === optionText
  )
  if (!opt) throw new Error(`下拉中无 option：${optionText}`)
  fireEvent.click(opt)
}

/** 用"当前可见文本"（placeholder 或已选值）定位 Select 的 selector 元素 */
function comboOf(visibleText: string): HTMLElement {
  const el = screen.getByText(visibleText).closest('.ant-select')
  if (!el) throw new Error(`未找到 Select：${visibleText}`)
  const selector = el.querySelector('.ant-select-selector')
  if (!selector) throw new Error(`Select 缺少 selector：${visibleText}`)
  return selector as HTMLElement
}

beforeEach(() => {
  vi.mocked(adminPricingConfigApi.getConfigs).mockResolvedValue(listResponse as never)
  vi.mocked(adminPricingConfigApi.createConfig).mockResolvedValue(callConfig as never)
  vi.mocked(adminPricingConfigApi.updateConfig).mockResolvedValue(callConfig as never)
})

describe('配置列表回显（TC-FE-PRICING-001）', () => {
  it('TC-FE-PRICING-001: 三种计费模式的价格/免费额度/VIP 折扣派生文案正确', async () => {
    renderPage()

    // 首次加载：默认分页参数
    await waitFor(() =>
      expect(adminPricingConfigApi.getConfigs).toHaveBeenCalledWith({ page: 1, page_size: 10 })
    )

    // 价格列（三种模式三种形态）
    expect(await screen.findByText('¥0.0200/次')).toBeInTheDocument()
    expect(screen.getByText('¥0.0010/1K输入, ¥0.0020/1K输出')).toBeInTheDocument()
    expect(screen.getByText('2 个套餐')).toBeInTheDocument()

    // 免费额度列
    expect(screen.getByText('100 次')).toBeInTheDocument()
    expect(screen.getByText('1000输入/500输出')).toBeInTheDocument()

    // VIP 折扣：有 3 档但**只展示前 2 档**
    expect(screen.getByText('VIP1: 10%')).toBeInTheDocument()
    expect(screen.getByText('VIP2: 20%')).toBeInTheDocument()
    expect(screen.queryByText('VIP3: 30%')).not.toBeInTheDocument()

    // ID 列截断为前 18 位
    expect(screen.getByText('cfg-call-1111-2222...')).toBeInTheDocument()

    // 分页总计文案
    expect(screen.getByText('共 3 条')).toBeInTheDocument()

    // 状态 → 操作按钮的映射：2 个 active 行给"禁用"，1 个 inactive 行给"启用"
    expect(screen.getAllByRole('button', { name: /编辑/ })).toHaveLength(3)
    expect(screen.getAllByRole('button', { name: /禁用/ })).toHaveLength(2)
    expect(screen.getAllByRole('button', { name: /启用/ })).toHaveLength(1)
  })
})

describe('编辑回显（TC-FE-PRICING-002 / 003）', () => {
  it('TC-FE-PRICING-002: 按调用配置的数值字段与联动字段正确灌回表单', async () => {
    renderPage()
    await screen.findByText('¥0.0200/次')

    fireEvent.click(screen.getAllByRole('button', { name: /编辑/ })[0])
    const modal = modalOf('编辑价格配置')

    // 计费模式下拉回显当前值。
    // ⚠️ 注意两处文案不同：下拉用的是 option 的 **label**（`按调用计费`），
    //    表格 Tag 用的是列 render 里的短文案（`按调用`）—— 首跑就是在这里断言错了。
    expect(within(modal).getByText('按调用计费')).toBeInTheDocument()

    // 数值字段回显（优先级 100 / 每次调用 0.02 / 免费 100 次）。
    // ⚠️ 价格字段带 `precision={4}` → 回显是 `0.0200` 而不是 `0.02`（首跑断言成 0.02 失败）。
    expect(valueOf(within(modal).getByLabelText('优先级'))).toBe('100')
    expect(valueOf(within(modal).getByLabelText('每次调用价格'))).toBe('0.0200')
    expect(valueOf(within(modal).getByLabelText('免费调用次数'))).toBe('100')

    // 联动：call 模式不应出现 token / package 专属字段
    expect(within(modal).queryByLabelText('每1K输入Token价格')).toBeNull()
    expect(within(modal).queryByLabelText('套餐包定义 (JSON)')).toBeNull()
  })

  it('TC-FE-PRICING-003: 套餐类配置的 packages 被序列化为 JSON 文本回显', async () => {
    renderPage()
    await screen.findByText('2 个套餐')

    fireEvent.click(screen.getAllByRole('button', { name: /编辑/ })[2])
    const modal = modalOf('编辑价格配置')

    const textarea = within(modal).getByLabelText('套餐包定义 (JSON)')
    // ⚠️ 关键：必须是可解析的 JSON（若某次改动漏了 JSON.stringify，这里会显示 [object Object]）
    expect(JSON.parse(valueOf(textarea))).toEqual(packageConfig.packages)
    // 且是带缩进的格式化文本（方便运营直接改）
    expect(valueOf(textarea)).toContain('"id": "free"')
    expect(valueOf(textarea)).toContain('\n')

    // 联动：package 模式不应出现 call / token 的价格字段
    expect(within(modal).queryByLabelText('每次调用价格')).toBeNull()
    expect(within(modal).queryByLabelText('每1K输入Token价格')).toBeNull()
  })
})

describe('必填校验与保存（TC-FE-PRICING-004）', () => {
  it('TC-FE-PRICING-004: 空提交与缺价格被拦截；补全后创建成功并重新拉取列表', async () => {
    renderPage()
    await screen.findByText('¥0.0200/次')
    const callsBefore = vi.mocked(adminPricingConfigApi.getConfigs).mock.calls.length

    fireEvent.click(screen.getByRole('button', { name: /创建配置/ }))
    const modal = modalOf('创建价格配置')
    const okButton = () => within(modal).getByRole('button', { name: /确\s*定/ })

    // ① 空表单提交 → 计费模式必填拦截，不发请求
    fireEvent.click(okButton())
    expect(await screen.findByText('请输入计费模式')).toBeInTheDocument()
    expect(adminPricingConfigApi.createConfig).not.toHaveBeenCalled()

    // ② 选了「按调用」但没填价格 → 对应价格字段必填拦截
    pick(comboOf('选择计费模式'), '按调用计费')
    fireEvent.click(okButton())
    expect(await screen.findByText('请输入每次调用价格')).toBeInTheDocument()
    expect(adminPricingConfigApi.createConfig).not.toHaveBeenCalled()

    // ③ 补全价格 → 提交成功
    fireEvent.change(within(modal).getByLabelText('每次调用价格'), { target: { value: '0.05' } })
    fireEvent.click(okButton())

    await waitFor(() => expect(adminPricingConfigApi.createConfig).toHaveBeenCalledTimes(1))
    expect(adminPricingConfigApi.createConfig).toHaveBeenCalledWith(
      expect.objectContaining({ pricing_type: 'call', price_per_call: 0.05 })
    )
    expect(messageSpies.success).toHaveBeenCalledWith('创建成功')

    // ④ 保存后**重新拉取列表**（否则页面仍是旧数据）
    await waitFor(() =>
      expect(vi.mocked(adminPricingConfigApi.getConfigs).mock.calls.length).toBe(callsBefore + 1)
    )
  })
})
