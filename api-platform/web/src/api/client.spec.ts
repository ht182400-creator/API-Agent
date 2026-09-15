/**
 * API 客户端（请求层）单元测试
 *
 * 为什么优先测它：
 *   所有页面都经由 `src/api/client.ts` 发请求，它决定了
 *   ① 是否带上认证 Token；② 统一响应如何解包；③ 各类错误给用户看什么文案；④ 401 是否自动登出。
 *   这些行为一旦回归，影响面是全站，因此用单测锁死。
 *
 * 实现方式说明：
 *   不引入额外 mock 库，直接替换 axios 的 `adapter`（axios 官方扩展点），
 *   从而在**不启动后端**的前提下覆盖"HTTP 成功 / HTTP 错误 / 网络错误 / 配置错误"四条路径。
 *
 * 用例编号：TC-FE-API-001 ~ TC-FE-API-013
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { AxiosError, type AxiosAdapter, type InternalAxiosRequestConfig } from 'axios'

// logger 只产生副作用（控制台/内存日志），单测中整体替换为 spy，避免噪音
vi.mock('../utils/logger', () => ({
  logger: {
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    logRequest: vi.fn(),
    logResponse: vi.fn(),
    logApiError: vi.fn(),
    setUserId: vi.fn(),
    clearUserId: vi.fn(),
  },
  LogLevel: { DEBUG: 0, INFO: 1, WARN: 2, ERROR: 3 },
}))

import client, { api } from './client'
import { useAuthStore } from '../stores/auth'

/** 记录最近一次请求的 config（用于断言请求拦截器行为） */
let lastConfig: InternalAxiosRequestConfig | undefined

/** 模拟成功响应 */
function mockSuccess(status: number, body: unknown): void {
  client.defaults.adapter = (async (config: InternalAxiosRequestConfig) => {
    lastConfig = config
    return { data: body, status, statusText: 'OK', headers: {}, config }
  }) as AxiosAdapter
}

/** 模拟 HTTP 错误响应（服务端已响应，状态码 >= 400） */
function mockHttpError(status: number, body: unknown): void {
  client.defaults.adapter = (async (config: InternalAxiosRequestConfig) => {
    lastConfig = config
    const response = { data: body, status, statusText: 'ERR', headers: {}, config }
    throw new AxiosError(`Request failed with status code ${status}`, 'ERR_BAD_REQUEST', config, {}, response)
  }) as AxiosAdapter
}

/** 模拟"请求已发出但无响应"（网络中断 / 超时） */
function mockNetworkError(): void {
  client.defaults.adapter = (async (config: InternalAxiosRequestConfig) => {
    lastConfig = config
    throw new AxiosError('Network Error', 'ERR_NETWORK', config, {})
  }) as AxiosAdapter
}

/** 模拟"请求配置错误"（既无 response 也无 request） */
function mockConfigError(): void {
  client.defaults.adapter = (async () => {
    throw new AxiosError('Config Error', 'ERR_CONFIG')
  }) as AxiosAdapter
}

/** 读取请求头中的 Authorization（AxiosHeaders 支持属性访问） */
function authHeader(): unknown {
  return (lastConfig?.headers as any)?.Authorization
}

beforeEach(() => {
  // 每个用例从"未登录"开始，避免相互影响
  useAuthStore.setState({
    user: null,
    accessToken: null,
    refreshToken: null,
    isAuthenticated: false,
  })
  lastConfig = undefined
})

describe('请求拦截器 —— 认证头', () => {
  it('TC-FE-API-001 已登录时注入 Bearer Token', async () => {
    useAuthStore.setState({ accessToken: 'token-abc', isAuthenticated: true })
    mockSuccess(200, { code: 0, message: 'success', data: { ok: true } })

    await api.get('/ping')

    expect(authHeader()).toBe('Bearer token-abc')
  })

  it('TC-FE-API-002 未登录时不带 Authorization（不发送空 Bearer）', async () => {
    mockSuccess(200, { code: 0, message: 'success', data: { ok: true } })

    await api.get('/ping')

    expect(authHeader()).toBeUndefined()
  })
})

