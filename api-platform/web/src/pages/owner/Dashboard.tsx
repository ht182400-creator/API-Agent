/**
 * 仓库所有者工作台
 */

import { useState, useEffect } from 'react'
import { Row, Col, Card, Statistic, Typography, Space, Table, Tag } from 'antd'
import { 
  ShopOutlined, 
  BarChartOutlined, 
  DollarOutlined, 
  RiseOutlined,
  FallOutlined 
} from '@ant-design/icons'
import { repoApi, Repository, RepoStats } from '../../api/repo'
import { useNavigate } from 'react-router-dom'
import dayjs from 'dayjs'
import styles from './Dashboard.module.css'

const { Title, Text } = Typography

export default function OwnerDashboard() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [repos, setRepos] = useState<Repository[]>([])
  const [stats, setStats] = useState<Record<string, RepoStats>>({})

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    setLoading(true)
    try {
      // api.get 已返回 res.data，所以直接是 PaginatedResponse
      const data = await repoApi.getMyRepos({ page_size: 10 })
      setRepos(data.items)

      // 获取每个仓库的统计
      const statsMap: Record<string, RepoStats> = {}
      await Promise.all(
        data.items.map(async (repo) => {
          try {
            const repoStats = await repoApi.getStats(repo.id)
            statsMap[repo.id] = repoStats
          } catch (e) {}
        })
      )
      setStats(statsMap)
    } catch (error) {
      console.error('获取数据失败:', error)
    } finally {
      setLoading(false)
    }
  }

  // 计算汇总
  const totalCalls = Object.values(stats).reduce((acc, s) => acc + (s.total_calls || 0), 0)
  const todayCalls = Object.values(stats).reduce((acc, s) => acc + (s.today_calls || 0), 0)
  const totalRevenue = Object.values(stats).reduce((acc, s) => acc + (s.total_cost || 0), 0)

  const columns = [
    { 
      title: '仓库', 
      dataIndex: 'name', 
      key: 'name',
      render: (name: string, record: any) => (
        <Space direction="vertical" size={0}>
          <Text strong>{record.display_name || name}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>{name}</Text>
        </Space>
      )
    },
    { 
      title: '状态', 
      dataIndex: 'status', 
      key: 'status',
      render: (status: string) => {
        const statusMap: Record<string, { color: string; text: string }> = {
          pending: { color: 'orange', text: '待审核' },
          approved: { color: 'blue', text: '已审核（待上线）' },
          rejected: { color: 'red', text: '已拒绝' },
          online: { color: 'green', text: '已上线' },
          offline: { color: 'default', text: '已下线' },
        }
        const config = statusMap[status] || { color: 'default', text: status || '未知' }
        return <Tag color={config.color}>{config.text}</Tag>
      }
    },
    { 
      title: '今日调用', 
      key: 'today',
      render: (_: any, record: any) => stats[record.id]?.today_calls || 0
    },
    { 
      title: '本周调用', 
      key: 'week',
      render: (_: any, record: any) => stats[record.id]?.week_calls || 0
    },
    { 
      title: '总调用', 
      key: 'total',
      render: (_: any, record: any) => stats[record.id]?.total_calls || 0
    },
    { 
      title: '更新时间', 
      dataIndex: 'updated_at', 
      key: 'updated_at',
      render: (date: string) => dayjs(date).format('YYYY-MM-DD')
    },
  ]

  return (
    <div className={styles.dashboard}>
      <Title level={4}>仓库所有者工作台</Title>

      <Row gutter={[16, 16]} className={styles.stats}>
        <Col xs={24} sm={12} lg={6}>
          <Card className={styles.statCard}>
            <Statistic
              title="我的仓库"
              value={repos.length}
              prefix={<ShopOutlined />}
              valueStyle={{ color: '#1677ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className={styles.statCard}>
            <Statistic
              title="今日调用"
              value={todayCalls}
              prefix={<RiseOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className={styles.statCard}>
            <Statistic
              title="总调用量"
              value={totalCalls}
              prefix={<BarChartOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className={styles.statCard}>
            <Statistic
              title="累计收益"
              value={totalRevenue}
              prefix={<DollarOutlined />}
              precision={2}
              suffix="元"
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      <Card 
        title="我的仓库" 
        className={styles.tableCard}
        extra={
          <a onClick={() => navigate('/owner/repos')}>查看全部</a>
        }
      >
        <Table
          dataSource={repos}
          columns={columns}
          rowKey="id"
          loading={loading}
          pagination={false}
        />
      </Card>
    </div>
  )
}
