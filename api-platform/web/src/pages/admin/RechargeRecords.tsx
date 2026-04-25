/**
 * 管理员充值明细页面
 * V2.6 新增
 */

import { useState, useEffect } from 'react'
import '../../styles/cyber-theme.css'
import { Card, Table, DatePicker, Select, Tag, Space, Typography, Row, Col, Statistic, Button, Input } from 'antd'
import { ReloadOutlined, SearchOutlined } from '@ant-design/icons'
import { adminReconciliationApi, RechargeRecordItem, RechargeSummary } from '../../api/adminReconciliation'
import { useErrorModal } from '../../components/ErrorModal'
import { useDevice } from '../../hooks/useDevice'
import styles from './RechargeRecords.module.css'

const { Title, Text } = Typography
const { RangePicker } = DatePicker

// 支付方式映射
const PAYMENT_METHOD_COLORS: Record<string, string> = {
  alipay: 'blue',
  wechat: 'green',
  bankcard: 'purple',
  paypal: 'cyan',
}

// 状态映射
const STATUS_CONFIG: Record<string, { color: string; text: string }> = {
  completed: { color: 'success', text: '已完成' },
  pending: { color: 'warning', text: '待支付' },
  failed: { color: 'error', text: '失败' },
  cancelled: { color: 'default', text: '已取消' },
}

