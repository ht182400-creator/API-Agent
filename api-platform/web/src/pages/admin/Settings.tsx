/**
 * 系统设置页面
 */

import { Card, Form, Input, Button, Switch, Space, Typography, Divider, message, Slider } from 'antd'
import { SaveOutlined, FolderOutlined, ArrowRightOutlined } from '@ant-design/icons'
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getBackupConfig, updateBackupConfig, BackupConfig } from '../../api/adminLogs'
import styles from './Settings.module.css'

const { Title, Text, Link } = Typography

export default function AdminSettings() {
  const [loading, setLoading] = useState(false)
  const [form] = Form.useForm()
  const [backupConfig, setBackupConfig] = useState<BackupConfig | null>(null)
  const [backupLoading, setBackupLoading] = useState(false)
  const navigate = useNavigate()

  // 加载备份配置
  useEffect(() => {
    loadBackupConfig()
  }, [])

  const loadBackupConfig = async () => {
    setBackupLoading(true)
    try {
      const data = await getBackupConfig()
      setBackupConfig(data)
    } catch (error) {
      console.error('加载备份配置失败:', error)
    } finally {
      setBackupLoading(false)
    }
  }

  const handleSave = async () => {
    setLoading(true)
    try {
      // 保存设置
      await new Promise(resolve => setTimeout(resolve, 1000))
      message.success('设置已保存')
    } catch (error) {
      message.error('保存失败')
    } finally {
      setLoading(false)
    }
  }

  const handleSaveBackupConfig = async () => {
    if (!backupConfig) return
    try {
      await updateBackupConfig(backupConfig)
      message.success('日志备份配置已保存')
    } catch (error) {
      message.error('保存失败')
    }
  }

  const handleBackupConfigChange = (key: keyof BackupConfig, value: any) => {
    if (backupConfig) {
      setBackupConfig({ ...backupConfig, [key]: value })
    }
  }

  return (
    <div className={styles.container}>
      <Title level={4}>系统设置</Title>

      <Card title="基础设置" className={styles.card}>
        <Form form={form} layout="vertical">
          <Form.Item label="平台名称">
            <Input defaultValue="API Platform" />
          </Form.Item>
          <Form.Item label="平台Logo URL">
            <Input placeholder="https://example.com/logo.png" />
          </Form.Item>
          <Form.Item label="联系邮箱">
            <Input defaultValue="support@platform.com" />
          </Form.Item>
        </Form>
      </Card>

      <Card title="注册设置" className={styles.card}>
        <Form layout="vertical">
          <Form.Item label="允许新用户注册">
            <Switch defaultChecked />
          </Form.Item>
          <Form.Item label="注册验证码">
            <Switch defaultChecked />
          </Form.Item>
          <Form.Item label="新用户默认类型">
            <Space>
              <Switch defaultChecked /> 开发者
              <Switch /> 仓库所有者（需审核）
            </Space>
          </Form.Item>
        </Form>
      </Card>

      <Card title="API调用设置" className={styles.card}>
        <Form layout="vertical">
          <Form.Item label="默认RPM限制">
            <Input type="number" defaultValue={1000} style={{ width: 200 }} />
          </Form.Item>
          <Form.Item label="默认RPH限制">
            <Input type="number" defaultValue={10000} style={{ width: 200 }} />
          </Form.Item>
          <Form.Item label="新用户免费配额（次/日）">
            <Input type="number" defaultValue={100} style={{ width: 200 }} />
          </Form.Item>
        </Form>
      </Card>

      <Card title="计费设置" className={styles.card}>
        <Form layout="vertical">
          <Form.Item label="启用计费">
            <Switch defaultChecked />
          </Form.Item>
          <Form.Item label="最低充值金额">
            <Input type="number" defaultValue={10} style={{ width: 200 }} suffix="元" />
          </Form.Item>
        </Form>
      </Card>

      <Card 
        title="日志备份设置" 
        className={styles.card}
        extra={
          <Link onClick={() => navigate('/admin/logs')}>
            打开日志管理 <ArrowRightOutlined />
          </Link>
        }
      >
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <Form.Item label="启用自动备份">
            <Switch
              checked={backupConfig?.enabled ?? true}
              onChange={(checked) => handleBackupConfigChange('enabled', checked)}
            />
          </Form.Item>

          <Form.Item label={`文件大小限制: ${backupConfig?.max_file_size_mb ?? 10} MB`}>
            <Slider
              min={1}
              max={100}
              value={backupConfig?.max_file_size_mb ?? 10}
              onChange={(value) => handleBackupConfigChange('max_file_size_mb', value)}
              disabled={!backupConfig?.enabled}
              marks={{
                10: '10MB',
                50: '50MB',
                100: '100MB',
              }}
            />
            <Text type="secondary">
              单个日志文件超过此大小后将自动备份
            </Text>
          </Form.Item>

          <Form.Item label={`最大备份数量: ${backupConfig?.max_backup_files ?? 100}`}>
            <Slider
              min={10}
              max={500}
              value={backupConfig?.max_backup_files ?? 100}
              onChange={(value) => handleBackupConfigChange('max_backup_files', value)}
              disabled={!backupConfig?.enabled}
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

          <Form.Item label="自动清理">
            <Switch
              checked={backupConfig?.auto_cleanup ?? true}
              onChange={(checked) => handleBackupConfigChange('auto_cleanup', checked)}
              disabled={!backupConfig?.enabled}
            />
          </Form.Item>

          <Form.Item label={`清理阈值: ${backupConfig?.cleanup_threshold ?? 80}%`}>
            <Slider
              min={50}
              max={100}
              value={backupConfig?.cleanup_threshold ?? 80}
              onChange={(value) => handleBackupConfigChange('cleanup_threshold', value)}
              disabled={!backupConfig?.enabled || !backupConfig?.auto_cleanup}
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

          <Button 
            type="primary" 
            icon={<SaveOutlined />} 
            onClick={handleSaveBackupConfig}
            loading={backupLoading}
          >
            保存备份设置
          </Button>
        </Space>
      </Card>

      <Button type="primary" icon={<SaveOutlined />} loading={loading} onClick={handleSave} size="large">
        保存设置
      </Button>
    </div>
  )
}
