/**
 * API Platform JavaScript/TypeScript SDK - 测试
 */

import { Client } from '../src/client';
import {
  APIError,
  AuthenticationError,
  RateLimitError,
  ErrorCode,
} from '../src/exceptions';

describe('Client', () => {
  describe('constructor', () => {
    it('should create a client with default options', () => {
      const client = new Client({ apiKey: 'sk_test_12345678901234567890' });
      expect(client).toBeDefined();
    });

    it('should create a client with custom options', () => {
      const client = new Client({
        apiKey: 'sk_test_12345678901234567890',
        apiSecret: 'secret',
        baseURL: 'https://custom.api.com/v1',
        timeout: 60000,
        maxRetries: 5,
        logLevel: 'debug',
      });
      expect(client).toBeDefined();
    });
  });
});

describe('Exceptions', () => {
  describe('APIError', () => {
    it('should create an API error', () => {
      const error = new APIError('Test error', ErrorCode.BAD_REQUEST, 'req_123');
      expect(error.message).toBe('Test error');
      expect(error.code).toBe(ErrorCode.BAD_REQUEST);
      expect(error.requestId).toBe('req_123');
    });
  });

  describe('AuthenticationError', () => {
    it('should create an authentication error', () => {
      const error = new AuthenticationError('Auth failed', ErrorCode.UNAUTHORIZED, 'req_123');
      expect(error.name).toBe('AuthenticationError');
      expect(error.code).toBe(ErrorCode.UNAUTHORIZED);
    });
  });

  describe('RateLimitError', () => {
    it('should create a rate limit error', () => {
      const error = new RateLimitError('Rate limited', 'rpm', 100, 0, 60, 'req_123');
      expect(error.name).toBe('RateLimitError');
      expect(error.limitType).toBe('rpm');
      expect(error.limit).toBe(100);
      expect(error.remaining).toBe(0);
      expect(error.retryAfter).toBe(60);
    });
  });
});

describe('ErrorCode', () => {
  it('should have correct error codes', () => {
    expect(ErrorCode.SUCCESS).toBe(0);
    expect(ErrorCode.BAD_REQUEST).toBe(40001);
    expect(ErrorCode.UNAUTHORIZED).toBe(40101);
    expect(ErrorCode.RATE_LIMIT_EXCEEDED).toBe(42901);
    expect(ErrorCode.INTERNAL_ERROR).toBe(50001);
  });
});
