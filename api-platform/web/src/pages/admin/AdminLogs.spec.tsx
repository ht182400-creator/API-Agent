/**
 * 管理员日志管理页（admin/AdminLogs.tsx）测试 —— 用例库 FE-ADMIN-ADMINLOGS
 *
 * 为什么值得测：本页既看**日志内容**又管**备份文件**，两边都是"操作错了要出事"：
 *   ① 日志内容按 `startLine = 当前页 × 500` 分页拉取，并带 `level` / `keyword` 过滤
 *      —— 参数错了会"看起来没有这条日志"，排障时会误判；
 *   ② 备份配置是**回显 + 保存**模式（Switch / Slider 就地改 state）——
 *      回显错会把配置改坏，保存时提交错值更危险；
 *   ③ 删除备份**不可恢复** → 必须二次确认；清理是**批量删除**，同样要确认。
 *
 * 用例编号：TC-FE-ADMINLOGS-001 ~ TC-FE-ADMINLOGS-005
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor, fireEvent, within } from '@testing-library/react'

const { messageSpies } = vi.hoisted(() => ({
  messageSpies: { success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn() },
}))

vi.mock('antd', async (importOriginal) => {
  const actual = await importOriginal<typeof import('antd')>()
  return { ...actual, message: messageSpies }
})

// 本模块是**具名函数导出**（不是对象）→ 逐个替换；LOG_LEVELS / getLevelColor 保留真实实现
vi.mock('../../api/adminLogs', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../api/adminLogs')>()
  return {
    ...actual,
    getLogFiles: vi.fn(),
    getLogContent: vi.fn(),
    getLogStats: vi.fn(),
    getBackups: vi.fn(),
    deleteBackup: vi.fn(),
    cleanupBackups: vi.fn(),
    getBackupConfig: vi.fn(),
    updateBackupConfig: vi.fn(),
    manualBackup: vi.fn(),
    getBackupContent: vi.fn(),
  }
})

import AdminLogs from './AdminLogs'
import {
  getLogFiles,
  getLogContent,
  getLogStats,
  getBackups,
  deleteBackup,
  cleanupBackups,
  getBackupConfig,
  updateBackupConfig,
  manualBackup,
} from '../../api/adminLogs'
import { renderWithProviders } from '../../test/renderWithProviders'

// ---------------- 测试数据 ----------------

const files = [
  { name: 'app.log', path: '/logs/app.log', module: 'app', size: 1024, size_formatted: '1.0 KB', modified_at: '2026-09-16T10:00:00Z' },
  { name: 'error.log', path: '/logs/error.log', module: 'error', size: 2048, size_formatted: '2.0 KB', modified_at: '2026-09-16T11:00:00Z' },
]

const backups = [
  { name: 'app_20260916.log', path: '/backups/app_20260916.log', size: 1024, size_formatted: '1.0 KB', created_at: '2026-09-16T10:00:00Z', modified_at: '2026-09-16T10:00:00Z' },
]

const config = {
  max_file_size_mb: 50,
  max_backup_files: 200,
  auto_cleanup: true,
  cleanup_threshold: 75,
  enabled: true,
}

const stats = {
  total_files: 2,
  total_size: 3072,
  total_size_formatted: '3.0 KB',
  backup_count: 1,
  backup_size: 512,
  backup_size_formatted: '512 B',
  config,
}

const logContent = {
  lines: [
    { line_number: 1, timestamp: '2026-09-16 10:00:00', level: 'ERROR', module: 'app', message: 'connection timeout', raw: 'raw line', color: '#ff4d4f' },
  ],
  total: 1,
  start_line: 0,
  max_lines: 500,
}

function renderPage() {
  return renderWithProviders(<AdminLogs />, { route: '/admin/logs' })
}

/** 按单元格文本定位表格行 */
function rowOf(text: string): HTMLElement {
  const row = screen.getByText(text).closest('tr')
  if (!row) throw new Error(`未找到行：${text}`)
  return row as HTMLElement
}

/** antd Select：打开下拉（必须 mouseDown）→ 点 option */
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

