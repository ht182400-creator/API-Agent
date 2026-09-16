/**
 * 「端点配置」Tab —— P1-4 巨型组件拆分（纯搬运，零行为改变）
 *
 * 由 `../Repos.tsx` 抽出（原占约 111 行）。内容：空态提示 + 添加按钮 +
 * 移动端卡片布局 / 桌面端表格布局（由 `isMobile` 决定，两条分支都保留）。
 *
 * ⚠️ 与拆分前的差异只有一处、且是**改进**：原先它是页面内定义的**闭包组件**
 *    （`const EndpointsTab = () => (...)`），每次父组件渲染都会产生一个新的组件类型
 *    → React 会把它当成"另一个组件"而**整棵子树卸载重建**（移动端卡片上的输入/滚动位置会丢）。
 *    现在改为模块级组件 + props 受控，类型稳定。
 *
 * ⚠️ 列定义与 `getMethodColor` 在 `./endpointColumns`：后者本页「仓库详情」抽屉也在用。
 */
import { Alert, Button, Card, Space, Table, Tag, Typography } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import { Endpoint } from '../../../api/repo'
import { createEndpointColumns, getMethodColor } from './endpointColumns'

const { Text } = Typography

export interface EndpointsTabProps {
  endpoints: Endpoint[]
  isMobile: boolean
  onAdd: () => void
  onEdit: (endpoint: Endpoint) => void
  onDelete: (endpoint: Endpoint) => void
}

export function EndpointsTab({ endpoints, isMobile, onAdd, onEdit, onDelete }: EndpointsTabProps) {
  const columns = createEndpointColumns({ onEdit, onDelete })

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Text type="secondary">配置仓库提供的所有API接口</Text>
        <Button type="primary" icon={<PlusOutlined />} onClick={onAdd}>
          添加端点
        </Button>
      </div>

      {endpoints.length === 0 ? (
        <Alert message="暂无API端点配置" description="点击上方按钮添加您的第一个API端点" type="info" showIcon />
      ) : isMobile ? (
        // 移动端：卡片布局
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {endpoints.map((endpoint) => (
            <Card
              key={endpoint.id || endpoint.path}
              size="small"
              style={{ borderRadius: 8, boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }}
              styles={{ body: { padding: 12 } }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
                <Tag color={getMethodColor(endpoint.method)}>{endpoint.method}</Tag>
                <Text code style={{ flex: 1, fontSize: 12, wordBreak: 'break-all' }}>{endpoint.path}</Text>
              </div>
              {endpoint.description && (
                <div style={{ fontSize: 12, color: '#666', marginBottom: 8 }}>
                  描述：{endpoint.description}
                </div>
              )}
              <div style={{ fontSize: 12, color: '#666', marginBottom: 8 }}>
                <Space size={16}>
                  <span>RPM限制：{endpoint.rpm_limit || '-'}</span>
                  <span>RPH限制：{endpoint.rph_limit || '-'}</span>
                </Space>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid #f0f0f0', paddingTop: 8 }}>
                <Tag color={endpoint.enabled !== false ? 'green' : 'default'}>
                  {endpoint.enabled !== false ? '启用' : '禁用'}
                </Tag>
                <Space size="small">
                  <Button size="small" onClick={() => onEdit(endpoint)}>编辑</Button>
                  <Button size="small" danger onClick={() => onDelete(endpoint)}>删除</Button>
                </Space>
              </div>
            </Card>
          ))}
        </div>
      ) : (
        // 桌面端：表格布局
        <Table
          dataSource={endpoints}
          rowKey={(record) => record.id || record.path}
          pagination={false}
          size="small"
          columns={columns}
        />
      )}
    </div>
  )
}
