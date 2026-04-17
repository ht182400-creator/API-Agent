/**
 * 登录页面
 */

import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Form, Input, Button, Card, message, Checkbox } from 'antd'
import { UserOutlined, LockOutlined } from '@ant-design/icons'
import { authApi } from '../../api/auth'
import { useAuthStore } from '../../stores/auth'
import styles from './Login.module.css'

export default function Login() {
  const navigate = useNavigate()
  const { setAuth } = useAuthStore()
  const [loading, setLoading] = useState(false)

  const onFinish = async (values: { email: string; password: string; remember: boolean }) => {
    setLoading(true)
    try {
      const { data } = await authApi.login({
        email: values.email,
        password: values.password,
      })
      
      // 获取用户信息
      const { data: user } = await authApi.me()
      
      // 保存认证信息
      setAuth(user, data.access_token, data.refresh_token)
      
      message.success('登录成功')
      
      // 根据用户类型跳转
      if (user.user_type === 'admin') {
        navigate('/admin')
      } else if (user.user_type === 'owner') {
        navigate('/owner')
      } else {
        navigate('/')
      }
    } catch (error: any) {
      message.error(error.message || '登录失败')
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
                { required: true, message: '请输入邮箱' },
                { type: 'email', message: '请输入有效的邮箱地址' },
              ]}
            >
              <Input
                prefix={<UserOutlined />}
                placeholder="邮箱"
              />
            </Form.Item>

            <Form.Item
              name="password"
              rules={[{ required: true, message: '请输入密码' }]}
            >
              <Input.Password
                prefix={<LockOutlined />}
                placeholder="密码"
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