describe('响应拦截器 —— 统一响应解包', () => {
  it('TC-FE-API-003 业务成功时自动取出 data 字段', async () => {
    mockSuccess(200, { code: 0, message: 'success', data: { id: 7, name: 'repo' } })

    const result = await api.get<{ id: number; name: string }>('/repo/7')

    expect(result).toEqual({ id: 7, name: 'repo' })
  })

  it('TC-FE-API-004 列表响应（无 code，含 items）原样返回', async () => {
    const listBody = { items: [{ id: 1 }], pagination: { page: 1, page_size: 20, total: 1, total_pages: 1 } }
    mockSuccess(200, listBody)

    const result = await api.get('/repos')

    expect(result).toEqual(listBody)
  })

  it('TC-FE-API-005 业务错误码非 0 → 抛出并携带 code / request_id / userMessage', async () => {
    mockSuccess(200, { code: 42901, message: '请求过于频繁', data: null, request_id: 'req-1' })

    await expect(api.get('/limited')).rejects.toMatchObject({
      code: 42901,
      userMessage: '请求过于频繁',
      request_id: 'req-1',
    })
  })
})

describe('响应拦截器 —— 失败文案映射', () => {
  it('TC-FE-API-006 401 触发自动登出（Token 被清空）', async () => {
    useAuthStore.setState({ accessToken: 'expired-token', isAuthenticated: true })
    mockHttpError(401, { message: '登录已过期' })

    await expect(api.get('/protected')).rejects.toBeTruthy()

    // 行为断言：登出后 token 必须被清空（这是 401 分支的核心副作用）
    expect(useAuthStore.getState().accessToken).toBeNull()
    expect(useAuthStore.getState().isAuthenticated).toBe(false)
  })

  it('TC-FE-API-007 401 但 URL 属于 /auth/（登录接口本身）→ 不登出', async () => {
    useAuthStore.setState({ accessToken: 'keep-me', isAuthenticated: true })
    mockHttpError(401, { message: '用户名或密码错误' })

    await expect(api.post('/auth/login', {})).rejects.toBeTruthy()

    expect(useAuthStore.getState().accessToken).toBe('keep-me')
  })

  it.each([
    [400, '请求参数错误', '数据验证失败，请检查输入'],
    [403, '无权限访问', '您没有权限执行此操作'],
    [404, '资源不存在', '请求的资源不存在'],
    [422, '数据验证失败', '数据格式不正确'],
    [429, '请求过于频繁', '请求过于频繁，请稍后再试'],
    [500, '服务器错误', '服务器开小差了，请稍后重试'],
    [502, '服务暂时不可用', '服务暂时不可用，请稍后重试'],
    [503, '服务暂时不可用', '服务暂时不可用，请稍后重试'],
    [504, '服务暂时不可用', '服务暂时不可用，请稍后重试'],
    [418, '请求失败 (418)', '操作失败 (418)'],
  ])('TC-FE-API-008 HTTP %s → message=%s / userMessage=%s', async (status, message, userMessage) => {
    mockHttpError(status as number, {})  // 无 message 字段 → 走状态码默认文案

    await expect(api.get('/x')).rejects.toMatchObject({ message, userMessage })
  })

  it('TC-FE-API-009 后端返回 message 时优先采用（不被默认文案覆盖）', async () => {
    mockHttpError(400, { message: '余额不足，请先充值' })

    await expect(api.get('/x')).rejects.toMatchObject({
      message: '余额不足，请先充值',
      userMessage: '余额不足，请先充值',
    })
  })

  it('TC-FE-API-010 后端返回 detail（FastAPI 校验错误）时同样被采用', async () => {
    mockHttpError(422, { detail: 'field required' })

    await expect(api.get('/x')).rejects.toMatchObject({ message: 'field required' })
  })

  it('TC-FE-API-011 网络错误（无响应）→ 网络连接失败', async () => {
    mockNetworkError()

    await expect(api.get('/x')).rejects.toMatchObject({
      message: '网络连接失败',
      userMessage: '网络连接失败，请检查网络',
    })
  })

  it('TC-FE-API-012 请求配置错误（无响应且无请求）→ 请求配置错误', async () => {
    mockConfigError()

    await expect(api.get('/x')).rejects.toMatchObject({ message: '请求配置错误' })
  })
})

describe('请求方法封装', () => {
  it('TC-FE-API-013 post/put/delete/patch 同样解包 data', async () => {
    const payload = { code: 0, message: 'success', data: { done: true } }

    mockSuccess(200, payload)
    await expect(api.post('/x', {})).resolves.toEqual({ done: true })

    mockSuccess(200, payload)
    await expect(api.put('/x', {})).resolves.toEqual({ done: true })

    mockSuccess(200, payload)
    await expect(api.delete('/x')).resolves.toEqual({ done: true })

    mockSuccess(200, payload)
    await expect(api.patch('/x', {})).resolves.toEqual({ done: true })
  })
})
