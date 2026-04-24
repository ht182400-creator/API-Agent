/**
 * 仓库图标组件 - V5.0 新增
 * 显示自定义图标或默认图标
 * 支持仓库类型对应的默认图标
 */

import React from 'react'
import {
  TranslationOutlined,
  CameraOutlined,
  StockOutlined,
  CustomerServiceOutlined,
  RobotOutlined,
  ApiOutlined,
  ShopOutlined,
} from '@ant-design/icons'

// 仓库类型到图标的映射
const typeIconMap: Record<string, React.ReactNode> = {
  translation: <TranslationOutlined />,
  vision: <CameraOutlined />,
  stock: <StockOutlined />,
  psychology: <CustomerServiceOutlined />,
  ai: <RobotOutlined />,
  custom: <ApiOutlined />,
}

// 仓库类型对应的背景颜色
const typeColorMap: Record<string, string> = {
  translation: '#3b82f6',  // 蓝色
  vision: '#8b5cf6',       // 紫色
  stock: '#f59e0b',       // 琥珀色
  psychology: '#ec4899',   // 粉色
  ai: '#10b981',          // 绿色
  custom: '#6b7280',      // 灰色
}

interface RepoLogoProps {
  logoUrl?: string  // 自定义图标 URL
  repoType?: string  // 仓库类型
  size?: number      // 图标尺寸，默认 48
  className?: string
}

export const RepoLogo: React.FC<RepoLogoProps> = ({
  logoUrl,
  repoType = 'custom',
  size = 48,
  className,
}) => {
  // 获取默认图标和颜色
  const defaultIcon = typeIconMap[repoType] || <ShopOutlined />
  const bgColor = typeColorMap[repoType] || '#6b7280'

  // 如果有自定义图标，显示自定义图标
  if (logoUrl) {
    return (
      <div
        className={className}
        style={{
          width: size,
          height: size,
          borderRadius: size * 0.2,
          overflow: 'hidden',
          background: '#fff',
          boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
        }}
      >
        <img
          src={logoUrl}
          alt="仓库图标"
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
          }}
          onError={(e) => {
            // 图片加载失败时显示默认图标
            const target = e.target as HTMLImageElement
            target.style.display = 'none'
            target.nextElementSibling?.removeAttribute('style')
          }}
        />
        {/* 备用默认图标（图片加载失败时显示） */}
        <div
          style={{
            width: '100%',
            height: '100%',
            background: `linear-gradient(135deg, ${bgColor}15, ${bgColor}25)`,
            color: bgColor,
            fontSize: size * 0.5,
            display: 'none',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          {defaultIcon}
        </div>
      </div>
    )
  }

  // 显示默认图标
  return (
    <div
      className={className}
      style={{
        width: size,
        height: size,
        borderRadius: size * 0.2,
        background: `linear-gradient(135deg, ${bgColor}20, ${bgColor}35)`,
        color: bgColor,
        fontSize: size * 0.5,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        boxShadow: `0 2px 8px ${bgColor}30`,
      }}
    >
      {defaultIcon}
    </div>
  )
}

export default RepoLogo
