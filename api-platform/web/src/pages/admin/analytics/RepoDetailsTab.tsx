/**
 * 「仓库明细」Tab —— P1-4 巨型组件拆分（B 轮，由 `../Analytics.tsx` 抽出）
 *
 * 内容：筛选（状态 / 排序字段 / 排序次序）+ 明细表格 + 服务端分页。
 *
 * ⚠️ 筛选与分页都**受控**：任一变化都会触发父组件的 effect 带参重查
 *    （回归用例 TC-FE-ANA-008 状态与排序、TC-FE-ANA-010 翻页）。
 */
import { Card, Select, Space, Spin, Table } from 'antd'
import type { RepoDetailItem } from '../../../api/adminAnalytics'
import type { createRepoDetailColumns } from './repoDetailColumns'
// ⚠️ 样式在 admin/ 下，本文件在 admin/analytics/ → 回退一级
import styles from '../Analytics.module.css'

export interface RepoDetailsTabProps {
  loading: boolean
  items: RepoDetailItem[]
  /** 列定义由父组件用工厂函数生成（需要注入两个动作回调） */
  columns: ReturnType<typeof createRepoDetailColumns>
  pagination: { page: number; page_size: number; total: number }
  onPageChange: (page: number, pageSize: number) => void
  status?: string
  onStatusChange: (value?: string) => void
  sortBy: string
  onSortByChange: (value: string) => void
  sortOrder: string
  onSortOrderChange: (value: string) => void
}

export function RepoDetailsTab({
  loading,
  items,
  columns,
  pagination,
  onPageChange,
  status,
  onStatusChange,
  sortBy,
  onSortByChange,
  sortOrder,
  onSortOrderChange,
}: RepoDetailsTabProps) {
  return (
    <Spin spinning={loading}>
      <Card
        title="仓库调用与收入明细"
        extra={
          <Space wrap>
            <Select
              placeholder="状态筛选"
              allowClear
              value={status}
              onChange={(v) => onStatusChange(v)}
              style={{ width: 120 }}
              options={[
                { label: '全部状态', value: undefined },
                { label: '已上线', value: 'online' },
                { label: '待审核', value: 'pending' },
                { label: '已下线', value: 'offline' },
                { label: '已拒绝', value: 'rejected' },
              ]}
            />
            <Select
              value={sortBy}
              onChange={onSortByChange}
              style={{ width: 130 }}
              options={[
                { label: '按调用量排序', value: 'total_calls' },
                { label: '按收入排序', value: 'total_cost' },
                { label: '按名称排序', value: 'name' },
              ]}
            />
            <Select
              value={sortOrder}
              onChange={onSortOrderChange}
              style={{ width: 100 }}
              options={[
                { label: '降序', value: 'desc' },
                { label: '升序', value: 'asc' },
              ]}
            />
          </Space>
        }
      >
        <Table
          dataSource={items}
          columns={columns}
          rowKey="repo_id"
          pagination={{
            current: pagination.page,
            pageSize: pagination.page_size,
            total: pagination.total,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 条`,
            onChange: onPageChange,
          }}
          scroll={{ x: 'max-content' }}
          size="small"
          tableLayout="fixed"
        />
      </Card>
    </Spin>
  )
}
