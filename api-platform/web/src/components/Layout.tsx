/**
 * 主布局组件
 * 根据用户类型显示不同的菜单和界面
 */

import { useState, useEffect, useCallback } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Layout as AntLayout, Menu, Avatar, Dropdown, Badge, Space, Typography, Tag } from 'antd'
import {
  DashboardOutlined,
  KeyOutlined,
  PieChartOutlined,
  FileTextOutlined,
  WalletOutlined,
  ShopOutlined,
  BarChartOutlined,
  DollarOutlined,
  UserOutlined,
  SettingOutlined,
  LogoutOutlined,
  BellOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  FolderOutlined,
  SafetyCertificateOutlined,
  TeamOutlined,
  ToolOutlined,
} from '@ant-design/icons'
import type { MenuProps } from 'antd'
import { useAuthStore } from '../stores/auth'
import { authApi } from '../api/auth'
import { notificationApi, Notification } from '../api/notification'
import styles from './Layout.module.css'

const { Header, Sider, Content } = AntLayout
const { Text } = Typography

// 用户类型显示配置
const userTypeConfig: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  super_admin: { label: '超级管理员', color: 'red', icon: <SafetyCertificateOutlined /> },
  admin: { label: '管理员', color: 'orange', icon: <ToolOutlined /> },
  owner: { label: '仓库所有者', color: 'blue', icon: <ShopOutlined /> },
  developer: { label: '开发者', color: 'green', icon: <KeyOutlined /> },
  user: { label: '普通用户', color: 'default', icon: <UserOutlined /> },
}

// 普通用户菜单（简化版，只能查看）
const userMenu: MenuProps['items'] = [
  { key: '/', icon: <DashboardOutlined />, label: '工作台' },
  { key: '/developer/quota', icon: <PieChartOutlined />, label: '配额使用' },
  { key: '/developer/billing', icon: <WalletOutlined />, label: '账单中心' },
]

// 开发者菜单
const developerMenu: MenuProps['items'] = [
  { key: '/', icon: <DashboardOutlined />, label: '工作台' },
  { key: '/developer/keys', icon: <KeyOutlined />, label: 'API Keys' },
  { key: '/developer/repos', icon: <ShopOutlined />, label: '仓库市场' },
  { key: '/developer/quota', icon: <PieChartOutlined />, label: '配额使用' },
  { key: '/developer/logs', icon: <FileTextOutlined />, label: '调用日志' },
  { key: '/developer/billing', icon: <WalletOutlined />, label: '账单中心' },
]

// 仓库所有者菜单（不包含开发者菜单，避免路由冲突）
const ownerMenu: MenuProps['items'] = [
  { key: '/owner', icon: <DashboardOutlined />, label: '工作台' },
  { key: '/owner/repos', icon: <ShopOutlined />, label: '仓库管理' },
  { key: '/owner/analytics', icon: <BarChartOutlined />, label: '数据分析' },
  { key: '/owner/settlement', icon: <DollarOutlined />, label: '收益结算' },
]

// 管理员菜单
const adminMenu: MenuProps['items'] = [
  { key: '/admin', icon: <DashboardOutlined />, label: '工作台' },
  { key: '/admin/users', icon: <TeamOutlined />, label: '用户管理' },
  { key: '/admin/repos', icon: <ShopOutlined />, label: '仓库管理' },
  { key: '/admin/logs', icon: <FolderOutlined />, label: '日志管理' },
  { key: '/admin/settings', icon: <SettingOutlined />, label: '系统设置' },
]

// 超级管理员菜单
const superAdminMenu: MenuProps['items'] = [
  { key: '/superadmin', icon: <DashboardOutlined />, label: '工作台' },
  { key: '/superadmin/users', icon: <TeamOutlined />, label: '全局用户' },
  { key: '/superadmin/roles', icon: <SafetyCertificateOutlined />, label: '角色权限' },
  { key: '/superadmin/system', icon: <SettingOutlined />, label: '系统配置' },
  { key: '/superadmin/audit', icon: <FileTextOutlined />, label: '审计日志' },
]

// 根据用户类型获取菜单
const getMenuItems = (userType: string): MenuProps['items'] => {
  switch (userType) {
    case 'super_admin':
      return superAdminMenu
    case 'admin':
      return adminMenu
    case 'owner':
      // 仓库所有者只能看到自己的菜单
      return ownerMenu
    case 'developer':
      // 开发者可以创建 API Keys
      return developerMenu
    case 'user':
    default:
      // 普通用户只能查看，不能创建 API Keys
      return userMenu
  }
}

