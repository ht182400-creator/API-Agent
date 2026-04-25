/**
 * 设备检测 Hook
 * 用于检测当前设备类型和屏幕尺寸
 * 
 * 使用示例：
 * ```typescript
 * const { deviceType, isMobile, isTablet, isDesktop, screenSize } = useDevice()
 * 
 * if (isMobile) {
 *   // 移动端逻辑
 * }
 * ```
 */

import { useState, useEffect, useCallback } from 'react'

// 设备类型枚举
export type DeviceType = 'mobile' | 'tablet' | 'desktop' | 'largeDesktop'

// 屏幕尺寸接口
export interface ScreenSize {
  width: number
  height: number
}

// Hook 返回值接口
export interface DeviceInfo {
  deviceType: DeviceType
  isMobile: boolean
  isTablet: boolean
  isDesktop: boolean
  isLargeDesktop: boolean
  screenSize: ScreenSize
  isPortrait: boolean  // 是否竖屏
  isLandscape: boolean // 是否横屏
}

// 断点配置（与 breakpoints.css 保持一致）
const BREAKPOINTS = {
  mobile: 576,   // 手机 < 576px
  tablet: 768,   // 平板 < 768px（修复：table → tablet）
  desktop: 992,  // 桌面 < 992px
  largeDesktop: 1200, // 大桌面 < 1200px
  // >= 1200px 为超大桌面
} as const

/**
 * 根据宽度获取设备类型
 * @param width - 屏幕宽度
 * @returns 设备类型
 */
function getDeviceType(width: number): DeviceType {
  if (width < BREAKPOINTS.mobile) {
    // < 576px → 手机
    return 'mobile'
  } else if (width < BREAKPOINTS.tablet) {
    // 576px ~ 767px → 平板
    return 'tablet'
  } else if (width < BREAKPOINTS.desktop) {
    // 768px ~ 991px → 桌面
    return 'desktop'
  } else {
    // >= 992px → 大桌面
    return 'largeDesktop'
  }
}

/**
 * 设备检测 Hook
 * @returns 设备信息对象
 */
export function useDevice(): DeviceInfo {
  // 初始化状态
  const [deviceType, setDeviceType] = useState<DeviceType>(() => 
    getDeviceType(typeof window !== 'undefined' ? window.innerWidth : 1024)
  )
  const [screenSize, setScreenSize] = useState<ScreenSize>({
    width: typeof window !== 'undefined' ? window.innerWidth : 1024,
    height: typeof window !== 'undefined' ? window.innerHeight : 768,
  })

  // 处理窗口大小变化
  const handleResize = useCallback(() => {
    const width = window.innerWidth
    const height = window.innerHeight
    
    setDeviceType(getDeviceType(width))
    setScreenSize({ width, height })
  }, [])

  // 监听窗口大小变化
  useEffect(() => {
    // 初始化
    handleResize()
    
    // 添加事件监听
    window.addEventListener('resize', handleResize)
    
    // 横竖屏切换监听
    window.addEventListener('orientationchange', handleResize)
    
    // 清理监听器
    return () => {
      window.removeEventListener('resize', handleResize)
      window.removeEventListener('orientationchange', handleResize)
    }
  }, [handleResize])

  // 计算派生状态
  const isMobile = deviceType === 'mobile'
  const isTablet = deviceType === 'tablet'
  const isDesktop = deviceType === 'desktop' || deviceType === 'largeDesktop'
  const isLargeDesktop = deviceType === 'largeDesktop'
  const isPortrait = screenSize.height > screenSize.width
  const isLandscape = screenSize.width > screenSize.height

  return {
    deviceType,
    isMobile,
    isTablet,
    isDesktop,
    isLargeDesktop,
    screenSize,
    isPortrait,
    isLandscape,
  }
}

/**
 * 平台检测 Hook
 * 检测当前操作系统
 */
export function usePlatform() {
  const [platform, setPlatform] = useState<'ios' | 'android' | 'windows' | 'mac' | 'other'>('other')

  useEffect(() => {
    const userAgent = navigator.userAgent || navigator.vendor || (window as any).opera || ''
    const isIOS = /iPad|iPhone|iPod/.test(userAgent) && !(window as any).MSStream
    const isAndroid = /Android/.test(userAgent)
    const isWindows = /Win/.test(userAgent)
    const isMac = /Mac/.test(userAgent)

    if (isIOS) {
      setPlatform('ios')
    } else if (isAndroid) {
      setPlatform('android')
    } else if (isWindows) {
      setPlatform('windows')
    } else if (isMac) {
      setPlatform('mac')
    } else {
      setPlatform('other')
    }
  }, [])

  return {
    platform,
    isIOS: platform === 'ios',
    isAndroid: platform === 'android',
    isWindows: platform === 'windows',
    isMac: platform === 'mac',
    isMobile: platform === 'ios' || platform === 'android',
  }
}

/**
 * 断点判断 Hook
 * 判断当前屏幕是否小于某个断点
 * 
 * 使用示例：
 * ```typescript
 * const isBelowMobile = useBreakpoint('mobile') // < 576px
 * const isBelowTablet = useBreakpoint('tablet')  // < 768px
 * ```
 */
export function useBreakpoint(breakpoint: keyof typeof BREAKPOINTS): boolean {
  const { screenSize } = useDevice()
  return screenSize.width < BREAKPOINTS[breakpoint]
}

/**
 * 响应式值 Hook
 * 根据屏幕大小返回不同的值
 * 
 * 使用示例：
 * ```typescript
 * const columns = useResponsiveValue({
 *   mobile: 1,
 *   tablet: 2,
 *   desktop: 3,
 *   default: 4,
 * })
 * ```
 */
export function useResponsiveValue<T>(values: {
  mobile?: T
  table?: T
  desktop?: T
  largeDesktop?: T
  default: T
}): T {
  const { deviceType } = useDevice()

  switch (deviceType) {
    case 'mobile':
      return values.mobile ?? values.default
    case 'tablet':
      return values.tablet ?? values.default
    case 'desktop':
      return values.desktop ?? values.default
    case 'largeDesktop':
      return values.largeDesktop ?? values.default
    default:
      return values.default
  }
}
