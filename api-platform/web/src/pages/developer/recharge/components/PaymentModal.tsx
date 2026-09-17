/**
 * 支付弹窗 —— P1-4 巨型组件拆分（由 `../Recharge.tsx` 抽出，纯搬运零行为改变）
 *
 * 三态：① `isProcessingCallback` → 「支付确认中」；② `paySuccess` → `PaySuccessView` 大界面；
 * ③ 其余 → 订单信息 + （二维码 / 跳转支付按钮）+ 刷新/取消。原先占约 130 行。
 *
 * ⚠️ 这是 Recharge 里**依赖最多**的一块（15 个 props），按 §2.25「按依赖数量从少到多切」
 *    的策略放在最后搬。为保持它**纯展示**（与 PackageCard / PaymentSummary / PaySuccessView 一致），
 *    「取消订单」的动作逻辑留在父组件（`handleCancelOrder`），这里只接收 `onCancelOrder`。
 */
import { Alert, Button, Descriptions, Divider, Modal, Space, Spin, Typography } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import type { Payment } from '../../../../api/payment'
import { PAYMENT_METHODS } from '../constants'
import { PaySuccessView } from './PaySuccessView'
// ⚠️ 样式在 developer/ 下，本文件在 developer/recharge/components/ → 回退两级
import styles from '../../Recharge.module.css'

const { Text } = Typography

export interface PaymentModalProps {
  open: boolean
  /** 支付宝同步回调处理中 → 「支付确认中」界面 */
  isProcessingCallback: boolean
  /** 已支付成功 → 切到 PaySuccessView 大界面 */
  paySuccess: boolean
  /** 普通用户（成功标题显示「升级成功」而非「充值成功」） */
  isNormalUser: boolean
  currentPayment: Payment | null
  currentBalance: number
  /** 订单剩余有效期（秒），<=0 视为已过期 */
  countdown: number
  paymentMethod: 'wechat' | 'alipay' | 'bankcard'
  /** 扫码轮询进行中 → 显示「等待支付结果...」 */
  qrcodePolling: boolean
  refreshingQrCode: boolean
  onClose: () => void
  onGoToUser: () => void
  onReload: () => void
  onRefreshQrCode: () => void
  onOpenPay: () => void
  onRefreshStatus: () => void
  onCancelOrder: () => void
}

export function PaymentModal({
  open,
  isProcessingCallback,
  paySuccess,
  isNormalUser,
  currentPayment,
  currentBalance,
  countdown,
  paymentMethod,
  qrcodePolling,
  refreshingQrCode,
  onClose,
  onGoToUser,
  onReload,
  onRefreshQrCode,
  onOpenPay,
  onRefreshStatus,
  onCancelOrder,
}: PaymentModalProps) {
  const hasQrCode = !!currentPayment?.qr_code && currentPayment.qr_code.length > 0

  return (
    <Modal
      title={isProcessingCallback ? "支付确认中" : (paySuccess ? (isNormalUser ? "升级成功" : "充值成功") : "订单支付")}
      open={open}
      onCancel={onClose}
      footer={null}
      width={paySuccess ? 480 : 500}
      maskClosable={!isProcessingCallback && !paySuccess}
      closable={!isProcessingCallback && !paySuccess}
    >
      {isProcessingCallback ? (
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          {/* ⚠️ 同上：Spin 的 tip 单独使用不显示 → 自行渲染 */}
          <Spin size="large" />
          <div style={{ marginTop: 12, color: '#666' }}>正在确认支付结果，请稍候...</div>
        </div>
      ) : paySuccess ? (
        // 成功界面已抽为展示组件 ./PaySuccessView
        <PaySuccessView
          isNormalUser={isNormalUser}
          currentPayment={currentPayment}
          currentBalance={currentBalance}
          onGoToUser={onGoToUser}
          onRefresh={onReload}
          onContinueRecharge={onClose}
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

          {/* 扫码支付：显示二维码 */}
          {hasQrCode ? (
            <div style={{ textAlign: 'center', padding: '20px 0' }}>
              <Alert
                type="info"
                message="请使用支付宝扫码支付"
                showIcon
                style={{ marginBottom: 16 }}
              />
              <img
                src={currentPayment?.qr_code}
                alt="支付宝扫码支付"
                style={{
                  width: 200,
                  height: 200,
                  border: '1px solid #f0f0f0',
                  borderRadius: 8
                }}
              />
              <div style={{ marginTop: 12 }}>
                <Button
                  size="small"
                  icon={<ReloadOutlined />}
                  onClick={onRefreshQrCode}
                  loading={refreshingQrCode}
                >
                  刷新二维码
                </Button>
              </div>
              {qrcodePolling && (
                <div style={{ marginTop: 16 }}>
                  <Spin size="small" />
                  <Text type="secondary" style={{ marginLeft: 8 }}>等待支付结果...</Text>
                </div>
              )}
            </div>
          ) : (
            /* 跳转支付：显示支付按钮 */
            <div className={styles.payActions}>
              <Alert
                type="warning"
                message="支付完成后，请手动关闭支付宝窗口"
                showIcon
                style={{ marginBottom: 16 }}
              />
              <Button
                type="primary"
                size="large"
                block
                onClick={onOpenPay}
                disabled={countdown <= 0}
              >
                {PAYMENT_METHODS.find(m => m.value === paymentMethod)?.icon}
                {countdown <= 0 ? '订单已过期' : '打开支付页面'}
              </Button>
            </div>
          )}

          <div style={{ marginTop: 16, textAlign: 'center' }}>
            <Space>
              <Button onClick={onRefreshStatus}>
                <ReloadOutlined /> 刷新状态
              </Button>
              <Button danger onClick={onCancelOrder}>
                取消订单
              </Button>
            </Space>
          </div>

          <Text type="secondary" className={styles.hint}>
            {hasQrCode
              ? '提示：支付完成后请耐心等待，系统将自动确认'
              : '提示：支付完成后请点击"刷新状态"确认支付结果'}
          </Text>
        </>
      )}
    </Modal>
  )
}
