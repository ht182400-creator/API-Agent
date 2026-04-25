/**
 * 账单中心页面
 * V2.6 更新：现代化UI设计，修复数据展示问题
 */

import { useState, useEffect } from 'react'
import '../../styles/cyber-theme.css'
import { Row, Col, Card, Table, Button, Typography, Statistic, Space, Tag, Empty, App, Alert } from 'antd'
import { 
  WalletOutlined, 
  RiseOutlined, 
  FallOutlined, 
  DownloadOutlined,
  ReloadOutlined,
  PlusOutlined,
  FieldTimeOutlined,
  PieChartOutlined,
  FileTextOutlined,
  HistoryOutlined,
  RocketOutlined
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { billingApi, Bill, Account, MonthlySummary } from '../../api/billing'
import { useErrorModal } from '../../components/ErrorModal'
import { useAuthStore } from '../../stores/auth'
import { useDevice } from '../../hooks/useDevice'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts'
import dayjs from 'dayjs'
import styles from './Billing.module.css'

const { Title, Text } = Typography

const COLORS = ['#1677ff', '#52c41a', '#faad14', '#ff4d4f', '#722ed1']

export default function DeveloperBilling() {
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const { isMobile } = useDevice()
  const [loading, setLoading] = useState(false)
  const [account, setAccount] = useState<Account | null>(null)
  const [bills, setBills] = useState<Bill[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [summary, setSummary] = useState<MonthlySummary | null>(null)
  const [balanceHistory, setBalanceHistory] = useState<any[]>([])
  const [mockMode, setMockMode] = useState<boolean>(true)

  const { showError, closeError, ErrorModal: ErrorModalComponent } = useErrorModal()
  
  // 判断是否是普通用户
  const isNormalUser = user?.user_type === 'user'

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

      setMockMode(accountData.mock_mode ?? true)
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
      consume: { color: 'red', text: '消费' },
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
          {amount >= 0 ? '+' : ''}¥{amount.toFixed(2)}
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
  ]

  // 计算消费分布数据
  const getConsumptionDistribution = () => {
    if (!summary?.by_repository || summary.by_repository.length === 0) {
      return []
    }
    return summary.by_repository.slice(0, 5).map((item, index) => ({
      name: item.repo_name || '未知',
      value: item.total,
      percent: summary.total_consumption > 0 
        ? ((item.total / summary.total_consumption) * 100).toFixed(1) 
        : '0'
    }))
  }

  const distributionData = getConsumptionDistribution()

  return (
    <div className={`${styles.container} bamboo-bg-pattern`}>
      <ErrorModalComponent />
      
      {/* 普通用户升级引导 */}
      {isNormalUser && (
        <Alert
          type="info"
          showIcon
          icon={<RocketOutlined />}
          message="升级为开发者，解锁更多功能"
          description="成为开发者后，您可以查看完整的消费统计、充值账户、管理账单等功能。"
          action={
            <Button type="primary" size="small" onClick={() => navigate('/user')}>
              前往升级
            </Button>
          }
          style={{ marginBottom: 16 }}
        />
      )}

      <div className={styles.header}>
        <div>
          <Space align="center">
            <Title level={4}>账单中心</Title>
            {mockMode ? (
              <Tag color="orange">模拟环境</Tag>
            ) : (
              <Tag color="green">生产环境</Tag>
            )}
          </Space>
        </div>
        <Space>
          <Button icon={<PlusOutlined />} type="primary" onClick={() => navigate('/developer/recharge')}>
            充值
          </Button>
          <Button icon={<ReloadOutlined />} onClick={fetchData}>刷新</Button>
        </Space>
      </div>

      {/* 账户概览 - 现代化卡片设计 */}
      <Row gutter={[16, 16]} className="mb-4">
        <Col xs={24} sm={12} lg={6}>
          <Card className={styles.statCard} style={{ borderTop: '3px solid #1677ff' }}>
            <div className={styles.statCardIcon} style={{ backgroundColor: '#e6f4ff' }}>
              <WalletOutlined style={{ color: '#1677ff', fontSize: 24 }} />
            </div>
            <Statistic
              title="账户余额"
              value={account?.balance || 0}
              precision={2}
              suffix="元"
              valueStyle={{ color: '#1677ff', fontSize: 24 }}
            />
            <div className={styles.statCardFooter}>
              {mockMode ? (
                <Tag color="orange">模拟模式</Tag>
              ) : (
                <Tag color="green">真实账户</Tag>
              )}
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className={styles.statCard} style={{ borderTop: '3px solid #52c41a' }}>
            <div className={styles.statCardIcon} style={{ backgroundColor: '#f6ffed' }}>
              <RiseOutlined style={{ color: '#52c41a', fontSize: 24 }} />
            </div>
            <Statistic
              title="本月充值"
              value={summary?.total_recharge || 0}
              precision={2}
              suffix="元"
              valueStyle={{ color: '#52c41a', fontSize: 24 }}
            />
            <div className={styles.statCardFooter}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                {dayjs().format('YYYY年MM月')}
              </Text>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className={styles.statCard} style={{ borderTop: '3px solid #ff4d4f' }}>
            <div className={styles.statCardIcon} style={{ backgroundColor: '#fff1f0' }}>
              <FallOutlined style={{ color: '#ff4d4f', fontSize: 24 }} />
            </div>
            <Statistic
              title="本月消费"
              value={summary?.total_consumption || 0}
              precision={2}
              suffix="元"
              valueStyle={{ color: '#ff4d4f', fontSize: 24 }}
            />
            <div className={styles.statCardFooter}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                共 {(summary?.consumption_count || 0).toLocaleString()} 次调用
              </Text>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className={styles.statCard} style={{ borderTop: '3px solid #722ed1' }}>
            <div className={styles.statCardIcon} style={{ backgroundColor: '#f9f0ff' }}>
              <FieldTimeOutlined style={{ color: '#722ed1', fontSize: 24 }} />
            </div>
            <Statistic
              title="本月调用"
              value={summary?.consumption_count || 0}
              suffix="次"
              valueStyle={{ color: '#722ed1', fontSize: 24 }}
            />
            <div className={styles.statCardFooter}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                平均 ¥{(summary?.consumption_count ? (summary.total_consumption / summary.consumption_count).toFixed(4) : '0.00')} / 次
              </Text>
            </div>
          </Card>
        </Col>
      </Row>

      {/* 图表区域 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={16}>
          <Card 
            title={
              <Space>
                <HistoryOutlined />
                <span>余额变化趋势（近30天）</span>
              </Space>
            } 
            className={styles.chartCard}
            extra={
              <Text type="secondary">
                当前余额: <Text strong>¥{(account?.balance || 0).toFixed(2)}</Text>
              </Text>
            }
          >
            {balanceHistory.length === 0 ? (
              <div style={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Empty description="暂无余额变化记录" image={Empty.PRESENTED_IMAGE_SIMPLE}>
                  <Button type="primary" onClick={() => navigate('/developer/recharge')}>
                    立即充值
                  </Button>
                </Empty>
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
                    dot={{ fill: '#1677ff', strokeWidth: 2 }}
                    activeDot={{ r: 6, fill: '#1677ff' }}
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card 
            title={
              <Space>
                <PieChartOutlined />
                <span>消费分布</span>
              </Space>
            }
            className={styles.pieCard}
          >
            {distributionData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={distributionData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    innerRadius={40}
                    paddingAngle={2}
                    label={({ name, percent }) => `${name} ${(Number(percent)).toFixed(0)}%`}
                    labelLine={false}
                  >
                    {distributionData.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value: number) => `¥${value.toFixed(2)}`} />
                  <Legend 
                    formatter={(value) => <span style={{ color: '#595959' }}>{value}</span>}
                  />
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
      <Card 
        title={
          <Space>
            <FileTextOutlined />
            <span>账单明细</span>
          </Space>
        } 
        className={styles.tableCard}
        extra={
          <Space>
            <Text type="secondary">共 {total} 条记录</Text>
            <Button 
              icon={<DownloadOutlined />} 
              onClick={() => {
                try {
                  billingApi.exportBills()
                } catch (error: any) {
                  showError(error, () => billingApi.exportBills())
                }
              }}
            >
              导出
            </Button>
          </Space>
        }
      >
        {isMobile ? (
          // 移动端：卡片列表
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {bills.map((bill) => (
              <Card key={bill.id} size="small" style={{ borderRadius: 8, boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }} bodyStyle={{ padding: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
                  {getBillTypeTag(bill.bill_type)}
                  <Text type={bill.amount >= 0 ? 'success' : 'danger'} strong style={{ marginLeft: 'auto' }}>
                    {bill.amount >= 0 ? '+' : ''}¥{bill.amount.toFixed(2)}
                  </Text>
                </div>
                <div style={{ fontSize: 12, color: '#666' }}>
                  <div>时间：{dayjs(bill.created_at).format('YYYY-MM-DD HH:mm')}</div>
                  <div>余额：¥{bill.balance_after.toFixed(2)}</div>
                  <div>描述：{bill.description || '-'}</div>
                </div>
              </Card>
            ))}
          </div>
        ) : (
          // 桌面端：表格
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
        )}
      </Card>
    </div>
  )
}
