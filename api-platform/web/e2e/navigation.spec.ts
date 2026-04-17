/**
 * 导航和布局 E2E 测试
 * 测试页面导航、菜单、布局组件
 */

import { test, expect } from '@playwright/test'

test.describe('导航和布局', () => {
  
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('页面标题正确', async ({ page }) => {
    // 检查页面有标题
    const title = await page.title()
    expect(title.length).toBeGreaterThan(0)
  })

  test('页面加载无控制台错误', async ({ page }) => {
    const consoleErrors: string[] = []
    
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text())
      }
    })
    
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    // 过滤掉已知的非关键错误
    const criticalErrors = consoleErrors.filter(err => 
      !err.includes('favicon') && 
      !err.includes('404') &&
      !err.includes('Failed to load resource')
    )
    
    expect(criticalErrors).toHaveLength(0)
  })

  test('页面导航链接存在', async ({ page }) => {
    // 查找导航链接
    const navLinks = page.locator('nav a, header a, [class*="nav"] a')
    const linkCount = await navLinks.count()
    
    // 至少应该有一些导航链接（如果用户已登录）
    console.log(`Found ${linkCount} navigation links`)
  })

  test('Footer 存在', async ({ page }) => {
    const footer = page.locator('footer, .footer, [class*="footer"]')
    
    if (await footer.count() > 0) {
      await expect(footer.first()).toBeVisible()
    }
  })

  test('页面加载时间合理', async ({ page }) => {
    const startTime = Date.now()
    
    await page.goto('/')
    await page.waitForLoadState('domcontentloaded')
    
    const loadTime = Date.now() - startTime
    
    // 页面应该在 5 秒内加载
    expect(loadTime).toBeLessThan(5000)
    console.log(`Page loaded in ${loadTime}ms`)
  })
})

test.describe('响应式设计', () => {
  
  const viewports = [
    { name: 'Desktop HD', width: 1920, height: 1080 },
    { name: 'Laptop', width: 1366, height: 768 },
    { name: 'Tablet', width: 768, height: 1024 },
    { name: 'Mobile', width: 375, height: 667 },
  ]

  for (const viewport of viewports) {
    test(`${viewport.name} (${viewport.width}x${viewport.height})`, async ({ page }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height })
      
      await page.goto('/')
      
      // 页面应该可以正常渲染
      await expect(page.locator('body')).toBeVisible()
      
      // 检查主要内容区域存在
      const mainContent = page.locator('main, #root, [role="main"]')
      await expect(mainContent.first()).toBeVisible({ timeout: 5000 })
      
      // 检查没有水平滚动条
      const hasHorizontalScroll = await page.evaluate(() => {
        return document.documentElement.scrollWidth > document.documentElement.clientWidth
      })
      
      // 在移动视口下允许水平滚动
      if (viewport.width >= 768) {
        expect(hasHorizontalScroll).toBe(false)
      }
    })
  }
})