/** 按可见文本（placeholder 或已选值）定位 Select，容忍弹层里的同名文本 */
function comboOf(visibleText: string): HTMLElement {
  for (const el of screen.getAllByText(visibleText)) {
    const selector = el.closest('.ant-select')?.querySelector('.ant-select-selector')
    if (selector) return selector as HTMLElement
  }
  throw new Error(`未找到 Select：${visibleText}`)
}

function flatText(): string {
  return (document.body.textContent || '').replace(/\s/g, '')
}

beforeEach(() => {
  vi.mocked(getLogFiles).mockResolvedValue(files as never)
  vi.mocked(getLogStats).mockResolvedValue(stats as never)
  vi.mocked(getBackups).mockResolvedValue(backups as never)
  vi.mocked(getLogContent).mockResolvedValue(logContent as never)
  vi.mocked(getBackupConfig).mockResolvedValue(config as never)
  vi.mocked(updateBackupConfig).mockResolvedValue(config as never)
  vi.mocked(deleteBackup).mockResolvedValue(undefined as never)
  vi.mocked(cleanupBackups).mockResolvedValue(undefined as never)
  vi.mocked(manualBackup).mockResolvedValue(undefined as never)
})

describe('首屏数据与列表（TC-FE-ADMINLOGS-001）', () => {
  it('TC-FE-ADMINLOGS-001: 三个数据源各拉一次；统计与两个列表按数据渲染', async () => {
    renderPage()

    await waitFor(() => expect(getLogFiles).toHaveBeenCalledTimes(1))
    expect(getLogStats).toHaveBeenCalledTimes(1)
    expect(getBackups).toHaveBeenCalledTimes(1)

    // 统计卡片（格式化后的体积文案最不易撞车）
    expect((await screen.findAllByText('日志文件')).length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('备份文件').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('3.0 KB')).toBeInTheDocument()
    expect(screen.getByText('512 B')).toBeInTheDocument()

    // 自动备份状态徽标（来自 stats.config.enabled）
    expect(screen.getByText('自动备份已启用')).toBeInTheDocument()

    // 日志文件表：文件名 / 大小 / 模块
    expect(screen.getByText('app.log')).toBeInTheDocument()
    expect(screen.getByText('error.log')).toBeInTheDocument()
    expect(screen.getByText('2.0 KB')).toBeInTheDocument()
    // ⚠️ '1.0 KB' 在**日志文件表与备份表各出现一次**（app.log 与 app_20260916.log 大小相同）→ 不能 getByText
    expect(screen.getAllByText('1.0 KB').length).toBeGreaterThanOrEqual(2)

    // 备份表
    expect(screen.getByText('app_20260916.log')).toBeInTheDocument()
  })
})

describe('查看日志与筛选（TC-FE-ADMINLOGS-002）', () => {
  it('TC-FE-ADMINLOGS-002: 首次按 500 行分页拉取；切换级别/关键字后带参重拉', async () => {
    renderPage()
    await screen.findByText('app.log')

    // ① 点「查看」→ 以 startLine=0 / maxLines=500 拉取，筛选为空
    fireEvent.click(within(rowOf('app.log')).getByRole('button', { name: /查看/ }))
    await waitFor(() =>
      expect(getLogContent).toHaveBeenCalledWith('app.log', {
        startLine: 0,
        maxLines: 500,
        level: null,
        keyword: null,
      })
    )
    expect(await screen.findByPlaceholderText('搜索关键词')).toBeInTheDocument()
    // ⚠️ 必须用 findByText 等待**内容加载完成**：弹窗一打开先渲染「加载中...」，
    //    此刻 body 里还没有日志行（首跑就是在这个时间窗里取文本才失败）。
    expect(await screen.findByText('connection timeout')).toBeInTheDocument()
    expect(flatText()).toContain('共1行，当前1行')

    // ② 切级别为「错误」→ 自动带 level 重拉（effect 依赖 loadLogContent）
    pick(comboOf('日志级别'), '错误')
    await waitFor(() =>
      expect(getLogContent).toHaveBeenLastCalledWith(
        'app.log',
        expect.objectContaining({ level: 'ERROR', startLine: 0 })
      )
    )

    // ③ 输入关键字 → 带 keyword 重拉
    fireEvent.change(screen.getByPlaceholderText('搜索关键词'), {
      target: { value: 'timeout' },
    })
    await waitFor(() =>
      expect(getLogContent).toHaveBeenLastCalledWith(
        'app.log',
        expect.objectContaining({ level: 'ERROR', keyword: 'timeout' })
      )
    )
  })
})

