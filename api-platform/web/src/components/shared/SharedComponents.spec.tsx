/**
 * P3 共享组件测试（TC-FE-SHARED：ResponsiveTable / RepoLogo / DynamicForm / EndpointList）
 *
 * 这四个组件都是 **props 驱动、无 api 依赖** 的纯展示层 —— 用例按「给定 props → 期望渲染」编写。
 * ResponsiveTable 的桌面/移动分支通过 **window.innerWidth** 切换（useDevice 读 innerWidth，零 mock）。
 *
 * ⚠️ 调试教训（见 test-log 43 号）：
 *   - DynamicForm 的 label 无 htmlFor → 不能 getByLabelText，用「文本节点向上找 fieldWrapper 再取控件」；
 *   - EndpointList 按 tag 分组 → 同名端点会出现在多个分组 → 一律 getAllByText；
 *   - RepoLogo 背景是 linear-gradient → 断言包含色值而非全等。
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ResponsiveTable from '../ResponsiveTable'
import { RepoLogo } from '../RepoLogo'
import { DynamicForm } from '../api-tester/DynamicForm'
import { EndpointList } from '../api-tester/EndpointList'
import type { Endpoint, Parameter } from '../../types/api-tester'

const columns = [
  { title: '名称', dataIndex: 'name', key: 'name' },
  { title: '状态', dataIndex: 'status', key: 'status' },
]

afterEach(() => {
  // 恢复视口（RT 移动端用例会改 innerWidth）
  Object.defineProperty(window, 'innerWidth', { value: 1024, configurable: true })
  Object.defineProperty(window, 'innerHeight', { value: 768, configurable: true })
})

describe('ResponsiveTable（TC-FE-SHARED-RT）', () => {
  it('TC-FE-SHARED-RT-001: 桌面端按表格渲染 dataSource', () => {
    render(
      <ResponsiveTable
        dataSource={[
          { id: 'r1', name: '天气服务', status: '在线' },
          { id: 'r2', name: '翻译服务', status: '离线' },
        ]}
        columns={columns}
        rowKey="id"
      />
    )
    expect(screen.getByText('天气服务')).toBeInTheDocument()
    expect(screen.getByText('翻译服务')).toBeInTheDocument()
    expect(screen.getByRole('table')).toBeInTheDocument()
  })

  it('TC-FE-SHARED-RT-002: 空数据显示 emptyText（默认"暂无数据"）', () => {
    render(<ResponsiveTable dataSource={[]} columns={columns} rowKey="id" />)
    expect(screen.getByText('暂无数据')).toBeInTheDocument()
  })

  it('TC-FE-SHARED-RT-003: 空数据可用 emptyText 自定义', () => {
    render(<ResponsiveTable dataSource={[]} columns={columns} rowKey="id" emptyText="还没有仓库" />)
    expect(screen.getByText('还没有仓库')).toBeInTheDocument()
  })

  it('TC-FE-SHARED-RT-004: 移动端（innerWidth=375）切为卡片模式并渲染 cardConfig', () => {
    // useDevice 初始化读 window.innerWidth → 渲染前收窄视口即可切移动端（零 mock）
    Object.defineProperty(window, 'innerWidth', { value: 375, configurable: true })
    const onAction = vi.fn()
    const { container } = render(
      <ResponsiveTable
        dataSource={[{ id: 'r1', name: '天气服务', status: '在线' }]}
        columns={columns}
        rowKey="id"
        cardConfig={{
          titleField: 'name',
          tagField: 'status',
          actionText: '查看',
          onAction,
        }}
      />
    )
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    expect(screen.getByText('天气服务')).toBeInTheDocument()
    expect(screen.getByText('在线')).toBeInTheDocument()

    // ⚠️ antd Button 对两字中文自动插入空格（accessible name 是「查 看」）→ 正则用 \s* 兼容
    fireEvent.click(screen.getByRole('button', { name: /查\s*看/ }))
    expect(onAction).toHaveBeenCalledWith(expect.objectContaining({ id: 'r1' }))
  })
})

describe('RepoLogo（TC-FE-SHARED-LOGO）', () => {
  it('TC-FE-SHARED-LOGO-001: 有 logoUrl 时渲染自定义图标', () => {
    const { container } = render(<RepoLogo logoUrl="https://example.com/x.png" />)
    const img = container.querySelector('img')
    expect(img).not.toBeNull()
    expect(img).toHaveAttribute('src', 'https://example.com/x.png')
  })

  it('TC-FE-SHARED-LOGO-002: 无 logoUrl 时按 repoType 渲染默认图标与主题色', () => {
    const { container } = render(<RepoLogo repoType="ai" />)
    // 背景来自 typeColorMap.ai（实为 linear-gradient，断言包含色值即可）
    const el = container.firstElementChild as HTMLElement
    expect(el?.style.background).toContain('16, 185, 129')
    // ai → RobotOutlined（aria-label "robot"）
    expect(container.querySelector('[aria-label="robot"]')).not.toBeNull()
  })

  it('TC-FE-SHARED-LOGO-003: 未知 repoType 不崩溃（渲染兜底内容）', () => {
    const { container } = render(<RepoLogo repoType="mystery" />)
    expect(container.firstElementChild).not.toBeNull()
  })
})

describe('DynamicForm（TC-FE-SHARED-FORM）', () => {
  const params: Parameter[] = [
    { name: 'city', type: 'string', required: true, description: '城市', in: 'query' },
    {
      name: 'days',
      type: 'select',
      required: false,
      description: '天数',
      in: 'query',
      options: [
        { label: '近7天', value: 7 },
        { label: '近30天', value: 30 },
      ],
    },
  ]

  /** label 无 htmlFor → 通过参数名文本向上找 fieldWrapper，再取其中的控件 */
  const controlOf = (paramName: string): HTMLElement => {
    const wrapper = screen.getByText(paramName).closest('div')
    const ctl = wrapper?.querySelector('input, select') as HTMLElement | null
    if (!ctl) throw new Error(`未找到参数 ${paramName} 的控件`)
    return ctl
  }

  it('TC-FE-SHARED-FORM-001: 按 schema 渲染输入与下拉控件', () => {
    render(<DynamicForm params={params} values={{}} onChange={vi.fn()} />)
    const cityCtl = controlOf('city')
    const daysCtl = controlOf('days') as HTMLSelectElement
    expect(cityCtl.tagName).toBe('INPUT')
    expect(daysCtl.tagName).toBe('SELECT')
    // select 渲染 options（请选择 + 2 项）
    expect(daysCtl.options.length).toBe(3)
  })

  it('TC-FE-SHARED-FORM-002: 输入变化回调 onChange(name, value)', () => {
    const onChange = vi.fn()
    render(<DynamicForm params={params} values={{}} onChange={onChange} />)
    fireEvent.change(controlOf('city'), { target: { value: '北京' } })
    expect(onChange).toHaveBeenCalledWith('city', '北京')
  })

  it('TC-FE-SHARED-FORM-003: 空参数不渲染任何控件', () => {
    const { container } = render(<DynamicForm params={[]} values={{}} onChange={vi.fn()} />)
    expect(container.querySelector('input, select')).toBeNull()
  })
})

