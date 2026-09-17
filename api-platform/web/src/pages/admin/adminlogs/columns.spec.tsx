import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Table } from 'antd'
import { buildBackupColumns, buildFileColumns } from './columns'
import { downloadBackup, exportLog, BackupFileInfo, LogFileInfo } from '../../../api/adminLogs'

/**
 * 列定义的**契约用例**（P1-4-D 拆分后补上）。
 *
 * 为什么值得测：`columns.tsx` 是纯 UI 工厂，页面用例只覆盖"表格能渲染、能点查看"，
 * 但**导出/下载链接是否指向正确接口**、**删除是否经过二次确认**这两类资金/数据安全相关的
 * 行为此前没有锁定 —— 抽成独立模块后恰好可以低成本锁死。
 *
 * ⚠️ 直接用 antd `<Table>` 渲染（无需 router/auth）—— 列定义是纯展示工厂，不依赖任何全局状态。
 */

const file = {
  name: 'api-2026-09-17.log',
  module: 'api',
  size_formatted: '1.2 MB',
  modified_at: '2026-09-17 10:00:00',
} as LogFileInfo

const backup = {
  name: 'api-2026-09-17.backup.log',
  size_formatted: '0.8 MB',
  created_at: '2026-09-17 10:00:00',
} as BackupFileInfo

describe('日志管理列定义（adminlogs/columns）', () => {
  it('TC-FE-ALCOL-001: 文件列四列头齐全；导出链接指向 exportLog；查看/备份动作带对参数', async () => {
    const onViewLog = vi.fn()
    const onManualBackup = vi.fn()
    const user = userEvent.setup()
    render(
      <Table
        columns={buildFileColumns({ onViewLog, onManualBackup })}
        dataSource={[file]}
        rowKey="name"
      />
    )

    // 四个业务列头
    for (const head of ['文件名', '模块', '大小', '修改时间']) {
      expect(screen.getByText(head)).toBeInTheDocument()
    }

    // ① 导出：href 必须是 exportLog 生成的下载地址（写错接口名/单号这里立刻红）
    expect(screen.getByRole('link', { name: /导出/ })).toHaveAttribute(
      'href',
      exportLog(file.name)
    )

    // ② 查看：带整条记录（页面用它设置选中文件）
    await user.click(screen.getByRole('button', { name: '查看' }))
    expect(onViewLog).toHaveBeenCalledWith(file)

    // ③ 备份：只带 **module** 字符串（manualBackup 接口按模块建备份，传整条记录是错的）
    //    ⚠️ 用子串匹配：antd 图标自带 role="img" + aria-label（如 "cloud-upload"），
    //       会**参与按钮的可访问名**（变成 "cloud-upload 备份"），精确匹配会失败
    await user.click(screen.getByRole('button', { name: /备份/ }))
    expect(onManualBackup).toHaveBeenCalledWith(file.module)
    expect(onManualBackup).not.toHaveBeenCalledWith(file)
  })

  it('TC-FE-ALCOL-002: 备份列下载链接正确；删除必须经 Popconfirm 二次确认', async () => {
    const onViewBackup = vi.fn()
    const onDeleteBackup = vi.fn()
    const user = userEvent.setup()
    render(
      <Table
        columns={buildBackupColumns({ onViewBackup, onDeleteBackup })}
        dataSource={[backup]}
        rowKey="name"
      />
    )

    // ① 下载链接
    expect(screen.getByRole('link', { name: /下载/ })).toHaveAttribute(
      'href',
      downloadBackup(backup.name)
    )

    // ② 查看动作（⚠️ 备份列的查看按钮**带图标** → 可访问名含图标 label，用子串匹配）
    await user.click(screen.getByRole('button', { name: /查看/ }))
    expect(onViewBackup).toHaveBeenCalledWith(backup.name)

    // ③ 删除不可恢复 → **必须二次确认**：点「删除」先只弹确认框，不触发回调
    //    ⚠️ 同上：图标参与可访问名 → 子串匹配。
    //    ⚠️ 弹层交互用 fireEvent（antd Popconfirm 的惯用驱动方式；userEvent 的
    //       pointer 事件序列在 jsdom 下偶发触发不了 Tooltip 系弹层）
    fireEvent.click(screen.getByRole('button', { name: /删除/ }))
    expect(onDeleteBackup).not.toHaveBeenCalled()

    // 确认弹层出现（标题即"确认删除此备份?"），点「确认」后才带文件名触发。
    // ⚠️ role 查询会被弹层 motion 的 aria-hidden 挡住（jsdom 动画不推进，曾白等 3 秒）；
    //    文本查询也可能因 antd 按钮的「两汉字加空格」而失配 → 用 antd 稳定类名拿主按钮。
    await screen.findByText('确认删除此备份?')
    const okButton = document.querySelector(
      '.ant-popconfirm-buttons .ant-btn-primary'
    ) as HTMLButtonElement | null
    if (!okButton) {
      const box = document.querySelector('.ant-popover, .ant-popconfirm')
      throw new Error('未找到 Popconfirm 主按钮：' + (box ? box.innerHTML : '弹层容器不存在'))
    }
    fireEvent.click(okButton)
    expect(onDeleteBackup).toHaveBeenCalledWith(backup.name)
  })
})
