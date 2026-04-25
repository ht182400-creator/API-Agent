/**
 * 响应式数据展示组件
 * 桌面端：表格模式
 * 移动端：卡片列表模式
 */

import React from 'react'
import { Table, Card, Tag, Avatar, Space, Button, Typography, Pagination, Spin } from 'antd'
import { useDevice } from '../hooks/useDevice'
import type { ColumnsType } from 'antd/es/table'

const { Text } = Typography

interface CardField {
  label: string
  dataIndex: string
  render?: (value: any, record: any) => React.ReactNode
}

interface ResponsiveTableProps<T = any> {
  dataSource: T[]
  columns: ColumnsType<T>
  rowKey: string | ((record: T) => string)
  loading?: boolean
  // 卡片模式配置
  cardConfig?: {
    titleField: string           // 卡片标题字段
    subtitleField?: string       // 卡片副标题字段
    avatarField?: string         // 头像字段（取第一个字符作为头像）
    tagField?: string            // 标签字段
    tagColorMap?: Record<string, string>  // 标签颜色映射
    fields?: CardField[]         // 自定义字段列表
    actionText?: string          // 操作按钮文字
    onAction?: (record: T) => void  // 操作按钮点击
    actionIcon?: React.ReactNode // 操作按钮图标
    showId?: boolean             // 是否显示ID（截断显示）
  }
  // 分页配置
  pagination?: {
    current: number
    pageSize: number
    total: number
    onChange: (page: number, pageSize: number) => void
  }
  // 桌面端表格滚动宽度
  scrollX?: number
  // 自定义卡片类名
  cardClassName?: string
  // 空状态文本
  emptyText?: string
}

/**
 * 响应式数据表格组件
 * 移动端自动切换为卡片列表
 */
export default function ResponsiveTable<T extends { id?: string }>({
  dataSource,
  columns,
  rowKey,
  loading = false,
  cardConfig,
  pagination,
  scrollX = 800,
  cardClassName,
  emptyText = '暂无数据',
}: ResponsiveTableProps<T>) {
  const { isMobile } = useDevice()

  // 移动端卡片列表渲染
  if (isMobile && cardConfig) {
    return (
      <div className={cardClassName}>
        <Spin spinning={loading}>
          {dataSource.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px 0', color: '#999' }}>
              {emptyText}
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {dataSource.map((record) => {
                const recordKey = typeof rowKey === 'function' ? rowKey(record) : record[rowKey as keyof T] as unknown as string
                const title = record[cardConfig.titleField as keyof T] as string
                const subtitle = cardConfig.subtitleField ? record[cardConfig.subtitleField as keyof T] as string : undefined
                const avatarChar = title?.charAt(0).toUpperCase() || 'U'
                const tagValue = cardConfig.tagField ? record[cardConfig.tagField as keyof T] as string : undefined
                const tagColor = tagValue && cardConfig.tagColorMap ? cardConfig.tagColorMap[tagValue] : undefined

                return (
                  <Card
                    key={recordKey}
                    size="small"
                    style={{ borderRadius: 8, boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }}
                    bodyStyle={{ padding: 12 }}
                  >
                    {/* 卡片头部：头像 + 标题 + 标签 */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
                      <Avatar
                        size={40}
                        style={{ background: 'var(--gradient-cyber)', flexShrink: 0 }}
                      >
                        {avatarChar}
                      </Avatar>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <Text strong style={{ display: 'block', fontSize: 15, lineHeight: 1.3 }}>
                          {title}
                        </Text>
                        {subtitle && (
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            {subtitle}
                          </Text>
                        )}
                      </div>
                      {tagValue && (
                        <Tag color={tagColor} style={{ marginInlineEnd: 0 }}>
                          {tagValue}
                        </Tag>
                      )}
                    </div>

                    {/* 卡片详情字段 */}
                    {cardConfig.fields && cardConfig.fields.length > 0 && (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: 12 }}>
                        {cardConfig.fields.map((field, idx) => (
                          <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            <Text type="secondary" style={{ flexShrink: 0 }}>{field.label}：</Text>
                            <div style={{ overflow: 'hidden' }}>
                              {field.render
                                ? field.render(record[field.dataIndex as keyof T], record)
                                : field.dataIndex === 'id' && cardConfig.showId
                                  ? <Text code style={{ fontSize: 10 }}>{(record[field.dataIndex as keyof T] as string)?.slice(0, 12)}...</Text>
                                  : <Text>{String(record[field.dataIndex as keyof T] ?? '-')}</Text>
                              }
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* 操作按钮 */}
                    {cardConfig.onAction && (
                      <div style={{ marginTop: 12, borderTop: '1px solid #f0f0f0', paddingTop: 12 }}>
                        <Button
                          type="primary"
                          size="small"
                          icon={cardConfig.actionIcon}
                          onClick={() => cardConfig.onAction?.(record)}
                        >
                          {cardConfig.actionText || '查看详情'}
                        </Button>
                      </div>
                    )}
                  </Card>
                )
              })}
            </div>
          )}
        </Spin>

        {/* 分页 */}
        {pagination && pagination.total > 0 && (
          <div style={{ marginTop: 16, textAlign: 'center' }}>
            <Pagination
              current={pagination.current}
              pageSize={pagination.pageSize}
              total={pagination.total}
              onChange={pagination.onChange}
              size="small"
              showSizeChanger={false}
            />
          </div>
        )}
      </div>
    )
  }

  // 桌面端：普通表格
  return (
    <Table
      dataSource={dataSource}
      columns={columns}
      rowKey={rowKey}
      loading={loading}
      scroll={{ x: scrollX }}
      size="small"
      pagination={pagination ? {
        current: pagination.current,
        pageSize: pagination.pageSize,
        total: pagination.total,
        showSizeChanger: true,
        showQuickJumper: true,
        showTotal: (t) => `共 ${t} 条`,
        onChange: pagination.onChange,
      } : false}
      locale={{ emptyText }}
    />
  )
}
