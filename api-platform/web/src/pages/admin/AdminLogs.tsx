/**
 * 管理员日志管理页面
 */

import { useState, useEffect, useCallback } from 'react'
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Input,
  Select,
  Modal,
  Form,
  Slider,
  Switch,
  message,
  Popconfirm,
  Typography,
  Row,
  Col,
  Statistic,
  Alert,
  Tooltip,
  Divider,
  Badge,
} from 'antd'
import {
  ReloadOutlined,
  SearchOutlined,
  DownloadOutlined,
  DeleteOutlined,
  SettingOutlined,
  FileTextOutlined,
  CloudUploadOutlined,
  ClearOutlined,
  FolderOutlined,
  SaveOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import styles from './AdminLogs.module.css'
import {
  getLogFiles,
  getLogContent,
  getLogStats,
  getBackups,
  deleteBackup,
  cleanupBackups,
  getBackupConfig,
  updateBackupConfig,
  manualBackup,
  downloadBackup,
  LogFileInfo,
  LogLine,
  LogStats,
  BackupFileInfo,
  BackupConfig,
  LogLevel,
  LOG_LEVELS,
  getLevelColor,
} from '../../api/adminLogs'

const { Title, Text } = Typography
const { Option } = Select

export default function AdminLogs() {
  // 日志文件列表
  const [files, setFiles] = useState<LogFileInfo[]>([])
  const [selectedFile, setSelectedFile] = useState<string | null>(null)
  const [selectedModule, setSelectedModule] = useState<string>('')
  
  // 日志内容
  const [logLines, setLogLines] = useState<LogLine[]>([])
  const [totalLines, setTotalLines] = useState(0)
  const [loading, setLoading] = useState(false)
  const [contentLoading, setContentLoading] = useState(false)
  
  // 过滤
  const [levelFilter, setLevelFilter] = useState<LogLevel | null>(null)
  const [keyword, setKeyword] = useState('')
  const [currentPage, setCurrentPage] = useState(0)
  const [pageSize] = useState(500)
  
  // 统计
  const [stats, setStats] = useState<LogStats | null>(null)
  
  // 备份列表
  const [backups, setBackups] = useState<BackupFileInfo[]>([])
  
  // 配置弹窗
  const [configVisible, setConfigVisible] = useState(false)
  const [config, setConfig] = useState<BackupConfig | null>(null)
  const [configLoading, setConfigLoading] = useState(false)
  
  // 日志查看弹窗
  const [viewVisible, setViewVisible] = useState(false)
  
  // 加载日志文件列表
  const loadFiles = useCallback(async () => {
    setLoading(true)
    try {
      const data = await getLogFiles()
      setFiles(data)
    } catch (error) {
      message.error('加载日志文件失败')
    } finally {
      setLoading(false)
    }
  }, [])
  
  // 加载日志内容
  const loadLogContent = useCallback(async () => {
    if (!selectedFile) return
    
    setContentLoading(true)
    try {
      const data = await getLogContent(selectedFile, {
        startLine: currentPage * pageSize,
        maxLines: pageSize,
        level: levelFilter,
        keyword: keyword || null,
      })
      setLogLines(data.lines)
      setTotalLines(data.total)
    } catch (error) {
      message.error('加载日志内容失败')
    } finally {
      setContentLoading(false)
    }
  }, [selectedFile, currentPage, pageSize, levelFilter, keyword])
  
  // 加载统计
  const loadStats = useCallback(async () => {
    try {
      const data = await getLogStats()
      setStats(data)
    } catch (error) {
      console.error('加载统计失败:', error)
    }
  }, [])
  
  // 加载备份列表
  const loadBackups = useCallback(async () => {
    try {
      const data = await getBackups()
      setBackups(data)
    } catch (error) {
      console.error('加载备份列表失败:', error)
    }
  }, [])
  
  // 加载配置
  const loadConfig = useCallback(async () => {
    setConfigLoading(true)
    try {
      const data = await getBackupConfig()
      setConfig(data)
    } catch (error) {
      message.error('加载配置失败')
    } finally {
      setConfigLoading(false)
    }
  }, [])
  
  // 初始加载
  useEffect(() => {
    loadFiles()
    loadStats()
    loadBackups()
  }, [loadFiles, loadStats, loadBackups])
  
  // 加载日志内容
  useEffect(() => {
    if (selectedFile) {
      loadLogContent()
    }
  }, [selectedFile, loadLogContent])
  
  // 查看日志
  const handleViewLog = (record: LogFileInfo) => {
    setSelectedFile(record.name)
    setSelectedModule(record.module)
    setViewVisible(true)
  }
  
  // 搜索
  const handleSearch = () => {
    setCurrentPage(0)
    loadLogContent()
  }
  
  // 刷新
  const handleRefresh = () => {
    loadFiles()
    loadStats()
    loadBackups()
    if (selectedFile) {
      loadLogContent()
    }
  }
  
  // 删除备份
  const handleDeleteBackup = async (filename: string) => {
    try {
      await deleteBackup(filename)
      message.success('删除成功')
      loadBackups()
      loadStats()
    } catch (error) {
      message.error('删除失败')
    }
  }
  
  // 清理备份
  const handleCleanup = async () => {
    try {
      await cleanupBackups()
      message.success('清理完成')
      loadBackups()
      loadStats()
    } catch (error) {
      message.error('清理失败')
    }
  }
  
  // 保存配置
  const handleSaveConfig = async () => {
    if (!config) return
    try {
      await updateBackupConfig(config)
      message.success('配置已保存')
      setConfigVisible(false)
      loadStats()
    } catch (error) {
      message.error('保存失败')
    }
  }
  
  // 手动备份
  const handleManualBackup = async (module: string) => {
    try {
      await manualBackup(module)
      message.success('备份成功')
      loadBackups()
      loadStats()
    } catch (error) {
      message.error('备份失败')
    }
  }
  
  // 切换配置开关
  const handleConfigChange = (key: keyof BackupConfig, value: any) => {
    if (config) {
      setConfig({ ...config, [key]: value })
    }
  }
  
  // 日志文件表格列
  const fileColumns: ColumnsType<LogFileInfo> = [
    {
      title: '文件名',
      dataIndex: 'name',
      key: 'name',
      render: (text, record) => (
        <Space>
          <FileTextOutlined />
          <Text strong>{text}</Text>
        </Space>
      ),
    },
    {
      title: '模块',
      dataIndex: 'module',
      key: 'module',
      render: (text) => <Tag color="blue">{text}</Tag>,
    },
    {
      title: '大小',
      dataIndex: 'size_formatted',
      key: 'size',
    },
    {
      title: '修改时间',
      dataIndex: 'modified_at',
      key: 'modified_at',
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            size="small"
            onClick={() => handleViewLog(record)}
          >
            查看
          </Button>
          <Button
            type="link"
            size="small"
            icon={<CloudUploadOutlined />}
            onClick={() => handleManualBackup(record.module)}
          >
            备份
          </Button>
        </Space>
      ),
    },
  ]
  
  // 备份表格列
  const backupColumns: ColumnsType<BackupFileInfo> = [
    {
      title: '文件名',
      dataIndex: 'name',
      key: 'name',
      render: (text) => <Text copyable={{ text }}>{text}</Text>,
    },
    {
      title: '大小',
      dataIndex: 'size_formatted',
      key: 'size',
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<DownloadOutlined />}
            href={downloadBackup(record.name)}
            target="_blank"
          >
            下载
          </Button>
          <Popconfirm
            title="确认删除此备份?"
            onConfirm={() => handleDeleteBackup(record.name)}
            okText="确认"
            cancelText="取消"
          >
            <Button
              type="link"
              size="small"
              danger
              icon={<DeleteOutlined />}
            >
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]
  
  // 加载更多日志
  const loadMoreLogs = () => {
    setCurrentPage(prev => prev + 1)
    loadLogContent()
  }
  
  return (
    <div className={styles.container}>
      <Title level={4}>日志管理</Title>
      
      {/* 统计卡片 */}
      {stats && (
        <Row gutter={16} className={styles.statsRow}>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title="日志文件"
                value={stats.total_files}
                prefix={<FileTextOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title="日志总大小"
                value={stats.total_size_formatted}
                prefix={<FolderOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title="备份文件"
                value={stats.backup_count}
                prefix={<CloudUploadOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title="备份总大小"
                value={stats.backup_size_formatted}
                prefix={<FolderOutlined />}
              />
            </Card>
          </Col>
        </Row>
      )}
      
      {/* 操作栏 */}
      <Space className={styles.actionBar}>
        <Button
          type="primary"
          icon={<SettingOutlined />}
          onClick={() => {
            loadConfig()
            setConfigVisible(true)
          }}
        >
          备份设置
        </Button>
        <Popconfirm
          title="确认清理旧备份?"
          description="将删除超过配置数量的备份文件"
          onConfirm={handleCleanup}
          okText="确认"
          cancelText="取消"
        >
          <Button icon={<ClearOutlined />}>
            清理备份
          </Button>
        </Popconfirm>
        <Button
          icon={<ReloadOutlined />}
          onClick={handleRefresh}
        >
          刷新
        </Button>
      </Space>
      
      {/* 日志文件列表 */}
      <Card
        title="日志文件"
        className={styles.card}
        extra={
          <Badge status={stats?.config.enabled ? 'success' : 'default'} 
                 text={stats?.config.enabled ? '自动备份已启用' : '自动备份已禁用'} />
        }
      >
        <Table
          columns={fileColumns}
          dataSource={files}
          rowKey="name"
          loading={loading}
          pagination={false}
          size="small"
        />
      </Card>
      
      {/* 备份文件列表 */}
      <Card
        title="备份文件"
        className={styles.card}
      >
        <Table
          columns={backupColumns}
          dataSource={backups}
          rowKey="name"
          pagination={{ pageSize: 10 }}
          size="small"
        />
      </Card>
      
      {/* 日志查看弹窗 */}
      <Modal
        title={`查看日志 - ${selectedModule || selectedFile}`}
        open={viewVisible}
        onCancel={() => setViewVisible(false)}
        footer={[
          <Button key="close" onClick={() => setViewVisible(false)}>
            关闭
          </Button>,
        ]}
        width={1000}
        style={{ top: 20 }}
      >
        {/* 过滤工具栏 */}
        <div className={styles.filterBar}>
          <Space wrap>
            <Select
              placeholder="日志级别"
              allowClear
              style={{ width: 120 }}
              value={levelFilter}
              onChange={(value) => {
                setLevelFilter(value)
                setCurrentPage(0)
              }}
            >
              {LOG_LEVELS.map((level) => (
                <Option key={level.value} value={level.value}>
                  <Tag color={level.color} style={{ margin: 0 }}>
                    {level.label}
                  </Tag>
                </Option>
              ))}
            </Select>
            <Input
              placeholder="搜索关键词"
              prefix={<SearchOutlined />}
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              onPressEnter={handleSearch}
              style={{ width: 200 }}
              allowClear
            />
            <Button type="primary" onClick={handleSearch}>
              搜索
            </Button>
          </Space>
          <Text type="secondary">
            共 {totalLines} 行，当前显示 {logLines.length} 行
          </Text>
        </div>
        
        {/* 日志内容 */}
        <div className={styles.logContent}>
          {contentLoading ? (
            <div className={styles.loading}>加载中...</div>
          ) : logLines.length === 0 ? (
            <div className={styles.empty}>暂无日志</div>
          ) : (
            <>
              {logLines.map((line, index) => (
                <div
                  key={index}
                  className={styles.logLine}
                  style={{ borderLeftColor: line.color }}
                >
                  <span className={styles.lineNumber}>{line.line_number}</span>
                  <span className={styles.timestamp}>{line.timestamp}</span>
                  <Tag color={line.level === 'DEBUG' ? 'blue' : line.level === 'INFO' ? 'green' : line.level === 'WARNING' ? 'orange' : 'red'}>
                    {line.level}
                  </Tag>
                  <span className={styles.module}>{line.module}</span>
                  <span className={styles.message}>{line.message}</span>
                </div>
              ))}
              {totalLines > (currentPage + 1) * pageSize && (
                <Button
                  type="link"
                  onClick={loadMoreLogs}
                  block
                >
                  加载更多...
                </Button>
              )}
            </>
          )}
        </div>
      </Modal>
      
      {/* 配置弹窗 */}
      <Modal
        title="备份设置"
        open={configVisible}
        onCancel={() => setConfigVisible(false)}
        footer={[
          <Button key="cancel" onClick={() => setConfigVisible(false)}>
            取消
          </Button>,
          <Button
            key="save"
            type="primary"
            icon={<SaveOutlined />}
            onClick={handleSaveConfig}
            loading={configLoading}
          >
            保存
          </Button>,
        ]}
      >
        {config && (
          <Form layout="vertical">
            <Form.Item label="启用自动备份">
              <Switch
                checked={config.enabled}
                onChange={(checked) => handleConfigChange('enabled', checked)}
              />
            </Form.Item>
            
            <Form.Item label={`文件大小限制: ${config.max_file_size_mb} MB`}>
              <Slider
                min={1}
                max={100}
                value={config.max_file_size_mb}
                onChange={(value) => handleConfigChange('max_file_size_mb', value)}
                disabled={!config.enabled}
                marks={{
                  10: '10MB',
                  50: '50MB',
                  100: '100MB',
                }}
              />
              <Text type="secondary">
                单个日志文件超过此大小后将自动备份并创建新文件
              </Text>
            </Form.Item>
            
            <Form.Item label={`最大备份数量: ${config.max_backup_files}`}>
              <Slider
                min={10}
                max={500}
                value={config.max_backup_files}
                onChange={(value) => handleConfigChange('max_backup_files', value)}
                disabled={!config.enabled}
                marks={{
                  50: '50',
                  100: '100',
                  200: '200',
                  500: '500',
                }}
              />
              <Text type="secondary">
                超过此数量的备份文件将被自动清理
              </Text>
            </Form.Item>
            
            <Form.Item label={`自动清理: ${config.auto_cleanup ? '启用' : '禁用'}`}>
              <Switch
                checked={config.auto_cleanup}
                onChange={(checked) => handleConfigChange('auto_cleanup', checked)}
                disabled={!config.enabled}
              />
            </Form.Item>
            
            <Form.Item label={`清理阈值: ${config.cleanup_threshold}%`}>
              <Slider
                min={50}
                max={100}
                value={config.cleanup_threshold}
                onChange={(value) => handleConfigChange('cleanup_threshold', value)}
                disabled={!config.enabled || !config.auto_cleanup}
                marks={{
                  50: '50%',
                  75: '75%',
                  90: '90%',
                }}
              />
              <Text type="secondary">
                当备份文件达到最大数量的此百分比时自动清理
              </Text>
            </Form.Item>
          </Form>
        )}
      </Modal>
    </div>
  )
}
