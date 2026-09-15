/**
 * 「仓库明细」表格列定义 —— P1-4 巨型组件拆分（纯搬运，零行为改变）
 *
 * 由 `../Analytics.tsx` 抽出。这一块原先占主组件约 115 行，且**只依赖两个动作回调**
 * （打开明细弹窗 / 跳转仓库页）与状态映射表，与页面状态无关 → 是最适合先切的一刀。
 *
 * ⚠️ 用**工厂函数**而不是常量：两个 onClick 需要组件内的 `openRepoDetail` 与 `navigate`，
 *    直接写成模块级常量就得反过来 import 组件，形成环。
 */
import { Button, Space, Tag, TableProps } from 'antd'
import { LineChartOutlined } from '@ant-design/icons'
import { RepoDetailItem } from '../../../api/adminAnalytics'
import { statusColors, statusText } from './constants'

export interface RepoDetailColumnActions {
  /** 打开该仓库的趋势明细弹窗 */
  onViewDetail: (record: RepoDetailItem) => void
  /** 跳转仓库详情页（按 slug） */
  onOpenRepo: (slug: string) => void
}

export const createRepoDetailColumns = (
  actions: RepoDetailColumnActions
): TableProps<RepoDetailItem>['columns'] => [
  {
    title: '仓库名称',
    dataIndex: 'name',
    key: 'name',
    width: 200,
    render: (text: string, record: RepoDetailItem) => (
      <div>
        <div style={{ fontWeight: 500 }}>{text}</div>
        <div style={{ color: '#999', fontSize: 12 }}>{record.slug}</div>
      </div>
    ),
  },
  {
    title: '状态',
    dataIndex: 'status',
    key: 'status',
    width: 100,
    render: (status: string) => (
      <Tag color={statusColors[status] || 'default'}>{statusText[status] || status}</Tag>
    ),
  },
  {
    title: '总调用',
    dataIndex: 'total_calls',
    key: 'total_calls',
    width: 120,
    sorter: true,
    render: (value: number) => <span style={{ color: '#059669' }}>{value.toLocaleString()} 次</span>,
  },
  {
    title: '成功',
    dataIndex: 'success_calls',
    key: 'success_calls',
    width: 100,
    render: (value: number) => <span style={{ color: '#52c41a' }}>{value.toLocaleString()}</span>,
  },
  {
    title: '失败',
    dataIndex: 'failed_calls',
    key: 'failed_calls',
    width: 100,
    render: (value: number) => (
      <span style={{ color: value > 0 ? '#ff4d4f' : '#999' }}>{value.toLocaleString()}</span>
    ),
  },
  {
    title: '成功率',
    dataIndex: 'success_rate',
    key: 'success_rate',
    width: 100,
    render: (value: number) => (
      <span style={{ color: value >= 99 ? '#52c41a' : value >= 95 ? '#faad14' : '#ff4d4f' }}>
        {value.toFixed(1)}%
      </span>
    ),
  },
  {
    title: '总收入',
    dataIndex: 'total_cost',
    key: 'total_cost',
    width: 120,
    sorter: true,
    render: (value: number) => (
      <span style={{ color: '#faad14', fontWeight: 500 }}>¥{value.toFixed(2)}</span>
    ),
  },
  {
    title: '创建时间',
    dataIndex: 'created_at',
    key: 'created_at',
    width: 170,
    render: (time: string) => (time ? new Date(time).toLocaleString('zh-CN') : '-'),
  },
  {
    title: '操作',
    key: 'action',
    width: 180,
    fixed: 'right' as const,
    render: (_: unknown, record: RepoDetailItem) => (
      <Space size="small">
        <Button
          type="primary"
          size="small"
          icon={<LineChartOutlined />}
          onClick={() => actions.onViewDetail(record)}
        >
          查看明细
        </Button>
        <Button type="link" size="small" onClick={() => actions.onOpenRepo(record.slug)}>
          详情
        </Button>
      </Space>
    ),
  },
]