export default function Layout() {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuthStore()
  const [collapsed, setCollapsed] = useState(false)
  const [loading, setLoading] = useState(true)
  const [unreadCount, setUnreadCount] = useState(0)
  const [recentNotifications, setRecentNotifications] = useState<Notification[]>([])
  const [notificationOpen, setNotificationOpen] = useState(false)


  // 获取未读通知数量
  const fetchUnreadCount = useCallback(async () => {
    try {
      const data = await notificationApi.getUnreadCount()
      setUnreadCount(data.unread_count)
    } catch (error) {
      console.error('获取未读数量失败:', error)
    }
  }, [])

  // 获取最近通知
  const fetchRecentNotifications = useCallback(async () => {
    try {
      const data = await notificationApi.getRecent(5)
      setRecentNotifications(data)
    } catch (error) {
      console.error('获取最近通知失败:', error)
    }
  }, [])

  // 获取用户信息
  useEffect(() => {
    const fetchUser = async () => {
      try {
        const userData = await authApi.me()
        useAuthStore.getState().setUser(userData)
      } catch (error) {
        console.error('获取用户信息失败:', error)
      } finally {
        setLoading(false)
      }
    }

    if (!user) {
      fetchUser()
    } else {
      setLoading(false)
    }
  }, [user])

  // 初始化获取通知数据
  useEffect(() => {
    if (user && !loading) {
      fetchUnreadCount()
      fetchRecentNotifications()
    }
  }, [user, loading, fetchUnreadCount, fetchRecentNotifications])

  // 标记单条通知已读
  const handleMarkAsRead = async (notificationId: string, e: React.MouseEvent) => {
    e.stopPropagation()
    try {
      await notificationApi.markAsRead(notificationId)
      fetchUnreadCount()
      fetchRecentNotifications()
    } catch (error) {
      console.error('标记已读失败:', error)
    }
  }

  // 全部已读
  const handleMarkAllAsRead = async () => {
    // 检查是否有未读
    if (unreadCount === 0) {
      return // 没有未读，不需要操作
    }
    try {
      await notificationApi.markAllAsRead()
      fetchUnreadCount()
      fetchRecentNotifications()
    } catch (error) {
      console.error('标记全部已读失败:', error)
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
    return date.toLocaleDateString()
  }

  // 处理登出
  const handleLogout = async () => {
    try {
      await authApi.logout()
    } catch (error) {
      console.error('登出失败:', error)
    } finally {
      // 清除所有敏感数据
      logout()
      
      // 清除剪贴板（防止密码被复制）
      try {
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText('').catch(() => {})
        }
      } catch (e) {
        // 忽略剪贴板错误
      }
      
      // 清除 sessionStorage
      try {
        sessionStorage.clear()
      } catch (e) {
        // 忽略 sessionStorage 错误
      }
      
      // 清除可能的密码自动填充数据
      const passwordInputs = document.querySelectorAll('input[type="password"]')
      passwordInputs.forEach((input) => {
        if (input instanceof HTMLInputElement) {
          input.value = ''
        }
      })
      
      // 延迟跳转，让敏感数据有更多时间被清除
      setTimeout(() => {
        navigate('/login', { replace: true })
      }, 100)
    }
  }

  // 用户菜单
  const userMenuItems: MenuProps['items'] = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: '个人中心',
      onClick: () => navigate('/profile'),
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: '账号设置',
      onClick: () => navigate('/settings'),
    },
    { type: 'divider' },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
    },
  ]

  const handleUserMenuClick: MenuProps['onClick'] = ({ key }) => {
    if (key === 'logout') {
      handleLogout()
    }
  }

  // 当前选中的菜单
  const selectedKeys = location.pathname
  const firstLevelPath = '/' + selectedKeys.split('/')[1]
  
  // 获取用户类型配置
  const userTypeInfo = user ? userTypeConfig[user.user_type] || userTypeConfig.user : userTypeConfig.user

  return (
    <AntLayout className={styles.layout}>
      <Sider
        trigger={null}
        collapsible
        collapsed={collapsed}
        width={220}
        className={styles.sider}
      >
        <div className={styles.logo}>
          {collapsed ? (
            <span className={styles.logoIcon}>API</span>
          ) : (
            <>
              <span className={styles.logoIcon}>API</span>
              <span className={styles.logoText}>Platform</span>
            </>
          )}
        </div>
        
        {/* 用户类型标签 */}
        {!collapsed && (
          <div className={styles.userTypeTag}>
            <Tag color={userTypeInfo.color} icon={userTypeInfo.icon}>
              {userTypeInfo.label}
            </Tag>
          </div>
        )}
        
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKeys]}
          defaultOpenKeys={[firstLevelPath]}
          items={getMenuItems(user?.user_type || 'user')}
          onClick={({ key }) => navigate(key)}
          className={styles.menu}
        />
      </Sider>
      
      <AntLayout>
        <Header className={styles.header}>
          <div className={styles.headerLeft}>
            {collapsed ? (
              <MenuUnfoldOutlined
                className={styles.trigger}
                onClick={() => setCollapsed(false)}
              />
            ) : (
              <MenuFoldOutlined
                className={styles.trigger}
                onClick={() => setCollapsed(true)}
              />
            )}
          </div>
          
          <div className={styles.headerRight}>
          <Dropdown
            trigger={['click']}
            placement="bottomRight"
            open={notificationOpen}
            onOpenChange={setNotificationOpen}
            overlay={
              <div 
                className={styles.notificationPanel}
                onClick={(e) => e.stopPropagation()}
              >
                <div className={styles.notificationHeader}>
                  <span>通知中心</span>
                  <span className={styles.notificationCount}>
                    {unreadCount > 0 ? `${unreadCount} 条未读` : '暂无未读'}
                  </span>
                </div>
                <div className={styles.notificationList}>
                  {recentNotifications.length === 0 ? (
                    <div className={styles.notificationEmpty}>暂无新通知</div>
                  ) : (
                    recentNotifications.map((notification) => (
                      <div 
                        key={notification.id} 
                        className={`${styles.notificationItem} ${styles.unread}`}
                        onClick={(e) => {
                          handleMarkAsRead(notification.id, e)
                          setNotificationOpen(false)
                          // 跳转到通知详情页
                          const basePath = user?.user_type === 'super_admin' ? '/superadmin' 
                            : user?.user_type === 'admin' ? '/admin' 
                            : user?.user_type === 'owner' ? '/owner' 
                            : ''
                          navigate(`${basePath}/notifications`)
                        }}
                      >
                        <div className={styles.notificationContent}>
                          <div className={styles.notificationTitle}>
                            {notification.title}
                          </div>
                          <div className={styles.notificationDesc}>
                            {notification.content.length > 50 
                              ? notification.content.substring(0, 50) + '...' 
                              : notification.content}
                          </div>
                          <div className={styles.notificationTime}>
                            {formatTime(notification.created_at)}
                          </div>
                        </div>
                        <div className={styles.unreadDot} />
                      </div>
                    ))
                  )}
                </div>
                <div className={styles.notificationFooter}>
                  {unreadCount > 0 && (
                    <span 
                      onClick={handleMarkAllAsRead}
                      className={styles.markAllRead}
                    >
                      全部已读
                    </span>
                  )}
                  <span 
                    onClick={() => {
                      setNotificationOpen(false)
                      const basePath = user?.user_type === 'super_admin' ? '/superadmin' 
                        : user?.user_type === 'admin' ? '/admin' 
                        : user?.user_type === 'owner' ? '/owner' 
                        : ''
                      navigate(`${basePath}/notifications`)
                    }}
                    className={styles.viewAll}
                  >
                    查看全部通知
                  </span>
                </div>
              </div>
            }
          >
            <Badge count={unreadCount} size="small" overflowCount={99}>
              <BellOutlined className={styles.headerIcon} />
            </Badge>
          </Dropdown>
            
            <Dropdown
              menu={{ items: userMenuItems, onClick: handleUserMenuClick }}
              placement="bottomRight"
            >
              <Space className={styles.userInfo}>
                <Avatar
                  size="small"
                  icon={<UserOutlined />}
                  src={user?.avatar_url}
                />
                <Text className={styles.username}>
                  {user?.username || user?.email?.split('@')[0] || 'User'}
                </Text>
                <Tag color={userTypeInfo.color} style={{ marginLeft: 8 }}>
                  {userTypeInfo.label}
                </Tag>
              </Space>
            </Dropdown>
          </div>
        </Header>
        
        <Content className={styles.content}>
          <Outlet />
        </Content>
      </AntLayout>
    </AntLayout>
  )
}
