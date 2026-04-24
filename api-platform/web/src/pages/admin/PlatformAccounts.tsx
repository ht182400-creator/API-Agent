/**
 * 管理员平台账户余额页面
 * V2.6 新增
 */

import { useState, useEffect } from 'react'
import '../../styles/cyber-theme.css'
import { Card, Row, Col, Statistic, Tag, Space, Typography, Spin, Button, Modal, Form, Input, message } from 'antd'
import { 
  AlipayOutlined, 
  WechatOutlined, 
  CreditCardOutlined, 
  ReloadOutlined,
  EditOutlined,
  CheckCircleOutlined,
  LockOutlined
} from '@ant-design/icons'
import { adminReconciliationApi, PlatformAccountItem } from '../../api/adminReconciliation'
import { useErrorModal } from '../../components/ErrorModal'
import styles from './PlatformAccounts.module.css'

const { Title, Text } = Typography

// 渠道图标映射
const CHANNEL_ICONS: Record<string, React.ReactNode> = {
  alipay: <AlipayOutlined style={{ fontSize: 36, color: '#1677FF' }} />,
  wechat: <WechatOutlined style={{ fontSize: 36, color: '#07C160' }} />,
  bankcard: <CreditCardOutlined style={{ fontSize: 36, color: '#722ED1' }} />,
}

