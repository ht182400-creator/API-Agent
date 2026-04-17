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
import styles from './Dashboard.module.css'

const { Title, Text } = Typography

export default function AdminDashboard() {
  const navigate = useNavigate()

  // 示例数据
  const systemStats = {
    totalUsers: 1250,
    todayNewUsers: 25,
    totalRepos: 156,
    todayCalls: 125000,
    totalRevenue: 125000,
    activeKeys: 3400,
  }

  const recentUsers = [
    { id: 1, email: 'user1@example.com', user_type: 'developer', created_at: dayjs().subtract(1, 'hour').toISOString() },
    { id: 2, email: 'user2@example.com', user_type: 'owner', created_at: dayjs().subtract(3, 'hour').toISOString() },
    { id: 3, email: 'user3@example.com', user_type: 'developer', created_at: dayjs().subtract(5, 'hour').toISOString() },
  ]

  const alerts = [
    { type: 'warning', message: '仓库 api-translate 响应超时率过高', time: '10分钟前' },
    { type: 'info', message: '新用户注册审核通过', time: '30分钟前' },
    { type: 'error', message: 'API Key sk_live_xxx 异常使用', time: '1小时前' },
  ]

  const columns = [
    { title: '邮箱', dataIndex: 'email', key: 'email' },
    { title: '类型', dataIndex: 'user_type', key: 'user_type', render: (t: string) => <Tag>{t}</Tag> },
    { title: '注册时间', dataIndex: 'created_at', key: 'created_at', render: (d: string) => dayjs(d).format('YYYY-MM-DD HH:mm') },
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
