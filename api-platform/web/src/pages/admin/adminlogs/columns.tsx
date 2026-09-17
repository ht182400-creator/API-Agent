/**
 * 日志管理页的两组表格列定义（P1-4 拆分，纯搬运零行为改变）。
 *
 * ⚠️ 列里带着**页面的动作回调**，所以做成工厂函数（与 `owner/repos/repoColumns` 同一套路）：
 *    页面每次渲染传入当前闭包，避免"定义时捕获旧 handler"的陈旧闭包问题。
 *
 * ⚠️ 两个操作列里的 `exportLog` / `downloadBackup` 直接作为 `<Button href>`（原生下载链接），
 *    这是有意保留 —— 保持与拆分前逐字节一致，不做"顺手优化"。
 */
import { Button, Popconfirm, Space, Tag, Typography } from 'antd'
import {
  CloudUploadOutlined,
  DeleteOutlined,
  DownloadOutlined,
  FileTextOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { downloadBackup, exportLog, BackupFileInfo, LogFileInfo } from '../../../api/adminLogs'

const { Text } = Typography

export interface FileColumnActions {
  onViewLog: (file: LogFileInfo) => void
  onManualBackup: (module: string) => void
}

/** 日志文件表格列 */
export function buildFileColumns({
  onViewLog,
  onManualBackup,
}: FileColumnActions): ColumnsType<LogFileInfo> {
  return [
    {
      title: '文件名',
      dataIndex: 'name',
      key: 'name',
      render: (text, record) => (
        <Space>
          <FileTextOutlined />
          <Text strong>{text}</Text>
        </Space>
      ),
    },
    {
      title: '模块',
      dataIndex: 'module',
      key: 'module',
      render: (text) => <Tag color="blue">{text}</Tag>,
    },
    {
      title: '大小',
      dataIndex: 'size_formatted',
      key: 'size',
    },
    {
      title: '修改时间',
      dataIndex: 'modified_at',
      key: 'modified_at',
    },
    {
      title: '操作',
      key: 'action',
      width: 250,
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<DownloadOutlined />}
            href={exportLog(record.name)}
            target="_blank"
          >
            导出
          </Button>
          <Button type="link" size="small" onClick={() => onViewLog(record)}>
            查看
          </Button>
          <Button
            type="link"
            size="small"
            icon={<CloudUploadOutlined />}
            onClick={() => onManualBackup(record.module)}
          >
            备份
          </Button>
        </Space>
      ),
    },
  ]
}

export interface BackupColumnActions {
  onViewBackup: (name: string) => void
  onDeleteBackup: (name: string) => void
}

/** 备份表格列 */
export function buildBackupColumns({
  onViewBackup,
  onDeleteBackup,
}: BackupColumnActions): ColumnsType<BackupFileInfo> {
  return [
    {
      title: '文件名',
      dataIndex: 'name',
      key: 'name',
      render: (text) => <Text copyable={{ text }}>{text}</Text>,
    },
    {
      title: '大小',
      dataIndex: 'size_formatted',
      key: 'size',
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<FileTextOutlined />}
            onClick={() => onViewBackup(record.name)}
          >
            查看
          </Button>
          <Button
            type="link"
            size="small"
            icon={<DownloadOutlined />}
            href={downloadBackup(record.name)}
            target="_blank"
          >
            下载
          </Button>
          <Popconfirm
            title="确认删除此备份?"
            onConfirm={() => onDeleteBackup(record.name)}
            okText="确认"
            cancelText="取消"
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]
}
