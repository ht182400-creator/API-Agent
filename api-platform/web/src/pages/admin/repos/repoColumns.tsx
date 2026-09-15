/**
 * admin/Repos 两个表格的列定义（P1-4 拆分：自 AdminRepos.tsx 抽出，纯搬移零行为变更）
 *
 * ⚠️ 用**工厂函数**而不是模块级常量：操作列需要组件内的 handler（审批 / 上下线 /
 *    删除 / 详情 / 跳转编辑端点），写成常量就得反过来 import 组件 → 循环依赖
 *    （约定见 OPTIMIZATION_BACKLOG §2.25 经验 1）。
 */
import { Tag, Button, Space, Popconfirm } from 'antd'
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  DeleteOutlined,
  ApiOutlined,
  EyeOutlined,
} from '@ant-design/icons'
import type { Repository } from '../../../api/repo'
import { RepoLogo } from '../../../components/RepoLogo'

/** 单仓库的调用统计（与主组件 state 共用的形状） */
export interface RepoStats {
  total_calls: number
  successful_calls: number
  failed_calls: number
  total_cost: number
  period: string

  [key: string]: unknown
}

export type RepoStatsMap = Record<string, RepoStats>

/** 状态标签：pending/approved/rejected/online/offline → 颜色与文案 */
export function getStatusTag(status: string) {
  const statusMap: Record<string, { color: string; text: string }> = {
    pending: { color: 'orange', text: '待审核' },
    approved: { color: 'blue', text: '已审核' },
    rejected: { color: 'red', text: '已拒绝' },
    online: { color: 'green', text: '已上线' },
    offline: { color: 'default', text: '已下线' },
  }
  const config = statusMap[status] || { color: 'default', text: status }
  return <Tag color={config.color}>{config.text}</Tag>
}

interface RepoColumnDeps {
  /** 待审核 → 通过；已拒绝 → 重新审核（两态共用打开审批弹窗） */
  onApprove: (repo: Repository) => void
  onReject: (repo: Repository) => void
  onOnline: (repo: Repository) => void
  onOffline: (repo: Repository) => void
  onDelete: (id: string) => void
  onViewDetail: (repo: Repository) => void
}

/** 「所有仓库」表格列（含按状态变化的审核 / 上下线操作列） */
export function createRepoColumns({
  onApprove,
  onReject,
  onOnline,
  onOffline,
  onDelete,
  onViewDetail,
}: RepoColumnDeps) {
  return [
    {
      title: '图标',
      key: 'logo',
      width: 70,
      render: (_: any, record: Repository) => (
        <RepoLogo logoUrl={record.logo_url} repoType={record.type} size={40} />
      ),
    },
    {
      title: '仓库名称',
      dataIndex: 'display_name',
      key: 'display_name',
      render: (_: any, record: Repository) => (
        <div>
          <div style={{ fontWeight: 500 }}>{record.display_name || record.name}</div>
          <div style={{ color: '#999', fontSize: 12 }}>{record.name}</div>
        </div>
      ),
    },
    {
      title: '所有者',
      dataIndex: ['owner', 'name'],
      key: 'owner',
      width: 120,
    },
    {
      title: '分类',
      dataIndex: 'type',
      key: 'type',
      width: 100,
      render: (type: string) => {
        const typeMap: Record<string, string> = {
          psychology: '心理',
          stock: '股票',
          ai: 'AI',
          translation: '翻译',
          vision: '视觉',
          custom: '自定义',
        }
        return <Tag>{typeMap[type] || type}</Tag>
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: getStatusTag,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 170,
      render: (time: string) => time ? new Date(time).toLocaleString('zh-CN') : '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 320,
      fixed: 'right' as const,
      render: (_: any, record: Repository) => {
        const actions = []

        // 待审核状态 - 可以批准或拒绝
        if (record.status === 'pending') {
          actions.push(
            <Button
              key="approve"
              type="link"
              size="small"
              icon={<CheckCircleOutlined />}
              onClick={() => onApprove(record)}
            >
              通过
            </Button>,
            <Button
              key="reject"
              type="link"
              size="small"
              danger
              icon={<CloseCircleOutlined />}
              onClick={() => onReject(record)}
            >
              拒绝
            </Button>
          )
        }

        // 已审核状态 - 可以上线
        if (record.status === 'approved') {
          actions.push(
            <Button
              key="online"
              type="link"
              size="small"
              icon={<ArrowUpOutlined />}
              onClick={() => onOnline(record)}
            >
              上线
            </Button>
          )
        }

        // 已上线状态 - 可以下线
        if (record.status === 'online') {
          actions.push(
            <Button
              key="offline"
              type="link"
              size="small"
              danger
              icon={<ArrowDownOutlined />}
              onClick={() => onOffline(record)}
            >
              下线
            </Button>
          )
        }

        // 已拒绝状态 - 可以重新审核
        if (record.status === 'rejected') {
          actions.push(
            <Button
              key="re-approve"
              type="link"
              size="small"
              icon={<CheckCircleOutlined />}
              onClick={() => onApprove(record)}
            >
              重新审核
            </Button>
          )
        }

        // 已下线状态 - 可以上线
        if (record.status === 'offline') {
          actions.push(
            <Button
              key="re-online"
              type="link"
              size="small"
              icon={<ArrowUpOutlined />}
              onClick={() => onOnline(record)}
            >
              上线
            </Button>
          )
        }

        // 删除按钮
        actions.push(
          <Popconfirm
            key="delete"
            title="确认删除？"
            description="删除后无法恢复"
            onConfirm={() => onDelete(record.id)}
            okText="确认删除"
            cancelText="取消"
            okButtonProps={{ danger: true }}
          >
            <Button
              type="link"
              size="small"
              danger
              icon={<DeleteOutlined />}
            >
              删除
            </Button>
          </Popconfirm>
        )

        // 详情按钮
        actions.push(
          <Button
            key="detail"
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => onViewDetail(record)}
          >
            详情
          </Button>
        )

        return <Space size="small" wrap>{actions}</Space>
      },
    },
  ]
}

