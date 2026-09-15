/**
 * 我的仓库表格列定义 —— P1-4 巨型组件拆分（纯搬运，零行为改变）
 *
 * 由 `../Repos.tsx` 抽出。这一块原先占主组件约 81 行，但**只依赖三个动作回调**
 * （查看详情 / 编辑 / 删除），与页面状态无关 → 依赖最少、适合先切。
 *
 * ⚠️ 用**工厂函数**而不是模块级常量：三个回调都来自组件内部，写成常量会形成反向依赖。
 *
 * ⚠️ 状态映射表 `statusMap` 目前**仍内联在本文件**（保持与拆分前完全一致）。
 *    它与 `admin/Analytics` 的 `analytics/constants.ts`、`admin/Repos` 内的映射表**三处重复**，
 *    后续可统一提到共享常量（拆分不夹带重构，故留待单独一轮）。
 */
import { Button, Popconfirm, Space, Tag, Typography } from 'antd'
import { repoStatusConfig } from '../../../config/repoStatus'
import {
  ApiOutlined,
  ThunderboltOutlined,
  EyeOutlined,
  EditOutlined,
  DeleteOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import { TableProps } from 'antd'
import { Repository } from '../../../api/repo'
import { RepoLogo } from '../../../components/RepoLogo'

const { Text } = Typography

export interface RepoColumnActions {
  onViewDetail: (record: Repository) => void
  onEdit: (record: Repository) => void
  onDelete: (repoId: string) => void
}

export const createRepoColumns = (actions: RepoColumnActions): TableProps<Repository>['columns'] => [
  {
    title: '图标',
    key: 'logo',
    width: 70,
    render: (_: unknown, record: Repository) => (
      <RepoLogo logoUrl={record.logo_url} repoType={record.type} size={40} />
    ),
  },
  {
    title: '仓库名称',
    dataIndex: 'name',
    key: 'name',
    render: (name: string, record: Repository) => (
      <Space direction="vertical" size={0}>
        <Text strong>{record.display_name || name}</Text>
        <Text type="secondary" style={{ fontSize: 12 }}>
          {name}
        </Text>
      </Space>
    ),
  },
  { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
  { title: '分类', dataIndex: 'type', key: 'type', render: (t: string) => <Tag>{t}</Tag> },
  {
    title: 'API端点',
    key: 'endpoints',
    render: (_: unknown, record: Repository) => (
      <Space>
        <Tag icon={<ApiOutlined />}>{record.endpoints?.length || 0} 个</Tag>
      </Space>
    ),
  },
  {
    title: '限流配置',
    key: 'limits',
    render: (_: unknown, record: Repository) => (
      <Space direction="vertical" size={0}>
        <Text style={{ fontSize: 12 }}>
          <ThunderboltOutlined /> {record.limits?.rpm || 1000}/分
        </Text>
        <Text type="secondary" style={{ fontSize: 12 }}>
          {record.limits?.rph || 10000}/时
        </Text>
      </Space>
    ),
  },
  {
    title: '状态',
    dataIndex: 'status',
    key: 'status',
    render: (status: string) => {
      // ⚠️ map 收敛到 src/config/repoStatus（owner 变体："已审核（待上线）"是提醒所有者的业务语义）
      const config = repoStatusConfig(status, 'owner')
      return <Tag color={config.color}>{config.text}</Tag>
    },
  },
  {
    title: '创建时间',
    dataIndex: 'created_at',
    key: 'created_at',
    render: (d: string) => dayjs(d).format('YYYY-MM-DD'),
  },
  {
    title: '操作',
    key: 'action',
    width: 280,
    render: (_: unknown, record: Repository) => (
      <Space size="small" wrap>
        <Button size="small" icon={<EyeOutlined />} onClick={() => actions.onViewDetail(record)}>
          详情
        </Button>
        <Button size="small" icon={<EditOutlined />} onClick={() => actions.onEdit(record)}>
          编辑
        </Button>
        <Popconfirm
          title="确认删除？"
          description="删除后无法恢复"
          onConfirm={() => actions.onDelete(record.id)}
        >
          <Button size="small" danger icon={<DeleteOutlined />}>
            删除
          </Button>
        </Popconfirm>
      </Space>
    ),
  },
]
