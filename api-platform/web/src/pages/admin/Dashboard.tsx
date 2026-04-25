/**
 * 管理员工作台 - 翠竹主题
 * 清新明亮的翡翠绿配色
 * V2.1 - 竹韵版
 */

import { Row, Col, Card, Statistic, Typography, Table, Tag, Space, Avatar } from 'antd'
import { 
  UserOutlined, 
  ShopOutlined, 
  LineChartOutlined, 
  DollarOutlined,
  SafetyCertificateOutlined,
  WarningOutlined,
  ThunderboltOutlined,
  DatabaseOutlined,
  ExclamationCircleOutlined,
  ArrowRightOutlined
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import dayjs from 'dayjs'
import { useState, useEffect } from 'react'
import { adminApi, userTypeMap } from '../../api/admin'
import styles from './Dashboard.module.css'
import '../../styles/cyber-theme.css'

const { Title, Text } = Typography

// 用户类型中文映射
const userTypeLabels: Record<string, string> = {
  super_admin: '超级管理员',
  admin: '管理员',
  owner: '所有者',
  developer: '开发者',
  user: '普通用户'
}

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
    { type: 'error', message: 'API Key sk_live_xxx 异常使用', time: '10分钟前' },
    { type: 'warning', message: '仓库 api-translate 响应超时率过高', time: '30分钟前' },
    { type: 'info', message: '新用户注册审核通过', time: '1小时前' },
  ]

  // 快捷入口
  const quickActions = [
    { icon: <UserOutlined />, title: '用户管理', desc: '管理系统用户', path: '/admin/users', color: 'violet' },
    { icon: <ShopOutlined />, title: '仓库管理', desc: '审核API仓库', path: '/admin/repos', color: 'gold' },
    { icon: <LineChartOutlined />, title: '数据分析', desc: '查看运营数据', path: '/admin/analytics', color: 'cinnabar' },
    { icon: <DatabaseOutlined />, title: '日志管理', desc: '系统日志', path: '/admin/logs', color: 'jade' },
  ]

  // 加载统计数据和用户列表
  useEffect(() => {
    const loadData = async () => {
      setLoading(true)
      setStatsLoading(true)
      try {
        const [statsRes, usersRes] = await Promise.all([
          adminApi.getStats(),
          adminApi.listUsers({ page: 1, page_size: 10 }).catch(() => ({ items: [] }))
        ])
        
        setSystemStats({
          totalUsers: statsRes.total_users || 0,
          todayNewUsers: statsRes.today_new_users || 0,
          totalRepos: statsRes.total_repos || 0,
          todayCalls: statsRes.today_calls || 0,
          totalRevenue: statsRes.total_revenue || 0,
          activeKeys: statsRes.total_api_keys || 0,
        })
        
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

  // 响应式列宽配置
  const columns = [
    { 
      title: '用户', 
      dataIndex: 'username',
      key: 'username',
      width: 150,
      ellipsis: true,
      render: (username: string, record: any) => (
        <Space size={8}>
          <Avatar 
            size={28} 
            style={{ 
              background: 'var(--gradient-cyber)',
              fontSize: 12,
              flexShrink: 0
            }}
          >
            {username?.charAt(0).toUpperCase() || 'U'}
          </Avatar>
          <div style={{ minWidth: 0, overflow: 'hidden' }}>
            <div style={{ fontWeight: 500, color: 'var(--text-primary)', whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>{username}</div>
            <div style={{ fontSize: 11, color: 'var(--text-secondary)', whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>{record.email}</div>
          </div>
        </Space>
      )
    },
    { 
      title: '类型', 
      dataIndex: 'user_type', 
      key: 'user_type', 
      width: 80,
      render: (t: string) => {
        const colorMap: Record<string, string> = {
          super_admin: '#c41d7f',
          admin: '#d46b08',
          owner: '#0958d9',
          developer: '#237804',
          user: '#595959'
        }
        return (
          <Tag color={colorMap[t] || '#595959'} style={{ fontSize: 11, marginInlineEnd: 0 }}>
            {userTypeLabels[t] || t}
          </Tag>
        )
      }
    },
    { 
      title: '注册时间', 
      dataIndex: 'created_at', 
      key: 'created_at', 
      width: 120,
      render: (d: string) => (
        <Text style={{ color: 'var(--text-secondary)', fontSize: 12, whiteSpace: 'nowrap' }}>
          {d ? dayjs(d).format('YYYY-MM-DD') : '-'}
        </Text>
      )
    },
  ]

  return (
    <div className={`${styles.dashboard} bamboo-bg-pattern`}>
      {/* 翠竹印章装饰 */}
      <div className="china-stamp">
        <svg viewBox="0 0 60 60" xmlns="http://www.w3.org/2000/svg">
          <rect x="5" y="5" width="50" height="50" fill="none" stroke="#059669" strokeWidth="2" rx="4"/>
          <rect x="10" y="10" width="40" height="40" fill="none" stroke="#059669" strokeWidth="0.5"/>
          <text x="30" y="38" textAnchor="middle" fontSize="14" fill="#059669" fontFamily="serif" fontWeight="bold">API</text>
          <text x="30" y="50" textAnchor="middle" fontSize="9" fill="#059669" fontFamily="serif">Manager</text>
        </svg>
      </div>

      {/* 页面标题 */}
      <div className={styles.header}>
        <div>
          <Title level={2} className="cyber-title">「控制台」</Title>
          <Text className="cyber-subtitle">API 管 理 平 台</Text>
        </div>
      </div>

      {/* 统计卡片区 */}
      <Row gutter={[20, 20]} className={styles.stats}>
        <Col xs={24} sm={12} lg={6}>
          <div 
            className={`cyber-stat-card card-violet ${styles.statCard}`} 
            onClick={() => navigate('/admin/users')}
          >
            <div className={`cyber-stat-icon icon-violet pulse-glow`}>
              <UserOutlined />
            </div>
            <Statistic
              title={<span style={{ color: 'var(--text-secondary)', fontSize: 12, letterSpacing: 1 }}>总用户数</span>}
              value={systemStats.totalUsers}
              valueStyle={{ color: 'var(--text-primary)', fontSize: 32, fontWeight: 700 }}
              suffix={<Text type="secondary" style={{ fontSize: 12 }}>+{systemStats.todayNewUsers} 今日</Text>}
            />
          </div>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <div 
            className={`cyber-stat-card card-gold ${styles.statCard}`} 
            onClick={() => navigate('/admin/repos')}
          >
            <div className={`cyber-stat-icon icon-gold`}>
              <ShopOutlined />
            </div>
            <Statistic
              title={<span style={{ color: 'var(--text-secondary)', fontSize: 12, letterSpacing: 1 }}>API仓库</span>}
              value={systemStats.totalRepos}
              valueStyle={{ color: 'var(--gold)', fontSize: 32, fontWeight: 700 }}
            />
          </div>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <div className={`cyber-stat-card card-cinnabar ${styles.statCard}`}>
            <div className={`cyber-stat-icon icon-cinnabar`}>
              <ThunderboltOutlined />
            </div>
            <Statistic
              title={<span style={{ color: 'var(--text-secondary)', fontSize: 12, letterSpacing: 1 }}>今日调用</span>}
              value={systemStats.todayCalls}
              valueStyle={{ color: 'var(--cinnabar)', fontSize: 32, fontWeight: 700 }}
              suffix={<Text style={{ color: 'var(--text-secondary)', fontSize: 12 }}>次</Text>}
            />
          </div>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <div className={`cyber-stat-card card-jade ${styles.statCard}`}>
            <div className={`cyber-stat-icon icon-jade`}>
              <DollarOutlined />
            </div>
            <Statistic
              title={<span style={{ color: 'var(--text-secondary)', fontSize: 12, letterSpacing: 1 }}>累计收入</span>}
              value={systemStats.totalRevenue}
              precision={2}
              valueStyle={{ color: 'var(--jade)', fontSize: 32, fontWeight: 700 }}
              suffix={<Text style={{ color: 'var(--text-secondary)', fontSize: 12 }}>元</Text>}
            />
          </div>
        </Col>
      </Row>

      {/* 快捷入口 */}
      <Row gutter={[20, 20]} className={styles.quickActions}>
        {quickActions.map((action, index) => (
          <Col xs={12} sm={6} key={index}>
            <div 
              className={`cyber-card-glow ${styles.quickCard} ${styles[`quickCard-${action.color}`]}`}
              onClick={() => navigate(action.path)}
            >
              <div className={styles.quickIcon}>{action.icon}</div>
              <div className={styles.quickInfo}>
                <div className={styles.quickTitle}>{action.title}</div>
                <div className={styles.quickDesc}>{action.desc}</div>
              </div>
              <ArrowRightOutlined className={styles.quickArrow} />
            </div>
          </Col>
        ))}
      </Row>

      {/* 主内容区 */}
      <Row gutter={[20, 20]}>
        {/* 最新用户表格 */}
        <Col xs={24} lg={16}>
          <Card 
            className={`cyber-card ${styles.tableCard}`}
            title={
              <Space>
                <SafetyCertificateOutlined style={{ color: 'var(--violet)' }} />
                <span style={{ color: 'var(--text-primary)' }}>最新注册用户</span>
              </Space>
            }
          >
            <Table
              dataSource={recentUsers}
              columns={columns}
              rowKey="id"
              pagination={false}
              loading={loading}
              locale={{ emptyText: '暂无数据' }}
              className="cyber-table"
              scroll={{ x: 350 }}
              size="small"
            />
          </Card>
        </Col>

        {/* 系统告警 */}
        <Col xs={24} lg={8}>
          <Card 
            className={`cyber-card ${styles.alertCard}`}
            title={
              <Space>
                <WarningOutlined style={{ color: 'var(--cinnabar)' }} />
                <span style={{ color: 'var(--text-primary)' }}>系统告警</span>
              </Space>
            }
          >
            {alerts.map((alert, index) => (
              <div key={index} className={`cyber-alert alert-${alert.type}`}>
                <Space align="start" size={12}>
                  <div className={`cyber-alert-icon`} style={{
                    background: alert.type === 'error' ? 'rgba(220, 38, 38, 0.15)' : 
                                 alert.type === 'warning' ? 'rgba(180, 83, 9, 0.15)' : 
                                 'rgba(37, 99, 235, 0.15)',
                    color: alert.type === 'error' ? 'var(--cinnabar)' : 
                           alert.type === 'warning' ? 'var(--gold)' : 
                           'var(--azure)'
                  }}>
                    {alert.type === 'error' ? <ExclamationCircleOutlined /> : 
                     alert.type === 'warning' ? <WarningOutlined /> : 
                     <SafetyCertificateOutlined />}
                  </div>
                  <div>
                    <div style={{ color: 'var(--text-primary)', fontSize: 14 }}>{alert.message}</div>
                    <div style={{ color: 'var(--text-muted)', fontSize: 12, marginTop: 4 }}>{alert.time}</div>
                  </div>
                </Space>
              </div>
            ))}
          </Card>
        </Col>
      </Row>

      {/* 底部装饰 */}
      <div className={styles.footer}>
        <Text type="secondary">
          API 管理平台 · 翠竹主题 · {dayjs().format('YYYY年MM月DD日')}
        </Text>
      </div>
    </div>
  )
}
