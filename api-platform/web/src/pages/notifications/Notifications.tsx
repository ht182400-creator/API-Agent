/**
 * 通知中心页面
 */

import { useState, useEffect, useCallback } from 'react'
import { Card, List, Tag, Typography, Space, Button, Empty, Tabs, message } from 'antd'
import { BellOutlined, CheckCircleOutlined, WarningOutlined, InfoCircleOutlined, DeleteOutlined } from '@ant-design/icons'
import { notificationApi, Notification } from '../../api/notification'
import styles from './Notifications.module.css'

const { Text } = Typography

// 获取通知图标
const getNotificationIcon = (type: string) => {
  switch (type) {
    case 'warning':
      return <WarningOutlined style={{ color: '#faad14', fontSize: 22 }} />
    case 'success':
      return <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 22 }} />
    case 'info':
    default:
      return <InfoCircleOutlined style={{ color: '#1677ff', fontSize: 22 }} />
  }
}

// 获取通知标签
const getNotificationTag = (type: string) => {
  switch (type) {
    case 'warning':
      return <Tag color="warning">警告</Tag>
    case 'success':
      return <Tag color="success">成功</Tag>
    case 'billing':
      return <Tag color="orange">账单</Tag>
    case 'api':
      return <Tag color="purple">API</Tag>
    case 'security':
      return <Tag color="red">安全</Tag>
    case 'info':
    default:
      return <Tag color="processing">通知</Tag>
  }
}

// 获取优先级标签
const getPriorityTag = (priority: string) => {
  switch (priority) {
    case 'urgent':
      return <Tag color="red">紧急</Tag>
    case 'high':
      return <Tag color="orange">高</Tag>
    case 'low':
      return <Tag color="default">低</Tag>
    default:
      return null
  }
}

// 格式化时间
const formatTime = (timeStr: string) => {
  const date = new Date(timeStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)
  
  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  if (hours < 24) return `${hours}小时前`
  if (days < 7) return `${days}天前`
  return date.toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' })
}

// 自定义通知项组件
const NotificationItem = ({ 
  item, 
  onMarkAsRead, 
  onDelete 
}: { 
  item: Notification
  onMarkAsRead: (id: string) => void
  onDelete: (id: string) => void
}) => (
  <div className={`${styles.notificationItem} ${item.status === 'unread' ? styles.unread : ''}`}>
    <div className={styles.itemContent}>
      <div className={styles.iconWrapper}>
        {getNotificationIcon(item.notification_type)}
      </div>
      <div className={styles.itemBody}>
        <div className={styles.itemHeader}>
          <span className={styles.itemTitle}>{item.title}</span>
          {getNotificationTag(item.notification_type)}
          {getPriorityTag(item.priority)}
          {item.status === 'unread' && <Tag color="blue">未读</Tag>}
        </div>
        <div className={styles.itemDesc}>{item.content}</div>
        <div className={styles.itemFooter}>
          <span className={styles.itemTime}>{formatTime(item.created_at)}</span>
          <Space size="small">
            {item.status === 'unread' && (
              <Button 
                type="link" 
                size="small" 
                onClick={() => onMarkAsRead(item.id)}
              >
                标记已读
              </Button>
            )}
            <Button 
              type="link" 
              size="small" 
              danger
              onClick={() => onDelete(item.id)}
            >
              删除
            </Button>
          </Space>
        </div>
      </div>
    </div>
  </div>
)

