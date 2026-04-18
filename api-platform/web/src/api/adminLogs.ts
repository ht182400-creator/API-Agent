/**
 * 管理员日志API客户端
 */

import { api } from './client'

// 日志文件信息
export interface LogFileInfo {
  name: string
  path: string
  module: string
  size: number
  size_formatted: string
  modified_at: string
}

// 日志行
export interface LogLine {
  line_number: number
  timestamp: string
  level: string
  module: string
  message: string
  raw: string
  color: string
}

// 日志内容响应
export interface LogContentResponse {
  lines: LogLine[]
  total: number
  start_line: number
  max_lines: number
  error?: string
}

// 日志统计
export interface LogStats {
  total_files: number
  total_size: number
  total_size_formatted: string
  backup_count: number
  backup_size: number
  backup_size_formatted: string
  config: BackupConfig
}

// 备份文件信息
export interface BackupFileInfo {
  name: string
  path: string
  size: number
  size_formatted: string
  created_at: string
  modified_at: string
}

// 备份配置
export interface BackupConfig {
  max_file_size_mb: number
  max_backup_files: number
  auto_cleanup: boolean
  cleanup_threshold: number
  enabled: boolean
}

// 备份配置更新
export interface BackupConfigUpdate {
  max_file_size_mb?: number
  max_backup_files?: number
  auto_cleanup?: boolean
  cleanup_threshold?: number
  enabled?: boolean
}

// 日志级别类型
export type LogLevel = 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL'

// 日志级别配置
export const LOG_LEVELS: { label: string; value: LogLevel; color: string }[] = [
  { label: '调试', value: 'DEBUG', color: '#1890ff' },
  { label: '信息', value: 'INFO', color: '#52c41a' },
  { label: '警告', value: 'WARNING', color: '#faad14' },
  { label: '错误', value: 'ERROR', color: '#ff4d4f' },
  { label: '严重', value: 'CRITICAL', color: '#722ed1' },
]

// API函数

/**
 * 获取日志文件列表
 */
export async function getLogFiles(): Promise<LogFileInfo[]> {
  return api.get('/admin/logs/files')
}

/**
 * 获取日志内容
 */
export async function getLogContent(
  filePath: string,
  options?: {
    startLine?: number
    maxLines?: number
    level?: LogLevel | null
    keyword?: string | null
  }
): Promise<LogContentResponse> {
  const params: Record<string, any> = { file_path: filePath }
  
  if (options?.startLine !== undefined) params.start_line = options.startLine
  if (options?.maxLines !== undefined) params.max_lines = options.maxLines
  if (options?.level) params.level = options.level
  if (options?.keyword) params.keyword = options.keyword
  
  return api.get('/admin/logs/content', params)
}

/**
 * 获取日志统计
 */
export async function getLogStats(): Promise<LogStats> {
  return api.get('/admin/logs/stats')
}

/**
 * 获取备份文件列表
 */
export async function getBackups(): Promise<BackupFileInfo[]> {
  return api.get('/admin/logs/backups')
}

/**
 * 下载备份文件
 */
export function downloadBackup(filename: string): string {
  const baseURL = import.meta.env.VITE_API_URL || '/api/v1'
  return `${baseURL}/admin/logs/backups/${filename}`
}

/**
 * 删除备份文件
 */
export async function deleteBackup(filename: string): Promise<void> {
  return api.delete(`/admin/logs/backups/${filename}`)
}

/**
 * 手动清理备份
 */
export async function cleanupBackups(): Promise<void> {
  return api.post('/admin/logs/backups/cleanup')
}

/**
 * 获取备份配置
 */
export async function getBackupConfig(): Promise<BackupConfig> {
  return api.get('/admin/logs/config')
}

/**
 * 更新备份配置
 */
export async function updateBackupConfig(config: BackupConfigUpdate): Promise<BackupConfig> {
  return api.put('/admin/logs/config', config)
}

/**
 * 手动备份指定模块
 */
export async function manualBackup(module: string): Promise<void> {
  return api.post(`/admin/logs/backup/${module}`)
}

/**
 * 获取日志级别颜色
 */
export function getLevelColor(level: string): string {
  const config = LOG_LEVELS.find(l => l.value === level)
  return config?.color || '#000000'
}

// 备份内容行
export interface BackupContentLine {
  line_number: number
  content: string
  timestamp?: string
  level?: string
  color?: string
}

// 备份内容响应
export interface BackupContentResponse {
  lines: BackupContentLine[]
  total: number
  start_line: number
  max_lines: number
}

/**
 * 导出日志文件
 */
export function exportLog(filename: string): string {
  const baseURL = import.meta.env.VITE_API_URL || '/api/v1'
  return `${baseURL}/admin/logs/export?file_path=${encodeURIComponent(filename)}`
}

/**
 * 获取备份文件内容
 */
export async function getBackupContent(
  filename: string,
  options?: {
    startLine?: number
    maxLines?: number
    level?: LogLevel | null
    keyword?: string | null
  }
): Promise<BackupContentResponse> {
  const params: Record<string, any> = { filename }

  if (options?.startLine !== undefined) params.start_line = options.startLine
  if (options?.maxLines !== undefined) params.max_lines = options.maxLines
  if (options?.level) params.level = options.level
  if (options?.keyword) params.keyword = options.keyword

  return api.get('/admin/logs/backup-content', params)
}
