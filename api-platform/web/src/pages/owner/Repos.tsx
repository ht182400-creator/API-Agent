/**
 * 仓库管理页面 - 仓库所有者视角
 * 管理自己创建的仓库，包括端点配置和限流设置
 */

import { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, Select, Card, message, Tag, Popconfirm, Space, Typography, Row, Col, Statistic, Drawer, Descriptions, Divider, Alert } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, UpOutlined, DownOutlined, ApiOutlined, ThunderboltOutlined, SettingOutlined, EyeOutlined } from '@ant-design/icons'
import { repoApi, Repository, RepositoryEndpoint, RepositoryLimits, CreateRepoRequest } from '../../api/repo'
import { useError } from '../../contexts/ErrorContext'
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
  const [detailVisible, setDetailVisible] = useState(false)
  const [selectedRepo, setSelectedRepo] = useState<Repository | null>(null)
  const [editingRepo, setEditingRepo] = useState<Repository | null>(null)
  const [createLoading, setCreateLoading] = useState(false)
  const [form] = Form.useForm()

  // 使用统一错误处理
  const { showError, showSuccess } = useError()

  useEffect(() => {
    fetchRepos()
  }, [page, pageSize])

  const fetchRepos = async () => {
    setLoading(true)
    try {
      const data = await repoApi.getMyRepos({ page, page_size: pageSize })
      setRepos(data.items)
      setTotal(data.pagination.total)
    } catch (error: any) {
      showError(error, fetchRepos)
    } finally {
      setLoading(false)
    }
  }

  // 获取仓库详情
  const fetchRepoDetail = async (repoId: string) => {
    try {
      const data = await repoApi.get(repoId)
      setSelectedRepo(data)
      setDetailVisible(true)
    } catch (error: any) {
      showError(error, () => fetchRepoDetail(repoId))
    }
  }

  const handleCreate = async (values: CreateRepoRequest) => {
    setCreateLoading(true)
    try {
      if (editingRepo) {
        await repoApi.update(editingRepo.id, values)
        showSuccess('仓库更新成功')
      } else {
        await repoApi.create(values)
        showSuccess('仓库创建成功')
      }
      setModalVisible(false)
      form.resetFields()
      setEditingRepo(null)
      fetchRepos()
    } catch (error: any) {
      showError(error, () => handleCreate(values))
    } finally {
      setCreateLoading(false)
    }
  }

  const handleEdit = (repo: Repository) => {
    setEditingRepo(repo)
    form.setFieldsValue({
      name: repo.name,
      display_name: repo.display_name,
      description: repo.description,
      repo_type: repo.type,
      protocol: repo.protocol || 'http',
      endpoint_url: repo.endpoint || '',
    })
    setModalVisible(true)
  }

  const handleViewDetail = (repo: Repository) => {
    fetchRepoDetail(repo.slug)
  }

  const handleDelete = async (repoId: string) => {
    try {
      await repoApi.delete(repoId)
      showSuccess('仓库已删除')
      fetchRepos()
    } catch (error: any) {
      showError(error, () => handleDelete(repoId))
    }
  }

  const handleToggleStatus = async (repo: Repository) => {
    try {
      if (repo.status === 'online') {
        await repoApi.deactivate(repo.id)
      } else {
        await repoApi.activate(repo.id)
      }
      showSuccess(repo.status === 'online' ? '仓库已下线' : '仓库已上线')
      fetchRepos()
    } catch (error: any) {
      showError(error, () => handleToggleStatus(repo))
    }
  }

  // 获取HTTP方法对应的颜色
  const getMethodColor = (method: string) => {
    const colors: Record<string, string> = {
      GET: 'green',
      POST: 'blue',
      PUT: 'orange',
      DELETE: 'red',
      PATCH: 'purple'
    }
    return colors[method] || 'default'
  }

  const columns = [
    { 
      title: '仓库名称', 
      dataIndex: 'name', 
      key: 'name', 
      render: (name: string, record: Repository) => (
        <Space direction="vertical" size={0}>
          <Text strong>{record.display_name || name}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>{name}</Text>
        </Space>
      )
    },
    { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
    { title: '分类', dataIndex: 'type', key: 'type', render: (t: string) => <Tag>{t}</Tag> },
    { 
      title: 'API端点', 
      key: 'endpoints',
      render: (_: any, record: Repository) => (
        <Space>
          <Tag icon={<ApiOutlined />}>{record.endpoints?.length || 0} 个</Tag>
        </Space>
      )
    },
    { 
      title: '限流配置', 
      key: 'limits',
      render: (_: any, record: Repository) => (
        <Space direction="vertical" size={0}>
          <Text style={{ fontSize: 12 }}>
            <ThunderboltOutlined /> {record.limits?.rpm || 1000}/分
          </Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.limits?.rph || 10000}/时
          </Text>
        </Space>
      )
    },
    { 
      title: '状态', 
      dataIndex: 'status', 
      key: 'status',
      render: (status: string) => {
        const statusMap: Record<string, { color: string; text: string }> = {
          pending: { color: 'orange', text: '待审核' },
          approved: { color: 'blue', text: '已审核（待上线）' },
          rejected: { color: 'red', text: '已拒绝' },
          online: { color: 'green', text: '已上线' },
          offline: { color: 'default', text: '已下线' },
        }
        const config = statusMap[status] || { color: 'default', text: status }
        return <Tag color={config.color}>{config.text}</Tag>
      }
    },
    { title: '创建时间', dataIndex: 'created_at', key: 'created_at', render: (d: string) => dayjs(d).format('YYYY-MM-DD') },
    {
      title: '操作',
      key: 'action',
      width: 280,
      render: (_: any, record: Repository) => (
        <Space size="small" wrap>
          <Button size="small" icon={<EyeOutlined />} onClick={() => handleViewDetail(record)}>详情</Button>
          <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)}>编辑</Button>
          <Popconfirm
            title="确认删除？"
            description="删除后无法恢复"
            onConfirm={() => handleDelete(record.id)}
          >
            <Button size="small" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <div>
          <Title level={4} style={{ marginBottom: 4 }}>仓库管理</Title>
          <Text type="secondary">管理您的API仓库，配置端点和限流策略</Text>
        </div>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => {
          setEditingRepo(null)
          form.resetFields()
          setModalVisible(true)
        }}>
          创建仓库
        </Button>
      </div>

      {/* 统计信息 */}
      <Row gutter={16} className={styles.statsRow}>
        <Col span={6}>
          <Card>
            <Statistic title="我的仓库" value={total} prefix={<ApiOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic 
              title="API端点总数" 
              value={repos.reduce((acc, repo) => acc + (repo.endpoints?.length || 0), 0)} 
              prefix={<ApiOutlined />} 
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic 
              title="已上线仓库" 
              value={repos.filter(r => r.status === 'online').length} 
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic 
              title="未上线仓库" 
              value={repos.filter(r => r.status !== 'online').length} 
              valueStyle={{ color: '#fa8c16' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 提示信息 */}
      <Alert
        message="仓库审核流程"
        description="创建仓库后需要管理员审核通过才能上线。请耐心等待审核结果，如有疑问请联系管理员。"
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />

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

      {/* 创建/编辑仓库弹窗 */}
      <Modal
        title={editingRepo ? '编辑仓库' : '创建仓库'}
        open={modalVisible}
        onCancel={() => { setModalVisible(false); form.resetFields(); setEditingRepo(null) }}
        footer={null}
        width={600}
      >
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item name="name" label="仓库标识" rules={[{ required: true, message: '请输入仓库标识' }]}>
            <Input placeholder="如：my-api (唯一标识)" disabled={!!editingRepo} />
          </Form.Item>
          <Form.Item name="display_name" label="显示名称" rules={[{ required: true, message: '请输入显示名称' }]}>
            <Input placeholder="如：我的API服务" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={3} placeholder="简要描述您的API服务" />
          </Form.Item>
          <Form.Item name="repo_type" label="仓库类型" rules={[{ required: true, message: '请选择仓库类型' }]}>
            <Select placeholder="请选择仓库类型">
              <Select.Option value="psychology">心理问答</Select.Option>
              <Select.Option value="translation">翻译服务</Select.Option>
              <Select.Option value="vision">图像识别</Select.Option>
              <Select.Option value="stock">股票行情</Select.Option>
              <Select.Option value="ai">AI服务</Select.Option>
              <Select.Option value="custom">自定义</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="protocol" label="协议类型" rules={[{ required: true }]}>
            <Select>
              <Select.Option value="http">HTTP</Select.Option>
              <Select.Option value="grpc">gRPC</Select.Option>
              <Select.Option value="websocket">WebSocket</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="endpoint_url" label="API端点地址">
            <Input placeholder="https://api.example.com/v1" />
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

      {/* 仓库详情抽屉 */}
      <Drawer
        title="仓库详情"
        placement="right"
        width={640}
        open={detailVisible}
        onClose={() => setDetailVisible(false)}
      >
        {selectedRepo && (
          <>
            {/* 基本信息 */}
            <Descriptions title="基本信息" column={2} bordered size="small">
              <Descriptions.Item label="仓库名称">{selectedRepo.display_name || selectedRepo.name}</Descriptions.Item>
              <Descriptions.Item label="仓库标识">{selectedRepo.name}</Descriptions.Item>
              <Descriptions.Item label="仓库类型">{selectedRepo.type}</Descriptions.Item>
              <Descriptions.Item label="协议">{selectedRepo.protocol?.toUpperCase()}</Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={selectedRepo.status === 'online' ? 'green' : selectedRepo.status === 'pending' ? 'orange' : selectedRepo.status === 'rejected' ? 'red' : 'blue'}>
                  {selectedRepo.status === 'online' ? '已上线' : selectedRepo.status === 'pending' ? '待审核' : selectedRepo.status === 'rejected' ? '已拒绝' : '已审核'}
                </Tag>
              </Descriptions.Item>
            </Descriptions>

            <Divider />

            {/* API端点列表 */}
            <Title level={5}><ApiOutlined /> API端点列表 ({selectedRepo.endpoints?.length || 0})</Title>
            {selectedRepo.endpoints && selectedRepo.endpoints.length > 0 ? (
              <Table
                dataSource={selectedRepo.endpoints}
                rowKey={(record) => `${record.method}-${record.path}`}
                pagination={false}
                size="small"
                columns={[
                  {
                    title: '方法',
                    dataIndex: 'method',
                    key: 'method',
                    width: 80,
                    render: (method: string) => <Tag color={getMethodColor(method)}>{method}</Tag>
                  },
                  {
                    title: '路径',
                    dataIndex: 'path',
                    key: 'path',
                    render: (path: string) => <Text code>{path}</Text>
                  },
                  {
                    title: '描述',
                    dataIndex: 'description',
                    key: 'description',
                    ellipsis: true
                  }
                ]}
              />
            ) : (
              <Text type="secondary">暂无API端点配置</Text>
            )}

            <Divider />

            {/* 限流配置 */}
            <Title level={5}><ThunderboltOutlined /> 限流配置</Title>
            <Descriptions column={2} bordered size="small">
              <Descriptions.Item label="每分钟请求 (RPM)">
                <Text strong>{selectedRepo.limits?.rpm || 1000}</Text> 次
              </Descriptions.Item>
              <Descriptions.Item label="每小时请求 (RPH)">
                <Text strong>{selectedRepo.limits?.rph || 10000}</Text> 次
              </Descriptions.Item>
              <Descriptions.Item label="每日请求 (RPD)">
                <Text strong>{selectedRepo.limits?.daily || 100000}</Text> 次
              </Descriptions.Item>
              {selectedRepo.limits?.burst_limit && (
                <Descriptions.Item label="突发限制">
                  <Text strong>{selectedRepo.limits.burst_limit}</Text> 次
                </Descriptions.Item>
              )}
              {selectedRepo.limits?.concurrent_limit && (
                <Descriptions.Item label="并发限制">
                  <Text strong>{selectedRepo.limits.concurrent_limit}</Text> 个
                </Descriptions.Item>
              )}
            </Descriptions>

            <Divider />

            {/* 定价信息 */}
            {selectedRepo.pricing && (
              <>
                <Title level={5}><SettingOutlined /> 定价信息</Title>
                <Descriptions column={2} bordered size="small">
                  <Descriptions.Item label="计费模式">
                    {selectedRepo.pricing.type === 'per_call' && '按次计费'}
                    {selectedRepo.pricing.type === 'token' && '按Token计费'}
                    {selectedRepo.pricing.type === 'flow' && '按流量计费'}
                    {selectedRepo.pricing.type === 'subscription' && '订阅计费'}
                    {selectedRepo.pricing.type === 'free' && '免费'}
                  </Descriptions.Item>
                  {selectedRepo.pricing.price_per_call && (
                    <Descriptions.Item label="每次调用">
                      ¥{selectedRepo.pricing.price_per_call.toFixed(4)}
                    </Descriptions.Item>
                  )}
                  {selectedRepo.pricing.price_per_token && (
                    <Descriptions.Item label="每Token">
                      ¥{selectedRepo.pricing.price_per_token.toFixed(6)}
                    </Descriptions.Item>
                  )}
                  {selectedRepo.pricing.free_calls !== undefined && selectedRepo.pricing.free_calls > 0 && (
                    <Descriptions.Item label="免费调用">
                      <Text type="success">{selectedRepo.pricing.free_calls} 次</Text>
                    </Descriptions.Item>
                  )}
                </Descriptions>
              </>
            )}
          </>
        )}
      </Drawer>
    </div>
  )
}
