/**
 * 支付摘要区 —— P1-4 前端拆分第 4 步（展示组件 2/3）
 *
 * 展示「充值方式 / 赠送金额 / 支付金额 / 实际到账」；
 * 自定义金额模式下改为「充值金额输入 + 赠送 + 实际到账」。
 *
 * 纯展示 + 一个受控输入：不持有状态，金额与回调由父组件传入。
 *
 * ⚠️ 已修复的显示缺陷（TC-FE-RECHARGE-015 覆盖）：
 *    自定义模式的「赠送金额」原写作 `+{(customAmount||0) * default_bonus_ratio}%`，
 *    但 `default_bonus_ratio` 是**小数**（0.05）—— 算出的是**金额**却标了「%」，
 *    于是一个"不可能正确的百分比"会随充值额变化：
 *      充 200 → 显示「+10%」、充 500 → 显示「+25%」（实际恒为 5%，前面看着对纯属巧合）。
 *    现改为 `+{ratio * 100}%`。
 *
 * ⚠️ 字段语义差异（写错的根源，务必区分）：
 *    - `rechargeConfig.default_bonus_ratio` = **小数**（0.05 表示 5%）
 *    - `RechargePackage.bonus_ratio`       = **百分数**（10 表示 10%，见 calcArrivedAmount 的 `/100`）
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
              // 比例与充值额无关：0.05 → +5%
              <Text type="warning">+{customRatio * 100}%</Text>
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
