/**
 * 前端日志工具
 * 支持日志级别控制、本地存储、日志上报
 * 
 * 环境变量配置:
 * - VITE_LOG_LEVEL: 日志级别 (debug|info|warn|error)
 * - VITE_LOG_MAX_SIZE: 最大日志条数 (默认500)
 * - VITE_LOG_ENABLE_CONSOLE: 是否输出到控制台 (true|false)
 * - VITE_LOG_ENABLE_STORAGE: 是否保存到本地存储 (true|false)
 * - VITE_LOG_ENABLE_REMOTE: 是否上报到服务器 (true|false)
 */

export enum LogLevel {
  DEBUG = 0,
  INFO = 1,
  WARN = 2,
  ERROR = 3,
}

const levelNames = ['DEBUG', 'INFO', 'WARN', 'ERROR']

// 解析日志级别
function parseLogLevel(level?: string): LogLevel {
  switch ((level || '').toLowerCase()) {
    case 'debug': return LogLevel.DEBUG
    case 'info': return LogLevel.INFO
    case 'warn': return LogLevel.WARN
    case 'error': return LogLevel.ERROR
    default:
      // 生产环境默认 INFO，开发环境默认 DEBUG
      return import.meta.env.PROD ? LogLevel.INFO : LogLevel.DEBUG
  }
}

// 解析布尔值
function parseBool(value?: string, defaultValue: boolean = true): boolean {
  if (!value) return defaultValue
  return value.toLowerCase() === 'true'
}

// 格式化时间为 yyyymmdd HH:mm:ss.fff
function formatTime(date: Date): string {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  const h = String(date.getHours()).padStart(2, '0')
  const min = String(date.getMinutes()).padStart(2, '0')
  const s = String(date.getSeconds()).padStart(2, '0')
  const ms = String(date.getMilliseconds()).padStart(3, '0')
  return `${y}${m}${d} ${h}:${min}:${s}.${ms}`
}

// 日志前缀
const LOG_PREFIX = '[WEB]'

export interface LogEntry {
  timestamp: string   // yyyymmdd HH:mm:ss 格式
  timestampRaw?: string // ISO 原始格式
  level: string
  message: string
  context?: string
  data?: any
  userId?: string
  sessionId?: string
  url?: string
  userAgent?: string
}

export interface LogConfig {
  level: LogLevel
  maxLogs: number
  enableConsole: boolean
  enableStorage: boolean
  enableRemote: boolean
  remoteUrl?: string
}

class Logger {
  private level: LogLevel
  private maxLogs: number
  private logs: LogEntry[]
  private enableConsole: boolean
  private enableStorage: boolean
  private enableRemote: boolean
  private sessionId: string
  private userId?: string

  constructor() {
    // 从环境变量读取配置
    this.level = parseLogLevel(import.meta.env.VITE_LOG_LEVEL)
    this.maxLogs = parseInt(import.meta.env.VITE_LOG_MAX_SIZE || '500', 10)
    this.enableConsole = parseBool(import.meta.env.VITE_LOG_ENABLE_CONSOLE, true)
    this.enableStorage = parseBool(import.meta.env.VITE_LOG_ENABLE_STORAGE, true)
    this.enableRemote = parseBool(import.meta.env.VITE_LOG_ENABLE_REMOTE, false)
    this.logs = []

    // 生成会话ID
    this.sessionId = this.generateSessionId()

    // 从 localStorage 恢复日志
    this.restoreLogs()

    // 记录启动信息
    this.info('Logger initialized', {
      level: levelNames[this.level],
      env: import.meta.env.MODE,
      sessionId: this.sessionId,
    })
  }

