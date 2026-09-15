/**
 * 前后端联测（API 契约测试）
 *
 * 为什么需要它 —— 单测与后端测试之间有一条**缝隙**：
 *   - 前端单测用 mock adapter，不碰真后端（`src/api/client.spec.ts`）；
 *   - 后端测试只保证自己的响应模型内部自洽。
 * 一旦契约改名（如 `data` → `result`、`pagination` → 扁平字段、token 字段拼写变化），
 * 两边测试都还是绿的，但页面会白屏或分页失效。本套用例直接打**真后端**，
 * 用前端代码里声明的类型去校验真实响应，专门堵这条缝。
 *
 * 前置条件：
 *   后端需在 API_URL（默认 http://localhost:8000）运行；账号使用
 *   `scripts/init_db_with_data.py` 的种子账号（可用环境变量覆盖）。
 *   **后端未启动时整组自动跳过**（不误报为失败）。
 *
 * 运行：`npm run test:e2e -- api-contract`（或 `npx playwright test e2e/api-contract.spec.ts`）
 *
 * 用例编号：TC-E2E-API-001 ~ TC-E2E-API-012
 */
import { test, expect } from '@playwright/test'

const API_URL = process.env.API_URL || 'http://localhost:8000'
const API_PREFIX = '/api/v1'
const WEB_ORIGIN = process.env.BASE_URL || 'http://localhost:3000'

// 种子账号（与 scripts/init_db_with_data.py 一致，可用环境变量覆盖）
const ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL || 'admin@example.com'
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD || 'admin123'

let backendReady = false

test.beforeAll(async ({ request }) => {
  try {
    const res = await request.get(`${API_URL}/health`, { timeout: 5000 })
    backendReady = res.ok()
  } catch {
    backendReady = false
  }
  if (!backendReady) {
    test.skip(true, `后端未启动（${API_URL}），跳过前后端联测`)
  }
})

/** 登录并返回 access_token（多个用例复用） */
async function login(request: any): Promise<string> {
  const res = await request.post(`${API_URL}${API_PREFIX}/auth/login`, {
    data: { email: ADMIN_EMAIL, password: ADMIN_PASSWORD },
  })
  expect(res.status(), '登录接口应返回 200（请确认种子账号已初始化）').toBe(200)
  const body = await res.json()
  expect(body.data?.access_token, '登录响应应包含 access_token').toBeTruthy()
  return body.data.access_token as string
}