export default function Notifications() {
  const [loading, setLoading] = useState(false)
  const [allNotifications, setAllNotifications] = useState<Notification[]>([])
  const [unreadNotifications, setUnreadNotifications] = useState<Notification[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize] = useState(20)

  // 获取所有通知
  const fetchAllNotifications = useCallback(async () => {
    setLoading(true)
    try {
      const result = await notificationApi.getList({ page, page_size: pageSize })
      setAllNotifications(result.notifications)
      setTotal(result.total)
    } catch (error: any) {
      console.error('获取通知失败:', error)
      message.error(error?.userMessage || error?.message || '获取通知列表失败')
    } finally {
      setLoading(false)
    }
  }, [page, pageSize])

  // 获取未读通知
  const fetchUnreadNotifications = useCallback(async () => {
    try {
      const result = await notificationApi.getList({ status: 'unread', page_size: 100 })
      setUnreadNotifications(result.notifications)
    } catch (error: any) {
      console.error('获取未读通知失败:', error)
    }
  }, [])

  // 初始化加载
  useEffect(() => {
    fetchAllNotifications()
    fetchUnreadNotifications()
  }, [fetchAllNotifications, fetchUnreadNotifications])

  // 标记单条已读
  const handleMarkAsRead = async (id: string) => {
    try {
      await notificationApi.markAsRead(id)
      message.success('已标记为已读')
      fetchAllNotifications()
      fetchUnreadNotifications()
    } catch (error: any) {
      console.error('标记已读失败:', error)
      message.error(error?.userMessage || error?.message || '操作失败，请重试')
    }
  }

  // 标记全部已读
  const handleMarkAllAsRead = async () => {
    // 检查是否有未读通知
    if (unreadNotifications.length === 0) {
      message.info('暂无未读通知')
      return
    }
    try {
      await notificationApi.markAllAsRead()
      message.success('已全部标记为已读')
      fetchAllNotifications()
      fetchUnreadNotifications()
    } catch (error: any) {
      console.error('标记全部已读失败:', error)
      message.error(error?.userMessage || error?.message || '操作失败，请重试')
    }
  }

  // 删除通知
  const handleDelete = async (id: string) => {
    try {
      await notificationApi.delete(id)
      message.success('删除成功')
      fetchAllNotifications()
      fetchUnreadNotifications()
    } catch (error: any) {
      console.error('删除通知失败:', error)
      message.error(error?.userMessage || error?.message || '删除失败，请重试')
    }
  }

  // 删除所有已读
  const handleDeleteAllRead = async () => {
    // 检查是否有已读通知可以删除
    const readCount = total - unreadNotifications.length
    if (readCount === 0) {
      message.info('暂无已读通知可删除')
      return
    }
    try {
      await notificationApi.deleteAllRead()
      message.success('已删除所有已读通知')
      fetchAllNotifications()
      fetchUnreadNotifications()
    } catch (error: any) {
      console.error('删除已读通知失败:', error)
      message.error(error?.userMessage || error?.message || '操作失败，请重试')
    }
  }

  const items = [
    {
      key: 'all',
      label: `全部通知 (${total})`,
      children: (
        <div className={styles.listContainer}>
          {allNotifications.length === 0 ? (
            <Empty description="暂无通知" style={{ padding: '60px 0' }} />
          ) : (
            <>
              {allNotifications.map((item) => (
                <NotificationItem 
                  key={item.id} 
                  item={item}
                  onMarkAsRead={handleMarkAsRead}
                  onDelete={handleDelete}
                />
              ))}
              {total > pageSize && (
                <div className={styles.pagination}>
                  <Button onClick={() => setPage(p => p - 1)} disabled={page === 1}>
                    上一页
                  </Button>
                  <span className={styles.pageInfo}>第 {page} / {Math.ceil(total / pageSize)} 页</span>
                  <Button onClick={() => setPage(p => p + 1)} disabled={page >= Math.ceil(total / pageSize)}>
                    下一页
                  </Button>
                </div>
              )}
            </>
          )}
        </div>
      ),
    },
    {
      key: 'unread',
      label: `未读通知 (${unreadNotifications.length})`,
      children: (
        <div className={styles.listContainer}>
          {unreadNotifications.length === 0 ? (
            <Empty description="暂无未读通知" style={{ padding: '60px 0' }} />
          ) : (
            unreadNotifications.map((item) => (
              <NotificationItem 
                key={item.id} 
                item={item}
                onMarkAsRead={handleMarkAsRead}
                onDelete={handleDelete}
              />
            ))
          )}
        </div>
      ),
    },
  ]

  return (
    <div className={styles.notifications}>
      <Card
        title={
          <Space size="middle">
            <BellOutlined style={{ fontSize: 20 }} />
            <span>通知中心</span>
          </Space>
        }
        extra={
          <Space>
            <Button 
              type="link" 
              size="small"
              icon={<CheckCircleOutlined />}
              onClick={handleMarkAllAsRead}
            >
              全部已读
            </Button>
            <Button 
              type="link" 
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={handleDeleteAllRead}
            >
              删除已读
            </Button>
          </Space>
        }
        styles={{ body: { padding: 0 } }}
        loading={loading}
      >
        <Tabs 
          items={items} 
          defaultActiveKey="all" 
          style={{ padding: '0 24px' }}
        />
      </Card>
    </div>
  )
}
