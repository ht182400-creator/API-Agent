/**
 * 超级管理员仪表板
 * 数据从数据库获取
 */

import { useState, useEffect } from 'react'
import { Row, Col, Card, Statistic, Table, Tag, Progress, Typography, Space, Button } from 'antd'
import { 
  UserOutlined, 
  ShopOutlined, 
  DollarOutlined, 
  SafetyCertificateOutlined,
  SettingOutlined,
  TeamOutlined
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import styles from './SuperAdminDashboard.module.css'
import { dashboardApi, userTypeLabels, userTypeColors, RecentActivity } from '../../api/superadmin'

const { Title, Text } = Typography

export default function SuperAdminDashboard() {
  const navigate = useNavigate()
  const [stats, setStats] = useState<{
    totalUsers: number
    totalRepos: number
    totalRevenue: number
    activeUsers: number
    userTypeStats: { type: string; count: number }[]
  }>({
    totalUsers: 0,
    totalRepos: 0,
    totalRevenue: 0,
    activeUsers: 0,
    userTypeStats: [],
  })
  const [activities, setActivities] = useState<RecentActivity[]>([])
  const [loading, setLoading] = useState(true)
  const [activityLoading, setActivityLoading] = useState(true)

  // 加载统计数据
  useEffect(() => {
    loadStats()
    loadActivities()
  }, [])

  const loadStats = async () => {
    try {
      setLoading(true)
      const data = await dashboardApi.getStats()
      setStats({
        totalUsers: data.total_users,
        totalRepos: data.total_repos,
        totalRevenue: data.total_revenue,
        activeUsers: data.active_users,
        userTypeStats: data.user_type_stats || [],
      })
    } catch (error) {
      console.error('加载统计数据失败:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadActivities = async () => {
    try {
      setActivityLoading(true)
      const data = await dashboardApi.getRecentActivity(5)
      setActivities(data || [])
    } catch (error) {
      console.error('加载活动数据失败:', error)
    } finally {
      setActivityLoading(false)
    }
  }

  const columns = [
    { 
      title: '操作', 
      dataIndex: 'action', 
      key: 'action',
      render: (action: string) => {
        // 简化操作名称显示
        const actionMap: Record<string, string> = {
          'user:login': '登录',
          'user:logout': '登出',
          'user:create': '创建用户',
          'user:update': '更新用户',
          'user:delete': '删除用户',
          'user:role_change': '修改角色',
          'api_key:create': '创建API Key',
          'api_key:delete': '删除API Key',
          'repo:create': '创建仓库',
          'repo:approve': '审核仓库',
          'system:config_update': '系统配置',
          'billing:recharge': '账户充值',
        }
        return actionMap[action] || action
      }
    },
    { 
      title: '操作者', 
      dataIndex: 'username', 
      key: 'username', 
      render: (username: string) => (
        <Tag color={username === 'superadmin' ? 'red' : 'blue'}>
          {username || 'System'}
        </Tag>
      )
    },
    { 
      title: '对象', 
      dataIndex: 'description', 
      key: 'description',
      ellipsis: true,
    },
    { 
      title: '状态', 
      dataIndex: 'status', 
      key: 'status',
      render: (status: string) => (
        <Tag color={status === 'success' ? 'green' : 'red'}>
          {status === 'success' ? '成功' : '失败'}
        </Tag>
      )
    },
    { 
      title: '时间', 
      dataIndex: 'created_at', 
      key: 'created_at',
      render: (time: string) => {
        const date = new Date(time)
        const now = new Date()
        const diff = now.getTime() - date.getTime()
        const minutes = Math.floor(diff / 60000)
        const hours = Math.floor(diff / 3600000)
        const days = Math.floor(diff / 86400000)
        
        if (minutes < 60) return `${minutes}分钟前`
        if (hours < 24) return `${hours}小时前`
        return `${days}天前`
      }
    },
  ]

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <div>
          <Title level={2} className={styles.title}>
            <SafetyCertificateOutlined /> 超级管理员控制台
          </Title>
          <Text type="secondary">系统全局管理与监控</Text>
        </div>
        <Space>
          <Button type="primary" icon={<SettingOutlined />} onClick={() => navigate('/superadmin/system')}>
            系统设置
          </Button>
        </Space>
      </div>

      <Row gutter={16} className={styles.statsRow}>
        <Col xs={24} sm={12} lg={6}>
          <Card loading={loading}>
            <Statistic 
              title="总用户数" 
              value={stats.totalUsers} 
              prefix={<UserOutlined />} 
              valueStyle={{ color: '#3f8600' }} 
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card loading={loading}>
            <Statistic 
              title="活跃用户" 
              value={stats.activeUsers} 
              prefix={<TeamOutlined />} 
              suffix={<span style={{ fontSize: 14 }}>/ {stats.totalUsers}</span>} 
            />
            <Progress 
              percent={stats.totalUsers > 0 ? Math.round((stats.activeUsers / stats.totalUsers) * 100) : 0} 
              showInfo={false} 
              strokeColor="#52c41a" 
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card loading={loading}>
            <Statistic 
              title="API 仓库" 
              value={stats.totalRepos} 
              prefix={<ShopOutlined />} 
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card loading={loading}>
            <Statistic 
              title="平台总收入" 
              value={stats.totalRevenue} 
              prefix={<DollarOutlined />} 
              suffix="元" 
              precision={2}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col xs={24} lg={8}>
          <Card title="用户角色分布" className={styles.card} loading={loading}>
            {stats.userTypeStats.map((item, index) => (
              <div key={index} className={styles.roleItem}>
                <div className={styles.roleInfo}>
                  <Tag color={userTypeColors[item.type] || 'default'}>
                    {userTypeLabels[item.type] || item.type}
                  </Tag>
                  <span className={styles.roleCount}>{item.count} 人</span>
                </div>
                <Progress 
                  percent={stats.totalUsers > 0 ? Math.round((item.count / stats.totalUsers) * 100) : 0} 
                  showInfo={false} 
                />
              </div>
            ))}
            {stats.userTypeStats.length === 0 && (
              <Text type="secondary">暂无数据</Text>
            )}
          </Card>
        </Col>

        <Col xs={24} lg={16}>
          <Card 
            title="实时动态" 
            extra={<Button type="link" onClick={() => navigate('/superadmin/audit')}>查看全部</Button>} 
            className={styles.card}
            loading={activityLoading}
          >
            <Table 
              dataSource={activities} 
              columns={columns} 
              rowKey="id" 
              pagination={false} 
              size="small"
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={16} className={styles.quickActions}>
        <Col span={24}>
          <Card title="快捷管理">
            <Row gutter={16}>
              <Col xs={24} sm={8}>
                <Button block size="large" icon={<UserOutlined />} onClick={() => navigate('/superadmin/users')}>
                  用户管理
                </Button>
              </Col>
              <Col xs={24} sm={8}>
                <Button block size="large" icon={<SafetyCertificateOutlined />} onClick={() => navigate('/superadmin/roles')}>
                  角色权限
                </Button>
              </Col>
              <Col xs={24} sm={8}>
                <Button block size="large" icon={<SettingOutlined />} onClick={() => navigate('/superadmin/system')}>
                  系统配置
                </Button>
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>
    </div>
  )
}
