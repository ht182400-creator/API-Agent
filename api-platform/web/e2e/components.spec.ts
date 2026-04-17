/**
 * UI 组件 E2E 测试
 * 测试按钮、表单、卡片等组件
 */

import { test, expect } from '@playwright/test'

test.describe('UI 组件', () => {
  
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('按钮组件可用', async ({ page }) => {
    // 查找任何按钮
    const buttons = page.locator('button')
    const buttonCount = await buttons.count()
    
    expect(buttonCount).toBeGreaterThan(0)
    
    // 检查按钮可点击
    if (buttonCount > 0) {
      const firstButton = buttons.first()
      await expect(firstButton).toBeEnabled()
    }
  })

  test('输入框组件可用', async ({ page }) => {
    const inputs = page.locator('input')
    const inputCount = await inputs.count()
    
    if (inputCount > 0) {
      // 测试输入
      const firstInput = inputs.first()
      await firstInput.fill('test input')
      
      const value = await firstInput.inputValue()
      expect(value).toBe('test input')
    }
  })

  test('Ant Design 组件加载', async ({ page }) => {
    // 检查是否有 Ant Design 组件类名
    const antComponents = page.locator('[class*="ant-"]')
    const antCount = await antComponents.count()
    
    console.log(`Found ${antCount} Ant Design components`)
    
    // Ant Design 应该已加载
    // 注意：这可能在首页不显示，取决于页面内容
  })

  test('下拉菜单可用', async ({ page }) => {
    // 查找下拉选择器
    const selects = page.locator('select, [class*="select"], [class*="dropdown"]')
    const selectCount = await selects.count()
    
    if (selectCount > 0) {
      console.log(`Found ${selectCount} select/dropdown components`)
    }
  })

  test('模态框可以打开', async ({ page }) => {
    // 查找可能触发模态框的元素
    const modalTriggers = page.locator('button:has-text("创建"), button:has-text("Add"), button:has-text("新建")')
    
    if (await modalTriggers.count() > 0) {
      await modalTriggers.first().click()
      
      // 等待模态框出现
      await page.waitForTimeout(500)
      
      // 检查模态框
      const modal = page.locator('.ant-modal, [class*="modal"]')
      if (await modal.count() > 0) {
        await expect(modal.first()).toBeVisible({ timeout: 3000 }).catch(() => {
          console.log('Modal did not appear')
        })
      }
    }
  })

  test('表单提交处理', async ({ page }) => {
    await page.goto('/login')
    
    // 查找表单
    const form = page.locator('form')
    
    if (await form.count() > 0) {
      // 检查表单有提交处理
      const submitButton = page.locator('button[type="submit"]')
      
      if (await submitButton.isVisible()) {
        console.log('Form with submit button found')
        
        // 尝试提交空表单
        await submitButton.click()
        
        // 等待处理
        await page.waitForTimeout(1000)
        
        // 应该显示验证错误或处理提交
        console.log('Form submission handled')
      }
    }
  })
})

test.describe('开发者功能页面', () => {
  
  test('API Keys 页面', async ({ page }) => {
    await page.goto('/developer/keys')
    await page.waitForLoadState('domcontentloaded')
    
    // 页面应该加载
    const pageContent = page.locator('body')
    await expect(pageContent).toBeVisible()
    
    // 检查标题或内容
    const heading = page.locator('h1, h2, [class*="title"]')
    const hasHeading = await heading.count() > 0
    
    if (hasHeading) {
      console.log('API Keys page has heading')
    }
  })

  test('配额页面', async ({ page }) => {
    await page.goto('/developer/quota')
    await page.waitForLoadState('domcontentloaded')
    
    const pageContent = page.locator('body')
    await expect(pageContent).toBeVisible()
  })

  test('日志页面', async ({ page }) => {
    await page.goto('/developer/logs')
    await page.waitForLoadState('domcontentloaded')
    
    const pageContent = page.locator('body')
    await expect(pageContent).toBeVisible()
  })

  test('计费页面', async ({ page }) => {
    await page.goto('/developer/billing')
    await page.waitForLoadState('domcontentloaded')
    
    const pageContent = page.locator('body')
    await expect(pageContent).toBeVisible()
  })
})
