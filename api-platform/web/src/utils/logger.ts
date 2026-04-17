/**
 * 前端日志工具
 * 支持日志级别控制、本地存储、日志上报
 */

export enum LogLevel {
  DEBUG = 0,
  INFO = 1,
  WARN = 2,
  ERROR = 3,
}

const levelNames = ['DEBUG', 'INFO', 'WARN', 'ERROR']

class Logger {
  private level: LogLevel
  private maxLogs: number
  private logs: LogEntry[]

  constructor() {
    // 默认日志级别：开发环境为 DEBUG，生产环境为 INFO
    this.level = import.meta.env.DEV ? LogLevel.DEBUG : LogLevel.INFO
    this.maxLogs = 500
    this.logs = []

    // 从 localStorage 恢复日志
    this.restoreLogs()
  }

  private restoreLogs() {
    try {
      const saved = localStorage.getItem('app_logs')
      if (saved) {
        this.logs = JSON.parse(saved)
      }
    } catch {
      // ignore
    }
  }

  private saveLogs() {
    try {
      // 只保存最近的日志
      const logsToSave = this.logs.slice(-this.maxLogs)
      localStorage.setItem('app_logs', JSON.stringify(logsToSave))
    } catch {
      // ignore
    }
  }

  private log(level: LogLevel, args: any[]) {
    if (level < this.level) return

    const entry: LogEntry = {
      timestamp: new Date().toISOString(),
      level: levelNames[level],
      message: args.map(a => {
        if (a instanceof Error) {
          return `${a.message}\n${a.stack}`
        }
        if (typeof a === 'object') {
          try {
            return JSON.stringify(a)
          } catch {
            return String(a)
          }
        }
        return String(a)
      }).join(' '),
    }

    this.logs.push(entry)
    this.saveLogs()

    const prefix = `[${entry.timestamp}] [${entry.level}]`
    
    switch (level) {
      case LogLevel.DEBUG:
        console.debug(prefix, ...args)
        break
      case LogLevel.INFO:
        console.info(prefix, ...args)
        break
      case LogLevel.WARN:
        console.warn(prefix, ...args)
        break
      case LogLevel.ERROR:
        console.error(prefix, ...args)
        break
    }
  }

  debug(...args: any[]) {
    this.log(LogLevel.DEBUG, args)
  }

  info(...args: any[]) {
    this.log(LogLevel.INFO, args)
  }

  warn(...args: any[]) {
    this.log(LogLevel.WARN, args)
  }

  error(...args: any[]) {
    this.log(LogLevel.ERROR, args)
  }

  // API 请求日志
  logRequest(method: string, url: string, data?: any) {
    this.debug(`[API] ${method} ${url}`, data)
  }

  // API 响应日志
  logResponse(method: string, url: string, status: number, data?: any) {
    if (status >= 400) {
      this.error(`[API] ${method} ${url} - ${status}`, data)
    } else {
      this.debug(`[API] ${method} ${url} - ${status}`, data)
    }
  }

  // API 错误日志
  logApiError(method: string, url: string, error: any) {
    this.error(`[API ERROR] ${method} ${url}`, {
      message: error.message,
      code: error.code,
      response: error.response,
    })
  }

  // 获取所有日志
  getLogs(): LogEntry[] {
    return [...this.logs]
  }

  // 清除日志
  clearLogs() {
    this.logs = []
    localStorage.removeItem('app_logs')
  }

  // 导出日志
  exportLogs(): string {
    return this.logs.map(l => `${l.timestamp} [${l.level}] ${l.message}`).join('\n')
  }

  // 设置日志级别
  setLevel(level: LogLevel) {
    this.level = level
  }
}

interface LogEntry {
  timestamp: string
  level: string
  message: string
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
  clear: () => logger.clearLogs(),
  export: () => logger.exportLogs(),
}
