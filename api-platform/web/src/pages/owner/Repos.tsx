/**
 * 仓库管理页面
 */

import { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, Select, Switch, Card, message, Tag, Popconfirm, Space, Typography } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, UpOutlined, DownOutlined } from '@ant-design/icons'
import { repoApi, Repository, CreateRepoRequest } from '../../api/repo'
import dayjs from 'dayjs'
import styles from './Repos.module.css'

const { Title, Text } = Typography

export default function OwnerRepos() {
  const [loading, setLoading] = useState(false)
  const [repos, setRepos] = useState<Repository[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [modalVisible, setModalVisible] = useState(false)
  const [editingRepo, setEditingRepo] = useState<Repository | null>(null)
  const [createLoading, setCreateLoading] = useState(false)
  const [form] = Form.useForm()

  useEffect(() => {
    fetchRepos()
  }, [page, pageSize])

  const fetchRepos = async () => {
    setLoading(true)
    try {
      const { data } = await repoApi.getMyRepos({ page, page_size: pageSize })
      setRepos(data.items)
      setTotal(data.total)
    } catch (error: any) {
      message.error(error.message || '获取仓库失败')
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = async (values: CreateRepoRequest) => {
    setCreateLoading(true)
    try {
      if (editingRepo) {
        await repoApi.update(editingRepo.id, values)
        message.success('仓库更新成功')
      } else {
        await repoApi.create(values)
        message.success('仓库创建成功')
      }
      setModalVisible(false)
      form.resetFields()
      setEditingRepo(null)
      fetchRepos()
    } catch (error: any) {
      message.error(error.message || '操作失败')
    } finally {
      setCreateLoading(false)
    }
  }

  const handleEdit = (repo: Repository) => {
    setEditingRepo(repo)
    form.setFieldsValue({
      name: repo.name,
      description: repo.description,
      category: repo.category,
      adapter_type: repo.adapter_type,
      endpoint: repo.endpoint,
      auth_type: repo.auth_type,
      is_public: repo.is_public,
    })
    setModalVisible(true)
  }

  const handleDelete = async (repoId: string) => {
    try {
      await repoApi.delete(repoId)
      message.success('仓库已删除')
      fetchRepos()
    } catch (error: any) {
      message.error(error.message || '删除失败')
    }
  }

  const handleToggleStatus = async (repo: Repository) => {
    try {
      if (repo.status === 'active') {
        await repoApi.deactivate(repo.id)
      } else {
        await repoApi.activate(repo.id)
      }
      message.success(repo.status === 'active' ? '仓库已下线' : '仓库已上线')
      fetchRepos()
    } catch (error: any) {
      message.error(error.message || '操作失败')
    }
  }

  const columns = [
    { title: '仓库名称', dataIndex: 'name', key: 'name', render: (name: string) => <Text strong>{name}</Text> },
    { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
    { title: '分类', dataIndex: 'category', key: 'category', render: (c: string) => <Tag>{c}</Tag> },
    { title: '适配器', dataIndex: 'adapter_type', key: 'adapter_type', render: (t: string) => <Tag color="blue">{t}</Tag> },
    { 
      title: '状态', 
      dataIndex: 'status', 
      key: 'status',
      render: (status: string) => (
        <Tag color={status === 'active' ? 'green' : 'orange'}>
          {status === 'active' ? '运行中' : '已下线'}
        </Tag>
      )
    },
    { 
      title: '公开', 
      dataIndex: 'is_public', 
      key: 'is_public',
      render: (isPublic: boolean) => isPublic ? '是' : '否'
    },
    { title: '创建时间', dataIndex: 'created_at', key: 'created_at', render: (d: string) => dayjs(d).format('YYYY-MM-DD') },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: Repository) => (
        <Space size="small">
          <Button type="text" icon={<EditOutlined />} onClick={() => handleEdit(record)}>编辑</Button>
          <Popconfirm
            title="确认操作？"
            onConfirm={() => handleToggleStatus(record)}
          >
            <Button type="text" icon={record.status === 'active' ? <DownOutlined /> : <UpOutlined />}>
              {record.status === 'active' ? '下线' : '上线'}
            </Button>
          </Popconfirm>
          <Popconfirm
            title="确认删除？"
            description="删除后无法恢复"
            onConfirm={() => handleDelete(record.id)}
          >
            <Button type="text" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <Title level={4}>仓库管理</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => {
          setEditingRepo(null)
          form.resetFields()
          setModalVisible(true)
        }}>
          创建仓库
        </Button>
      </div>

      <Table
        dataSource={repos}
        columns={columns}
        rowKey="id"
        loading={loading}
        pagination={{
          current: page,
          pageSize,
          total,
          showSizeChanger: true,
          showTotal: (total) => `共 ${total} 条`,
          onChange: (p, ps) => { setPage(p); setPageSize(ps) },
        }}
      />

      <Modal
        title={editingRepo ? '编辑仓库' : '创建仓库'}
        open={modalVisible}
        onCancel={() => { setModalVisible(false); form.resetFields(); setEditingRepo(null) }}
        footer={null}
        width={600}
      >
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item name="name" label="仓库名称" rules={[{ required: true, message: '请输入仓库名称' }]}>
            <Input placeholder="如：my-api" disabled={!!editingRepo} />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={3} placeholder="简要描述您的API" />
          </Form.Item>
          <Form.Item name="category" label="分类" rules={[{ required: true }]}>
            <Select>
              <Select.Option value="ai">AI模型</Select.Option>
              <Select.Option value="translate">翻译</Select.Option>
              <Select.Option value="vision">图像识别</Select.Option>
              <Select.Option value="nlp">自然语言</Select.Option>
              <Select.Option value="other">其他</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="adapter_type" label="适配器类型" rules={[{ required: true }]}>
            <Select>
              <Select.Option value="http">HTTP</Select.Option>
              <Select.Option value="grpc">gRPC</Select.Option>
              <Select.Option value="websocket">WebSocket</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="endpoint" label="API端点" rules={[{ required: true, message: '请输入API端点' }]}>
            <Input placeholder="https://api.example.com/v1" />
          </Form.Item>
          <Form.Item name="auth_type" label="认证方式">
            <Select>
              <Select.Option value="none">无认证</Select.Option>
              <Select.Option value="bearer">Bearer Token</Select.Option>
              <Select.Option value="api_key">API Key</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="is_public" label="公开访问" valuePropName="checked" initialValue={true}>
            <Switch />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={createLoading}>
                {editingRepo ? '保存' : '创建'}
              </Button>
              <Button onClick={() => { setModalVisible(false); form.resetFields() }}>取消</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