  private generateSessionId(): string {
    return `sess_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }

  // 设置用户ID（登录后调用）
  setUserId(userId: string) {
    this.userId = userId
    this.debug('User logged in', { userId })
  }

  // 清除用户ID（登出时调用）
  clearUserId() {
    this.debug('User logged out', { userId: this.userId })
    this.userId = undefined
  }

  private restoreLogs() {
    if (!this.enableStorage) return
    
    try {
      const saved = localStorage.getItem('app_logs')
      if (saved) {
        const parsed = JSON.parse(saved)
        this.logs = Array.isArray(parsed) ? parsed.slice(-this.maxLogs) : []
      }
    } catch {
      // ignore
    }
  }

  private saveLogs() {
    if (!this.enableStorage) return
    
    try {
      const logsToSave = this.logs.slice(-this.maxLogs)
      localStorage.setItem('app_logs', JSON.stringify(logsToSave))
    } catch {
      // ignore
    }
  }

  // 异步上报日志到服务器
  private async reportToRemote(entry: LogEntry) {
    if (!this.enableRemote) return
    
    try {
      const remoteUrl = import.meta.env.VITE_LOG_REMOTE_URL || '/api/v1/logs/frontend'
      await fetch(remoteUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...entry,
          sessionId: this.sessionId,
          userId: this.userId,
          url: window.location.href,
          userAgent: navigator.userAgent,
        }),
      })
    } catch {
      // ignore - 不阻塞主流程
    }
  }

  private createEntry(level: LogLevel, message: string, data?: any, context?: string): LogEntry {
    const now = new Date()
    return {
      timestamp: formatTime(now),
      timestampRaw: now.toISOString(),
      level: levelNames[level],
      message,
      context,
      data,
      userId: this.userId,
      sessionId: this.sessionId,
      url: window.location.pathname,
    }
  }

  private log(level: LogLevel, args: any[]) {
    if (level < this.level) return

    const message = args.map(a => {
      if (a instanceof Error) {
        return `${a.message}\n${a.stack}`
      }
      if (typeof a === 'object') {
        try {
          return JSON.stringify(a, null, 2)
        } catch {
          return String(a)
        }
      }
      return String(a)
    }).join(' ')

    const context = args.length > 1 && typeof args[1] === 'string' ? args[1] : undefined
    const data = args.length > 2 ? args.slice(2) : (args.length === 2 && typeof args[1] === 'object' ? args[1] : undefined)

    const entry = this.createEntry(level, message, data, context)

    this.logs.push(entry)
    this.saveLogs()
    this.reportToRemote(entry)

    if (this.enableConsole) {
      const prefix = `[${entry.timestamp}] ${LOG_PREFIX} [${entry.level}]${context ? ` [${context}]` : ''}`
      
      switch (level) {
        case LogLevel.DEBUG:
          console.debug(prefix, ...(data ? [data] : []))
          break
        case LogLevel.INFO:
          console.info(prefix, message, ...(data ? [data] : []))
          break
        case LogLevel.WARN:
          console.warn(prefix, message, ...(data ? [data] : []))
          break
        case LogLevel.ERROR:
          console.error(prefix, message, ...(data ? [data] : []))
          break
      }
    }
  }

  debug(message: string, ...args: any[]) {
    this.log(LogLevel.DEBUG, [message, ...args])
  }

  info(message: string, ...args: any[]) {
    this.log(LogLevel.INFO, [message, ...args])
  }

  warn(message: string, ...args: any[]) {
    this.log(LogLevel.WARN, [message, ...args])
  }

  error(message: string, ...args: any[]) {
    this.log(LogLevel.ERROR, [message, ...args])
  }

  // API 请求日志
  logRequest(method: string, url: string, data?: any) {
    this.debug('[WEB-API] Request', { method, url, data })
  }

  // API 响应日志
  logResponse(method: string, url: string, status: number, data?: any) {
    if (status >= 400) {
      this.error('[WEB-API] Response Error', { method, url, status, data })
    } else {
      this.debug('[WEB-API] Response', { method, url, status, data })
    }
  }

  // API 错误日志
  logApiError(method: string, url: string, error: any) {
    this.error('[WEB-API] Error', {
      method,
      url,
      message: error.message,
      code: error.code,
      status: error.response?.status,
      data: error.response?.data,
      stack: error.stack,
    })
  }

  // 页面访问日志
  logPageView(page: string, params?: any) {
    this.info('[WEB-Page]', { page, params })
  }

  // 用户操作日志
  logUserAction(action: string, target?: string, params?: any) {
    this.info('[WEB-Action]', { action, target, params })
  }

  // 获取所有日志
  getLogs(): LogEntry[] {
    return [...this.logs]
  }

  // 获取日志统计
  getStats() {
    const stats = {
      total: this.logs.length,
      debug: 0,
      info: 0,
      warn: 0,
      error: 0,
      byPage: {} as Record<string, number>,
    }

    this.logs.forEach(log => {
      stats[log.level.toLowerCase() as keyof typeof stats]++
      if (log.url) {
        stats.byPage[log.url] = (stats.byPage[log.url] || 0) + 1
      }
    })

    return stats
  }

  // 清除日志
  clearLogs() {
    this.logs = []
    localStorage.removeItem('app_logs')
    this.info('Logs cleared')
  }

  // 导出日志（带文件名）
  exportLogs(): { filename: string; content: string } {
    const now = new Date()
    const dateStr = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}`
    const timeStr = `${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}${String(now.getSeconds()).padStart(2, '0')}`
    const filename = `web-app-log-${dateStr}-${timeStr}.txt`
    const content = this.logs.map(l => {
      const parts = [`[${l.timestamp}]`, LOG_PREFIX, `[${l.level}]`]
      if (l.context) parts.push(`[${l.context}]`)
      parts.push(l.message)
      if (l.data) parts.push(JSON.stringify(l.data))
      return parts.join(' ')
    }).join('\n')
    return { filename, content }
  }

