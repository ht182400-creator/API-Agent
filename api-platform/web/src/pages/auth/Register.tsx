/**
 * 注册页面
 */

import { useState, useEffect, useCallback } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Form, Input, Button, Card, message, Radio } from 'antd'
import { MailOutlined, LockOutlined, UserOutlined, EyeInvisibleOutlined, EyeTwoTone } from '@ant-design/icons'
import { authApi } from '../../api/auth'
import styles from './Register.module.css'

// 根据用户类型获取提示文本
const getUserTypeHint = (userType: string): string => {
  switch (userType) {
    case 'developer':
      return '开发者可使用API服务、创建仓库并获得收益分成'
    case 'user':
      return '普通用户可领取试用金额，升级后成为开发者'
    default:
      return ''
  }
}

export default function Register() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [userType, setUserType] = useState<string>('developer')
  const [form] = Form.useForm()

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
  }, [])

  // 组件挂载时清空表单（包括密码字段）
  useEffect(() => {
    // 清空整个表单，包括密码等敏感字段
    form.resetFields()
    
    // 使用多个延迟清空任务，覆盖浏览器延迟填充的时机
    const timers = [
      setTimeout(() => clearAutofillData(), 300),
      setTimeout(() => clearAutofillData(), 1000),
      setTimeout(() => clearAutofillData(), 2000),
    ]
    
    // 清除 sessionStorage 中的敏感信息
    try {
      sessionStorage.removeItem('pending_password')
      sessionStorage.removeItem('register_password')
    } catch (e) {}
    
    return () => {
      timers.forEach(clearTimeout)
    }
  }, [form, clearAutofillData])

  const onFinish = async (values: {
    username: string
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
        username: values.username,
        email: values.email,
        password: values.password,
        user_type: values.user_type,
      })
      
      message.success('注册成功，请登录')
      
      // 清空表单中的密码（内存中的密码值）
      form.setFieldValue('password', '')
      form.setFieldValue('confirmPassword', '')
      
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
              name="username"
              rules={[
                { required: true, message: '请输入用户名' },
                { min: 3, max: 50, message: '用户名3-50个字符' },
                { pattern: /^[a-zA-Z0-9_]+$/, message: '只能是字母、数字、下划线' },
              ]}
            >
              <Input prefix={<UserOutlined />} placeholder="用户名（用于登录）" autoComplete="off" />
            </Form.Item>

            <Form.Item
              name="email"
              rules={[
                { required: true, message: '请输入邮箱' },
                { type: 'email', message: '请输入有效的邮箱地址' },
              ]}
            >
              <Input prefix={<MailOutlined />} placeholder="邮箱" autoComplete="off" />
            </Form.Item>

            <Form.Item
              name="password"
              rules={[
                { required: true, message: '请输入密码' },
                { min: 8, message: '密码至少8位' },
              ]}
            >
              <Input.Password 
                prefix={<LockOutlined />} 
                placeholder="密码（至少8位）"
                autoComplete="new-password"
                iconRender={(visible) => 
                  visible ? <EyeTwoTone /> : <EyeInvisibleOutlined />
                }
              />
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
              <Input.Password 
                prefix={<LockOutlined />} 
                placeholder="确认密码"
                autoComplete="new-password"
                iconRender={(visible) => 
                  visible ? <EyeTwoTone /> : <EyeInvisibleOutlined />
                }
              />
            </Form.Item>

            <Form.Item
              name="user_type"
              rules={[{ required: true, message: '请选择账号类型' }]}
              extra={getUserTypeHint(userType)}
            >
              <Radio.Group 
                buttonStyle="solid"
                onChange={(e) => setUserType(e.target.value)}
              >
                <Radio.Button value="user">普通用户</Radio.Button>
                {/* 【V4.0 重构】去掉 owner 选项，owner = developer + 有仓库 */}
                <Radio.Button value="developer">开发者</Radio.Button>
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
