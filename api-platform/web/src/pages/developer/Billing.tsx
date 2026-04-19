/**
 * 账单中心页面
 */

import { useState, useEffect } from 'react'
import { Row, Col, Card, Table, DatePicker, Select, Button, Typography, Statistic, Space, Tag, Empty } from 'antd'
import { 
  WalletOutlined, 
  RiseOutlined, 
  FallOutlined, 
  DownloadOutlined,
  ReloadOutlined 
} from '@ant-design/icons'
import { billingApi, Bill, Account, MonthlySummary } from '../../api/billing'
import { useErrorModal } from '../../components/ErrorModal'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import dayjs from 'dayjs'
import styles from './Billing.module.css'

const { Title, Text } = Typography
const { RangePicker } = DatePicker

const COLORS = ['#1677ff', '#52c41a', '#faad14', '#ff4d4f', '#722ed1']

export default function DeveloperBilling() {
  const [loading, setLoading] = useState(false)
  const [account, setAccount] = useState<Account | null>(null)
  const [bills, setBills] = useState<Bill[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [summary, setSummary] = useState<MonthlySummary | null>(null)
  const [balanceHistory, setBalanceHistory] = useState<any[]>([])

  // 使用统一的错误提示
  const { showError, closeError, ErrorModal: ErrorModalComponent } = useErrorModal()

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    setLoading(true)
    try {
      const [accountData, summaryData, historyData] = await Promise.all([
        billingApi.getAccount(),
        billingApi.getMonthlySummary(),
        billingApi.getBalanceHistory(30),
      ])

      setAccount(accountData)
      setSummary(summaryData)
      setBalanceHistory(historyData)
      fetchBills()
    } catch (error: any) {
      showError(error, () => fetchData())
    } finally {
      setLoading(false)
    }
  }

  const fetchBills = async (params?: any) => {
    try {
      // api.get 已返回 res.data，所以直接是 PaginatedResponse
      const data = await billingApi.getBills({ page, page_size: pageSize, ...params })
      setBills(data.items)
      setTotal(data.pagination.total)
    } catch (error: any) {
      showError(error, () => fetchBills(params))
    }
  }

  const getBillTypeTag = (type: string) => {
    const map: Record<string, { color: string; text: string }> = {
      recharge: { color: 'green', text: '充值' },
      consumption: { color: 'red', text: '消费' },
      refund: { color: 'cyan', text: '退款' },
      freeze: { color: 'orange', text: '冻结' },
      unfreeze: { color: 'purple', text: '解冻' },
      settlement: { color: 'blue', text: '结算' },
    }
    const config = map[type] || { color: 'default', text: type }
    return <Tag color={config.color}>{config.text}</Tag>
  }

  const columns = [
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (date: string) => dayjs(date).format('YYYY-MM-DD HH:mm:ss'),
    },
    {
      title: '类型',
      dataIndex: 'bill_type',
      key: 'bill_type',
      width: 100,
      render: (type: string) => getBillTypeTag(type),
    },
    {
      title: '金额',
      dataIndex: 'amount',
      key: 'amount',
      width: 120,
      render: (amount: number) => (
        <Text type={amount >= 0 ? 'success' : 'danger'} strong>
          {amount >= 0 ? '+' : ''}{amount.toFixed(2)}
        </Text>
      ),
    },
    {
      title: '余额',
      dataIndex: 'balance_after',
      key: 'balance_after',
      width: 120,
      render: (balance: number) => `¥${balance.toFixed(2)}`,
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '仓库',
      dataIndex: 'repo_name',
      key: 'repo_name',
      width: 120,
      render: (name: string) => name || '-',
    },
  ]

  return (
    <div className={styles.container}>
      {/* 统一的错误提示组件 */}
      <ErrorModalComponent />

      <div className={styles.header}>
        <Title level={4}>账单中心</Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchData}>刷新</Button>
          <Button icon={<DownloadOutlined />}>导出</Button>
        </Space>
      </div>

      {/* 账户概览 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card className={styles.statCard}>
            <Statistic
              title="账户余额"
              value={account?.balance || 0}
              prefix={<WalletOutlined />}
              precision={2}
              suffix="元"
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className={styles.statCard}>
            <Statistic
              title="本月充值"
              value={summary?.total_recharge || 0}
              prefix={<RiseOutlined />}
              precision={2}
              suffix="元"
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className={styles.statCard}>
            <Statistic
              title="本月消费"
              value={summary?.total_consumption || 0}
              prefix={<FallOutlined />}
              precision={2}
              suffix="元"
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className={styles.statCard}>
            <Statistic
              title="本月调用"
              value={summary?.consumption_count || 0}
              suffix="次"
            />
          </Card>
        </Col>
      </Row>

      {/* 图表 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={16}>
          <Card title="余额变化趋势（近30天）" className={styles.chartCard}>
            {balanceHistory.length === 0 ? (
              <div style={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Empty description="暂无余额变化记录" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={balanceHistory}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    dataKey="date"
                    tickFormatter={(val) => dayjs(val).format('MM-DD')}
                  />
                  <YAxis />
                  <Tooltip 
                    labelFormatter={(val) => dayjs(val).format('YYYY-MM-DD')}
                    formatter={(value: number) => [`¥${value.toFixed(2)}`, '余额']}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="balance" 
                    stroke="#1677ff" 
                    strokeWidth={2}
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="消费分布" className={styles.pieCard}>
            {summary?.by_repository && summary.by_repository.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={summary.by_repository.slice(0, 5)}
                    dataKey="total"
                    nameKey="repo_name"
                    cx="50%"
                    cy="50%"
                    outerRadius={100}
                    label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
                  >
                    {summary.by_repository.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value: number) => `¥${value.toFixed(2)}`} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Empty description="暂无消费数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              </div>
            )}
          </Card>
        </Col>
      </Row>

      {/* 账单列表 */}
      <Card title="账单明细" className={styles.tableCard}>
        <Table
          dataSource={bills}
          columns={columns}
          rowKey="id"
          loading={loading}
          locale={{ emptyText: <Empty description="暂无账单记录" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
            onChange: (p, ps) => {
              setPage(p)
              setPageSize(ps)
            },
          }}
        />
      </Card>
    </div>
  )
}
