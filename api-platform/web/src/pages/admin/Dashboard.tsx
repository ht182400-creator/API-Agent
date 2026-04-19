/**
 * 管理员工作台
 */

import { Row, Col, Card, Statistic, Typography, Table, Tag, Space } from 'antd'
import { 
  UserOutlined, 
  ShopOutlined, 
  LineChartOutlined, 
  DollarOutlined,
  SafetyCertificateOutlined,
  WarningOutlined
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import dayjs from 'dayjs'
import { useState, useEffect } from 'react'
import { adminApi, userTypeMap } from '../../api/admin'
import styles from './Dashboard.module.css'

const { Title, Text } = Typography

export default function AdminDashboard() {
  const navigate = useNavigate()
  const [recentUsers, setRecentUsers] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [statsLoading, setStatsLoading] = useState(true)

  // 统计数据
  const [systemStats, setSystemStats] = useState({
    totalUsers: 0,
    todayNewUsers: 0,
    totalRepos: 0,
    todayCalls: 0,
    totalRevenue: 0,
    activeKeys: 0,
  })

  const alerts = [
    { type: 'warning', message: '仓库 api-translate 响应超时率过高', time: '10分钟前' },
    { type: 'info', message: '新用户注册审核通过', time: '30分钟前' },
    { type: 'error', message: 'API Key sk_live_xxx 异常使用', time: '1小时前' },
  ]

  // 加载统计数据和用户列表
  useEffect(() => {
    const loadData = async () => {
      setLoading(true)
      setStatsLoading(true)
      try {
        // 并行加载统计数据和用户列表
        const [statsRes, usersRes] = await Promise.all([
          adminApi.getStats(),
          adminApi.listUsers({ page: 1, page_size: 10 }).catch(() => ({ items: [] }))
        ])
        
        // 更新统计数据
        setSystemStats({
          totalUsers: statsRes.total_users || 0,
          todayNewUsers: statsRes.today_new_users || 0,
          totalRepos: statsRes.total_repos || 0,
          todayCalls: statsRes.today_calls || 0,
          totalRevenue: statsRes.total_revenue || 0,
          activeKeys: statsRes.total_api_keys || 0,
        })
        
        // 更新用户列表
        if (usersRes.items) {
          setRecentUsers(usersRes.items)
        }
      } catch (err) {
        console.error('加载数据失败', err)
      } finally {
        setLoading(false)
        setStatsLoading(false)
      }
    }
    loadData()
  }, [])

  const columns = [
    { title: '用户名', dataIndex: 'username', key: 'username' },
    { title: '邮箱', dataIndex: 'email', key: 'email' },
    { 
      title: '类型', 
      dataIndex: 'user_type', 
      key: 'user_type', 
      render: (t: string) => {
        const config = userTypeMap[t] || { label: t, color: 'default' }
        return <Tag color={config.color}>{config.label}</Tag>
      }
    },
    { 
      title: '注册时间', 
      dataIndex: 'created_at', 
      key: 'created_at', 
      render: (d: string) => d ? dayjs(d).format('YYYY-MM-DD HH:mm') : '-' 
    },
  ]

  return (
    <div className={styles.dashboard}>
      <Title level={4}>管理后台</Title>

      <Row gutter={[16, 16]} className={styles.stats}>
        <Col xs={24} sm={12} lg={6}>
          <Card className={styles.statCard} onClick={() => navigate('/admin/users')}>
            <Statistic
              title="总用户数"
              value={systemStats.totalUsers}
              prefix={<UserOutlined />}
              suffix={<Text type="secondary">+{systemStats.todayNewUsers}今日</Text>}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className={styles.statCard} onClick={() => navigate('/admin/repos')}>
            <Statistic
              title="API仓库"
              value={systemStats.totalRepos}
              prefix={<ShopOutlined />}
              valueStyle={{ color: '#1677ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className={styles.statCard}>
            <Statistic
              title="今日调用"
              value={systemStats.todayCalls}
              prefix={<LineChartOutlined />}
              suffix="次"
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className={styles.statCard}>
            <Statistic
              title="累计收入"
              value={systemStats.totalRevenue}
              prefix={<DollarOutlined />}
              precision={2}
              suffix="元"
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={16}>
          <Card title="最新注册用户" className={styles.tableCard}>
            <Table
              dataSource={recentUsers}
              columns={columns}
              rowKey="id"
              pagination={false}
              loading={loading}
              locale={{ emptyText: '暂无数据' }}
            />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="系统告警" className={styles.alertCard}>
            {alerts.map((alert, index) => (
              <div key={index} className={styles.alertItem}>
                <Space>
                  {alert.type === 'warning' && <WarningOutlined style={{ color: '#faad14' }} />}
                  {alert.type === 'error' && <WarningOutlined style={{ color: '#ff4d4f' }} />}
                  {alert.type === 'info' && <SafetyCertificateOutlined style={{ color: '#1677ff' }} />}
                  <Text>{alert.message}</Text>
                </Space>
                <Text type="secondary" className={styles.alertTime}>{alert.time}</Text>
              </div>
            ))}
          </Card>
        </Col>
      </Row>
    </div>
  )
}
