/**
 * API Platform JavaScript/TypeScript SDK
 * 入口文件
 */

// 导出客户端
export { Client, ClientOptions, APIResponse, Usage, ChatResponse, TranslationResponse } from './client';

// 导出异常
export {
  ErrorCode,
  APIError,
  AuthenticationError,
  RateLimitError,
  QuotaExceededError,
  ValidationError,
  NotFoundError,
  ServerError,
  NetworkError,
  TimeoutError,
  RetryExhaustedError,
} from './exceptions';

// 版本
export const VERSION = '1.0.0';
