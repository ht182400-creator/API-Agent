/**
 * 登录页面
 */

import { useState, useEffect, useCallback } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Form, Input, Button, Card, Checkbox, message } from 'antd'
import { UserOutlined, LockOutlined, EyeInvisibleOutlined, EyeTwoTone } from '@ant-design/icons'
import { authApi } from '../../api/auth'
import { useAuthStore } from '../../stores/auth'
import { useError } from '../../contexts/ErrorContext'
import { logger } from '../../utils/logger'
import styles from './Login.module.css'

// 存储上次登录的用户名/邮箱，用于退出后清空
let lastLoginIdentifier = ''

// 用户类型映射到重定向路径
const getRedirectPath = (userType: string): string => {
  switch (userType) {
    case 'super_admin':
      return '/superadmin'
    case 'admin':
      return '/admin'
    case 'owner':
      return '/owner'
    case 'user':
      return '/user'  // 普通用户跳转到 /user 引导页
    case 'developer':
    default:
      return '/'  // 开发者跳转到 /
  }
}

// 获取用户类型显示名称
const getUserTypeLabel = (userType: string): string => {
  const labels: Record<string, string> = {
    super_admin: '超级管理员',
    admin: '管理员',
    owner: '仓库所有者',
    developer: '开发者',
    user: '普通用户',
  }
  return labels[userType] || userType
}

export default function Login() {
  const navigate = useNavigate()
  const { setAuth } = useAuthStore()
  const [loading, setLoading] = useState(false)
  const [form] = Form.useForm()
  const { showError } = useError()

  // 清除输入框中的浏览器自动填充数据
  const clearAutofillData = useCallback(() => {
    // 清除所有密码输入框
    const passwordInputs = document.querySelectorAll('input[type="password"]')
    passwordInputs.forEach((input) => {
      if (input instanceof HTMLInputElement && input.value) {
        input.value = ''
        input.dispatchEvent(new Event('input', { bubbles: true }))
        input.dispatchEvent(new Event('change', { bubbles: true }))
      }
    })
    
    // 清除用户名输入框
    const usernameInput = document.querySelector('input[placeholder="用户名或邮箱"]')
    if (usernameInput instanceof HTMLInputElement && usernameInput.value) {
      usernameInput.value = ''
      usernameInput.dispatchEvent(new Event('input', { bubbles: true }))
    }
  }, [])

  // 组件挂载时清空表单（包括密码字段），确保安全
  useEffect(() => {
    // 清空整个表单，包括密码等敏感字段
    form.resetFields()
    
    // 使用多个延迟清空任务，覆盖浏览器延迟填充的时机
    // 浏览器填充通常发生在页面加载后 300ms-2s 内
    const timers = [
      setTimeout(() => clearAutofillData(), 300),
      setTimeout(() => clearAutofillData(), 1000),
      setTimeout(() => clearAutofillData(), 2000),
    ]
    
    // 清除 sessionStorage 中可能残留的敏感信息
    try {
      sessionStorage.removeItem('pending_password')
      sessionStorage.removeItem('login_password')
    } catch (e) {
      // 忽略 sessionStorage 错误
    }
    
    return () => {
      timers.forEach(clearTimeout)
    }
  }, [form, clearAutofillData])

  const onFinish = async (values: { identifier: string; password: string; remember: boolean }) => {
    setLoading(true)
    try {
      logger.info('[Login] Attempting login', { identifier: values.identifier })
      
      // 保存登录标识（用于后续可能的自动填充清除）
      lastLoginIdentifier = values.identifier
      
      // 根据输入自动判断是邮箱还是用户名
      const loginData: { email?: string; username?: string; password: string } = {
        password: values.password,
      }
      
      if (values.identifier.includes('@')) {
        // 邮箱登录
        loginData.email = values.identifier
      } else {
        // 用户名登录
        loginData.username = values.identifier
      }
      
      const response = await authApi.login(loginData)
      
      const tokenData = response
      
      if (!tokenData?.access_token) {
        throw new Error('登录失败：未获取到访问令牌')
      }
      
      // 先保存 token 到 store
      setAuth({ 
        id: '', 
        email: values.email, 
        user_type: 'developer', 
        role: 'user',
        user_status: 'active', 
        email_verified: false, 
        vip_level: 0, 
        created_at: '' 
      }, tokenData.access_token, tokenData.refresh_token)
      
      // 获取用户信息
      const user = await authApi.me()
      
      // 更新用户信息
      setAuth(user, tokenData.access_token, tokenData.refresh_token)
      
      // 设置日志用户ID
      logger.setUserId(user.id)
      
      logger.info('[Login] Success', { 
        userId: user.id, 
        userType: user.user_type,
        role: user.role 
      })
      
      // 清空表单中的密码（内存中的密码值）
      form.setFieldValue('password', '')
      
      // 根据用户类型重定向到对应页面
      const redirectPath = getRedirectPath(user.user_type)
      logger.info('[Login] Redirecting to', { path: redirectPath })
      navigate(redirectPath, { replace: true })
      
    } catch (error: any) {
      logger.error('[Login] Failed', {
        message: error.message,
        email: values.email,
      })
      // 使用统一的错误处理
      showError(error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={styles.container}>
      <div className={styles.content}>
        <Card className={styles.card}>
          <div className={styles.header}>
            <h1 className={styles.title}>API Platform</h1>
            <p className={styles.subtitle}>通用API服务平台</p>
          </div>

          <Form
            form={form}
            name="login"
            onFinish={onFinish}
            autoComplete="off"
            size="large"
          >
            <Form.Item
              name="identifier"
              rules={[
                { required: true, message: '请输入用户名或邮箱' },
                { min: 3, message: '至少3个字符' },
              ]}
            >
              <Input
                prefix={<UserOutlined />}
                placeholder="用户名或邮箱"
                autoComplete="off"
              />
            </Form.Item>

            <Form.Item
              name="password"
              rules={[{ required: true, message: '请输入密码' }]}
            >
              <Input.Password
                prefix={<LockOutlined />}
                placeholder="密码"
                autoComplete="new-password"
                iconRender={(visible) => 
                  visible ? <EyeTwoTone /> : <EyeInvisibleOutlined />
                }
              />
            </Form.Item>

            <Form.Item>
              <div className={styles.formFooter}>
                <Form.Item name="remember" valuePropName="checked" noStyle>
                  <Checkbox>记住我</Checkbox>
                </Form.Item>
                <Link to="/forgot-password">忘记密码？</Link>
              </div>
            </Form.Item>

            <Form.Item>
              <Button type="primary" htmlType="submit" loading={loading} block>
                登录
              </Button>
            </Form.Item>

            <div className={styles.register}>
              还没有账号？<Link to="/register">立即注册</Link>
            </div>
          </Form>
        </Card>

        <div className={styles.footer}>
          <p>© 2024 API Platform. All rights reserved.</p>
        </div>
      </div>
    </div>
  )
}
