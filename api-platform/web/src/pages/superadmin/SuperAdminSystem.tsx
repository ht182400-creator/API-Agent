/**
 * 超级管理员 - 系统配置页面
 * 数据从数据库获取
 */

import { useState, useEffect } from 'react'
import '../../styles/cyber-theme.css'
import { Card, Form, Input, Switch, Select, Button, Tabs, Space, message, Typography, Divider, Spin, Tag } from 'antd'
import { SettingOutlined, GlobalOutlined, SafetyOutlined, DatabaseOutlined, SaveOutlined } from '@ant-design/icons'
import { configApi, ConfigItem } from '../../api/superadmin'

const { Title, Text } = Typography

export default function SuperAdminSystem() {
  const [form] = Form.useForm()
  const [securityForm] = Form.useForm()
  const [apiForm] = Form.useForm()
  const [loggingForm] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [initLoading, setInitLoading] = useState(false)
  const [configs, setConfigs] = useState<ConfigItem[]>([])
  const [configLoading, setConfigLoading] = useState(true)
  const [savingKey, setSavingKey] = useState<string | null>(null)

  useEffect(() => {
    loadConfigs()
  }, [])

  const loadConfigs = async () => {
    try {
      setConfigLoading(true)
      const data = await configApi.list()
      setConfigs(data || [])
      
      // 填充表单值
      const configMap: Record<string, string> = {}
      data.forEach(c => {
        configMap[`${c.category}.${c.key}`] = c.value || ''
      })
      
      form.setFieldsValue({
        siteName: configMap['general.site_name'],
        siteUrl: configMap['general.site_url'],
        supportEmail: configMap['general.support_email'],
        timezone: configMap['general.timezone'],
        language: configMap['general.language'],
      })
      
      securityForm.setFieldsValue({
        passwordMinLength: configMap['security.password_min_length'],
        passwordRequireUppercase: configMap['security.password_require_uppercase'] === 'true',
        passwordRequireNumber: configMap['security.password_require_number'] === 'true',
        passwordRequireSpecial: configMap['security.password_require_special'] === 'true',
        sessionTimeout: configMap['security.session_timeout'],
        maxLoginAttempts: configMap['security.max_login_attempts'],
        enableMFA: configMap['security.enable_mfa'] === 'true',
        enableCaptcha: configMap['security.enable_captcha'] === 'true',
      })
      
      apiForm.setFieldsValue({
        defaultRateLimitRpm: configMap['api.default_rate_limit_rpm'],
        defaultDailyQuota: configMap['api.default_daily_quota'],
        keyPrefix: configMap['api.key_prefix'],
        keyLength: configMap['api.key_length'],
      })
      
      loggingForm.setFieldsValue({
        logLevel: configMap['logging.level'],
        logRetention: configMap['logging.retention_days'],
        enableAudit: configMap['logging.enable_audit'] === 'true',
        enableMetrics: configMap['logging.enable_metrics'] === 'true',
        cacheType: configMap['cache.type'],
        cacheTTL: configMap['cache.ttl'],
      })
    } catch (error) {
      console.error('加载配置失败:', error)
      message.error('加载配置失败')
    } finally {
      setConfigLoading(false)
    }
  }

  const handleSaveConfig = async (category: string, key: string, value: string, configId?: string) => {
    if (!configId) {
      message.warning('配置项不存在，无法保存')
      return
    }
    
    try {
      setSavingKey(configId)
      await configApi.update(configId, value)
      message.success('配置已保存')
      
      // 更新本地状态
      setConfigs(prev => prev.map(c => 
        c.id === configId ? { ...c, value } : c
      ))
    } catch (error: any) {
      message.error(error.message || '保存失败')
    } finally {
      setSavingKey(null)
    }
  }

  const handleSaveGeneral = async () => {
    const values = form.getFieldsValue()
    const configMap = configs.reduce((acc, c) => {
      acc[`${c.category}.${c.key}`] = c
      return acc
    }, {} as Record<string, ConfigItem>)
    
    setLoading(true)
    try {
      // 保存各项配置
      if (configMap['general.site_name']) {
        await handleSaveConfig('general', 'site_name', values.siteName, configMap['general.site_name'].id)
      }
      if (configMap['general.site_url']) {
        await handleSaveConfig('general', 'site_url', values.siteUrl, configMap['general.site_url'].id)
      }
      if (configMap['general.support_email']) {
        await handleSaveConfig('general', 'support_email', values.supportEmail, configMap['general.support_email'].id)
      }
      if (configMap['general.timezone']) {
        await handleSaveConfig('general', 'timezone', values.timezone, configMap['general.timezone'].id)
      }
      if (configMap['general.language']) {
        await handleSaveConfig('general', 'language', values.language, configMap['general.language'].id)
      }
    } finally {
      setLoading(false)
    }
  }

  const handleSaveSecurity = async () => {
    const values = securityForm.getFieldsValue()
    const configMap = configs.reduce((acc, c) => {
      acc[`${c.category}.${c.key}`] = c
      return acc
    }, {} as Record<string, ConfigItem>)
    
    setLoading(true)
    try {
      if (configMap['security.password_min_length']) {
        await handleSaveConfig('security', 'password_min_length', String(values.passwordMinLength), configMap['security.password_min_length'].id)
      }
      if (configMap['security.password_require_uppercase']) {
        await handleSaveConfig('security', 'password_require_uppercase', String(values.passwordRequireUppercase), configMap['security.password_require_uppercase'].id)
      }
      if (configMap['security.password_require_number']) {
        await handleSaveConfig('security', 'password_require_number', String(values.passwordRequireNumber), configMap['security.password_require_number'].id)
      }
      if (configMap['security.password_require_special']) {
        await handleSaveConfig('security', 'password_require_special', String(values.passwordRequireSpecial), configMap['security.password_require_special'].id)
      }
      if (configMap['security.session_timeout']) {
        await handleSaveConfig('security', 'session_timeout', String(values.sessionTimeout), configMap['security.session_timeout'].id)
      }
      if (configMap['security.max_login_attempts']) {
        await handleSaveConfig('security', 'max_login_attempts', String(values.maxLoginAttempts), configMap['security.max_login_attempts'].id)
      }
      if (configMap['security.enable_mfa']) {
        await handleSaveConfig('security', 'enable_mfa', String(values.enableMFA), configMap['security.enable_mfa'].id)
      }
      if (configMap['security.enable_captcha']) {
        await handleSaveConfig('security', 'enable_captcha', String(values.enableCaptcha), configMap['security.enable_captcha'].id)
      }
    } finally {
      setLoading(false)
    }
  }

  const handleSaveApi = async () => {
    const values = apiForm.getFieldsValue()
    const configMap = configs.reduce((acc, c) => {
      acc[`${c.category}.${c.key}`] = c
      return acc
    }, {} as Record<string, ConfigItem>)
    
    setLoading(true)
    try {
      if (configMap['api.default_rate_limit_rpm']) {
        await handleSaveConfig('api', 'default_rate_limit_rpm', String(values.defaultRateLimitRpm), configMap['api.default_rate_limit_rpm'].id)
      }
      if (configMap['api.default_daily_quota']) {
        await handleSaveConfig('api', 'default_daily_quota', String(values.defaultDailyQuota), configMap['api.default_daily_quota'].id)
      }
      if (configMap['api.key_prefix']) {
        await handleSaveConfig('api', 'key_prefix', values.keyPrefix, configMap['api.key_prefix'].id)
      }
      if (configMap['api.key_length']) {
        await handleSaveConfig('api', 'key_length', String(values.keyLength), configMap['api.key_length'].id)
      }
    } finally {
      setLoading(false)
    }
  }

  const handleSaveLogging = async () => {
    const values = loggingForm.getFieldsValue()
    const configMap = configs.reduce((acc, c) => {
      acc[`${c.category}.${c.key}`] = c
      return acc
    }, {} as Record<string, ConfigItem>)
    
    setLoading(true)
    try {
      if (configMap['logging.level']) {
        await handleSaveConfig('logging', 'level', values.logLevel, configMap['logging.level'].id)
      }
      if (configMap['logging.retention_days']) {
        await handleSaveConfig('logging', 'retention_days', String(values.logRetention), configMap['logging.retention_days'].id)
      }
      if (configMap['logging.enable_audit']) {
        await handleSaveConfig('logging', 'enable_audit', String(values.enableAudit), configMap['logging.enable_audit'].id)
      }
      if (configMap['logging.enable_metrics']) {
        await handleSaveConfig('logging', 'enable_metrics', String(values.enableMetrics), configMap['logging.enable_metrics'].id)
      }
      if (configMap['cache.type']) {
        await handleSaveConfig('cache', 'type', values.cacheType, configMap['cache.type'].id)
      }
      if (configMap['cache.ttl']) {
        await handleSaveConfig('cache', 'ttl', String(values.cacheTTL), configMap['cache.ttl'].id)
      }
    } finally {
      setLoading(false)
    }
  }

  const handleInitialize = async () => {
    try {
      setInitLoading(true)
      const result = await configApi.initialize()
      message.success(result.message || '初始化成功')
      loadConfigs()
    } catch (error: any) {
      message.error(error.message || '初始化失败')
    } finally {
      setInitLoading(false)
    }
  }

  if (configLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 400 }}>
        <Spin size="large" />
      </div>
    )
  }

  const tabItems = [
    {
      key: 'general',
      label: <span><GlobalOutlined /> 通用设置</span>,
      children: (
        <Form form={form} layout="vertical">
          <Form.Item label="平台名称" name="siteName">
            <Input />
          </Form.Item>
          <Form.Item label="平台地址" name="siteUrl">
            <Input />
          </Form.Item>
          <Form.Item label="支持邮箱" name="supportEmail">
            <Input />
          </Form.Item>
          <Form.Item label="时区" name="timezone">
            <Select>
              <Select.Option value="Asia/Shanghai">Asia/Shanghai (UTC+8)</Select.Option>
              <Select.Option value="America/New_York">America/New_York (UTC-5)</Select.Option>
              <Select.Option value="Europe/London">Europe/London (UTC+0)</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item label="默认语言" name="language">
            <Select>
              <Select.Option value="zh-CN">简体中文</Select.Option>
              <Select.Option value="en-US">English</Select.Option>
            </Select>
          </Form.Item>
          <Button type="primary" icon={<SaveOutlined />} onClick={handleSaveGeneral} loading={loading}>
            保存设置
          </Button>
        </Form>
      ),
    },
    {
      key: 'security',
      label: <span><SafetyOutlined /> 安全设置</span>,
      children: (
        <Form form={securityForm} layout="vertical">
          <Divider>密码策略</Divider>
          <Form.Item label="密码最小长度" name="passwordMinLength">
            <Select style={{ width: 200 }}>
              {[6, 8, 10, 12, 16].map(len => <Select.Option key={len} value={len}>{len} 位</Select.Option>)}
            </Select>
          </Form.Item>
          <Form.Item label="必须包含大写字母" name="passwordRequireUppercase" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item label="必须包含数字" name="passwordRequireNumber" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item label="必须包含特殊字符" name="passwordRequireSpecial" valuePropName="checked">
            <Switch />
          </Form.Item>

          <Divider>会话与登录</Divider>
          <Form.Item label="会话超时时间(分钟)" name="sessionTimeout">
            <Select style={{ width: 200 }}>
              {[15, 30, 60, 120, 240].map(min => <Select.Option key={min} value={min}>{min} 分钟</Select.Option>)}
            </Select>
          </Form.Item>
          <Form.Item label="最大登录失败次数" name="maxLoginAttempts">
            <Select style={{ width: 200 }}>
              {[3, 5, 10, 20].map(num => <Select.Option key={num} value={num}>{num} 次</Select.Option>)}
            </Select>
          </Form.Item>

          <Divider>双重认证</Divider>
          <Form.Item label="启用双因素认证" name="enableMFA" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item label="启用验证码" name="enableCaptcha" valuePropName="checked">
            <Switch />
          </Form.Item>

          <Button type="primary" icon={<SaveOutlined />} onClick={handleSaveSecurity} loading={loading}>
            保存设置
          </Button>
        </Form>
      ),
    },
    {
      key: 'api',
      label: <span><SettingOutlined /> API设置</span>,
      children: (
        <Form form={apiForm} layout="vertical">
          <Divider>限流与配额</Divider>
          <Form.Item label="默认API限流(RPM)" name="defaultRateLimitRpm">
            <Select style={{ width: 200 }}>
              {[30, 60, 100, 200, 500].map(num => <Select.Option key={num} value={num}>{num} RPM</Select.Option>)}
            </Select>
          </Form.Item>
          <Form.Item label="默认每日配额" name="defaultDailyQuota">
            <Select style={{ width: 200 }}>
              {[500, 1000, 5000, 10000, 50000].map(num => <Select.Option key={num} value={num}>{num} 次</Select.Option>)}
            </Select>
          </Form.Item>

          <Divider>API Key配置</Divider>
          <Form.Item label="API Key前缀" name="keyPrefix">
            <Input style={{ width: 200 }} />
          </Form.Item>
          <Form.Item label="API Key长度" name="keyLength">
            <Select style={{ width: 200 }}>
              {[16, 24, 32, 48].map(len => <Select.Option key={len} value={len}>{len} 字符</Select.Option>)}
            </Select>
          </Form.Item>

          <Button type="primary" icon={<SaveOutlined />} onClick={handleSaveApi} loading={loading}>
            保存设置
          </Button>
        </Form>
      ),
    },
    {
      key: 'logging',
      label: <span><SettingOutlined /> 日志与缓存</span>,
      children: (
        <Form form={loggingForm} layout="vertical">
          <Divider>日志配置</Divider>
          <Form.Item label="日志级别" name="logLevel">
            <Select>
              <Select.Option value="DEBUG">DEBUG</Select.Option>
              <Select.Option value="INFO">INFO</Select.Option>
              <Select.Option value="WARNING">WARNING</Select.Option>
              <Select.Option value="ERROR">ERROR</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item label="日志保留天数" name="logRetention">
            <Select style={{ width: 200 }}>
              {[7, 14, 30, 60, 90, 180, 365].map(num => <Select.Option key={num} value={num}>{num} 天</Select.Option>)}
            </Select>
          </Form.Item>
          <Form.Item label="启用审计日志" name="enableAudit" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item label="启用性能指标" name="enableMetrics" valuePropName="checked">
            <Switch />
          </Form.Item>

          <Divider>缓存配置</Divider>
          <Form.Item label="缓存类型" name="cacheType">
            <Select>
              <Select.Option value="redis">Redis</Select.Option>
              <Select.Option value="memcached">Memcached</Select.Option>
              <Select.Option value="memory">内存缓存</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item label="缓存TTL(秒)" name="cacheTTL">
            <Select style={{ width: 200 }}>
              {[300, 600, 1800, 3600, 7200].map(num => <Select.Option key={num} value={num}>{num} 秒</Select.Option>)}
            </Select>
          </Form.Item>

          <Button type="primary" icon={<SaveOutlined />} onClick={handleSaveLogging} loading={loading}>
            保存设置
          </Button>
        </Form>
      ),
    },
  ]

  return (
    <div style={{ padding: 24 }} className="bamboo-bg-pattern">
      <div style={{ marginBottom: 24 }}>
        <Title level={2}><SettingOutlined /> 系统配置</Title>
        <Text type="secondary">全局系统参数配置</Text>
        <div style={{ marginTop: 8 }}>
          <Button 
            type="link" 
            onClick={handleInitialize}
            loading={initLoading}
          >
            初始化/重置配置
          </Button>
        </div>
      </div>

      <Card>
        <Tabs items={tabItems} tabPosition="left" style={{ minHeight: 500 }} />
      </Card>
    </div>
  )
}
