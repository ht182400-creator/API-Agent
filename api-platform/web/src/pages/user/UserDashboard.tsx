/**
 * 普通用户首页 - 引导页
 * 
 * 功能：
 * - 领取试用金额
 * - 升级为开发者
 * - 引导用户开始使用平台
 */

import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Row, Col, Statistic, Button, Typography, Space, message, Spin, Alert } from 'antd'
import { GiftOutlined, RocketOutlined, DollarOutlined, CheckCircleOutlined, RightOutlined } from '@ant-design/icons'
import { userApi, UserStatus } from '../../api/user'
import { useAuthStore } from '../../stores/auth'
import styles from './UserDashboard.module.css'

const { Title, Text, Paragraph } = Typography

export default function UserDashboard() {
  const navigate = useNavigate()
  const { setAuth } = useAuthStore()
  const [loading, setLoading] = useState(true)
  const [claiming, setClaiming] = useState(false)
  const [userStatus, setUserStatus] = useState<UserStatus | null>(null)

  // 获取用户状态
  useEffect(() => {
    fetchUserStatus()
  }, [])

  const fetchUserStatus = async () => {
    setLoading(true)
    try {
      const status = await userApi.getStatus()
      setUserStatus(status)
      
      // 如果已经是开发者，跳转到开发者首页
      if (status.is_developer) {
        message.info('您已是开发者，正在跳转...')
        navigate('/', { replace: true })
      }
    } catch (error: any) {
      console.error('获取用户状态失败:', error)
      message.error('获取用户状态失败')
    } finally {
      setLoading(false)
    }
  }

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
        is_developer: true,
      } : null)
      
      // 刷新用户信息
      const me = await fetch('/api/v1/auth/me', {
        headers: {
          'Authorization': `Bearer ${useAuthStore.getState().accessToken}`,
        },
      }).then(r => r.json())
      
      if (me.data) {
        setAuth(
          me.data,
          useAuthStore.getState().accessToken || '',
          useAuthStore.getState().refreshToken || ''
        )
      }
      
      // 延迟跳转，让用户看到成功提示
      setTimeout(() => {
        message.info('正在跳转到开发者工作台...')
        navigate('/', { replace: true })
      }, 1500)
    } catch (error: any) {
      console.error('领取试用失败:', error)
      message.error(error.message || '领取试用失败')
    } finally {
      setClaiming(false)
    }
  }

  // 升级为开发者（不领取试用）
  const handleUpgrade = async () => {
    try {
      await userApi.upgrade()
      message.success('升级成功！正在刷新页面...')
      
      // 刷新页面
      setTimeout(() => {
        window.location.reload()
      }, 1000)
    } catch (error: any) {
      console.error('升级失败:', error)
      message.error(error.message || '升级失败')
    }
  }

  if (loading) {
    return (
      <div className={styles.loadingContainer}>
        <Spin size="large" tip="加载中..." />
      </div>
    )
  }

  return (
    <div className={styles.container}>
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
                <div className={styles.trialBadge}>
                  <GiftOutlined /> 新用户专享
                </div>
                <Title level={3}>领取 {userStatus?.balance === 0 ? '10' : '0'} 元试用金额</Title>
                <Paragraph type="secondary">
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
              <Text type="secondary">获得创建 API、管理密钥等全部功能</Text>
            </div>
            <Button onClick={handleUpgrade}>
              立即升级
            </Button>
          </div>
          <div className={styles.actionItem}>
            <div className={styles.actionInfo}>
              <Title level={5}>充值账户</Title>
              <Text type="secondary">账户余额：{userStatus?.balance || 0} 元</Text>
            </div>
            <Button type="primary" onClick={() => navigate('/developer/recharge')}>
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
