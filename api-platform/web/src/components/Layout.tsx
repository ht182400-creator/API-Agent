/**
 * 主布局组件
 */

import { useState, useEffect } from 'react'
import { Outlet, useNavigate, useLocation, useMatches } from 'react-router-dom'
import { Layout as AntLayout, Menu, Avatar, Dropdown, Badge, Space, Typography } from 'antd'
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
} from '@ant-design/icons'
import type { MenuProps } from 'antd'
import { useAuthStore } from '../stores/auth'
import { authApi } from '../api/auth'
import styles from './Layout.module.css'

const { Header, Sider, Content } = AntLayout
const { Text } = Typography

// 菜单配置
const getMenuItems = (userType: string): MenuProps['items'] => {
  const developerMenu: MenuProps['items'] = [
    { key: '/', icon: <DashboardOutlined />, label: '工作台' },
    { key: '/developer/keys', icon: <KeyOutlined />, label: 'API Keys' },
    { key: '/developer/quota', icon: <PieChartOutlined />, label: '配额使用' },
    { key: '/developer/logs', icon: <FileTextOutlined />, label: '调用日志' },
    { key: '/developer/billing', icon: <WalletOutlined />, label: '账单中心' },
  ]

  const ownerMenu: MenuProps['items'] = [
    { key: '/owner', icon: <DashboardOutlined />, label: '工作台' },
    { key: '/owner/repos', icon: <ShopOutlined />, label: '仓库管理' },
    { key: '/owner/analytics', icon: <BarChartOutlined />, label: '数据分析' },
    { key: '/owner/settlement', icon: <DollarOutlined />, label: '收益结算' },
  ]

  const adminMenu: MenuProps['items'] = [
    { key: '/admin', icon: <DashboardOutlined />, label: '工作台' },
    { key: '/admin/users', icon: <UserOutlined />, label: '用户管理' },
    { key: '/admin/repos', icon: <ShopOutlined />, label: '仓库管理' },
    { key: '/admin/logs', icon: <FolderOutlined />, label: '日志管理' },
    { key: '/admin/settings', icon: <SettingOutlined />, label: '系统设置' },
  ]

  switch (userType) {
    case 'admin':
      return [...developerMenu, { type: 'divider' }, ...adminMenu]
    case 'owner':
      return [...developerMenu, { type: 'divider' }, ...ownerMenu]
    default:
      return developerMenu
  }
}

export default function Layout() {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuthStore()
  const [collapsed, setCollapsed] = useState(false)
  const [loading, setLoading] = useState(true)

  // 获取用户信息
  useEffect(() => {
    const fetchUser = async () => {
      try {
        const { data } = await authApi.me()
        useAuthStore.getState().setUser(data)
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

  // 处理登出
  const handleLogout = async () => {
    try {
      await authApi.logout()
    } catch (error) {
      console.error('登出失败:', error)
    } finally {
      logout()
      navigate('/login')
    }
  }

  // 用户菜单
  const userMenuItems: MenuProps['items'] = [
    { key: 'profile', icon: <UserOutlined />, label: '个人中心' },
    { key: 'settings', icon: <SettingOutlined />, label: '设置' },
    { type: 'divider' },
    { key: 'logout', icon: <LogoutOutlined />, label: '退出登录' },
  ]

  const handleUserMenuClick: MenuProps['onClick'] = ({ key }) => {
    if (key === 'logout') {
      handleLogout()
    }
  }

  // 当前选中的菜单
  const selectedKeys = location.pathname
  const openKeys = ['/'].includes(selectedKeys) ? ['/'] : ['/' + selectedKeys.split('/')[1]]

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
        
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKeys]}
          defaultOpenKeys={openKeys}
          items={getMenuItems(user?.user_type || 'developer')}
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
            <Badge count={5} size="small">
              <BellOutlined className={styles.headerIcon} />
            </Badge>
            
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
                <Text className={styles.username}>{user?.email?.split('@')[0]}</Text>
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
