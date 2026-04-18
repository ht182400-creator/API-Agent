/**
 * 登录页面
 */

import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Form, Input, Button, Card, Checkbox } from 'antd'
import { UserOutlined, LockOutlined } from '@ant-design/icons'
import { authApi } from '../../api/auth'
import { useAuthStore } from '../../stores/auth'
import { useError } from '../../contexts/ErrorContext'
import { logger } from '../../utils/logger'
import styles from './Login.module.css'

export default function Login() {
  const navigate = useNavigate()
  const { setAuth } = useAuthStore()
  const [loading, setLoading] = useState(false)
  const { showError, showSuccess } = useError()

  const onFinish = async (values: { email: string; password: string; remember: boolean }) => {
    setLoading(true)
    try {
      logger.info('[Login] Attempting login', { email: values.email })
      
      const response = await authApi.login({
        email: values.email,
        password: values.password,
      })
      
      const tokenData = response
      
      if (!tokenData?.access_token) {
        throw new Error('登录失败：未获取到访问令牌')
      }
      
      // 先保存 token 到 store
      setAuth({ id: '', email: values.email, user_type: 'developer', user_status: 'active', email_verified: false, vip_level: 0, created_at: '' }, tokenData.access_token, tokenData.refresh_token)
      
      // 获取用户信息
      const user = await authApi.me()
      
      // 更新用户信息
      setAuth(user, tokenData.access_token, tokenData.refresh_token)
      
      // 设置日志用户ID
      logger.setUserId(user.id)
      
      logger.info('[Login] Success', { userId: user.id, userType: user.user_type })
      showSuccess('登录成功')
      
      // 根据用户类型跳转
      if (user.user_type === 'admin') {
        navigate('/admin')
      } else if (user.user_type === 'owner') {
        navigate('/owner')
      } else {
        navigate('/')
      }
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
            name="login"
            onFinish={onFinish}
            autoComplete="off"
            size="large"
          >
            <Form.Item
              name="email"
              rules={[
                { required: true, message: '请输入用户名或邮箱' },
                { min: 3, message: '至少3个字符' },
              ]}
            >
              <Input
                prefix={<UserOutlined />}
                placeholder="用户名或邮箱"
              />
            </Form.Item>

            <Form.Item
              name="password"
              rules={[{ required: true, message: '请输入密码' }]}
            >
              <Input.Password
                prefix={<LockOutlined />}
                placeholder="密码"
                autoComplete="current-password"
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
