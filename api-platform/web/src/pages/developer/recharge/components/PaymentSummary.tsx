/**
 * 支付摘要区 —— P1-4 前端拆分第 4 步（展示组件 2/3）
 *
 * 展示「充值方式 / 赠送金额 / 支付金额 / 实际到账」；
 * 自定义金额模式下改为「充值金额输入 + 赠送 + 实际到账」。
 *
 * 纯展示 + 一个受控输入：不持有状态，金额与回调由父组件传入。
 *
 * ⚠️ 已知显示缺陷（拆分时**原样保留**，未顺手改行为，待确认后再动）：
 *    自定义模式下的「赠送金额」写成 `+{(customAmount||0) * default_bonus_ratio}%`，
 *    但 `default_bonus_ratio` 是**小数**（如 0.05）—— 于是它算出来的是**金额**却标了「%」。
 *    例：充 200、ratio=0.05 → 显示「+10%」，而实际赠送是 10 元（10% 是巧合）。
 *    若要修，应为 `+{default_bonus_ratio * 100}%` 或 `+¥{customAmount * ratio}`。
 */
import { Descriptions, InputNumber, Typography } from 'antd'
import type { RechargeConfig, RechargePackage } from '../../../../api/payment'
import { calcArrivedAmount } from '../constants'
// ⚠️ 样式在 developer/ 下，本文件在 recharge/components/ → 回退两级
import styles from '../../Recharge.module.css'

const { Text } = Typography

export interface PaymentSummaryProps {
  selectedPackage: RechargePackage | null
  customAmount: number | null
  rechargeConfig: RechargeConfig | null
  onCustomAmountChange: (value: number | null) => void
}

export function PaymentSummary({
  selectedPackage,
  customAmount,
  rechargeConfig,
  onCustomAmountChange,
}: PaymentSummaryProps) {
  const customRatio = rechargeConfig?.default_bonus_ratio ?? 0

  return (
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
            <Text strong className={styles.payAmount}>
              ¥{selectedPackage.price.toFixed(2)}
            </Text>
          </Descriptions.Item>
          <Descriptions.Item label="实际到账">
            <Text type="success">¥{calcArrivedAmount(selectedPackage)}</Text>
          </Descriptions.Item>
        </>
      ) : (
        <>
          <Descriptions.Item label="充值金额">
            <InputNumber
              min={rechargeConfig?.min_amount || 1}
              max={rechargeConfig?.max_amount || 10000}
              value={customAmount}
              onChange={onCustomAmountChange}
              prefix="¥"
              style={{ width: 150 }}
              placeholder={`${rechargeConfig?.min_amount || 1} - ${rechargeConfig?.max_amount || 10000}`}
            />
          </Descriptions.Item>
          <Descriptions.Item label="赠送金额">
            {rechargeConfig && customRatio > 0 ? (
              // ⚠️ 见文件顶部「已知显示缺陷」：这里把金额当成了百分比
              <Text type="warning">+{(customAmount || 0) * customRatio}%</Text>
            ) : (
              '无'
            )}
          </Descriptions.Item>
          <Descriptions.Item label="实际到账">
            {rechargeConfig && customRatio > 0 ? (
              <Text type="success">¥{((customAmount || 0) * (1 + customRatio)).toFixed(2)}</Text>
            ) : (
              <Text type="success">¥{(customAmount || 0).toFixed(2)}</Text>
            )}
          </Descriptions.Item>
        </>
      )}
    </Descriptions>
  )
}
