/**
 * 注册页面
 */

import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Form, Input, Button, Card, message, Radio } from 'antd'
import { MailOutlined, LockOutlined, UserOutlined } from '@ant-design/icons'
import { authApi } from '../../api/auth'
import styles from './Register.module.css'

export default function Register() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)

  const onFinish = async (values: {
    email: string
    password: string
    confirmPassword: string
    user_type: string
  }) => {
    if (values.password !== values.confirmPassword) {
      message.error('两次输入的密码不一致')
      return
    }

    setLoading(true)
    try {
      await authApi.register({
        email: values.email,
        password: values.password,
        user_type: values.user_type,
      })
      
      message.success('注册成功，请登录')
      navigate('/login')
    } catch (error: any) {
      message.error(error.message || '注册失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={styles.container}>
      <div className={styles.content}>
        <Card className={styles.card}>
          <div className={styles.header}>
            <h1 className={styles.title}>注册账号</h1>
            <p className={styles.subtitle}>加入API Platform</p>
          </div>

          <Form
            name="register"
            onFinish={onFinish}
            autoComplete="off"
            size="large"
            initialValues={{ user_type: 'developer' }}
          >
            <Form.Item
              name="email"
              rules={[
                { required: true, message: '请输入邮箱' },
                { type: 'email', message: '请输入有效的邮箱地址' },
              ]}
            >
              <Input prefix={<MailOutlined />} placeholder="邮箱" />
            </Form.Item>

            <Form.Item
              name="password"
              rules={[
                { required: true, message: '请输入密码' },
                { min: 8, message: '密码至少8位' },
              ]}
            >
              <Input.Password prefix={<LockOutlined />} placeholder="密码（至少8位）" />
            </Form.Item>

            <Form.Item
              name="confirmPassword"
              dependencies={['password']}
              rules={[
                { required: true, message: '请确认密码' },
                ({ getFieldValue }) => ({
                  validator(_, value) {
                    if (!value || getFieldValue('password') === value) {
                      return Promise.resolve()
                    }
                    return Promise.reject(new Error('两次输入的密码不一致'))
                  },
                }),
              ]}
            >
              <Input.Password prefix={<LockOutlined />} placeholder="确认密码" />
            </Form.Item>

            <Form.Item
              name="user_type"
              rules={[{ required: true, message: '请选择账号类型' }]}
            >
              <Radio.Group buttonStyle="solid">
                <Radio.Button value="developer">开发者</Radio.Button>
                <Radio.Button value="owner">仓库所有者</Radio.Button>
              </Radio.Group>
            </Form.Item>

            <Form.Item>
              <Button type="primary" htmlType="submit" loading={loading} block>
                注册
              </Button>
            </Form.Item>

            <div className={styles.login}>
              已有账号？<Link to="/login">立即登录</Link>
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
