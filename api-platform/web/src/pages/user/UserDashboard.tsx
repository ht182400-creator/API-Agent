/**
 * 普通用户首页 - 引导页
 * 
 * 功能：
 * - 领取试用金额
 * - 升级为开发者
 * - 引导用户开始使用平台
 * 
 * V4.0 更新：
 * - 修复升级后页面不刷新的问题
 * - 确保 localStorage 持久化完成后再刷新
 */

import { useState, useEffect, useCallback } from 'react'
import '../../styles/cyber-theme.css'
import { useNavigate } from 'react-router-dom'
import { Card, Row, Col, Statistic, Button, Typography, Space, message, Spin, Alert, Modal, Divider } from 'antd'
import { GiftOutlined, RocketOutlined, DollarOutlined, CheckCircleOutlined, RightOutlined, SafetyCertificateOutlined } from '@ant-design/icons'
import { userApi, UserStatus, UpgradeInfo } from '../../api/user'
import { authApi } from '../../api/auth'
import { useAuthStore } from '../../stores/auth'
import styles from './UserDashboard.module.css'

const { Title, Text, Paragraph } = Typography

export default function UserDashboard() {
  const navigate = useNavigate()
  const { setAuth, accessToken, refreshToken } = useAuthStore()
  const [loading, setLoading] = useState(true)
  const [claiming, setClaiming] = useState(false)
  const [upgrading, setUpgrading] = useState(false)
  const [userStatus, setUserStatus] = useState<UserStatus | null>(null)
  const [trialAmount, setTrialAmount] = useState<number>(0)
  const [upgradeInfo, setUpgradeInfo] = useState<UpgradeInfo | null>(null)

  // 获取用户状态和试用配置
  useEffect(() => {
    fetchUserStatus()
    fetchTrialConfig()
    fetchUpgradeInfo()
  }, [])

  // 获取试用配置
  const fetchTrialConfig = async () => {
    try {
      const config = await userApi.getTrialConfig()
      // 始终设置试用金额，不管是否启用
      setTrialAmount(config.trial_amount || 0)
    } catch (error) {
      console.error('获取试用配置失败:', error)
      // API失败时使用默认值
      setTrialAmount(20)
    }
  }

  // 获取升级信息 (V4.1)
  const fetchUpgradeInfo = async () => {
    try {
      const info = await userApi.getUpgradeInfo()
      setUpgradeInfo(info)
    } catch (error) {
      console.error('获取升级信息失败:', error)
    }
  }

  const fetchUserStatus = async () => {
    setLoading(true)
    try {
      const status = await userApi.getStatus()
      setUserStatus(status)
      
      // 如果已经是开发者，跳转到开发者首页
      if (status.is_developer) {
        message.info('您已是开发者，正在跳转...')
        // 使用 window.location 直接跳转，避免 React Router 循环
        window.location.href = '/'
      }
    } catch (error: any) {
      console.error('获取用户状态失败:', error)
      message.error('获取用户状态失败')
    } finally {
      setLoading(false)
    }
  }

  /**
   * 刷新认证状态并等待持久化完成
   * 确保 localStorage 更新后再刷新页面
   */
  const refreshAuthAndReload = useCallback(async () => {
    try {
      // 1. 获取最新的用户信息
      const user = await authApi.me()
      console.log('[UserDashboard] 刷新后的用户信息:', user)
      console.log('[UserDashboard] user_type:', user.user_type)
      
      // 2. 验证用户数据
      if (!user || !user.user_type) {
        console.error('[UserDashboard] 用户数据不完整:', user)
        throw new Error('用户数据不完整')
      }
      
      // 3. 更新 auth store（persist 中间件会自动写入 localStorage）
      setAuth(user, accessToken || '', refreshToken || '')
      
      // 4. 等待 localStorage 写入完成
      // zustand persist 默认使用 requestIdleCallback 或 setTimeout，延迟约 50-100ms
      // 增加等待时间到 500ms 确保写入完成
      await new Promise(resolve => setTimeout(resolve, 500))
      
      // 5. 验证 localStorage 是否已更新
      const storedData = localStorage.getItem('auth-storage')
      if (storedData) {
        const parsed = JSON.parse(storedData)
        const storedUserType = parsed.state?.user?.user_type
        console.log('[UserDashboard] localStorage 中的 user_type:', storedUserType)
        
        // 如果 localStorage 中的 user_type 不是 developer，再等待一段时间
        if (storedUserType !== 'developer') {
          console.warn('[UserDashboard] localStorage 还未更新，再等待 500ms...')
          await new Promise(resolve => setTimeout(resolve, 500))
          
          // 再次检查
          const storedData2 = localStorage.getItem('auth-storage')
          if (storedData2) {
            const parsed2 = JSON.parse(storedData2)
            console.log('[UserDashboard] 再次检查 localStorage user_type:', parsed2.state?.user?.user_type)
          }
        }
      }
      
      // 6. 刷新页面
      console.log('[UserDashboard] 刷新页面...')
      window.location.reload()
    } catch (error) {
      console.error('[UserDashboard] 刷新认证状态失败:', error)
      // 即使出错也尝试刷新页面
      message.warning('刷新页面以更新状态...')
      window.location.reload()
    }
  }, [accessToken, refreshToken, setAuth])

  // 领取试用金额
  const handleClaimTrial = async () => {
    setClaiming(true)
    try {
      const result = await userApi.claimTrial()
      message.success(result.message)
      
      // 更新本地用户信息
      setUserStatus(prev => prev ? {
        ...prev,
        balance: result.new_balance,
        trial_claimed: true,
        trial_amount_claimed: result.amount,  // 【修复】更新领取金额
        is_developer: true,
      } : null)
      
      // 延迟显示跳转信息，然后刷新
      setTimeout(() => {
        message.info('正在跳转到开发者工作台...')
        refreshAuthAndReload()
      }, 1500)
    } catch (error: any) {
      console.error('领取试用失败:', error)
      message.error(error.message || '领取试用失败')
    } finally {
      setClaiming(false)
    }
  }

  // 升级为开发者（付费1元升级 V4.1）
  const handleUpgrade = async () => {
    // 1. 二次确认弹窗
    Modal.confirm({
      title: (
        <div>
          <SafetyCertificateOutlined style={{ color: '#1890ff', marginRight: 8 }} />
          确认升级为开发者
        </div>
      ),
      icon: null,
      content: (
        <div style={{ padding: '8px 0' }}>
          <Alert 
            type="warning" 
            message="升级后无法降级为普通用户" 
            showIcon 
            style={{ marginBottom: 16 }}
          />
          <p><strong>升级为开发者后，您将享受：</strong></p>
          <ul style={{ paddingLeft: 20, marginBottom: 16 }}>
            <li>创建API仓库并获得收益分成</li>
            <li>专属开发者管理后台</li>
            <li>API调用详细日志</li>
            <li>完整的API管理功能</li>
          </ul>
          <Divider style={{ margin: '12px 0' }} />
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>支付金额：</span>
            <Text strong style={{ fontSize: 18, color: '#ff4d4f' }}>
              ¥{upgradeInfo?.upgrade_fee || 1.00}
            </Text>
          </div>
          <Text type="secondary" style={{ display: 'block', marginTop: 8, fontSize: 12 }}>
            {upgradeInfo?.balance_tip || `当前余额 ¥${userStatus?.balance || 0}`}
          </Text>
        </div>
      ),
      okText: '确认支付并升级',
      cancelText: '取消',
      onOk: async () => {
        setUpgrading(true)
        try {
          const result = await userApi.upgradeWithPayment()
          message.success(result.message || '升级成功！正在刷新页面...')
          
          // 延迟刷新，确保 localStorage 持久化完成
          setTimeout(() => {
            refreshAuthAndReload()
          }, 1500)
        } catch (error: any) {
          console.error('升级失败:', error)
          message.error(error.message || '升级失败')
          // 刷新升级信息
          fetchUpgradeInfo()
        } finally {
          setUpgrading(false)
        }
      },
    })
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
      {/* 顶部欢迎区域 */}
      <div className={styles.welcomeSection}>
        <Title level={2} className={styles.welcomeTitle}>
          <RocketOutlined /> 欢迎使用 API 服务平台
        </Title>
        <Paragraph className={styles.welcomeDesc}>
          轻松接入高质量 API，快速构建您的应用
        </Paragraph>
      </div>

      {/* 试用金额卡片 */}
      {!userStatus?.trial_claimed && (
        <Card className={styles.trialCard} bordered={false}>
          <Row gutter={[24, 24]} align="middle">
            <Col xs={24} md={16}>
              <div className={styles.trialInfo}>
                <div className={styles.trialBadge} style={{ color: 'white' }}>
                  <GiftOutlined /> 新用户专享
                </div>
                <Title level={3} style={{ color: 'white', margin: '8px 0' }}>领取 {trialAmount} 元试用金额</Title>
                <Paragraph style={{ color: 'rgba(255,255,255,0.85)', margin: 0 }}>
                  立即体验平台全部功能，无需充值
                </Paragraph>
              </div>
            </Col>
            <Col xs={24} md={8} className={styles.trialAction}>
              <Button
                type="primary"
                size="large"
                icon={<GiftOutlined />}
                onClick={handleClaimTrial}
                loading={claiming}
                className={styles.claimButton}
              >
                立即领取
              </Button>
            </Col>
          </Row>
        </Card>
      )}

      {/* 已领取提示 */}
      {userStatus?.trial_claimed && (
        <Alert
          message="试用金额已领取"
          description={`您已领取 ${userStatus.trial_amount_claimed} 元试用金额，正在跳转到开发者工作台...`}
          type="success"
          showIcon
          icon={<CheckCircleOutlined />}
          className={styles.claimedAlert}
        />
      )}

      {/* 功能介绍 */}
      <div className={styles.featuresSection}>
        <Title level={4} className={styles.sectionTitle}>
          成为开发者，解锁全部功能
        </Title>
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} md={6}>
            <Card className={styles.featureCard} hoverable>
              <RocketOutlined className={styles.featureIcon} />
              <Title level={5}>API 管理</Title>
              <Text type="secondary">创建和管理您的 API 产品</Text>
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card className={styles.featureCard} hoverable>
              <DollarOutlined className={styles.featureIcon} />
              <Title level={5}>费用透明</Title>
              <Text type="secondary">实时查看使用量和费用明细</Text>
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card className={styles.featureCard} hoverable>
              <CheckCircleOutlined className={styles.featureIcon} />
              <Title level={5}>数据安全</Title>
              <Text type="secondary">企业级安全保护您的数据</Text>
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card className={styles.featureCard} hoverable>
              <RightOutlined className={styles.featureIcon} />
              <Title level={5}>快速接入</Title>
              <Text type="secondary">几分钟内完成 API 集成</Text>
            </Card>
          </Col>
        </Row>
      </div>

      {/* 操作按钮 */}
      <Card className={styles.actionCard}>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <div className={styles.actionItem}>
            <div className={styles.actionInfo}>
              <Title level={5}>升级为开发者</Title>
              <Text type="secondary">
                {upgradeInfo?.can_upgrade 
                  ? `支付 ¥${upgradeInfo.upgrade_fee || 1} 升级，解锁全部开发者功能`
                  : upgradeInfo?.balance_tip || `账户余额：${userStatus?.balance || 0} 元`
                }
              </Text>
            </div>
            <Button 
              type="primary" 
              onClick={handleUpgrade}
              loading={upgrading}
              disabled={!upgradeInfo?.can_upgrade}
              className={!upgradeInfo?.can_upgrade ? styles.insufficientBtn : ''}
            >
              <SafetyCertificateOutlined /> {upgradeInfo?.can_upgrade ? `付费升级 ¥${upgradeInfo.upgrade_fee || 1.00}` : '余额不足'}
            </Button>
          </div>
          <div className={styles.actionItem}>
            <div className={styles.actionInfo}>
              <Title level={5}>充值账户</Title>
              <Text type="secondary">账户余额：{userStatus?.balance || 0} 元</Text>
            </div>
            <Button onClick={() => navigate('/user/recharge')}>
              前往充值
            </Button>
          </div>
        </Space>
      </Card>

      {/* 快速链接 */}
      <div className={styles.quickLinks}>
        <Text type="secondary">
          遇到问题？
          <a href="/help" className={styles.helpLink}> 查看帮助文档</a>
          或
          <a href="/contact" className={styles.helpLink}> 联系客服</a>
        </Text>
      </div>
    </div>
  )
}
