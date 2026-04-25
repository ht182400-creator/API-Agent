import React, { useState, useEffect } from 'react'
import '../../styles/cyber-theme.css'
import {
  Tabs,
  Table,
  Button,
  Space,
  Modal,
  Form,
  Input,
  InputNumber,
  Select,
  Switch,
  message,
  Card,
  Statistic,
  Row,
  Col,
  Alert,
  Popconfirm,
  Divider,
  Tag,
  Typography,
} from 'antd'
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  CheckCircleOutlined,
  StopOutlined,
  DollarOutlined,
  CalculatorOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import styles from './PricingConfig.module.css'
import {
  adminPricingConfigApi,
  PricingConfig,
  CreatePricingConfigRequest,
  CostPreviewRequest,
  PRICING_TYPE_OPTIONS,
  STATUS_OPTIONS,
} from '../../api/adminPricingConfig'
import { useDevice } from '../../hooks/useDevice'

const { TextArea } = Input
const { Text } = Typography

const PricingConfigPage: React.FC = () => {
  const { isMobile } = useDevice()
  const [activeTab, setActiveTab] = useState('list')
  const [loading, setLoading] = useState(false)
  const [configList, setConfigList] = useState<PricingConfig[]>([])
  const [pagination, setPagination] = useState({ page: 1, page_size: 10, total: 0 })
  const [filterType, setFilterType] = useState<string>('')
  const [filterStatus, setFilterStatus] = useState<string>('')

  // Modal state
  const [modalVisible, setModalVisible] = useState(false)
  const [editingConfig, setEditingConfig] = useState<PricingConfig | null>(null)
  const [form] = Form.useForm()

  // Preview state
  const [previewVisible, setPreviewVisible] = useState(false)
  const [previewResult, setPreviewResult] = useState<any>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [previewForm] = Form.useForm()

  // Load configs
  const loadConfigs = async () => {
    setLoading(true)
    try {
      const params: any = { page: pagination.page, page_size: pagination.page_size }
      if (filterType) params.pricing_type = filterType
      if (filterStatus) params.status = filterStatus

      const response = await adminPricingConfigApi.getConfigs(params)
      if (response) {
        setConfigList(response.items || [])
        setPagination({
          ...pagination,
          total: response.total || 0,
        })
      }
    } catch (error) {
      message.error('加载价格配置失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadConfigs()
  }, [pagination.page, filterType, filterStatus])

  // Table columns
  const columns: ColumnsType<PricingConfig> = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 200,
      ellipsis: true,
      render: (id: string) => <code style={{ fontSize: 11 }}>{id.substring(0, 18)}...</code>,
    },
    {
      title: '计费模式',
      dataIndex: 'pricing_type',
      key: 'pricing_type',
      width: 120,
      render: (type: string) => {
        const map: Record<string, { label: string; color: string }> = {
          call: { label: '按调用', color: 'blue' },
          token: { label: '按Token', color: 'green' },
          package: { label: '套餐包', color: 'purple' },
        }
        const item = map[type] || { label: type, color: 'default' }
        return <Tag color={item.color}>{item.label}</Tag>
      },
    },
    {
      title: '价格',
      key: 'price',
      width: 200,
      render: (_, record) => {
        if (record.pricing_type === 'call') {
          return `¥${(record.price_per_call || 0).toFixed(4)}/次`
        } else if (record.pricing_type === 'token') {
          return `¥${(record.price_per_1k_input_tokens || 0).toFixed(4)}/1K输入, ¥${(record.price_per_1k_output_tokens || 0).toFixed(4)}/1K输出`
        } else {
          const pkgCount = record.packages?.length || 0
          return `${pkgCount} 个套餐`
        }
      },
    },
    {
      title: '免费额度',
      key: 'free',
      width: 150,
      render: (_, record) => {
        if (record.pricing_type === 'call') {
          return record.free_calls ? `${record.free_calls} 次` : '-'
        } else if (record.pricing_type === 'token') {
          const input = record.free_input_tokens || 0
          const output = record.free_output_tokens || 0
          return input || output ? `${input}输入/${output}输出` : '-'
        }
        return '-'
      },
    },
    {
      title: 'VIP折扣',
      key: 'vip',
      width: 120,
      render: (_, record) => {
        if (!record.vip_discounts) return '-'
        const levels = Object.entries(record.vip_discounts)
        return levels.slice(0, 2).map(([level, discount]) => (
          <span key={level} style={{ marginRight: 8 }}>
            VIP{level}: {(discount * 100).toFixed(0)}%
          </span>
        ))
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 80,
      render: (status: string) => (
        <Tag color={status === 'active' ? 'success' : 'default'}>
          {status === 'active' ? '启用' : '禁用'}
        </Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          {record.status === 'active' ? (
            <Button
              type="link"
              size="small"
              danger
              icon={<StopOutlined />}
              onClick={() => handleToggleStatus(record.id, false)}
            >
              禁用
            </Button>
          ) : (
            <Button
              type="link"
              size="small"
              icon={<CheckCircleOutlined />}
              onClick={() => handleToggleStatus(record.id, true)}
            >
              启用
            </Button>
          )}
          <Popconfirm
            title="确定删除此配置？"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  // 移动端卡片列表渲染
  const renderConfigCards = () => (
    <div className={styles.cardList}>
      {configList.map((config) => {
        const typeMap: Record<string, { label: string; color: string }> = {
          call: { label: '按调用', color: 'blue' },
          token: { label: '按Token', color: 'green' },
          package: { label: '套餐包', color: 'purple' },
        }
        const typeInfo = typeMap[config.pricing_type] || { label: config.pricing_type, color: 'default' }

        let priceText = ''
        if (config.pricing_type === 'call') {
          priceText = `¥${(config.price_per_call || 0).toFixed(4)}/次`
        } else if (config.pricing_type === 'token') {
          priceText = `¥${(config.price_per_1k_input_tokens || 0).toFixed(4)}/1K输入, ¥${(config.price_per_1k_output_tokens || 0).toFixed(4)}/1K输出`
        } else {
          priceText = `${config.packages?.length || 0} 个套餐`
        }

        return (
          <Card key={config.id} className={styles.configCard} size="small">
            <div className={styles.cardHeader}>
              <Space>
                <Tag color={typeInfo.color}>{typeInfo.label}</Tag>
                <Tag color={config.status === 'active' ? 'success' : 'default'}>
                  {config.status === 'active' ? '启用' : '禁用'}
                </Tag>
              </Space>
              <Text type="secondary" style={{ fontSize: 12 }}>{config.priority}级</Text>
            </div>

            <div className={styles.cardBody}>
              <div className={styles.cardRow}>
                <Text type="secondary">ID：</Text>
                <Text code style={{ fontSize: 11 }}>{config.id.substring(0, 18)}...</Text>
              </div>
              <div className={styles.cardRow}>
                <Text type="secondary">价格：</Text>
                <Text>{priceText}</Text>
              </div>
              {config.free_calls || (config.free_input_tokens || config.free_output_tokens) ? (
                <div className={styles.cardRow}>
                  <Text type="secondary">免费额度：</Text>
                  <Text>
                    {config.pricing_type === 'call' && config.free_calls ? `${config.free_calls} 次` : ''}
                    {config.pricing_type === 'token' && (
                      `${config.free_input_tokens || 0}输入/${config.free_output_tokens || 0}输出`
                    )}
                  </Text>
                </div>
              ) : null}
              {config.vip_discounts && Object.keys(config.vip_discounts).length > 0 && (
                <div className={styles.cardRow}>
                  <Text type="secondary">VIP折扣：</Text>
                  <Text>
                    {Object.entries(config.vip_discounts).map(([level, discount]) => (
                      <span key={level} style={{ marginRight: 8 }}>VIP{level}: {((discount as number) * 100).toFixed(0)}%</span>
                    ))}
                  </Text>
                </div>
              )}
            </div>

            <div className={styles.cardActions}>
              <Space>
                <Button type="link" size="small" icon={<EditOutlined />} onClick={() => handleEdit(config)}>
                  编辑
                </Button>
                {config.status === 'active' ? (
                  <Button type="link" size="small" danger icon={<StopOutlined />} onClick={() => handleToggleStatus(config.id, false)}>
                    禁用
                  </Button>
                ) : (
                  <Button type="link" size="small" icon={<CheckCircleOutlined />} onClick={() => handleToggleStatus(config.id, true)}>
                    启用
                  </Button>
                )}
                <Popconfirm
                  title="确定删除此配置？"
                  onConfirm={() => handleDelete(config.id)}
                  okText="确定"
                  cancelText="取消"
                >
                  <Button type="link" size="small" danger icon={<DeleteOutlined />}>
                    删除
                  </Button>
                </Popconfirm>
              </Space>
            </div>
          </Card>
        )
      })}
      {configList.length === 0 && (
        <Card className={styles.configCard} size="small">
          <div style={{ textAlign: 'center', padding: '40px 0', color: '#999' }}>暂无配置</div>
        </Card>
      )}
    </div>
  )

  // Handlers
  const handleEdit = (config: PricingConfig) => {
    setEditingConfig(config)
    form.setFieldsValue({
      ...config,
      packages: config.packages ? JSON.stringify(config.packages, null, 2) : '[]',
    })
    setModalVisible(true)
  }

  const handleToggleStatus = async (id: string, enable: boolean) => {
    try {
      if (enable) {
        await adminPricingConfigApi.enableConfig(id)
        message.success('已启用')
      } else {
        await adminPricingConfigApi.disableConfig(id)
        message.success('已禁用')
      }
      loadConfigs()
    } catch (error) {
      message.error('操作失败')
    }
  }

  const handleDelete = async (id: string) => {
    try {
      await adminPricingConfigApi.deleteConfig(id)
      message.success('删除成功')
      loadConfigs()
    } catch (error) {
      message.error('删除失败')
    }
  }

  const handleSubmit = async (values: any) => {
    try {
      // Parse packages JSON if present
      if (values.packages && typeof values.packages === 'string') {
        values.packages = JSON.parse(values.packages)
      }

      if (editingConfig) {
        await adminPricingConfigApi.updateConfig(editingConfig.id, values)
        message.success('更新成功')
      } else {
        await adminPricingConfigApi.createConfig(values)
        message.success('创建成功')
      }
      setModalVisible(false)
      form.resetFields()
      loadConfigs()
    } catch (error: any) {
      message.error(error?.message || '操作失败')
    }
  }

  // Preview handlers
  const handlePreview = async (values: CostPreviewRequest) => {
    setPreviewLoading(true)
    try {
      const result = await adminPricingConfigApi.calculateCost(values)
      setPreviewResult(result)
    } catch (error) {
      message.error('费用计算失败')
    } finally {
      setPreviewLoading(false)
    }
  }

  // Render form based on pricing type
  const renderPricingFields = () => {
    const pricingType = Form.useWatch('pricing_type', form)

    return (
      <>
        <Form.Item name="pricing_type" label="计费模式" rules={[{ required: true }]}>
          <Select options={PRICING_TYPE_OPTIONS} placeholder="选择计费模式" />
        </Form.Item>

        {pricingType === 'call' && (
          <>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item name="price_per_call" label="每次调用价格" rules={[{ required: true }]}>
                  <InputNumber min={0} step={0.0001} precision={4} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="free_calls" label="免费调用次数">
                  <InputNumber min={0} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
            </Row>
          </>
        )}

        {pricingType === 'token' && (
          <>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item name="price_per_1k_input_tokens" label="每1K输入Token价格" rules={[{ required: true }]}>
                  <InputNumber min={0} step={0.0001} precision={4} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="price_per_1k_output_tokens" label="每1K输出Token价格" rules={[{ required: true }]}>
                  <InputNumber min={0} step={0.0001} precision={4} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item name="free_input_tokens" label="免费输入Token">
                  <InputNumber min={0} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="free_output_tokens" label="免费输出Token">
                  <InputNumber min={0} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
            </Row>
          </>
        )}

        {pricingType === 'package' && (
          <Form.Item name="packages" label="套餐包定义 (JSON)">
            <TextArea rows={6} placeholder='[{"id":"free","name":"Free","calls":100,"price":0}]' />
          </Form.Item>
        )}

        <Form.Item name="description" label="Description">
          <TextArea rows={2} />
        </Form.Item>
      </>
    )
  }

  return (
    <div className={`${styles.container} bamboo-bg-pattern`}>
      <Card
        title={
          <Space>
            <DollarOutlined />
            <span>价格配置</span>
          </Space>
        }
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={() => {
            setEditingConfig(null)
            form.resetFields()
            setModalVisible(true)
          }}>
            创建配置
          </Button>
        }
      >
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={[
            {
              key: 'list',
              label: '配置列表',
              children: (
                <>
                  <div className={styles.filters} style={{ flexWrap: 'wrap', gap: 8 }}>
                    <Space wrap size="small">
                      <Select
                        placeholder="计费类型"
                        options={PRICING_TYPE_OPTIONS}
                        value={filterType}
                        onChange={setFilterType}
                        allowClear
                        style={{ width: 140 }}
                      />
                      <Select
                        placeholder="状态"
                        options={STATUS_OPTIONS}
                        value={filterStatus}
                        onChange={setFilterStatus}
                        style={{ width: 110 }}
                      />
                    </Space>
                    <Button icon={<CalculatorOutlined />} onClick={() => setPreviewVisible(true)} style={{ marginTop: 8 }}>
                      费用预览
                    </Button>
                  </div>

                  {isMobile ? (
                    <>
                      {renderConfigCards()}
                      {pagination.total > pagination.page_size && (
                        <div style={{ textAlign: 'center', marginTop: 16 }}>
                          <Button
                            onClick={() => setPagination({ ...pagination, page: pagination.page + 1 })}
                            loading={loading}
                          >
                            加载更多
                          </Button>
                        </div>
                      )}
                    </>
                  ) : (
                    <Table
                      columns={columns}
                      dataSource={configList}
                      rowKey="id"
                      loading={loading}
                      scroll={{ x: 900 }}
                      pagination={{
                        current: pagination.page,
                        pageSize: pagination.page_size,
                        total: pagination.total,
                        showSizeChanger: true,
                        showTotal: (total) => `共 ${total} 条`,
                        onChange: (page, pageSize) => setPagination({ ...pagination, page, page_size: pageSize }),
                      }}
                    />
                  )}
                </>
              ),
            },
          ]}
        />
      </Card>

      {/* Create/Edit Modal */}
      <Modal
        title={editingConfig ? '编辑价格配置' : '创建价格配置'}
        open={modalVisible}
        onCancel={() => {
          setModalVisible(false)
          form.resetFields()
        }}
        onOk={() => form.submit()}
        width="90%"
        style={{ maxWidth: 700 }}
        destroyOnClose
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Row gutter={[16, 8]}>
            <Col xs={24} md={12}>
              <Form.Item name="repo_id" label="仓库ID（留空=全局）">
                <Input placeholder="留空为全局配置" />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item name="priority" label="优先级">
                <InputNumber min={0} max={1000} defaultValue={100} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          {renderPricingFields()}
        </Form>
      </Modal>

      {/* 费用预览弹窗 */}
      <Modal
        title="费用预览"
        open={previewVisible}
        onCancel={() => {
          setPreviewVisible(false)
          previewForm.resetFields()
          setPreviewResult(null)
        }}
        footer={null}
        width={500}
      >
        <Form form={previewForm} layout="vertical" onFinish={handlePreview}>
          <Form.Item name="pricing_type" label="计费模式" rules={[{ required: true }]}>
            <Select options={PRICING_TYPE_OPTIONS} />
          </Form.Item>

          <Form.Item noStyle shouldUpdate={(prev, curr) => prev.pricing_type !== curr.pricing_type}>
            {({ getFieldValue }) => {
              const type = getFieldValue('pricing_type')
              if (type === 'call') {
                return (
                  <Form.Item name="call_count" label="调用次数" rules={[{ required: true }]}>
                    <InputNumber min={0} style={{ width: '100%' }} placeholder="如：100" />
                  </Form.Item>
                )
              } else if (type === 'token') {
                return (
                  <Row gutter={16}>
                    <Col span={12}>
                      <Form.Item name="input_tokens" label="输入Token数">
                        <InputNumber min={0} style={{ width: '100%' }} placeholder="如：10000" />
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item name="output_tokens" label="输出Token数">
                        <InputNumber min={0} style={{ width: '100%' }} placeholder="如：5000" />
                      </Form.Item>
                    </Col>
                  </Row>
                )
              }
              return null
            }}
          </Form.Item>

          <Form.Item name="vip_level" label="VIP等级">
            <InputNumber min={0} max={10} placeholder="如：0, 1, 2, 3" />
          </Form.Item>

          <Button type="primary" htmlType="submit" loading={previewLoading} block>
            计算
          </Button>
        </Form>

        {previewResult && (
          <div className={styles.previewResult}>
            <Divider />
            <h4>计算结果：</h4>
            <Card>
              <Row gutter={16}>
                <Col span={12}>
                  <Statistic title="总费用" value={previewResult.cost} precision={4} prefix="¥" />
                </Col>
                <Col span={12}>
                  <Statistic
                    title="基础费用"
                    value={previewResult.details?.base_cost}
                    precision={4}
                    prefix="¥"
                  />
                </Col>
              </Row>
              <Divider />
              <p><strong>VIP折扣：</strong> {(previewResult.details?.vip_discount * 100).toFixed(0)}%</p>
              <p><strong>阶梯折扣：</strong> {(previewResult.details?.tier_discount * 100).toFixed(0)}%</p>
            </Card>
          </div>
        )}
      </Modal>
    </div>
  )
}

export default PricingConfigPage