describe('备份配置回显与保存（TC-FE-ADMINLOGS-003）', () => {
  it('TC-FE-ADMINLOGS-003: 打开时回显四项配置；保存把当前配置整体提交并提示', async () => {
    renderPage()
    await screen.findByText('app.log')

    fireEvent.click(screen.getByRole('button', { name: /备份设置/ }))
    await waitFor(() => expect(getBackupConfig).toHaveBeenCalledTimes(1))

    // 回显：标签里直接带当前值（改动会立刻反映在标签上）
    expect(await screen.findByText('启用自动备份')).toBeInTheDocument()
    expect(screen.getByText('文件大小限制: 50 MB')).toBeInTheDocument()
    expect(screen.getByText('最大备份数量: 200')).toBeInTheDocument()
    expect(screen.getByText('自动清理: 启用')).toBeInTheDocument()
    expect(screen.getByText('清理阈值: 75%')).toBeInTheDocument()

    // 保存 → 整体提交当前配置 + 提示 + 关弹窗（改为读 stats）
    fireEvent.click(screen.getByRole('button', { name: /保存/ }))
    await waitFor(() => expect(updateBackupConfig).toHaveBeenCalledWith(config))
    expect(messageSpies.success).toHaveBeenCalledWith('配置已保存')
    await waitFor(() => expect(getLogStats).toHaveBeenCalledTimes(2))
  })
})

describe('备份操作（TC-FE-ADMINLOGS-004 / 005）', () => {
  it('TC-FE-ADMINLOGS-004: 手动备份按模块调用；清理需二次确认后才执行', async () => {
    renderPage()
    await screen.findByText('app.log')

    // ① 行内「备份」→ 以该文件的 module 调用
    fireEvent.click(within(rowOf('app.log')).getByRole('button', { name: /备份$/ }))
    await waitFor(() => expect(manualBackup).toHaveBeenCalledWith('app'))
    expect(messageSpies.success).toHaveBeenCalledWith('备份成功')

    // ② 清理备份：先弹确认，未确认不发请求
    fireEvent.click(screen.getByRole('button', { name: /清理备份/ }))
    expect(await screen.findByText('确认清理旧备份?')).toBeInTheDocument()
    expect(cleanupBackups).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: /确\s*认/ }))
    await waitFor(() => expect(cleanupBackups).toHaveBeenCalledTimes(1))
    expect(messageSpies.success).toHaveBeenCalledWith('清理完成')
  })

  it('TC-FE-ADMINLOGS-005: 删除备份取消不发请求、确认才删除并重新拉取列表', async () => {
    const first = renderPage()
    await screen.findByText('app_20260916.log')

    // ① 取消 → 不删除
    fireEvent.click(within(rowOf('app_20260916.log')).getByRole('button', { name: /删除/ }))
    expect(await screen.findByText('确认删除此备份?')).toBeInTheDocument()
    expect(deleteBackup).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: /取\s*消/ }))
    expect(deleteBackup).not.toHaveBeenCalled()
    first.unmount()

    // ② 确认 → 才删除，并重新拉取备份列表与统计
    renderPage()
    await screen.findByText('app_20260916.log')
    const backupsBefore = vi.mocked(getBackups).mock.calls.length

    fireEvent.click(within(rowOf('app_20260916.log')).getByRole('button', { name: /删除/ }))
    fireEvent.click(await screen.findByRole('button', { name: /确\s*认/ }))

    await waitFor(() => expect(deleteBackup).toHaveBeenCalledWith('app_20260916.log'))
    expect(messageSpies.success).toHaveBeenCalledWith('删除成功')
    await waitFor(() =>
      expect(vi.mocked(getBackups).mock.calls.length).toBe(backupsBefore + 1)
    )
  })
})