export default function AdminRechargeRecords() {
  const { isMobile } = useDevice()
  const [loading, setLoading] = useState(false)
  const [records, setRecords] = useState<RechargeRecordItem[]>([])
  const [summary, setSummary] = useState<RechargeSummary | null>(null)
  const [pagination, setPagination] = useState({ page: 1, page_size: 20, total: 0, total_pages: 0 })
  
  // 筛选条件
  const [dateRange, setDateRange] = useState<[string, string] | null>(null)
  const [channel, setChannel] = useState<string | undefined>(undefined)
  const [status, setStatus] = useState<string | undefined>(undefined)
  const [searchKeyword, setSearchKeyword] = useState('')
  
  const { showError, ErrorModal: ErrorModalComponent } = useErrorModal()

  useEffect(() => {
    fetchRecords()
  }, [dateRange, channel, status, pagination.page, pagination.page_size])

  const fetchRecords = async () => {
    setLoading(true)
    try {
      const params: any = {
        page: pagination.page,
        page_size: pagination.page_size,
      }
      
      if (dateRange) {
        params.date = dateRange[0]
      }
      if (channel) {
        params.channel = channel
      }
      if (status) {
        params.status = status
      }
      
      const response = await adminReconciliationApi.getRechargeRecords(params)
      console.log('API Response:', response)
      if (response && typeof response === 'object') {
        setRecords(Array.isArray(response.items) ? response.items : [])
        setSummary(response.summary || null)
        setPagination(response.pagination || { page: 1, page_size: 20, total: 0, total_pages: 0 })
      } else {
        setRecords([])
        setSummary(null)
      }
    } catch (error: any) {
      showError(error, fetchRecords)
    } finally {
      setLoading(false)
    }
  }

  const handleTableChange = (newPagination: any) => {
    setPagination(prev => ({
      ...prev,
      page: newPagination.current,
      page_size: newPagination.pageSize,
    }))
  }

  // 过滤显示的记录
  const filteredRecords = searchKeyword
    ? records.filter(r => 
        r.payment_no.includes(searchKeyword) ||
        r.user_phone?.includes(searchKeyword) ||
        r.user_email?.includes(searchKeyword)
      )
    : records

  const columns = [
    {
      title: '订单号',
      dataIndex: 'payment_no',
      key: 'payment_no',
      width: 180,
      render: (text: string) => <Text code>{text}</Text>,
    },
    {
      title: '用户信息',
      key: 'user',
      width: 160,
      render: (_: any, record: RechargeRecordItem) => (
        <Space direction="vertical" size={0}>
          {record.user_phone && <Text>{record.user_phone}</Text>}
          {record.user_email && <Text type="secondary" style={{ fontSize: 12 }}>{record.user_email}</Text>}
        </Space>
      ),
    },
    {
      title: '充值金额',
      key: 'amount',
      width: 140,
      render: (_: any, record: RechargeRecordItem) => (
        <Space direction="vertical" size={0}>
          <Text strong style={{ color: '#52c41a' }}>¥{record.amount.toFixed(2)}</Text>
          {record.bonus_amount > 0 && (
            <Text type="warning" style={{ fontSize: 12 }}>+赠送¥{record.bonus_amount.toFixed(2)}</Text>
          )}
        </Space>
      ),
    },
    {
      title: '到账金额',
      dataIndex: 'total_amount',
      key: 'total_amount',
      width: 100,
      render: (amount: number) => <Text type="success">¥{amount.toFixed(2)}</Text>,
    },
    {
      title: '支付方式',
      dataIndex: 'payment_method_name',
      key: 'payment_method',
      width: 100,
      render: (name: string, record: RechargeRecordItem) => (
        <Tag color={PAYMENT_METHOD_COLORS[record.payment_method] || 'default'}>
          {name}
        </Tag>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (status: string) => {
        const config = STATUS_CONFIG[status] || { color: 'default', text: status }
        return <Tag color={config.color}>{config.text}</Tag>
      },
    },
    {
      title: '第三方流水号',
      dataIndex: 'transaction_id',
      key: 'transaction_id',
      width: 180,
      render: (text: string) => text ? <Text type="secondary" style={{ fontSize: 12 }}>{text}</Text> : '-',
    },
    {
      title: '环境',
      dataIndex: 'environment',
      key: 'environment',
      width: 80,
      render: (env: string) => (
        <Tag color={env === 'simulation' ? 'orange' : 'green'}>
          {env === 'simulation' ? '模拟' : '真实'}
        </Tag>
      ),
    },
    {
      title: '充值时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 170,
      render: (time: string) => new Date(time).toLocaleString('zh-CN'),
    },
    {
      title: '充值后余额',
      dataIndex: 'balance_after',
      key: 'balance_after',
      width: 110,
      render: (balance: number) => balance ? `¥${balance.toFixed(2)}` : '-',
    },
  ]

  // 移动端卡片列表渲染
  const renderCardList = () => (
    <div className={styles.cardList}>
      {filteredRecords.map((record) => {
        const statusConfig = STATUS_CONFIG[record.status] || { color: 'default', text: record.status }
        return (
          <Card key={record.id} className={styles.recordCard} size="small">
            <div className={styles.cardHeader}>
              <Space>
                <Tag color={PAYMENT_METHOD_COLORS[record.payment_method] || 'default'}>
                  {record.payment_method_name}
                </Tag>
                <Tag color={statusConfig.color}>{statusConfig.text}</Tag>
                <Tag color={record.environment === 'simulation' ? 'orange' : 'green'}>
                  {record.environment === 'simulation' ? '模拟' : '真实'}
                </Tag>
              </Space>
              <Text type="secondary" style={{ fontSize: 12 }}>
                {new Date(record.created_at).toLocaleString('zh-CN')}
              </Text>
            </div>
            <div className={styles.cardBody}>
              <div className={styles.cardRow}>
                <Text type="secondary">订单号：</Text>
                <Text code style={{ fontSize: 12 }}>{record.payment_no}</Text>
              </div>
              <div className={styles.cardRow}>
                <Text type="secondary">用户：</Text>
                <Text>{record.user_phone || record.user_email}</Text>
              </div>
              <div className={styles.cardRow}>
                <Text type="secondary">充值金额：</Text>
                <Text strong style={{ color: '#52c41a' }}>¥{record.amount.toFixed(2)}</Text>
                {record.bonus_amount > 0 && (
                  <Text type="warning" style={{ fontSize: 12 }}> +赠送¥{record.bonus_amount.toFixed(2)}</Text>
                )}
              </div>
              <div className={styles.cardRow}>
                <Text type="secondary">到账金额：</Text>
                <Text type="success">¥{record.total_amount.toFixed(2)}</Text>
              </div>
              {record.transaction_id && (
                <div className={styles.cardRow}>
                  <Text type="secondary">流水号：</Text>
                  <Text type="secondary" style={{ fontSize: 12 }}>{record.transaction_id}</Text>
                </div>
              )}
              {record.balance_after > 0 && (
                <div className={styles.cardRow}>
                  <Text type="secondary">余额：</Text>
                  <Text>¥{record.balance_after.toFixed(2)}</Text>
                </div>
              )}
            </div>
          </Card>
        )
      })}
      {filteredRecords.length === 0 && (
        <Card className={styles.recordCard} size="small">
          <div style={{ textAlign: 'center', padding: '40px 0', color: '#999' }}>
            暂无充值记录
          </div>
        </Card>
      )}
    </div>
  )

  return (
    <div className={`${styles.container} bamboo-bg-pattern`}>
      <ErrorModalComponent />

      <div className={styles.header}>
        <Title level={4}>充值明细</Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchRecords}>
            刷新
          </Button>
        </Space>
      </div>

      {/* 汇总统计 */}
      {summary && (
        <Card className={styles.summaryCard}>
          <Row gutter={[12, 12]}>
            <Col xs={24} sm={12} md={6}>
              <Statistic 
                title="总交易笔数" 
                value={summary.total_count}
                suffix="笔"
                valueStyle={{ fontSize: 20 }}
              />
              <Text type="secondary" style={{ fontSize: 12 }}>
                成功 {summary.success_count} | 待支付 {summary.pending_count}
              </Text>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Statistic 
                title="总充值金额" 
                value={summary.total_amount}
                precision={2}
                prefix="¥"
                valueStyle={{ color: '#1890ff', fontSize: 20 }}
              />
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Statistic 
                title="赠送金额" 
                value={summary.total_bonus}
                precision={2}
                prefix="¥"
                valueStyle={{ color: '#faad14', fontSize: 20 }}
              />
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Statistic 
                title="实际到账" 
                value={summary.total_receivable}
                precision={2}
                prefix="¥"
                valueStyle={{ color: '#52c41a', fontSize: 20 }}
              />
            </Col>
          </Row>
        </Card>
      )}

      {/* 筛选条件 */}
      <Card className={styles.filterCard}>
        <Space wrap size="middle">
          <Space size="small">
            <Text>日期：</Text>
            <DatePicker 
              onChange={(date, dateString) => {
                setDateRange(dateString ? [dateString as string, dateString as string] : null)
                setPagination(prev => ({ ...prev, page: 1 }))
              }}
              placeholder="选择日期"
            />
          </Space>
          <Space size="small">
            <Text>渠道：</Text>
            <Select
              allowClear
              placeholder="全部渠道"
              style={{ width: 110 }}
              value={channel}
              onChange={(value) => {
                setChannel(value)
                setPagination(prev => ({ ...prev, page: 1 }))
              }}
              options={[
                { label: '全部', value: undefined },
                { label: '支付宝', value: 'alipay' },
                { label: '微信支付', value: 'wechat' },
                { label: '银行卡', value: 'bankcard' },
              ]}
            />
          </Space>
          <Space size="small">
            <Text>状态：</Text>
            <Select
              allowClear
              placeholder="全部状态"
              style={{ width: 110 }}
              value={status}
              onChange={(value) => {
                setStatus(value)
                setPagination(prev => ({ ...prev, page: 1 }))
              }}
              options={[
                { label: '全部', value: undefined },
                { label: '已完成', value: 'completed' },
                { label: '待支付', value: 'pending' },
                { label: '失败', value: 'failed' },
              ]}
            />
          </Space>
          <Input
            placeholder="搜索订单号/手机/邮箱"
            prefix={<SearchOutlined />}
            style={{ width: 180 }}
            value={searchKeyword}
            onChange={(e) => setSearchKeyword(e.target.value)}
            allowClear
          />
        </Space>
      </Card>

      {/* 数据展示：移动端卡片列表，桌面端表格 */}
      {isMobile ? (
        <>
          {renderCardList()}
          {pagination.total > pagination.page_size && (
            <div style={{ textAlign: 'center', marginTop: 16 }}>
              <Button onClick={() => setPagination(prev => ({ ...prev, page: prev.page + 1 }))} loading={loading}>
                加载更多
              </Button>
            </div>
          )}
        </>
      ) : (
        <Card>
          <Table
            columns={columns}
            dataSource={filteredRecords}
            rowKey="id"
            loading={loading}
            size="small"
            pagination={{
              current: pagination.page,
              pageSize: pagination.page_size,
              total: pagination.total,
              showSizeChanger: true,
              showQuickJumper: true,
              showTotal: (total) => `共 ${total} 条记录`,
            }}
            onChange={handleTableChange}
            scroll={{ x: 1400 }}
          />
        </Card>
      )}
    </div>
  )
}
