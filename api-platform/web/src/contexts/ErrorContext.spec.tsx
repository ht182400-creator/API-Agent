/**
 * 全局错误处理（ErrorContext.tsx）测试
 *
 * 为什么优先测它（P0）：
 *   所有页面的失败路径最终都经过这里 —— 状态码分类错了会把"数据验证失败"显示成"服务器故障"，
 *   让用户做错下一步动作；认证错误码文案错了，用户无法判断该重新登录还是该换 API Key。
 *   其核心（分类 / 文案提取 / 认证码映射 / 兜底文案表）都是纯函数，最适合单测；
 *   再补三条组件级（Provider 外抛错、弹窗标题与消息、普通错误兜底）。
 *
 * 用例编号：TC-FE-ERRCTX-001 ~ TC-FE-ERRCTX-013
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

vi.mock('../utils/logger', () => ({
  logger: {
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    setUserId: vi.fn(),
    clearUserId: vi.fn(),
  },
  LogLevel: { DEBUG: 0, INFO: 1, WARN: 2, ERROR: 3 },
}))

import {
  ErrorProvider,
  ErrorType,
  errorConfigs,
  extractErrorMessage,
  getAuthErrorConfig,
  parseErrorType,
  useError,
} from './ErrorContext'

/** 构造 axios 形状的错误对象 */
function httpError(status: number, data?: unknown, message = 'request failed') {
  return { response: { status, data }, message }
}

describe('parseErrorType（状态码 → 错误类型）', () => {
  it('TC-FE-ERRCTX-001: 状态码分类矩阵', () => {
    const cases: Array<[unknown, ErrorType, string]> = [
      [httpError(401), ErrorType.AUTH, '未认证'],
      [httpError(403), ErrorType.AUTH, '无权限也归入认证'],
      [httpError(404), ErrorType.NOT_FOUND, '资源不存在'],
      [httpError(410), ErrorType.NOT_FOUND, '已删除'],
      [httpError(422), ErrorType.VALIDATION, '参数校验失败'],
      [httpError(400), ErrorType.VALIDATION, '普通 400'],
      [httpError(429), ErrorType.BUSINESS, '限流算业务限制'],
      [httpError(500), ErrorType.SERVER, '服务器错误'],
      [httpError(502), ErrorType.SERVER, '网关错误'],
      [httpError(504), ErrorType.SERVER, '网关超时'],
      [{ status: 0 }, ErrorType.NETWORK, '网络中断'],
      // ✅ 已修（用例库 FE-BUG-ERRCTX-ECONNABORTED）：axios 把超时/网络类错误码放在
      //    `error.code` 上而非 status，现在会显式识别下列错误码 —— 这几条即回归防线。
      [{ code: 'ECONNABORTED' }, ErrorType.NETWORK, '请求超时'],
      [{ code: 'ETIMEDOUT' }, ErrorType.NETWORK, '连接超时'],
      [{ code: 'ERR_NETWORK' }, ErrorType.NETWORK, '网络不可达'],
      [{ code: 'ERR_CONNECTION_REFUSED' }, ErrorType.NETWORK, '连接被拒绝'],
      // 非网络类错误码不受影响，仍按状态码/关键词判断
      [{ code: 'ERR_BAD_REQUEST' }, ErrorType.UNKNOWN, '其它错误码不应被误判为网络问题'],
    ]

    cases.forEach(([err, expected, reason]) => {
      expect(parseErrorType(err), reason).toBe(expected)
    })
  })

  it('TC-FE-ERRCTX-002: 400 且携带 4xxxx 业务码时归类为业务错误', () => {
    expect(parseErrorType(httpError(400, { code: 42901 }))).toBe(ErrorType.BUSINESS)
    // 业务码区间外仍是参数校验
    expect(parseErrorType(httpError(400, { code: 1234 }))).toBe(ErrorType.VALIDATION)
    expect(parseErrorType(httpError(400, { code: 50000 }))).toBe(ErrorType.VALIDATION)
  })

  it('TC-FE-ERRCTX-003: 无状态码时按消息关键词兜底', () => {
    expect(parseErrorType({ message: 'Network Error' })).toBe(ErrorType.NETWORK)
    expect(parseErrorType({ message: '请求超时，连接失败' })).toBe(ErrorType.NETWORK)
    expect(parseErrorType({ message: '登录已过期' })).toBe(ErrorType.AUTH)
    expect(parseErrorType({ message: 'invalid token' })).toBe(ErrorType.AUTH)
    expect(parseErrorType({ message: '余额不足' })).toBe(ErrorType.BUSINESS)
    expect(parseErrorType({ message: '库存不足' })).toBe(ErrorType.UNKNOWN)
  })

  it('TC-FE-ERRCTX-004: 空输入兜底为 UNKNOWN 且不抛错', () => {
    expect(parseErrorType(null)).toBe(ErrorType.UNKNOWN)
    expect(parseErrorType(undefined)).toBe(ErrorType.UNKNOWN)
    expect(parseErrorType({})).toBe(ErrorType.UNKNOWN)
  })
})

