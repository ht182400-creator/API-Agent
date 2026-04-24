/**
 * 充值中心页面
 * V2.5 新增
 */

import { useState, useEffect } from 'react'
import '../../styles/cyber-theme.css'
import { Card, Row, Col, Typography, Button, Tag, Empty, Spin, Modal, Radio, Space, message, Descriptions, Divider, Result, InputNumber, Alert } from 'antd'
import { 
  GiftOutlined, 
  CheckCircleOutlined, 
  WechatOutlined, 
  AlipayOutlined, 
  CreditCardOutlined,
  ReloadOutlined,
  ExclamationCircleOutlined,
  EditOutlined,
  RocketOutlined
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { paymentApi, RechargePackage, Payment, RechargeConfig } from '../../api/payment'
import { authApi } from '../../api/auth'
import { useErrorModal } from '../../components/ErrorModal'
import { useAuthStore } from '../../stores/auth'
import styles from './Recharge.module.css'
import '../../styles/payment-methods.css'

const { Title, Text, Paragraph } = Typography

// 支付方式配置
const PAYMENT_METHODS = [
  { value: 'wechat', label: '微信支付', icon: <WechatOutlined />, color: '#07C160' },
  { value: 'alipay', label: '支付宝', icon: <AlipayOutlined />, color: '#1677FF' },
  { value: 'bankcard', label: '银行卡', icon: <CreditCardOutlined />, color: '#722ED1' },
]

export default function DeveloperRecharge() {
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const [loading, setLoading] = useState(false)
  const [packages, setPackages] = useState<RechargePackage[]>([])
  const [selectedPackage, setSelectedPackage] = useState<RechargePackage | null>(null)
  const [paymentMethod, setPaymentMethod] = useState<string>('alipay')
  const [payModalVisible, setPayModalVisible] = useState(false)
  const [creatingOrder, setCreatingOrder] = useState(false)
  const [currentPayment, setCurrentPayment] = useState<Payment | null>(null)
  const [paySuccess, setPaySuccess] = useState(false)
  const [countdown, setCountdown] = useState(0)
  // 自定义金额
  const [showCustomAmount, setShowCustomAmount] = useState(false)
  const [customAmount, setCustomAmount] = useState<number | null>(null)
  const [rechargeConfig, setRechargeConfig] = useState<RechargeConfig | null>(null)

  const { showError, ErrorModal: ErrorModalComponent } = useErrorModal()
  
  // 判断是否是普通用户
  const isNormalUser = user?.user_type === 'user'

  useEffect(() => {
    fetchPackages()
    fetchConfig()
  }, [])

  // 倒计时刷新支付状态
  useEffect(() => {
    if (countdown > 0 && currentPayment && currentPayment.status === 'pending') {
      const timer = setTimeout(() => setCountdown(c => c - 1), 1000)
      return () => clearTimeout(timer)
    }
  }, [countdown, currentPayment])

  const fetchPackages = async () => {
    setLoading(true)
    try {
      const data = await paymentApi.getPackages()
      setPackages(data.filter(pkg => pkg.is_active))
    } catch (error: any) {
      showError(error, fetchPackages)
    } finally {
      setLoading(false)
    }
  }

  const fetchConfig = async () => {
    try {
      const config = await paymentApi.getConfig()
      setRechargeConfig(config)
    } catch (error) {
      console.error('获取充值配置失败', error)
    }
  }

  const handleSelectPackage = (pkg: RechargePackage) => {
    setSelectedPackage(pkg)
    setShowCustomAmount(false)
    setCustomAmount(null)
  }

  const handleCustomAmountSelect = () => {
    setSelectedPackage(null)
    setShowCustomAmount(true)
  }

  const handleCustomAmountChange = (value: number | null) => {
    setCustomAmount(value)
  }

  const handleCreateOrder = async () => {
    // 套餐充值
    if (selectedPackage) {
      setCreatingOrder(true)
      try {
        const payment = await paymentApi.createPayment({
          package_id: selectedPackage.id,
          payment_method: paymentMethod,
        })
        setCurrentPayment(payment)
        setPayModalVisible(true)
        setPaySuccess(false)
        setCountdown(60) // 60秒有效期
        message.success('订单创建成功')
      } catch (error: any) {
        showError(error, handleCreateOrder)
      } finally {
        setCreatingOrder(false)
      }
      return
    }

    // 自定义金额充值
    if (showCustomAmount && customAmount) {
      if (!rechargeConfig) {
        message.error('充值配置加载失败')
        return
      }
      if (customAmount < rechargeConfig.min_amount) {
        message.error(`最低充值金额为 ${rechargeConfig.min_amount} 元`)
        return
      }
      if (customAmount > rechargeConfig.max_amount) {
        message.error(`最高充值金额为 ${rechargeConfig.max_amount} 元`)
        return
      }

      setCreatingOrder(true)
      try {
        const payment = await paymentApi.createCustomRecharge(customAmount, paymentMethod)
        setCurrentPayment(payment)
        setPayModalVisible(true)
        setPaySuccess(false)
        setCountdown(60)
        message.success('订单创建成功')
      } catch (error: any) {
        showError(error, handleCreateOrder)
      } finally {
        setCreatingOrder(false)
      }
      return
    }

    message.warning('请选择充值套餐或输入自定义金额')
  }

  const handleOpenPay = async () => {
    if (!currentPayment) return
    
    const isMockMode = rechargeConfig?.mock_mode ?? true
    
    if (isMockMode) {
      // 模拟支付模式（开发环境）
      Modal.confirm({
        title: '模拟支付',
        icon: <ExclamationCircleOutlined />,
        content: (
          <div>
            <p>支付金额：<Text strong>¥{currentPayment.amount.toFixed(2)}</Text></p>
            <p>支付方式：{PAYMENT_METHODS.find(m => m.value === paymentMethod)?.label}</p>
            <Paragraph type="secondary">
              （开发环境：点击确认后自动完成支付）
            </Paragraph>
          </div>
        ),
        onOk: async () => {
          // 模拟支付成功 - 调用后端回调接口
          message.loading({ content: '支付处理中...', key: 'pay' })
          try {
            await paymentApi.mockPaymentCallback(currentPayment.payment_no)
            message.success({ content: '支付成功！', key: 'pay' })
            setPaySuccess(true)
            setCurrentPayment({ ...currentPayment, status: 'paid' })
          } catch (error) {
            message.error({ content: '支付处理失败', key: 'pay' })
          }
        },
      })
    } else {
      // 真实支付模式（生产环境）
      // 打开真实支付页面
      message.loading({ content: '获取支付链接...', key: 'payUrl' })
      try {
        const status = await paymentApi.getPaymentStatus(currentPayment.payment_no)
        if (status.pay_url) {
          window.open(status.pay_url, '_blank', 'width=800,height=600')
          message.success({ content: '支付页面已打开，请在页面中完成支付', key: 'payUrl' })
          setCountdown(600) // 10分钟有效期
        } else {
          message.error({ content: '支付链接生成失败，请稍后重试', key: 'payUrl' })
        }
      } catch (error) {
        message.error({ content: '获取支付状态失败', key: 'payUrl' })
      }
    }
  }

  const handlePayModalClose = () => {
    setPayModalVisible(false)
    // 注意：支付成功后的跳转已由 useEffect 处理，此处不需要重复逻辑
  }

  // 监听支付成功状态，自动刷新并跳转
  useEffect(() => {
    if (paySuccess) {
      if (isNormalUser) {
        // 普通用户升级后，刷新用户信息后跳转到用户控制台（不是 /developer，因为普通用户无权限访问）
        message.success({ content: '充值成功！正在刷新用户状态...', key: 'rechargeSuccess' })
        setTimeout(async () => {
          try {
            // 刷新用户信息（获取最新的 user_type）
            const updatedUser = await authApi.me()
            useAuthStore.getState().setUser(updatedUser)
            message.success({ content: '充值成功！', key: 'rechargeSuccess' })
            // 普通用户跳转到 /user 页面，而不是 /developer
            // 因为 /developer 是开发者专属路由，普通用户无法访问
            navigate('/user')
          } catch (error) {
            console.error('刷新用户信息失败', error)
            // 即使刷新失败也跳转
            navigate('/user')
          }
        }, 2000)
      } else {
        // 开发者续费，直接刷新页面更新余额
        message.loading({ content: '充值成功，正在刷新页面...', key: 'rechargeSuccess' })
        setTimeout(() => {
          window.location.reload()
        }, 2000)
      }
    }
  }, [paySuccess])

  const handleRefreshStatus = async () => {
    if (!currentPayment) return
    try {
      const status = await paymentApi.getPaymentStatus(currentPayment.payment_no)
      setCurrentPayment({ ...currentPayment, status: status.status as any })
      if (status.status === 'paid') {
        setPaySuccess(true)
        message.success('支付成功！')
      }
      setCountdown(60)
    } catch (error: any) {
      message.error('查询失败')
    }
  }

  const renderPackageCard = (pkg: RechargePackage) => {
    const isSelected = selectedPackage?.id === pkg.id
    const hasBonus = pkg.bonus_amount > 0 || pkg.bonus_ratio > 0

    return (
      <Card
        key={pkg.id}
        className={`${styles.packageCard} ${isSelected ? styles.selected : ''} ${pkg.is_featured ? styles.featured : ''}`}
        hoverable
        onClick={() => handleSelectPackage(pkg)}
      >
        {pkg.is_featured && (
          <div className={styles.featuredTag}>
            <GiftOutlined /> 推荐
          </div>
        )}
        
        <div className={styles.packageHeader}>
          <Text strong className={styles.packageName}>{pkg.name}</Text>
          {hasBonus && (
            <Tag color="gold" icon={<GiftOutlined />}>
              {pkg.bonus_ratio > 0 ? `赠送${pkg.bonus_ratio}%` : `+¥${pkg.bonus_amount}`}
            </Tag>
          )}
        </div>

        <div className={styles.priceSection}>
          <span className={styles.currencyIcon}>¥</span>
          <span className={styles.price}>{pkg.price.toFixed(2)}</span>
        </div>

        <div className={styles.packageDetail}>
          <Text type="secondary">
            {hasBonus ? (
              <>实际到账：<Text strong>¥{((pkg.price || 0) + (pkg.bonus_amount || 0) + (pkg.price || 0) * ((pkg.bonus_ratio || 0) / 100)).toFixed(2)}</Text></>
            ) : (
              '无赠送'
            )}
          </Text>
        </div>

        {pkg.description && (
          <Paragraph type="secondary" className={styles.description}>
            {pkg.description}
          </Paragraph>
        )}

        {isSelected && (
          <div className={styles.selectedIndicator}>
            <CheckCircleOutlined /> 已选择
          </div>
        )}
      </Card>
    )
  }

  if (loading) {
    return (
      <div className={styles.loading}>
        <Spin size="large" tip="加载套餐列表..." />
      </div>
    )
  }

  return (
    <div className={`${styles.container} bamboo-bg-pattern`}>
      <ErrorModalComponent />
      
      {/* 普通用户升级引导 - 明确告知充值即升级 */}
      {isNormalUser && (
        <Alert
          type="warning"
          showIcon
          icon={<RocketOutlined />}
          message="充值即可升级为开发者"
          description={
            <div>
              <p style={{ marginBottom: 8 }}>
                <strong>升级说明：</strong>充值成功后，您的账户将自动升级为开发者，可享受：
              </p>
              <ul style={{ marginBottom: 0, paddingLeft: 20 }}>
                <li>创建API仓库并获得收益分成</li>
                <li>充值金额将作为账户余额使用</li>
              </ul>
            </div>
          }
          action={
            <Button type="primary" size="small" onClick={() => navigate('/user')}>
              查看升级详情
            </Button>
          }
          style={{ marginBottom: 16 }}
        />
      )}

      <div className={styles.header}>
        <div>
          <Title level={4}>充值中心</Title>
          <Text type="secondary">选择充值套餐，完成支付后立即到账</Text>
        </div>
        <Space>
          {rechargeConfig?.mock_mode && (
            <Tag color="orange">⚠️ 开发环境 - 模拟支付</Tag>
          )}
          {!rechargeConfig?.mock_mode && (
            <Tag color="green">🛡️ 生产环境 - 真实支付</Tag>
          )}
          <Button icon={<ReloadOutlined />} onClick={fetchPackages}>
            刷新套餐
          </Button>
        </Space>
      </div>

      {/* 充值套餐 */}
      <Card title="选择充值套餐" className={styles.packageSection}>
        {packages.length === 0 ? (
          <Empty description="暂无充值套餐" />
        ) : (
          <>
            <Row gutter={[16, 16]}>
              {packages.map(pkg => (
                <Col xs={24} sm={12} lg={8} xl={6} key={pkg.id}>
                  {renderPackageCard(pkg)}
                </Col>
              ))}
            </Row>
            
            {/* 自定义金额选项 */}
            <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
              <Col xs={24} sm={12} lg={8} xl={6}>
                <Card
                  className={`${styles.packageCard} ${showCustomAmount ? styles.selected : ''}`}
                  hoverable
                  onClick={handleCustomAmountSelect}
                >
                  <div className={styles.packageHeader}>
                    <EditOutlined style={{ marginRight: 8 }} />
                    <Text strong>自定义金额</Text>
                  </div>
                  <div className={styles.packageDetail}>
                    <Text type="secondary">
                      {rechargeConfig ? `可充值 ${rechargeConfig.min_amount} - ${rechargeConfig.max_amount} 元` : '输入任意金额'}
                    </Text>
                  </div>
                  {showCustomAmount && (
                    <div className={styles.selectedIndicator}>
                      <CheckCircleOutlined /> 已选择
                    </div>
                  )}
                </Card>
              </Col>
            </Row>
          </>
        )}
      </Card>

      {/* 支付方式 */}
      {(selectedPackage || showCustomAmount) && (
        <Card title="选择支付方式" className={styles.paymentSection}>
          <Radio.Group
            value={paymentMethod}
            onChange={(e) => setPaymentMethod(e.target.value)}
            className={styles.paymentMethods}
          >
            <Space size="large" wrap>
              {PAYMENT_METHODS.map(method => (
                <Radio.Button key={method.value} value={method.value} className="methodButton">
                  <Space>
                    <span style={{ color: method.color }}>{method.icon}</span>
                    <span>{method.label}</span>
                  </Space>
                </Radio.Button>
              ))}
            </Space>
          </Radio.Group>

          <Divider />

          <Descriptions bordered column={2}>
            <Descriptions.Item label="充值方式">
              {selectedPackage ? selectedPackage.name : '自定义金额'}
            </Descriptions.Item>
            {selectedPackage ? (
              <>
                <Descriptions.Item label="赠送金额">
                  {selectedPackage.bonus_amount > 0 && `+¥${selectedPackage.bonus_amount}`}
                  {selectedPackage.bonus_ratio > 0 && ` + ${selectedPackage.bonus_ratio}%`}
                  {!selectedPackage.bonus_amount && !selectedPackage.bonus_ratio && '无'}
                </Descriptions.Item>
                <Descriptions.Item label="支付金额">
                  <Text strong className={styles.payAmount}>¥{selectedPackage.price.toFixed(2)}</Text>
                </Descriptions.Item>
                <Descriptions.Item label="实际到账">
                  <Text type="success">
                    ¥{((selectedPackage.price || 0) + (selectedPackage.bonus_amount || 0) + (selectedPackage.price || 0) * ((selectedPackage.bonus_ratio || 0) / 100)).toFixed(2)}
                  </Text>
                </Descriptions.Item>
              </>
            ) : (
              <>
                <Descriptions.Item label="充值金额">
                  <InputNumber
                    min={rechargeConfig?.min_amount || 1}
                    max={rechargeConfig?.max_amount || 10000}
                    value={customAmount}
                    onChange={handleCustomAmountChange}
                    prefix="¥"
                    style={{ width: 150 }}
                    placeholder={`${rechargeConfig?.min_amount || 1} - ${rechargeConfig?.max_amount || 10000}`}
                  />
                </Descriptions.Item>
                <Descriptions.Item label="赠送金额">
                  {rechargeConfig && rechargeConfig.default_bonus_ratio > 0 ? (
                    <Text type="warning">+{(customAmount || 0) * rechargeConfig.default_bonus_ratio}%</Text>
                  ) : '无'}
                </Descriptions.Item>
                <Descriptions.Item label="实际到账">
                  {rechargeConfig && rechargeConfig.default_bonus_ratio > 0 ? (
                    <Text type="success">
                      ¥{((customAmount || 0) * (1 + rechargeConfig.default_bonus_ratio)).toFixed(2)}
                    </Text>
                  ) : (
                    <Text type="success">¥{(customAmount || 0).toFixed(2)}</Text>
                  )}
                </Descriptions.Item>
              </>
            )}
          </Descriptions>

          <div className={styles.actionSection}>
            {selectedPackage ? (
              <Button 
                type="primary" 
                size="large" 
                onClick={handleCreateOrder}
                loading={creatingOrder}
                disabled={!selectedPackage}
              >
                立即充值 ¥{selectedPackage.price.toFixed(2)}
              </Button>
            ) : (
              <Button 
                type="primary" 
                size="large" 
                onClick={handleCreateOrder}
                loading={creatingOrder}
                disabled={!customAmount}
              >
                立即充值 ¥{customAmount?.toFixed(2) || '0.00'}
              </Button>
            )}
          </div>
        </Card>
      )}

      {/* 支付弹窗 */}
      <Modal
        title="订单支付"
        open={payModalVisible}
        onCancel={handlePayModalClose}
        footer={null}
        width={500}
        maskClosable={false}
      >
        {paySuccess ? (
          <Result
            status="success"
            title={isNormalUser ? "升级成功！" : "充值成功！"}
            subTitle={isNormalUser 
              ? `已成功充值 ¥${currentPayment?.amount.toFixed(2)}，并升级为开发者`
              : `已成功充值 ¥${currentPayment?.amount.toFixed(2)}，余额已到账`
            }
            extra={[
              <Alert 
                key="info"
                type="success" 
                message={isNormalUser 
                  ? "恭喜！您已成为开发者，页面将自动跳转..." 
                  : "充值已到账，页面将自动刷新..."
                } 
                style={{ marginBottom: 16, textAlign: 'center' }}
                showIcon
              />,
              <Space key="actions">
                <Button 
                  type="primary" 
                  onClick={() => isNormalUser ? navigate('/user') : window.location.reload()}
                >
                  {isNormalUser ? '查看用户状态' : '刷新页面'}
                </Button>
                <Button onClick={handlePayModalClose}>
                  返回充值中心
                </Button>
              </Space>
            ]}
          />
        ) : (
          <>
            <Descriptions bordered column={1} size="small">
              <Descriptions.Item label="订单号">{currentPayment?.payment_no}</Descriptions.Item>
              <Descriptions.Item label="充值金额">
                <Text strong>¥{currentPayment?.amount.toFixed(2)}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="支付方式">
                {PAYMENT_METHODS.find(m => m.value === paymentMethod)?.label}
              </Descriptions.Item>
              <Descriptions.Item label="剩余有效期">
                <Text type={countdown < 10 ? 'danger' : 'secondary'}>{countdown} 秒</Text>
              </Descriptions.Item>
            </Descriptions>

            <Divider />

            <div className={styles.payActions}>
              <Button 
                type="primary" 
                size="large" 
                block 
                onClick={handleOpenPay}
                disabled={countdown <= 0}
              >
                {PAYMENT_METHODS.find(m => m.value === paymentMethod)?.icon} 
                {countdown <= 0 ? '订单已过期' : '打开支付页面'}
              </Button>
              
              <Space style={{ marginTop: 16 }}>
                <Button onClick={handleRefreshStatus}>
                  <ReloadOutlined /> 刷新状态
                </Button>
                <Button 
                  danger 
                  onClick={async () => {
                    if (currentPayment) {
                      await paymentApi.cancelPayment(currentPayment.payment_no)
                      message.success('订单已取消')
                      setPayModalVisible(false)
                    }
                  }}
                >
                  取消订单
                </Button>
              </Space>
            </div>

            <Text type="secondary" className={styles.hint}>
              提示：支付完成后请点击"刷新状态"确认支付结果
            </Text>
          </>
        )}
      </Modal>
    </div>
  )
}
