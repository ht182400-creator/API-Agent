/**
 * 创建仓库页面 - V4.2新增
 * 任何用户都可以创建仓库
 * 普通用户/开发者创建的仓库需要管理员审核
 * 管理员创建的仓库直接上线
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Card,
  Form,
  Input,
  Select,
  Button,
  Typography,
  Space,
  Alert,
  Divider,
  message,
} from 'antd'
import {
  ShopOutlined,
  InfoCircleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons'
import { useAuthStore } from '../../stores/auth'
import { repoApi, CreateRepoRequest } from '../../api/repo'
import styles from './CreateRepo.module.css'

const { Title, Text, Paragraph } = Typography
const { TextArea } = Input

// 仓库类型选项 - 必须匹配后端正则: psychology|stock|ai|translation|vision|custom
const repoTypeOptions = [
  { value: 'translation', label: '翻译服务' },
  { value: 'vision', label: '图像识别' },
  { value: 'stock', label: '股票行情' },
  { value: 'psychology', label: '心理问答' },
  { value: 'ai', label: 'AI服务' },
  { value: 'custom', label: '自定义服务' },
]

// 协议类型选项 - 必须匹配后端正则: http|grpc|websocket
const protocolOptions = [
  { value: 'http', label: 'HTTP' },
  { value: 'grpc', label: 'gRPC' },
  { value: 'websocket', label: 'WebSocket' },
]

interface CreateRepoForm {
  name: string
  display_name: string
  description: string
  repo_type: string
  protocol: string
  endpoint_url?: string
}

export default function CreateRepo() {
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const [form] = Form.useForm<CreateRepoForm>()
  const [loading, setLoading] = useState(false)

  // 判断是否是管理员
  const isAdmin = user?.user_type === 'admin' || user?.user_type === 'super_admin'

  // 提交表单
  const handleSubmit = async (values: CreateRepoForm) => {
    setLoading(true)
    try {
      // 使用统一的 api 客户端
      const result = await repoApi.create(values as CreateRepoRequest)

      message.success(result.message || '仓库创建成功')
      // 根据状态跳转到不同页面
      if (result.status === 'online') {
        // 管理员创建的仓库直接上线，跳转到管理员仓库管理页面
        navigate('/admin/repos')
      } else {
        // 普通用户/开发者创建的仓库需要审核
        navigate('/developer/repos')
      }
    } catch (error: any) {
      message.error(error?.detail || error?.message || '创建失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <Title level={3}>
          <ShopOutlined style={{ marginRight: 8 }} />
          创建仓库
        </Title>
        <Text type="secondary">发布您的API服务，让更多用户使用</Text>
      </div>

      {/* 管理员提示 */}
      {isAdmin && (
        <Alert
          type="info"
          showIcon
          icon={<InfoCircleOutlined />}
          message="管理员操作"
          description="您是管理员，创建的仓库将直接上线，无需审核。"
          style={{ marginBottom: 24 }}
        />
      )}

      {/* 非管理员提示 */}
      {!isAdmin && (
        <Alert
          type="warning"
          showIcon
          icon={<ExclamationCircleOutlined />}
          message="审核须知"
          description="您创建的仓库需要管理员审核后才会正式上线。审核通过后，您将获得API销售收入分成。"
          style={{ marginBottom: 24 }}
        />
      )}

      <Card>
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          initialValues={{
            protocol: 'http',
            repo_type: 'custom',
          }}
        >
          <Form.Item
            name="name"
            label="仓库名称"
            rules={[
              { required: true, message: '请输入仓库名称' },
              { min: 3, max: 50, message: '名称长度在3-50个字符之间' },
              { pattern: /^[a-zA-Z0-9_-]+$/, message: '只允许字母、数字、下划线和连字符' },
            ]}
            extra="英文名称，用于API调用。如：weather-api"
          >
            <Input placeholder="例如：weather-api" />
          </Form.Item>

          <Form.Item
            name="display_name"
            label="显示名称"
            rules={[
              { required: true, message: '请输入显示名称' },
              { max: 100, message: '显示名称最多100个字符' },
            ]}
            extra="用户看到的友好名称"
          >
            <Input placeholder="例如：天气查询API" />
          </Form.Item>

          <Form.Item
            name="description"
            label="仓库描述"
            rules={[
              { required: true, message: '请输入仓库描述' },
              { max: 500, message: '描述最多500个字符' },
            ]}
          >
            <TextArea
              rows={4}
              placeholder="详细描述您的API服务功能、使用场景、调用方式等..."
            />
          </Form.Item>

          <Divider />

          <Form.Item
            name="repo_type"
            label="仓库类型"
            rules={[{ required: true, message: '请选择仓库类型' }]}
          >
            <Select options={repoTypeOptions} placeholder="选择API服务类型" />
          </Form.Item>

          <Form.Item
            name="protocol"
            label="协议类型"
            rules={[{ required: true, message: '请选择协议类型' }]}
          >
            <Select options={protocolOptions} placeholder="选择API协议" />
          </Form.Item>

          <Form.Item
            name="endpoint_url"
            label="API端点地址"
            rules={[
              { required: false, message: '请输入API端点地址' },
              { type: 'url', message: '请输入有效的URL地址' },
            ]}
            extra="您的API服务地址（可选）"
          >
            <Input placeholder="例如：https://api.example.com/v1" />
          </Form.Item>

          <Divider />

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={loading}>
                <CheckCircleOutlined />
                {isAdmin ? '创建并上线' : '提交审核'}
              </Button>
              <Button onClick={() => navigate(-1)}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>

      {/* 提示信息 */}
      <Card className={styles.tipsCard}>
        <Title level={5}>创建仓库提示</Title>
        <ul className={styles.tips}>
          <li>仓库名称一旦创建不可修改，请谨慎填写</li>
          <li>确保您提供的API服务稳定可靠</li>
          <li>合理设置API调用价格，获取更多收益</li>
          <li>完善API文档，帮助用户快速接入</li>
          <li>遵守平台规则，不得发布违规内容</li>
        </ul>
      </Card>
    </div>
  )
}
