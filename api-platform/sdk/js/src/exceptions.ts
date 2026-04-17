/**
 * API Platform JavaScript/TypeScript SDK
 * 异常类型定义
 */

/**
 * 错误码枚举
 */
export enum ErrorCode {
  SUCCESS = 0,
  BAD_REQUEST = 40001,
  INVALID_SIGNATURE = 40002,
  TIMESTAMP_EXPIRED = 40003,
  NONCE_REUSED = 40004,
  INVALID_PARAMETER = 40005,
  UNAUTHORIZED = 40101,
  INVALID_KEY = 40102,
  KEY_DISABLED = 40103,
  KEY_EXPIRED = 40104,
  ACCESS_DENIED = 40301,
  REPO_NOT_ALLOWED = 40302,
  REPO_NOT_FOUND = 40401,
  ENDPOINT_NOT_FOUND = 40402,
  RATE_LIMIT_EXCEEDED = 42901,
  QUOTA_EXCEEDED = 42902,
  CONCURRENT_LIMIT = 42903,
  INTERNAL_ERROR = 50001,
  REPO_UNAVAILABLE = 50301,
  REPO_TIMEOUT = 50302,
  REPO_ERROR = 50303,
}

/**
 * 基础API异常类
 */
export class APIError extends Error {
  code: ErrorCode;
  requestId: string;
  details?: Record<string, unknown>;

  constructor(
    message: string,
    code: ErrorCode | number = ErrorCode.INTERNAL_ERROR,
    requestId: string = '',
    details?: Record<string, unknown>
  ) {
    super(message);
    this.name = 'APIError';
    this.code = code as ErrorCode;
    this.requestId = requestId;
    this.details = details;
  }
}

/**
 * 认证错误（401）
 */
export class AuthenticationError extends APIError {
  constructor(
    message: string = '认证失败',
    code: ErrorCode = ErrorCode.UNAUTHORIZED,
    requestId: string = ''
  ) {
    super(message, code, requestId);
    this.name = 'AuthenticationError';
  }
}

/**
 * 限流错误（429）
 */
export class RateLimitError extends APIError {
  limitType: 'rpm' | 'rph' | 'daily' | 'monthly';
  limit: number;
  remaining: number;
  retryAfter: number;

  constructor(
    message: string = '请求过于频繁',
    limitType: string = 'rpm',
    limit: number = 0,
    remaining: number = 0,
    retryAfter: number = 60,
    requestId: string = ''
  ) {
    super(message, ErrorCode.RATE_LIMIT_EXCEEDED, requestId);
    this.name = 'RateLimitError';
    this.limitType = limitType as RateLimitError['limitType'];
    this.limit = limit;
    this.remaining = remaining;
    this.retryAfter = retryAfter;
  }
}

/**
 * 配额超限错误
 */
export class QuotaExceededError extends APIError {
  quotaType: string;
  used: number;
  limit: number;

  constructor(
    message: string = '配额超限',
    quotaType: string = '',
    used: number = 0,
    limit: number = 0,
    requestId: string = ''
  ) {
    super(message, ErrorCode.QUOTA_EXCEEDED, requestId);
    this.name = 'QuotaExceededError';
    this.quotaType = quotaType;
    this.used = used;
    this.limit = limit;
  }
}

/**
 * 参数验证错误（400）
 */
export class ValidationError extends APIError {
  constructor(
    message: string,
    code: ErrorCode = ErrorCode.BAD_REQUEST,
    requestId: string = '',
    details?: Record<string, unknown>
  ) {
    super(message, code, requestId, details);
    this.name = 'ValidationError';
  }
}

/**
 * 资源不存在错误（404）
 */
export class NotFoundError extends APIError {
  resourceType: string;
  resourceId: string;

  constructor(
    message: string = '资源不存在',
    resourceType: string = '',
    resourceId: string = '',
    requestId: string = ''
  ) {
    super(message, ErrorCode.REPO_NOT_FOUND, requestId);
    this.name = 'NotFoundError';
    this.resourceType = resourceType;
    this.resourceId = resourceId;
  }
}

/**
 * 服务器错误（500/503）
 */
export class ServerError extends APIError {
  constructor(
    message: string = '服务器错误',
    code: ErrorCode = ErrorCode.INTERNAL_ERROR,
    requestId: string = ''
  ) {
    super(message, code, requestId);
    this.name = 'ServerError';
  }
}

/**
 * 网络错误
 */
export class NetworkError extends APIError {
  cause?: Error;

  constructor(message: string, cause?: Error) {
    super(message, -1);
    this.name = 'NetworkError';
    this.cause = cause;
  }
}

/**
 * 超时错误
 */
export class TimeoutError extends APIError {
  timeout: number;

  constructor(message: string = '请求超时', timeout: number = 30) {
    super(message, -1);
    this.name = 'TimeoutError';
    this.timeout = timeout;
  }
}

/**
 * 重试耗尽错误
 */
export class RetryExhaustedError extends APIError {
  lastError?: Error;

  constructor(message: string = '重试次数耗尽', lastError?: Error) {
    super(message, -1);
    this.name = 'RetryExhaustedError';
    this.lastError = lastError;
  }
}