interface MyRepoColumnDeps {
  statsMap: RepoStatsMap
  onEditEndpoints: () => void
  onDelete: (id: string) => void
  onViewDetail: (repo: Repository) => void
}

/** 「我的仓库」表格列（含调用统计四列；管理员名下仓库的只读视角） */
export function createMyRepoColumns({
  statsMap,
  onEditEndpoints,
  onDelete,
  onViewDetail,
}: MyRepoColumnDeps) {
  return [
    {
      title: '图标',
      key: 'logo',
      width: 70,
      render: (_: any, record: Repository) => (
        <RepoLogo logoUrl={record.logo_url} repoType={record.type} size={40} />
      ),
    },
    {
      title: '仓库名称',
      dataIndex: 'display_name',
      key: 'display_name',
      render: (_: any, record: Repository) => (
        <div>
          <div style={{ fontWeight: 500 }}>{record.display_name || record.name}</div>
          <div style={{ color: '#999', fontSize: 12 }}>{record.name}</div>
        </div>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: getStatusTag,
    },
    {
      title: '总调用次数',
      key: 'total_calls',
      width: 130,
      render: (_: any, record: Repository) => {
        const stats = statsMap[record.id]
        return (
          <span style={{ color: stats?.total_calls > 0 ? '#1890ff' : '#999' }}>
            {(stats?.total_calls || 0).toLocaleString()} 次
          </span>
        )
      },
    },
    {
      title: '成功调用',
      key: 'successful_calls',
      width: 110,
      render: (_: any, record: Repository) => {
        const stats = statsMap[record.id]
        return (
          <span style={{ color: '#52c41a' }}>
            {(stats?.successful_calls || 0).toLocaleString()} 次
          </span>
        )
      },
    },
    {
      title: '失败调用',
      key: 'failed_calls',
      width: 110,
      render: (_: any, record: Repository) => {
        const stats = statsMap[record.id]
        return (
          <span style={{ color: stats?.failed_calls > 0 ? '#ff4d4f' : '#999' }}>
            {(stats?.failed_calls || 0).toLocaleString()} 次
          </span>
        )
      },
    },
    {
      title: '总收入',
      key: 'total_cost',
      width: 110,
      render: (_: any, record: Repository) => {
        const stats = statsMap[record.id]
        return (
          <span style={{ color: '#faad14', fontWeight: 500 }}>
            ¥{(stats?.total_cost || 0).toFixed(2)}
          </span>
        )
      },
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 170,
      render: (time: string) => time ? new Date(time).toLocaleString('zh-CN') : '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 220,
      fixed: 'right' as const,
      render: (_: any, record: Repository) => (
        <Space size="small" wrap>
          <Button
            type="primary"
            size="small"
            icon={<ApiOutlined />}
            onClick={onEditEndpoints}
          >
            编辑端点
          </Button>
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => onViewDetail(record)}
          >
            详情
          </Button>
          <Popconfirm
            title="确认删除？"
            description="删除后无法恢复"
            onConfirm={() => onDelete(record.id)}
            okText="确认删除"
            cancelText="取消"
            okButtonProps={{ danger: true }}
          >
            <Button
              type="link"
              size="small"
              danger
              icon={<DeleteOutlined />}
            >
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]
}
