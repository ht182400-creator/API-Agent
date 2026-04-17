/**
 * API Platform JavaScript/TypeScript SDK
 * 客户端主类
 */

import {
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
  ErrorCode,
} from './exceptions';

/**
 * 客户端配置选项
 */
export interface ClientOptions {
  /** API密钥 */
  apiKey: string;
  /** API密钥私钥（可选，用于HMAC签名） */
  apiSecret?: string;
  /** API基础URL */
  baseURL?: string;
  /** 请求超时时间（毫秒） */
  timeout?: number;
  /** 最大重试次数 */
  maxRetries?: number;
  /** 初始重试延迟（毫秒） */
  retryDelay?: number;
  /** 重试延迟倍数 */
  retryMultiplier?: number;
  /** 日志级别 */
  logLevel?: 'debug' | 'info' | 'warn' | 'error';
}

/**
 * API响应基础结构
 */
export interface APIResponse<T = unknown> {
  code: number;
  message: string;
  data?: T;
  request_id?: string;
}

/**
 * 用量信息
 */
export interface Usage {
  tokens: number;
  cost: number;
}

/**
 * 心理问答响应
 */
export interface ChatResponse {
  answer: string;
  suggestions?: string[];
  request_id: string;
  usage: Usage;
}

/**
 * 翻译响应
 */
export interface TranslationResponse {
  result: string;
  detected_lang?: string;
  usage: Usage;
}

/**
 * API Platform 客户端
 */
export class Client {
  private apiKey: string;
  private apiSecret?: string;
  private baseURL: string;
  private timeout: number;
  private maxRetries: number;
  private retryDelay: number;
  private retryMultiplier: number;
  private logger: Console;

  constructor(options: ClientOptions) {
    this.apiKey = options.apiKey;
    this.apiSecret = options.apiSecret;
    this.baseURL = (options.baseURL || 'https://api.platform.com/v1').replace(/\/$/, '');
    this.timeout = options.timeout || 30000;
    this.maxRetries = options.maxRetries ?? 3;
    this.retryDelay = options.retryDelay || 1000;
    this.retryMultiplier = options.retryMultiplier || 2;
    this.logger = console;
    
    // 设置日志级别
    const logLevel = options.logLevel || 'info';
    this.logger = {
      debug: logLevel === 'debug' ? console.debug : () => {},
      info: ['debug', 'info'].includes(logLevel) ? console.info : () => {},
      warn: ['debug', 'info', 'warn'].includes(logLevel) ? console.warn : () => {},
      error: () => console.error,
    } as Console;
  }

  /**
   * 生成签名
   */
  private generateSignature(
    method: string,
    path: string,
    timestamp: string,
    nonce: string,
    body: string = ''
  ): string {
    if (!this.apiSecret) return '';

    const crypto = require('crypto');
    const stringToSign = [
      `AccessKey=${this.apiKey}`,
      `Timestamp=${timestamp}`,
      `Nonce=${nonce}`,
      `BodyHash=${crypto.createHash('sha256').update(body).digest('hex')}`,
    ].join('\n');

    const signature = crypto
      .createHmac('sha256', this.apiSecret)
      .update(stringToSign)
      .digest('hex');

    return signature;
  }