describe('EndpointList（TC-FE-SHARED-EP）', () => {
  const eps: Endpoint[] = [
    { id: 'e1', name: '查询天气', path: '/weather', method: 'GET', tags: ['天气'] },
    {
      id: 'e2',
      name: '订阅天气',
      path: '/weather/subscribe',
      method: 'POST',
      tags: ['天气', '订阅'],
    },
  ]

  it('TC-FE-SHARED-EP-001: 空列表显示空态文案', () => {
    render(<EndpointList endpoints={[]} selected={null} onSelect={vi.fn()} />)
    expect(screen.getByText('暂无API端点')).toBeInTheDocument()
  })

  it('TC-FE-SHARED-EP-002: 渲染端点（按 tag 分组，同端点多组出现）并支持选中回调', () => {
    const onSelect = vi.fn()
    render(<EndpointList endpoints={eps} selected={null} onSelect={onSelect} />)
    expect(screen.getByText('查询天气')).toBeInTheDocument()
    // ⚠️ e2 属于「天气」「订阅」两个分组 → 名字出现两次 → 必须 getAllByText
    expect(screen.getAllByText('订阅天气').length).toBe(2)
    expect(screen.getByText('订阅')).toBeInTheDocument()

    fireEvent.click(screen.getAllByText('查询天气')[0])
    expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ id: 'e1' }))
  })
})
