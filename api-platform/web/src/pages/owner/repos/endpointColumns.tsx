/**
 * 「端点配置」表格列定义 + HTTP 方法配色 —— P1-4 巨型组件拆分（2026-09-17）
 *
 * 由 `../Repos.tsx` 抽出。为什么单独成文件、而不是塞进 `EndpointsTab.tsx`：
 *   `getMethodColor` 在页面里有**两处**消费方 —— 端点配置 Tab，以及「仓库详情」抽屉里的
 *   端点表格（`Repos.tsx` 第 653/730 行附近）。放在这里两边都能用。
 *   形态上也与既有的 `repoColumns.tsx`（同样导出列工厂 + 状态映射）保持一致。
 *
 * ⚠️ 列定义用**工厂函数**而不是模块级常量：操作列的按钮必须回调父组件（编辑 / 删除），
 *    写成常量就得反过来 import 组件 → **循环依赖**（见 docs/OPTIMIZATION_BACKLOG.md §2.25）。
 */
import { Button, Space, Tag, Typography } from 'antd'
import { TableProps } from 'antd'
import { Endpoint } from '../../../api/repo'

const { Text } = Typography

/** 获取 HTTP 方法对应的颜色 */
export function getMethodColor(method: string): string {
  const colors: Record<string, string> = {
    GET: 'green',
    POST: 'blue',
    PUT: 'orange',
    DELETE: 'red',
    PATCH: 'purple',
  }
  return colors[method] || 'default'
}

export interface EndpointColumnActions {
  onEdit: (record: Endpoint) => void
  onDelete: (record: Endpoint) => void
}

export const createEndpointColumns = ({
  onEdit,
  onDelete,
}: EndpointColumnActions): TableProps<Endpoint>['columns'] => [
  {
    title: '方法',
    dataIndex: 'method',
    key: 'method',
    width: 80,
    render: (method: string) => <Tag color={getMethodColor(method)}>{method}</Tag>,
  },
  {
    title: '路径',
    dataIndex: 'path',
    key: 'path',
    render: (path: string) => <Text code>{path}</Text>,
  },
  {
    title: '描述',
    dataIndex: 'description',
    key: 'description',
    ellipsis: true,
  },
  {
    title: 'RPM限制',
    dataIndex: 'rpm_limit',
    key: 'rpm_limit',
    width: 100,
    render: (v: number) => v || '-',
  },
  {
    title: '状态',
    dataIndex: 'enabled',
    key: 'enabled',
    width: 80,
    render: (enabled: boolean) => (
      <Tag color={enabled !== false ? 'green' : 'default'}>
        {enabled !== false ? '启用' : '禁用'}
      </Tag>
    ),
  },
  {
    title: '操作',
    key: 'action',
    width: 120,
    render: (_: unknown, record: Endpoint) => (
      <Space size="small">
        <Button size="small" onClick={() => onEdit(record)}>
          编辑
        </Button>
        <Button size="small" danger onClick={() => onDelete(record)}>
          删除
        </Button>
      </Space>
    ),
  },
]
