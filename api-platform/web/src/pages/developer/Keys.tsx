/**
 * API Keys管理页面
 */

import { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, Select, message, Tag, Popconfirm, Space, Typography } from 'antd'
import { PlusOutlined, KeyOutlined, DeleteOutlined, StopOutlined, CheckCircleOutlined, EyeOutlined } from '@ant-design/icons'
import { quotaApi, APIKey, CreateKeyRequest } from '../../api/quota'
import { useErrorModal, extractErrorMessage, parseErrorType } from '../../components/ErrorModal'
import dayjs from 'dayjs'
import styles from './Keys.module.css'

const { Title, Text } = Typography

export default function DeveloperKeys() {
  const [loading, setLoading] = useState(false)
  const [keys, setKeys] = useState<APIKey[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [modalVisible, setModalVisible] = useState(false)
  const [createLoading, setCreateLoading] = useState(false)
  const [newKeyData, setNewKeyData] = useState<APIKey | null>(null)
  const [revealModalVisible, setRevealModalVisible] = useState(false)
  const [revealLoading, setRevealLoading] = useState(false)
  const [revealKeyData, setRevealKeyData] = useState<{ key_name: string; api_key: string } | null>(null)
  const [form] = Form.useForm()

  // 使用统一的错误提示
  const { showError, closeError, ErrorModal: ErrorModalComponent } = useErrorModal()

  useEffect(() => {
    fetchKeys()
  }, [page, pageSize])

  const fetchKeys = async () => {
    setLoading(true)
    try {
      // api.get 已返回 res.data，所以直接是 PaginatedResponse
      const data = await quotaApi.getKeys({ page, page_size: pageSize })
      setKeys(data.items)
      setTotal(data.pagination.total)
    } catch (error: any) {
      // 使用友好的错误提示
      showError(error, () => fetchKeys())
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = async (values: CreateKeyRequest) => {
    setCreateLoading(true)
    try {
      // api.post 已返回 res.data，所以直接是 APIKey 对象
      const newKey = await quotaApi.createKey(values)
      setNewKeyData(newKey)
      setModalVisible(false)
      form.resetFields()
      message.success('API Key创建成功')
      fetchKeys()
    } catch (error: any) {
      // 使用友好的错误提示
      showError(error, () => handleCreate(values))
    } finally {
      setCreateLoading(false)
    }
  }

  const handleDisable = async (keyId: string) => {
    try {
      await quotaApi.disableKey(keyId)
      message.success('API Key已禁用')
      fetchKeys()
    } catch (error: any) {
      showError(error, () => handleDisable(keyId))
    }
  }

  const handleEnable = async (keyId: string) => {
    try {
      await quotaApi.enableKey(keyId)
      message.success('API Key已启用')
      fetchKeys()
    } catch (error: any) {
      showError(error, () => handleEnable(keyId))
    }
  }

  const handleDelete = async (keyId: string) => {
    try {
      await quotaApi.deleteKey(keyId)
      message.success('API Key已删除')
      fetchKeys()
    } catch (error: any) {
      showError(error, () => handleDelete(keyId))
    }
  }

  const handleReveal = async (keyId: string) => {
    setRevealLoading(true)
    try {
      const data = await quotaApi.revealKey(keyId)
      setRevealKeyData(data)
      setRevealModalVisible(true)
    } catch (error: any) {
      showError(error, () => handleReveal(keyId))
    } finally {
      setRevealLoading(false)
    }
  }

  const columns = [
    {
      title: 'Key名称',
      dataIndex: 'key_name',
      key: 'key_name',
    },
    {
      title: 'Key前缀',
      dataIndex: 'key_prefix',
      key: 'key_prefix',
      render: (prefix: string) => <Tag color="blue">{prefix}...****</Tag>,
    },
    {
      title: '认证方式',
      dataIndex: 'auth_type',
      key: 'auth_type',
      render: (type: string) => (
        <Tag>{type === 'api_key' ? 'API Key' : type === 'hmac' ? 'HMAC' : 'JWT'}</Tag>
      ),
    },
    {
      title: 'RPM限制',
      dataIndex: 'rate_limit_rpm',
      key: 'rate_limit_rpm',
      render: (rpm: number) => `${rpm}次/分钟`,
    },
    {
      title: 'RPH限制',
      dataIndex: 'rate_limit_rph',
      key: 'rate_limit_rph',
      render: (rph: number) => `${rph}次/小时`,
    },
    {
      title: '日配额',
      dataIndex: 'daily_quota',
      key: 'daily_quota',
      render: (quota: number | null) => quota ? `${quota}次` : '无限制',
    },
    {
      title: '月配额',
      dataIndex: 'monthly_quota',
      key: 'monthly_quota',
      render: (quota: number | null) => quota ? `${quota}次` : '无限制',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={status === 'active' ? 'success' : status === 'disabled' ? 'error' : 'warning'}>
          {status === 'active' ? '正常' : status === 'disabled' ? '禁用' : '已过期'}
        </Tag>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => dayjs(date).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: APIKey) => (
        <Space size="small">
          <Button
            type="text"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleReveal(record.id)}
            loading={revealLoading}
          >
            查看
          </Button>
          {record.status === 'active' ? (
            <Button
              type="text"
              danger
              size="small"
              icon={<StopOutlined />}
              onClick={() => handleDisable(record.id)}
            >
              禁用
            </Button>
          ) : (
            <Button
              type="text"
              size="small"
              icon={<CheckCircleOutlined />}
              onClick={() => handleEnable(record.id)}
            >
              启用
            </Button>
          )}
          <Popconfirm
            title="确认删除？"
            description="删除后无法恢复"
            onConfirm={() => handleDelete(record.id)}
            okText="确认"
            cancelText="取消"
          >
            <Button type="text" danger size="small" icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div className={styles.container}>
      {/* 统一的错误提示组件 */}
      <ErrorModalComponent />

      <div className={styles.header}>
        <Title level={4}>API Keys管理</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalVisible(true)}>
          创建API Key
        </Button>
      </div>

      <Table
        dataSource={keys}
        columns={columns}
        rowKey="id"
        loading={loading}
        pagination={{
          current: page,
          pageSize,
          total,
          showSizeChanger: true,
          showTotal: (total) => `共 ${total} 条`,
          onChange: (p, ps) => {
            setPage(p)
            setPageSize(ps)
          },
        }}
      />

      {/* 创建Key弹窗 */}
      <Modal
        title="创建API Key"
        open={modalVisible}
        onCancel={() => {
          setModalVisible(false)
          form.resetFields()
        }}
        footer={null}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCreate}
        >
          <Form.Item
            name="name"
            label="Key名称"
            rules={[{ required: true, message: '请输入Key名称' }]}
          >
            <Input placeholder="用于标识此Key，如：我的应用" />
          </Form.Item>

          <Form.Item
            name="auth_type"
            label="认证方式"
            initialValue="api_key"
          >
            <Select>
              <Select.Option value="api_key">API Key（推荐）</Select.Option>
              <Select.Option value="hmac">HMAC签名</Select.Option>
              <Select.Option value="jwt">JWT Token</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item name="rate_limit_rpm" label="每分钟请求限制" initialValue={1000}>
            <Input type="number" />
          </Form.Item>

          <Form.Item name="rate_limit_rph" label="每小时请求限制" initialValue={10000}>
            <Input type="number" />
          </Form.Item>

          <Form.Item name="daily_quota" label="每日配额（不填则无限制）">
            <Input type="number" placeholder="如：10000" />
          </Form.Item>

          <Form.Item name="monthly_quota" label="每月配额（不填则无限制）">
            <Input type="number" placeholder="如：100000" />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={createLoading}>
                创建
              </Button>
              <Button onClick={() => setModalVisible(false)}>取消</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 查看完整Key弹窗 */}
      <Modal
        title="查看 API Key"
        open={revealModalVisible}
        onCancel={() => {
          setRevealModalVisible(false)
          setRevealKeyData(null)
        }}
        footer={[
          <Button key="close" type="primary" onClick={() => {
            setRevealModalVisible(false)
            setRevealKeyData(null)
          }}>
            我已保存
          </Button>
        ]}
      >
        {revealKeyData && (
          <div className={styles.keyDisplay}>
            <Text type="secondary">Key名称：{revealKeyData.key_name}</Text>
            <div className={styles.keyBox}>
              <KeyOutlined /> {revealKeyData.api_key}
            </div>
            <Text type="warning">请妥善保管，关闭后将无法再次查看完整内容</Text>
          </div>
        )}
      </Modal>

      {/* 新Key展示弹窗 */}
      <Modal
        title="API Key创建成功"
        open={!!newKeyData}
        onCancel={() => setNewKeyData(null)}
        onOk={() => setNewKeyData(null)}
        okText="我已保存"
      >
        <div className={styles.keyDisplay}>
          <Text type="secondary">请妥善保管以下Key，仅显示一次</Text>
          <div className={styles.keyBox}>
            <KeyOutlined /> {newKeyData?.api_key}
          </div>
          <Text type="warning">创建时显示的Secret：需要妥善保管，无法找回</Text>
        </div>
      </Modal>
    </div>
  )
}
