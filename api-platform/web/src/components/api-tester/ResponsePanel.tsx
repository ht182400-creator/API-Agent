/**
 * 响应面板组件
 * @description 显示API响应结果和curl命令
 */

import React, { useState } from 'react';
import styles from './ResponsePanel.module.css';

interface Props {
  response: any;
  status: number;
  duration: number;
  curlCommand?: string;
}

/** 状态配置 */
const statusConfig: Record<string, { icon: string; bg: string; text: string; label: string; border: string }> = {
  success: { icon: '✅', bg: 'bg-emerald-50', text: 'text-emerald-600', label: '成功', border: 'border-emerald-200' },
  redirect: { icon: '🔄', bg: 'bg-blue-50', text: 'text-blue-600', label: '重定向', border: 'border-blue-200' },
  clientError: { icon: '⚠️', bg: 'bg-amber-50', text: 'text-amber-600', label: '客户端错误', border: 'border-amber-200' },
  serverError: { icon: '❌', bg: 'bg-rose-50', text: 'text-rose-600', label: '服务器错误', border: 'border-rose-200' },
  error: { icon: '❌', bg: 'bg-rose-50', text: 'text-rose-600', label: '请求失败', border: 'border-rose-200' }
};

/** 获取状态配置 */
const getStatusConfig = (status: number, hasError: boolean) => {
  if (hasError) return statusConfig.error;
  if (status >= 200 && status < 300) return statusConfig.success;
  if (status >= 300 && status < 400) return statusConfig.redirect;
  if (status >= 400 && status < 500) return statusConfig.clientError;
  return statusConfig.serverError;
};

export const ResponsePanel: React.FC<Props> = ({ response, status, duration, curlCommand }) => {
  const [showCurl, setShowCurl] = useState(true);
  const [copied, setCopied] = useState(false);
  const [copiedType, setCopiedType] = useState<'response' | 'curl' | null>(null);

  const hasError = !response || response.error;
  const config = getStatusConfig(status, hasError);

  /**
   * 复制到剪贴板
   */
  const handleCopy = async (text: string, type: 'response' | 'curl') => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setCopiedType(type);
      setTimeout(() => {
        setCopied(false);
        setCopiedType(null);
      }, 2000);
    } catch (err) {
      // 降级方案
      const textarea = document.createElement('textarea');
      textarea.value = text;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      setCopied(true);
      setCopiedType(type);
      setTimeout(() => {
        setCopied(false);
        setCopiedType(null);
      }, 2000);
    }
  };

  /**
   * 格式化JSON
   */
  const formatJson = (data: any): string => {
    try {
      return JSON.stringify(data, null, 2);
    } catch {
      return String(data);
    }
  };

  return (
    <div className={`${styles.panel} ${config.bg} ${config.border}`}>
      {/* 响应状态栏 */}
      <div className={styles.statusBar}>
        <div className={styles.statusLeft}>
          <span className={styles.statusIcon}>{config.icon}</span>
          <div>
            <p className={`${styles.statusLabel} ${config.text}`}>{config.label}</p>
            <p className={styles.statusMessage}>{response?.message || (hasError ? '请求失败' : 'success')}</p>
          </div>
        </div>
        <div className={styles.statusRight}>
          <p className={`${styles.statusCode} ${config.text}`}>
            {hasError ? 'Error' : status}
          </p>
          <p className={styles.duration}>{duration}ms</p>
        </div>
      </div>

      {/* curl 命令 */}
      {curlCommand && (
        <div className={styles.curlSection}>
          <div 
            className={styles.curlHeader}
            onClick={() => setShowCurl(!showCurl)}
          >
            <span className={styles.curlTitle}>
              <span>📋</span>
              <span>curl 请求命令</span>
              <span className={styles.curlToggle}>{showCurl ? '▼' : '▶'}</span>
            </span>
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleCopy(curlCommand, 'curl');
              }}
              className={`${styles.copyBtn} ${copied && copiedType === 'curl' ? styles.copyBtnSuccess : ''}`}
            >
              {copied && copiedType === 'curl' ? '✓ 已复制' : '复制'}
            </button>
          </div>
          {showCurl && (
            <pre className={styles.curlCode}>
              {curlCommand}
            </pre>
          )}
        </div>
      )}

      {/* 响应内容 */}
      <div className={styles.responseSection}>
        <div className={styles.responseHeader}>
          <span className={styles.responseTitle}>
            <span>📄</span>
            <span>响应内容</span>
          </span>
          <button
            onClick={() => handleCopy(formatJson(response), 'response')}
            className={`${styles.copyBtn} ${copied && copiedType === 'response' ? styles.copyBtnSuccess : ''}`}
          >
            {copied && copiedType === 'response' ? '✓ 已复制' : '复制 JSON'}
          </button>
        </div>
        <pre className={styles.responseJson}>
          {formatJson(response)}
        </pre>
      </div>
    </div>
  );
};