describe('extractErrorMessage（可展示文案）', () => {
  it('TC-FE-ERRCTX-005: 后端 message 优先，其次 detail', () => {
    expect(extractErrorMessage(httpError(400, { message: '余额不足，请先充值' }))).toBe(
      '余额不足，请先充值'
    )
    expect(extractErrorMessage(httpError(422, { detail: 'field required' }))).toBe('field required')
    // message 优先于 detail
    expect(extractErrorMessage(httpError(400, { message: 'A', detail: 'B' }))).toBe('A')
  })

  it('TC-FE-ERRCTX-006: 超过 200 字符的文案被截断（避免弹窗被超长堆栈撑爆）', () => {
    const long = 'x'.repeat(500)
    const out = extractErrorMessage(httpError(400, { message: long }))
    expect(out).toHaveLength(203)
    expect(out.endsWith('...')).toBe(true)

    // 非字符串 message（对象）走 JSON.stringify，同样受限
    const objOut = extractErrorMessage(httpError(400, { message: { a: 1 } }))
    expect(objOut).toBe('{"a":1}')
  })

  it('TC-FE-ERRCTX-007: 无可用字段时给出可读兜底', () => {
    expect(extractErrorMessage(null)).toBe('未知错误')
    expect(extractErrorMessage({ response: { status: 500, data: {} }, message: '' })).toBe('操作失败')
  })
})

describe('getAuthErrorConfig（认证错误码 → 弹窗文案）', () => {
  it('TC-FE-ERRCTX-008: 五个认证错误码各有专属标题', () => {
    const cases: Array<[number, string]> = [
      [40101, '登录失败'],
      [40102, '登录已过期'],
      [40103, 'API Key已禁用'],
      [40104, 'API Key已过期'],
      [40105, 'API Key无效'],
    ]

    cases.forEach(([code, title]) => {
      const config = getAuthErrorConfig(httpError(401, { code }))
      expect(config.title, `code=${code}`).toBe(title)
      expect(config.subTitle).toBeTruthy()
      expect(config.showLogout).toBe(true)
    })
  })

  it('TC-FE-ERRCTX-009: 未登记的认证错误码走默认「登录已过期」', () => {
    expect(getAuthErrorConfig(httpError(401, { code: 99999 })).title).toBe('登录已过期')
    expect(getAuthErrorConfig(null).title).toBe('登录已过期')
  })
})

describe('errorConfigs（兜底文案表完整性）', () => {
  it('TC-FE-ERRCTX-010: 七种错误类型都有标题与副标题', () => {
    const types = [
      ErrorType.AUTH,
      ErrorType.VALIDATION,
      ErrorType.NETWORK,
      ErrorType.SERVER,
      ErrorType.NOT_FOUND,
      ErrorType.BUSINESS,
      ErrorType.UNKNOWN,
    ]

    types.forEach((type) => {
      expect(errorConfigs[type], `${type} 缺失配置`).toBeTruthy()
      expect(errorConfigs[type].title, `${type} 缺标题`).toBeTruthy()
      expect(errorConfigs[type].subTitle, `${type} 缺副标题`).toBeTruthy()
    })
  })
})

describe('ErrorProvider 组件级行为', () => {
  it('TC-FE-ERRCTX-011: useError 在 Provider 外调用直接抛错（防误用）', () => {
    const Probe = () => {
      useError()
      return null
    }
    // React 会把渲染期异常同时打到 console.error，这里静默以免污染测试输出
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    expect(() => render(<Probe />)).toThrow('useError must be used within ErrorProvider')

    consoleSpy.mockRestore()
  })

  it('TC-FE-ERRCTX-012: showError 弹出弹窗，并按认证错误码显示对应文案', async () => {
    const Probe = () => {
      const { showError } = useError()
      return <button onClick={() => showError(httpError(401, { code: 40101 }))}>触发认证错误</button>
    }

    render(
      <MemoryRouter>
        <ErrorProvider>
          <Probe />
        </ErrorProvider>
      </MemoryRouter>
    )

    fireEvent.click(screen.getByText('触发认证错误'))

    expect(await screen.findByText('登录失败')).toBeInTheDocument()
    expect(screen.getByText('用户名/邮箱或密码错误，请检查后重试')).toBeInTheDocument()
  })

  it('TC-FE-ERRCTX-013: 服务器错误弹窗显示类型标题 + 提取后的原始消息', async () => {
    const Probe = () => {
      const { showError } = useError()
      return (
        <button onClick={() => showError(httpError(500, { message: '数据库连接失败' }))}>
          触发服务器错误
        </button>
      )
    }

    render(
      <MemoryRouter>
        <ErrorProvider>
          <Probe />
        </ErrorProvider>
      </MemoryRouter>
    )

    fireEvent.click(screen.getByText('触发服务器错误'))

    expect(await screen.findByText('服务器开小差了')).toBeInTheDocument()
    expect(screen.getByText('数据库连接失败')).toBeInTheDocument()
  })
})