test.describe('前后端契约联测', () => {
  test('TC-E2E-API-001 /health 存活探针契约（前端环境徽标依赖）', async ({ request }) => {
    const res = await request.get(`${API_URL}/health`)
    expect(res.status()).toBe(200)

    const body = await res.json()
    // 前端 Layout 顶栏环境徽标 + 生产警示条依赖这两个字段
    expect(body).toHaveProperty('billing_environment')
    expect(['simulation', 'production']).toContain(body.billing_environment)
    expect(typeof body.is_production).toBe('boolean')
  })

  test('TC-E2E-API-002 /ready 就绪探针（DB 必需）', async ({ request }) => {
    const res = await request.get(`${API_URL}/ready`)
    expect(res.status()).toBe(200)
  })

  test('TC-E2E-API-003 响应头携带环境标识', async ({ request }) => {
    const res = await request.get(`${API_URL}/health`)
    const headers = res.headers()
    // 约定：中间件统一注入，便于排查"这份响应来自哪个环境"
    expect(headers['x-environment']).toBeTruthy()
    expect(headers['x-billing-environment']).toBeTruthy()
  })

  test('TC-E2E-API-004 未认证访问受保护接口 → 401', async ({ request }) => {
    const res = await request.get(`${API_URL}${API_PREFIX}/auth/me`)
    expect(res.status()).toBe(401)
  })

  test('TC-E2E-API-005 登录响应契约与前端 TokenResponse 对齐', async ({ request }) => {
    const res = await request.post(`${API_URL}${API_PREFIX}/auth/login`, {
      data: { email: ADMIN_EMAIL, password: ADMIN_PASSWORD },
    })
    expect(res.status()).toBe(200)

    const body = await res.json()
    // 统一响应包装（前端 client.ts 依赖 code / message / data / request_id）
    expect(body).toHaveProperty('code')
    expect(body.code).toBe(0)
    expect(body).toHaveProperty('message')

    // data 即前端 `TokenResponse`（字段名与类型必须完全一致）
    const data = body.data
    expect(typeof data.access_token).toBe('string')
    expect(typeof data.refresh_token).toBe('string')
    expect(typeof data.expires_in).toBe('number')
    expect(data.access_token.length).toBeGreaterThan(10)
  })

  test('TC-E2E-API-006 登录失败可被前端解析出可展示文案', async ({ request }) => {
    const res = await request.post(`${API_URL}${API_PREFIX}/auth/login`, {
      data: { email: ADMIN_EMAIL, password: 'definitely-wrong-password' },
    })

    expect(res.ok(), '错误密码不应返回 2xx').toBeFalsy()

    const body = await res.json().catch(() => ({}))
    // 前端 client.ts 的错误分支优先读 message / detail，二者至少有其一才谈得上"友好提示"
    const hasMessage = typeof body.message === 'string' && body.message.length > 0
    const hasDetail = body.detail !== undefined
    expect(hasMessage || hasDetail, '错误响应必须含 message 或 detail').toBe(true)
  })

  test('TC-E2E-API-007 /auth/me 契约与前端 User 接口对齐', async ({ request }) => {
    const token = await login(request)

    const res = await request.get(`${API_URL}${API_PREFIX}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    expect(res.status()).toBe(200)

    const body = await res.json()
    expect(body.code).toBe(0)

    const user = body.data
    // 前端 `src/api/auth.ts` 的 User 接口字段
    expect(typeof user.id).toBe('string')
    expect(typeof user.email).toBe('string')
    expect(user).toHaveProperty('user_type')
    expect(user).toHaveProperty('role')
    expect(Array.isArray(user.permissions)).toBe(true)
  })

  test('TC-E2E-API-008 分页契约与前端 PaginatedResponse 对齐', async ({ request }) => {
    const token = await login(request)

    const res = await request.get(`${API_URL}${API_PREFIX}/repositories?page=1&page_size=5`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    expect(res.status()).toBe(200)

    const body = await res.json()
    expect(body.code).toBe(0)

    // 前端 `PaginatedResponse<T> = { items, pagination }`（src/api/client.ts）
    expect(Array.isArray(body.data.items)).toBe(true)
    const pagination = body.data.pagination
    expect(pagination).toBeTruthy()
    for (const key of ['page', 'page_size', 'total', 'total_pages']) {
      expect(typeof pagination[key], `分页字段缺少或类型不符: ${key}`).toBe('number')
    }
    expect(pagination.page).toBe(1)
    expect(pagination.page_size).toBe(5)
  })

  test('TC-E2E-API-009 参数校验失败 → 422（前端按"数据格式不正确"提示）', async ({ request }) => {
    const token = await login(request)

    // page_size 上限为 100（后端 Query(le=100)）
    const res = await request.get(`${API_URL}${API_PREFIX}/repositories?page=1&page_size=1000`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    expect(res.status()).toBe(422)
  })

  test('TC-E2E-API-010 未知路由 → 404', async ({ request }) => {
    const res = await request.get(`${API_URL}${API_PREFIX}/__not_exists__`)
    expect([404, 401]).toContain(res.status())
  })

  test('TC-E2E-API-011 CORS 预检允许前端源（联调必需）', async ({ request }) => {
    const res = await request.fetch(`${API_URL}${API_PREFIX}/auth/login`, {
      method: 'OPTIONS',
      headers: {
        Origin: WEB_ORIGIN,
        'Access-Control-Request-Method': 'POST',
        'Access-Control-Request-Headers': 'content-type,authorization',
      },
    })

    // 后端 CORS 中间件应放行预检并回显允许源
    expect(res.status()).toBeLessThan(400)
    const allowOrigin = res.headers()['access-control-allow-origin']
    expect(allowOrigin, 'CORS 预检必须回显 access-control-allow-origin').toBeTruthy()
  })

  test('TC-E2E-API-012 登出接口契约（前端 authApi.logout 依赖）', async ({ request }) => {
    const token = await login(request)

    const res = await request.post(`${API_URL}${API_PREFIX}/auth/logout`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    expect(res.status()).toBe(200)

    const body = await res.json()
    expect(body.code).toBe(0)
  })
})