export default function AdminPlatformAccounts() {
  const [loading, setLoading] = useState(false)
  const [accounts, setAccounts] = useState<PlatformAccountItem[]>([])
  const [totalBalance, setTotalBalance] = useState(0)
  const [totalFrozen, setTotalFrozen] = useState(0)
  const [totalAvailable, setTotalAvailable] = useState(0)
  const [editModalVisible, setEditModalVisible] = useState(false)
  const [editingAccount, setEditingAccount] = useState<PlatformAccountItem | null>(null)
  const [form] = Form.useForm()
  
  const { showError, ErrorModal: ErrorModalComponent } = useErrorModal()

  useEffect(() => {
    fetchAccounts()
  }, [])

  const fetchAccounts = async () => {
    setLoading(true)
    try {
      const response = await adminReconciliationApi.getPlatformAccounts()
      setAccounts(response.accounts || [])
      setTotalBalance(response.total_balance || 0)
      setTotalFrozen(response.total_frozen || 0)
      setTotalAvailable(response.total_available || 0)
    } catch (error: any) {
      showError(error, fetchAccounts)
    } finally {
      setLoading(false)
    }
  }

  const handleEdit = (account: PlatformAccountItem) => {
    setEditingAccount(account)
    form.setFieldsValue({
      account_no: account.account_no,
      account_name: account.account_name,
      balance: account.balance,
      remark: account.remark,
    })
    setEditModalVisible(true)
  }

  const handleUpdate = async () => {
    try {
      const values = await form.validateFields()
      if (editingAccount) {
        await adminReconciliationApi.updatePlatformAccount(editingAccount.id, values)
        message.success('更新成功')
        setEditModalVisible(false)
        fetchAccounts()
      }
    } catch (error) {
      message.error('更新失败')
    }
  }

  const renderAccountCard = (account: PlatformAccountItem) => {
    return (
      <Card 
        key={account.id}
        className={styles.accountCard}
        actions={[
          <Button 
            type="text" 
            icon={<EditOutlined />} 
            onClick={() => handleEdit(account)}
            key="edit"
          >
            编辑
          </Button>,
        ]}
      >
        <div className={styles.cardHeader}>
          <Space>
            {CHANNEL_ICONS[account.channel]}
            <div>
              <Text strong style={{ fontSize: 16 }}>{account.channel_name}</Text>
              <br />
              <Text type="secondary" style={{ fontSize: 12 }}>
                {account.account_name || '未设置'}
              </Text>
            </div>
          </Space>
          <Tag color={account.status === 'active' ? 'success' : 'default'}>
            {account.status === 'active' ? '正常' : '停用'}
          </Tag>
        </div>

        <div className={styles.cardContent}>
          <div className={styles.balanceSection}>
            <Text type="secondary">账户余额</Text>
            <div className={styles.mainBalance}>
              ¥{account.balance.toFixed(2)}
            </div>
          </div>

          <Row gutter={16} className={styles.subBalances}>
            <Col span={12}>
              <Text type="secondary" style={{ fontSize: 12 }}>可用余额</Text>
              <div className={styles.subBalance}>
                ¥{account.available_balance.toFixed(2)}
              </div>
            </Col>
            <Col span={12}>
              <Text type="secondary" style={{ fontSize: 12 }}>冻结金额</Text>
              <div className={styles.subBalance}>
                ¥{account.frozen_balance.toFixed(2)}
              </div>
            </Col>
          </Row>

          {account.account_no && (
            <div className={styles.accountNo}>
              <Text type="secondary">账户号：</Text>
              <Text>{account.account_no}</Text>
            </div>
          )}

          {account.remark && (
            <div className={styles.remark}>
              <Text type="secondary">备注：</Text>
              <Text>{account.remark}</Text>
            </div>
          )}
        </div>
      </Card>
    )
  }

  if (loading) {
    return (
      <div className={styles.loadingContainer}>
        <Spin size="large" tip="加载中..." />
      </div>
    )
  }

  return (
    <div className={`${styles.container} bamboo-bg-pattern`}>
      <ErrorModalComponent />

      <div className={styles.header}>
        <Title level={4}>平台账户余额</Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchAccounts}>
            刷新
          </Button>
        </Space>
      </div>

      {/* 汇总卡片 */}
      <Card className={styles.summaryCard}>
        <Row gutter={24}>
          <Col span={8}>
            <Statistic
              title="总账户余额"
              value={totalBalance}
              precision={2}
              prefix="¥"
              valueStyle={{ color: '#1890ff', fontSize: 28 }}
            />
          </Col>
          <Col span={8}>
            <Statistic
              title="可用余额"
              value={totalAvailable}
              precision={2}
              prefix="¥"
              valueStyle={{ color: '#52c41a', fontSize: 28 }}
            />
          </Col>
          <Col span={8}>
            <Statistic
              title="冻结金额"
              value={totalFrozen}
              precision={2}
              prefix="¥"
              valueStyle={{ color: totalFrozen > 0 ? '#faad14' : '#999', fontSize: 28 }}
            />
          </Col>
        </Row>
      </Card>

      {/* 账户卡片 */}
      <Row gutter={[16, 16]}>
        {accounts.map(account => (
          <Col xs={24} sm={12} lg={8} key={account.id}>
            {renderAccountCard(account)}
          </Col>
        ))}
      </Row>

      {/* 提示 */}
      <Card className={styles.tipCard}>
        <Space>
          <LockOutlined style={{ color: '#1890ff' }} />
          <Text type="secondary">
            账户余额数据需从第三方支付平台同步。如需更新，请点击「编辑」手动修改账户配置信息。
          </Text>
        </Space>
      </Card>

      {/* 编辑弹窗 */}
      <Modal
        title="编辑平台账户"
        open={editModalVisible}
        onOk={handleUpdate}
        onCancel={() => setEditModalVisible(false)}
        okText="保存"
        cancelText="取消"
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="account_no"
            label="账户号"
            rules={[{ required: true, message: '请输入账户号' }]}
          >
            <Input placeholder="请输入第三方账户号" />
          </Form.Item>
          <Form.Item
            name="account_name"
            label="账户名称"
            rules={[{ required: true, message: '请输入账户名称' }]}
          >
            <Input placeholder="请输入账户名称" />
          </Form.Item>
          <Form.Item
            name="balance"
            label="账户余额"
          >
            <Input type="number" placeholder="请输入账户余额" prefix="¥" />
          </Form.Item>
          <Form.Item name="remark" label="备注">
            <Input.TextArea rows={3} placeholder="请输入备注信息" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
