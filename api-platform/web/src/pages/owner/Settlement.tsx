/**
 * 收益结算页面
 */

import { useState, useEffect } from 'react'
import '../../styles/cyber-theme.css'
import { Card, Row, Col, Statistic, Table, Typography, Button, message, Space, Tag, Tabs } from 'antd'
import { DollarOutlined, BankOutlined, AlipayOutlined, WechatOutlined } from '@ant-design/icons'
import { billingApi, Account, Bill } from '../../api/billing'
import dayjs from 'dayjs'
import styles from './Settlement.module.css'

const { Title, Text } = Typography

export default function OwnerSettlement() {
  const [loading, setLoading] = useState(false)
  const [account, setAccount] = useState<Account | null>(null)
  const [settlementBills, setSettlementBills] = useState<Bill[]>([])
  const [activeTab, setActiveTab] = useState('overview')

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    setLoading(true)
    try {
      // api.get 已返回 res.data，所以直接是对象
      const accountData = await billingApi.getAccount()
      setAccount(accountData)
      
      // 获取结算记录
      const billsData = await billingApi.getBills({ bill_type: 'settlement', page_size: 20 })
      setSettlementBills(billsData.items)
    } catch (error) {
      console.error('获取数据失败:', error)
    } finally {
      setLoading(false)
    }
  }

  const columns = [
    { 
      title: '时间', 
      dataIndex: 'created_at', 
      key: 'created_at',
      render: (date: string) => dayjs(date).format('YYYY-MM-DD HH:mm'),
    },
    { 
      title: '仓库', 
      dataIndex: 'repo_name', 
      key: 'repo_name',
    },
    { 
      title: '金额', 
      dataIndex: 'amount', 
      key: 'amount',
      render: (amount: number) => (
        <Text type="success" strong>+¥{amount.toFixed(2)}</Text>
      )
    },
    { 
      title: '描述', 
      dataIndex: 'description', 
      key: 'description',
    },
  ]

  return (
    <div className={`${styles.container} bamboo-bg-pattern`}>
      <Title level={4}>收益结算</Title>

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={8}>
          <Card className={styles.statCard}>
            <Statistic
              title="可结算余额"
              value={account?.total_revenue || 0}
              prefix={<DollarOutlined />}
              precision={2}
              suffix="元"
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card className={styles.statCard}>
            <Statistic
              title="冻结金额"
              value={account?.frozen_balance || 0}
              prefix={<BankOutlined />}
              precision={2}
              suffix="元"
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card className={styles.statCard}>
            <Statistic
              title="累计收益"
              value={account?.total_revenue || 0}
              prefix={<DollarOutlined />}
              precision={2}
              suffix="元"
            />
          </Card>
        </Col>
      </Row>

      <Card className={styles.actionCard}>
        <Space wrap size="middle">
          <Button type="primary" icon={<BankOutlined />}>
            银行卡转账
          </Button>
          <Button icon={<AlipayOutlined />}>
            支付宝
          </Button>
          <Button icon={<WechatOutlined />}>
            微信支付
          </Button>
        </Space>
        <Text type="secondary" className={styles.tip} style={{ marginTop: 12, display: 'block' }}>
          * 结算将在1-3个工作日内到账
        </Text>
      </Card>

      <Card title="结算记录" className={styles.tableCard}>
        <Table
          dataSource={settlementBills}
          columns={columns}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10 }}
        />
      </Card>
    </div>
  )
}
