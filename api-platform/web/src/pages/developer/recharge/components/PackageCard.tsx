/**
 * 充值套餐卡片 —— P1-4 前端拆分第 4 步（展示组件 1/N）
 *
 * 纯展示组件：**不含任何状态与副作用**，选中态与点击回调全部由父组件传入。
 * 这样它既能被套餐列表复用，也能单独单测/截图。
 *
 * ⚠️ "实际到账"的算法与主页面摘要区（支付金额/实际到账那一段）**用的是同一个式子**，
 *    改动时必须两处一起改（后续可考虑提到共享常量里）。
 */
import { Card, Tag, Typography } from 'antd'
import { GiftOutlined, CheckCircleOutlined } from '@ant-design/icons'
import { RechargePackage } from '../../../../api/payment'
import { calcArrivedAmount } from '../constants'
// ⚠️ 注意层级：本组件在 recharge/components/ 下，而样式文件在 developer/ 下 → 需要回退两级
import styles from '../../Recharge.module.css'

const { Text, Paragraph } = Typography

export interface PackageCardProps {
  pkg: RechargePackage
  /** 是否当前选中 */
  selected: boolean
  /** 点击卡片（父组件负责切换选中态） */
  onSelect: (pkg: RechargePackage) => void
}

export function PackageCard({ pkg, selected, onSelect }: PackageCardProps) {
  const hasBonus = pkg.bonus_amount > 0 || pkg.bonus_ratio > 0

  return (
    <Card
      className={`${styles.packageCard} ${selected ? styles.selected : ''} ${pkg.is_featured ? styles.featured : ''}`}
      hoverable
      onClick={() => onSelect(pkg)}
    >
      {pkg.is_featured && (
        <div className={styles.featuredTag}>
          <GiftOutlined /> 推荐
        </div>
      )}

      <div className={styles.packageHeader}>
        <Text strong className={styles.packageName}>
          {pkg.name}
        </Text>
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
            <>
              实际到账：
              <Text strong>¥{calcArrivedAmount(pkg)}</Text>
            </>
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

      {selected && (
        <div className={styles.selectedIndicator}>
          <CheckCircleOutlined /> 已选择
        </div>
      )}
    </Card>
  )
}
