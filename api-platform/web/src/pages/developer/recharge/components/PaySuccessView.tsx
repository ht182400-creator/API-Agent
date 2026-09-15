/**
 * 支付成功视图 —— P1-4 前端拆分第 4 步（展示组件 3/3）
 *
 * 大尺寸成功界面（对齐支付宝跳转页的醒目度）：成功图标 + 标题 + 订单信息卡 + 后续操作。
 *
 * 纯展示：不依赖 router，跳转/刷新通过回调传入 → 更易测、也能被其它支付入口复用。
 */
import { Alert, Button, Card, Divider, Space, Tag, Typography } from 'antd'
import { CheckCircleOutlined } from '@ant-design/icons'
import type { Payment } from '../../../../api/payment'

const { Text, Title } = Typography

export interface PaySuccessViewProps {
  /** 普通用户（role=user）走"充值即升级"文案 */
  isNormalUser: boolean
  currentPayment: Payment | null
  currentBalance: number | null
  /** 普通用户：前往 /user */
  onGoToUser: () => void
  /** 开发者：刷新页面 */
  onRefresh: () => void
  onContinueRecharge: () => void
}

export function PaySuccessView({
  isNormalUser,
  currentPayment,
  currentBalance,
  onGoToUser,
  onRefresh,
  onContinueRecharge,
}: PaySuccessViewProps) {
  return (
    <div style={{ textAlign: 'center', padding: '20px 0' }}>
      {/* 成功图标 */}
      <div
        style={{
          width: 80,
          height: 80,
          borderRadius: '50%',
          background: '#f6ffed',
          border: '3px solid #52c41a',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 20px',
        }}
      >
        <CheckCircleOutlined style={{ fontSize: 48, color: '#52c41a' }} />
      </div>

      {/* 成功标题 */}
      <Title level={3} style={{ color: '#52c41a', marginBottom: 8 }}>
        {isNormalUser ? '升级成功！' : '充值成功！'}
      </Title>

      {/* 副标题 */}
      <Text type="secondary" style={{ fontSize: 14 }}>
        {isNormalUser
          ? '恭喜！您已成为开发者，可以开始使用 API 服务了'
          : `充值金额 ¥${currentPayment?.amount?.toFixed(2)} 已到账`}
      </Text>

      <Divider style={{ margin: '24px 0' }} />

      {/* 详细信息卡片 */}
      <Card size="small" style={{ marginBottom: 20, background: '#fafafa', borderRadius: 8 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {/* 订单号 */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Text type="secondary">订单号</Text>
            <Text copyable={{ text: currentPayment?.payment_no }} style={{ fontFamily: 'monospace' }}>
              {currentPayment?.payment_no}
            </Text>
          </div>

          {/* 充值金额 */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Text type="secondary">充值金额</Text>
            <Text strong style={{ fontSize: 18, color: '#52c41a' }}>
              ¥{currentPayment?.amount?.toFixed(2) || '0.00'}
            </Text>
          </div>

          {/* 账户余额 */}
          {currentBalance !== null && !isNormalUser && (
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Text type="secondary">账户余额</Text>
              <Text strong style={{ fontSize: 18 }}>
                ¥{currentBalance.toFixed(2)}
              </Text>
            </div>
          )}

          {/* 支付状态 */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Text type="secondary">支付状态</Text>
            <Tag color="success" style={{ margin: 0 }}>
              已支付
            </Tag>
          </div>

          {/* 支付时间 */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Text type="secondary">支付时间</Text>
            <Text>{new Date().toLocaleString('zh-CN')}</Text>
          </div>
        </div>
      </Card>

      {/* 倒计时提示 */}
      <Alert
        type="success"
        message={
          <span>
            页面将在 <Text strong style={{ color: '#52c41a' }}>5</Text> 秒后自动刷新
          </span>
        }
        style={{ marginBottom: 20 }}
        showIcon
      />

      {/* 操作按钮 */}
      <Space style={{ width: '100%' }} direction="vertical">
        <Button type="primary" size="large" block onClick={isNormalUser ? onGoToUser : onRefresh}>
          {isNormalUser ? '开始使用 API 服务' : '立即刷新'}
        </Button>
        <Button size="large" block onClick={onContinueRecharge}>
          继续充值
        </Button>
      </Space>
    </div>
  )
}
