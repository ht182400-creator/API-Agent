/**
 * Vitest 单元测试配置（前端单测）
 *
 * 与 vite.config.ts 分离的原因：
 *   1. vite.config.ts 含端口探测（portfinder）与 dev 代理等运行期配置，跑单测不需要；
 *   2. 单测需要 jsdom 环境 + setup 文件，并且必须**显式排除 e2e/**（Playwright 用例）。
 */
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    // 与 vite.config.ts / tsconfig.json 的 "@/*" 别名保持一致
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    // ⚠️ 必须排除 e2e/：那里的 *.spec.ts 由 `npm run test:e2e`（Playwright）运行，
    //    混进 vitest 会因缺少 Playwright 运行期而全部报错。
    //    tests/** 纳入收集：用例库自检（tests/cases/frontend_cases.spec.ts）放这里。
    include: ['src/**/*.{test,spec}.{ts,tsx}', 'tests/**/*.{test,spec}.{ts,tsx}'],
    exclude: [
      'node_modules/**',
      'dist/**',
      'e2e/**',
      'test-results/**',
      'playwright-report/**',
    ],
    // 单测不需要处理 CSS
    css: false,
    // 用例之间互相隔离：自动恢复/清理 mock
    restoreMocks: true,
    clearMocks: true,
    // 超时（组件渲染在 jsdom 下略慢；全量并行时机器被几十个 worker 压满，慢用例会接近 10s）
    // ⚠️ 配套：`src/test/setup.ts` 里把 Testing Library 的 asyncUtilTimeout 放宽到 3s ——
    //    两处一起才是"慢用例在满载下不假失败"的完整解，详见那里的注释。
    testTimeout: 20000,
    reporters: ['default'],
  },
})