  // 导出日志为 JSON（带文件名）
  exportLogsAsJson(): { filename: string; content: string } {
    const now = new Date()
    const dateStr = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}`
    const timeStr = `${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}${String(now.getSeconds()).padStart(2, '0')}`
    const filename = `web-app-log-${dateStr}-${timeStr}.json`
    return { filename, content: JSON.stringify(this.logs, null, 2) }
  }

  // 设置日志级别（运行时动态调整）
  setLevel(level: LogLevel) {
    this.level = level
    this.info('Log level changed', { level: levelNames[level] })
  }

  // 获取当前配置
  getConfig(): LogConfig {
    return {
      level: this.level,
      maxLogs: this.maxLogs,
      enableConsole: this.enableConsole,
      enableStorage: this.enableStorage,
      enableRemote: this.enableRemote,
      remoteUrl: import.meta.env.VITE_LOG_REMOTE_URL,
    }
  }
}

// 导出单例
export const logger = new Logger()

// 导出快捷方法
export const log = {
  debug: (...args: any[]) => logger.debug(...args),
  info: (...args: any[]) => logger.info(...args),
  warn: (...args: any[]) => logger.warn(...args),
  error: (...args: any[]) => logger.error(...args),
  getLogs: () => logger.getLogs(),
  getStats: () => logger.getStats(),
  clear: () => logger.clearLogs(),
  export: () => logger.exportLogs(),
  exportJson: () => logger.exportLogsAsJson(),
  setLevel: (level: LogLevel) => logger.setLevel(level),
  getConfig: () => logger.getConfig(),
  setUserId: (userId: string) => logger.setUserId(userId),
  clearUserId: () => logger.clearUserId(),
  pageView: (page: string, params?: any) => logger.logPageView(page, params),
  userAction: (action: string, target?: string, params?: any) => logger.logUserAction(action, target, params),
}

// 下载日志文件
export function downloadLogs(format: 'txt' | 'json' = 'txt') {
  const { filename, content } = format === 'json' ? logger.exportLogsAsJson() : logger.exportLogs()
  const blob = new Blob([content], { type: format === 'json' ? 'application/json' : 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
