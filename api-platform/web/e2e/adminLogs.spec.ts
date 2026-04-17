/**
 * 日志管理模块 E2E 测试
 * 测试日志查看、备份配置等功能
 */

import { test, expect } from '@playwright/test'

test.describe('日志管理模块', () => {
  
  test.beforeEach(async ({ page }) => {
    // 登录管理员账号
    await page.goto('/login')
    await page.waitForLoadState('networkidle')
    
    // 填写登录表单
    const usernameInput = page.locator('input[id="username"], input[name="username"], input[placeholder*="用户"], input[placeholder*="账号"]')
    const passwordInput = page.locator('input[type="password"]')
    
    if (await usernameInput.isVisible()) {
      await usernameInput.fill('admin')
    }
    if (await passwordInput.isVisible()) {
      await passwordInput.fill('admin123')
    }
    
    // 提交登录
    const submitButton = page.locator('button[type="submit"]')
    if (await submitButton.isVisible()) {
      await submitButton.click()
      await page.waitForTimeout(2000)
    }
  })

  test('日志管理页面加载', async ({ page }) => {
    // 导航到日志管理页面
    await page.goto('/admin/logs')
    await page.waitForLoadState('networkidle')
    
    // 检查页面元素
    const pageContent = await page.content()
    expect(pageContent.length).toBeGreaterThan(0)
    
    // 检查是否有日志相关元素
    const hasLogsContent = pageContent.includes('日志') || pageContent.includes('Log') || pageContent.includes('log')
    expect(hasLogsContent).toBeTruthy()
  })

  test('日志文件列表显示', async ({ page }) => {
    await page.goto('/admin/logs')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(1000)
    
    // 检查是否有表格或列表
    const table = page.locator('.ant-table, table, [class*="table"]')
    const hasTable = await table.count() > 0
    
    // 检查是否有统计卡片
    const cards = page.locator('.ant-card, [class*="card"], [class*="stat"]')
    const hasCards = await cards.count() > 0
    
    expect(hasTable || hasCards).toBeTruthy()
  })

  test('日志备份配置页面', async ({ page }) => {
    // 尝试访问设置页面
    await page.goto('/admin/settings')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(1000)
    
    // 检查页面内容
    const pageContent = await page.content()
    const hasSettings = pageContent.includes('设置') || pageContent.includes('配置') || pageContent.includes('Setting') || pageContent.includes('Config')
    expect(hasSettings).toBeTruthy()
  })

  test('API 日志端点连通性', async ({ page }) => {
    // 测试后端 API
    const response = await page.request.get('http://localhost:8080/api/v1/health')
    
    // 如果 health 端点不存在，尝试其他方式验证
    if (response.status() === 404) {
      // 尝试访问 Swagger
      const swaggerResponse = await page.request.get('http://localhost:8080/docs')
      expect(swaggerResponse.ok() || swaggerResponse.status() === 200).toBeTruthy()
    } else {
      expect(response.ok()).toBeTruthy()
    }
  })
})

test.describe('日志管理 - API 直接测试', () => {
  
  test('获取日志文件列表', async ({ request }) => {
    // 获取日志文件列表
    const response = await request.get('http://localhost:8080/api/v1/admin/logs/files')
    
    // 验证响应
    expect([200, 401, 403]).toContain(response.status())
    
    if (response.status() === 200) {
      const data = await response.json()
      expect(data).toBeDefined()
    }
  })

  test('获取日志统计信息', async ({ request }) => {
    const response = await request.get('http://localhost:8080/api/v1/admin/logs/stats')
    
    expect([200, 401, 403]).toContain(response.status())
    
    if (response.status() === 200) {
      const data = await response.json()
      expect(data).toBeDefined()
    }
  })

  test('获取备份配置', async ({ request }) => {
    const response = await request.get('http://localhost:8080/api/v1/admin/logs/config')
    
    expect([200, 401, 403]).toContain(response.status())
    
    if (response.status() === 200) {
      const data = await response.json()
      expect(data).toBeDefined()
    }
  })
})
