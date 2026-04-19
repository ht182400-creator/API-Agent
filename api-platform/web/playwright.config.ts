/**
 * Playwright E2E 测试配置
 * Windows 环境下的前端自动化测试配置
 */

import { defineConfig, devices } from '@playwright/test'

// 环境变量
const BASE_URL = process.env.BASE_URL || 'http://localhost:3000'
const API_URL = process.env.API_URL || 'http://localhost:8000'

export default defineConfig({
  // 测试目录
  testDir: './e2e',
  
  // 全局超时
  timeout: 30000,
  
  // 期望退出码
  expect: {
    timeout: 5000,
  },
  
  // 完整追踪
  fullyParallel: false,
  
  // 失败重试
  retries: process.env.CI ? 2 : 0,
  
  // 工作线程
  workers: 1,
  
  // 报告器
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['list'],
  ],
  
  // 全局预处理
  use: {
    // 基础 URL
    baseURL: BASE_URL,
    
    // 导航超时
    navigationTimeout: 30000,
    
    // 截图
    screenshot: 'only-on-failure',
    
    // 视频
    video: 'retain-on-failure',
    
    // 跟踪
    trace: 'on-first-retry',
    
    // 上下文配置
    viewport: { width: 1280, height: 720 },
    ignoreHTTPSErrors: true,
    
    // 颜色方案
    colorScheme: 'light',
  },
  
  // 项目配置
  projects: [
    // Chromium - Windows 主要浏览器
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        channel: 'chrome',
      },
    },
    
    // Edge
    {
      name: 'edge',
      use: {
        ...devices['Desktop Edge'],
      },
    },
    
    // Firefox
    {
      name: 'firefox',
      use: {
        ...devices['Desktop Firefox'],
      },
    },
  ],
  
  // Web 服务器配置 (启动测试前自动启动后端)
  webServer: process.env.CI ? undefined : {
    command: 'npm run dev',
    url: BASE_URL,
    reuseExistingServer: true,
    timeout: 120 * 1000,
    stdout: 'ignore',
    stderr: 'pipe',
  },
})
