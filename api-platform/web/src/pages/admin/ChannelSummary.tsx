/**
 * 管理员渠道收款汇总页面
 * V2.6 新增
 */

import { useState, useEffect } from 'react'
import '../../styles/cyber-theme.css'
import { Card, DatePicker, Row, Col, Statistic, Tag, Space, Typography, Spin, Progress, Button } from 'antd'
import {
  AlipayOutlined,
  WechatOutlined,
  CreditCardOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined
} from '@ant-design/icons'
import { adminReconciliationApi, ChannelSummary as ChannelSummaryType, TotalSummary } from '../../api/adminReconciliation'
import { useErrorModal } from '../../components/ErrorModal'
import dayjs from 'dayjs'
import styles from './ChannelSummary.module.css'

const { Title, Text } = Typography

// 渠道图标映射
const CHANNEL_ICONS: Record<string, React.ReactNode> = {
  alipay: <AlipayOutlined style={{ fontSize: 32, color: '#1677FF' }} />,
  wechat: <WechatOutlined style={{ fontSize: 32, color: '#07C160' }} />,
  bankcard: <CreditCardOutlined style={{ fontSize: 32, color: '#722ED1' }} />,
}

export default function AdminChannelSummary() {
  const [loading, setLoading] = useState(false)
  const [dateStr, setDateStr] = useState<string>(new Date().toISOString().split('T')[0])
  const [channels, setChannels] = useState<ChannelSummaryType[]>([])
  const [total, setTotal] = useState<TotalSummary | null>(null)
  
  const { showError, ErrorModal: ErrorModalComponent } = useErrorModal()

  useEffect(() => {
    fetchSummary()
  }, [dateStr])

  const fetchSummary = async () => {
    setLoading(true)
    try {
      const response = await adminReconciliationApi.getChannelSummary(dateStr)
      setChannels(response.channels || [])
      setTotal(response.total || null)
    } catch (error: any) {
      showError(error, fetchSummary)
    } finally {
      setLoading(false)
    }
  }

  const renderChannelCard = (channel: ChannelSummaryType) => {
    const reconcileRate = channel.trade_count > 0 
      ? Math.round((channel.success_count / channel.trade_count) * 100) 
      : 0

    return (
      <Card 
        key={channel.channel}
        className={styles.channelCard}
        hoverable
      >
        <div className={styles.channelHeader}>
          <Space>
            {CHANNEL_ICONS[channel.channel]}
            <Text strong style={{ fontSize: 18 }}>{channel.channel_name}</Text>
          </Space>
          <Tag color={channel.pending_count > 0 ? 'orange' : 'green'}>
            {channel.pending_count > 0 ? (
              <><ClockCircleOutlined /> 待处理</>
            ) : (
              <><CheckCircleOutlined /> 已完成</>
            )}
          </Tag>
        </div>

        <div className={styles.channelStats}>
          <Row gutter={16}>
            <Col span={12}>
              <Statistic
                title="交易笔数"
                value={channel.trade_count}
                suffix="笔"
              />
            </Col>
            <Col span={12}>
              <Statistic
                title="收款金额"
                value={channel.trade_amount}
                precision={2}
                prefix="¥"
                valueStyle={{ color: '#52c41a' }}
              />
            </Col>
          </Row>

          <div className={styles.subStats}>
            <Space size="large">
              <Text type="secondary">
                成功: <Text type="success">{channel.success_count}</Text> 笔
              </Text>
              <Text type="secondary">
                待处理: <Text type="warning">{channel.pending_count}</Text> 笔
              </Text>
              <Text type="secondary">
                失败: <Text type="danger">{channel.failed_count}</Text> 笔
              </Text>
            </Space>
          </div>

          <div className={styles.progressSection}>
            <Text type="secondary" style={{ marginBottom: 8 }}>完成率</Text>
            <Progress 
              percent={reconcileRate} 
              status={reconcileRate === 100 ? 'success' : 'active'}
              strokeColor="#52c41a"
            />
          </div>
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

      <div className={styles.header} style={{ flexWrap: 'wrap', gap: 8 }}>
        <Title level={4} style={{ marginBottom: 0 }}>渠道收款汇总</Title>
        <Space wrap size="small">
          <DatePicker
            value={dateStr ? dayjs(dateStr) : undefined}
            onChange={(date, dateString) => {
              if (dateString) {
                setDateStr(dateString as string)
              }
            }}
            placeholder="选择日期"
          />
          <Button type="link" size="small" onClick={() => setDateStr(new Date().toISOString().split('T')[0])}>
            今天
          </Button>
          <Button type="link" size="small" onClick={() => {
            const yesterday = new Date()
            yesterday.setDate(yesterday.getDate() - 1)
            setDateStr(yesterday.toISOString().split('T')[0])
          }}>
            昨天
          </Button>
          <Button type="link" size="small" icon={<ReloadOutlined />} onClick={fetchSummary}>
            刷新
          </Button>
        </Space>
      </div>

      {/* 总览卡片 */}
      {total && (
        <Card className={styles.totalCard}>
          <Row gutter={[12, 12]}>
            <Col xs={12} sm={6}>
              <Statistic
                title="总交易笔数"
                value={total.trade_count}
                suffix="笔"
              />
            </Col>
            <Col xs={12} sm={6}>
              <Statistic
                title="总收款金额"
                value={total.trade_amount}
                precision={2}
                prefix="¥"
                valueStyle={{ color: '#1890ff' }}
              />
            </Col>
            <Col xs={12} sm={6}>
              <Statistic
                title="已完成笔数"
                value={total.success_count}
                valueStyle={{ color: '#52c41a' }}
              />
            </Col>
            <Col xs={12} sm={6}>
              <Statistic
                title="待处理笔数"
                value={total.pending_count}
                valueStyle={{ color: total.pending_count > 0 ? '#faad14' : '#52c41a' }}
              />
            </Col>
          </Row>
        </Card>
      )}

      {/* 渠道卡片 */}
      <Row gutter={[16, 16]}>
        {channels.map(channel => (
          <Col xs={24} sm={12} lg={8} key={channel.channel}>
            {renderChannelCard(channel)}
          </Col>
        ))}
      </Row>

      {/* 提示信息 */}
      <Card className={styles.tipCard}>
        <Space>
          <ExclamationCircleOutlined style={{ color: '#faad14' }} />
          <Text type="secondary">
            对账数据每日凌晨自动更新。如有差异，请联系技术支持。
          </Text>
        </Space>
      </Card>
    </div>
  )
}