  /**
   * 生成请求头
   */
  private generateHeaders(method: string, path: string, body: string = ''): Record<string, string> {
    const timestamp = Date.now().toString();
    const crypto = require('crypto');
    const nonce = crypto.randomBytes(16).toString('hex');

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${this.apiKey}`,
      'X-Api-Key': this.apiKey,
      'X-Timestamp': timestamp,
      'X-Nonce': nonce,
    };

    if (this.apiSecret) {
      const signature = this.generateSignature(method, path, timestamp, nonce, body);
      headers['X-Signature'] = signature;
    }

    return headers;
  }

  /**
   * 处理响应
   */
  private handleResponse<T>(response: Response): Promise<T> {
    return response.json().then((data) => {
      const status = response.status;
      const errorCode = data.code || 0;
      const errorMsg = data.message || '';
      const requestId = data.request_id || '';

      if (status === 200 && errorCode === 0) {
        return data.data || data;
      }

      const errorOptions = {
        message: errorMsg,
        requestId,
      };

      switch (status) {
        case 401:
          throw new AuthenticationError(errorMsg, errorCode, requestId);
        case 429:
          throw new RateLimitError(
            errorMsg,
            data.limit_type || 'rpm',
            data.limit || 0,
            data.remaining || 0,
            data.retry_after || 60,
            requestId
          );
        case 403:
          throw new APIError(errorMsg, errorCode, requestId);
        case 404:
          throw new NotFoundError(errorMsg, data.resource_type || '', data.resource_id || '', requestId);
        case 400:
          throw new ValidationError(errorMsg, errorCode, requestId, data.details);
        default:
          if (status >= 500) {
            throw new ServerError(errorMsg, errorCode, requestId);
          }
          throw new APIError(errorMsg, errorCode, requestId);
      }
    });
  }

  /**
   * 带重试的请求
   */
  private async requestWithRetry<T>(
    method: string,
    path: string,
    options: RequestInit = {}
  ): Promise<T> {
    let lastError: Error | undefined;

    for (let attempt = 0; attempt <= this.maxRetries; attempt++) {
      try {
        const body = options.body as string || '';
        const headers = this.generateHeaders(method, path, body);

        const response = await fetch(`${this.baseURL}/${path.replace(/^\//, '')}`, {
          ...options,
          method,
          headers: { ...headers, ...options.headers },
          signal: AbortSignal.timeout(this.timeout),
        });

        return await this.handleResponse<T>(response);
      } catch (error) {
        lastError = error as Error;

        if (
          error instanceof RateLimitError ||
          error instanceof ServerError ||
          error instanceof NetworkError ||
          error instanceof TimeoutError
        ) {
          if (attempt < this.maxRetries) {
            let delay = this.retryDelay * Math.pow(this.retryMultiplier, attempt);
            
            if (error instanceof RateLimitError && error.retryAfter) {
              delay = error.retryAfter * 1000;
            }

            this.logger.warn(
              `请求失败（第${attempt + 1}次尝试），等待${delay}ms后重试：${error.message}`
            );
            await this.sleep(delay);
          } else {
            this.logger.error(`重试次数耗尽，最后错误：${error}`);
          }
        } else {
          throw error;
        }
      }
    }

    throw new RetryExhaustedError(
      `重试${this.maxRetries}次后仍然失败`,
      lastError
    );
  }

  /**
   * 睡眠
   */
  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  /**
   * GET请求
   */
  async get<T>(path: string, params?: Record<string, string>): Promise<T> {
    let url = path;
    if (params) {
      const searchParams = new URLSearchParams(params);
      url += `?${searchParams.toString()}`;
    }
    return this.requestWithRetry<T>('GET', url);
  }

  /**
   * POST请求
   */
  async post<T>(path: string, data?: unknown): Promise<T> {
    const body = data ? JSON.stringify(data) : '';
    return this.requestWithRetry<T>('POST', path, { body });
  }

  /**
   * PUT请求
   */
  async put<T>(path: string, data?: unknown): Promise<T> {
    const body = data ? JSON.stringify(data) : '';
    return this.requestWithRetry<T>('PUT', path, { body });
  }

  /**
   * DELETE请求
   */
  async delete<T>(path: string): Promise<T> {
    return this.requestWithRetry<T>('DELETE', path);
  }

  /**
   * 心理问答
   */
  async chat(options: { message: string; userId?: string; context?: Record<string, unknown> }): Promise<ChatResponse> {
    return this.post<ChatResponse>('/repos/psychology/chat', options);
  }

  /**
   * 翻译
   */
  async translate(options: {
    text: string;
    source_lang: string;
    target_lang: string;
    engine?: 'accurate' | 'fast';
  }): Promise<TranslationResponse> {
    return this.post<TranslationResponse>('/repos/translation/translate', options);
  }

  /**
   * 通用仓库调用
   */
  async repo(repoName: string): Promise<RepoClient> {
    return new RepoClient(this, repoName);
  }
}

/**
 * 仓库客户端
 */
export class RepoClient {
  private client: Client;
  private repoName: string;

  constructor(client: Client, repoName: string) {
    this.client = client;
    this.repoName = repoName;
  }

  /**
   * 调用端点
   */
  async call<T>(endpoint: string, data?: unknown): Promise<T> {
    return this.client.post<T>(`/repos/${this.repoName}/${endpoint}`, data);
  }

  /**
   * 获取端点
   */
  endpoint(endpoint: string) {
    return (data?: unknown) => this.call(endpoint, data);
  }
}
