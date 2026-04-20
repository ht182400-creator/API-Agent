/**
 * 管理员月度账单管理页面
 */

import { useState, useEffect } from 'react'
import {
  Row, Col, Card, Table, Button, Typography, Tag, Space, DatePicker, Select,
  Modal, Form, Input, message, Drawer, Descriptions, Statistic, Empty, App, Popconfirm
} from 'antd'
import {
  FileTextOutlined,
  ReloadOutlined,
  EyeOutlined,
  CheckOutlined,
  CloseOutlined,
  UploadOutlined,
  DownloadOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import { billingApi, AdminMonthlyBill, PaginatedAdminMonthlyBills } from '../../api/billing'
import { useErrorModal } from '../../components/ErrorModal'
import { adminApi } from '../../api/superadmin'
import styles from './AdminBilling.module.css'

const { Title, Text } = Typography
const { RangePicker } = DatePicker

// 状态颜色映射
const STATUS_COLORS: Record<string, string> = {
  pending: 'default',
  generated: 'processing',
  reviewed: 'success',
  published: 'blue',
  rejected: 'error',
}

const STATUS_TEXT: Record<string, string> = {
  pending: '待生成',
  generated: '已生成',
  reviewed: '已审核',
  published: '已发布',
  rejected: '已拒绝',
}

export default function AdminMonthlyBills() {
  const [loading, setLoading] = useState(false)
  const [bills, setBills] = useState<AdminMonthlyBill[]>([])
  const [pagination, setPagination] = useState({ page: 1, page_size: 20, total: 0, total_pages: 0 })
  const [selectedYear, setSelectedYear] = useState<number>(dayjs().year())
  const [selectedMonth, setSelectedMonth] = useState<number>(dayjs().month() + 1)
  const [selectedStatus, setSelectedStatus] = useState<string | undefined>()
  const [detailVisible, setDetailVisible] = useState(false)
  const [currentBill, setCurrentBill] = useState<AdminMonthlyBill | null>(null)
  const [generating, setGenerating] = useState(false)
  const [reviewModalVisible, setReviewModalVisible] = useState(false)
  const [reviewBill, setReviewBill] = useState<AdminMonthlyBill | null>(null)
  const [reviewAction, setReviewAction] = useState<'approve' | 'reject'>('approve')
  const [reviewComment, setReviewComment] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const { showError, closeError, ErrorModal: ErrorModalComponent } = useErrorModal()
  const [messageApi, contextHolder] = message.useMessage()

  useEffect(() => {
    fetchBills()
  }, [selectedYear, selectedMonth, selectedStatus, pagination.page])

  const fetchBills = async () => {
    setLoading(true)
    try {
      const data = await billingApi.getAdminMonthlyBills({
        page: pagination.page,
        page_size: pagination.page_size,
        year: selectedYear,
        month: selectedMonth,
        status: selectedStatus,
      })
      setBills(data.items)
      setPagination(data.pagination)
    } catch (error: any) {
      showError(error, fetchBills)
    } finally {
      setLoading(false)
    }
  }

  const handleGenerate = async () => {
    setGenerating(true)
    try {
      const result = await billingApi.generateMonthlyBills({
        year: selectedYear,
        month: selectedMonth,
      })
      messageApi.success(`成功生成 ${result.generated_count} 个账单，跳过 ${result.skipped_count} 个已存在的账单`)
      fetchBills()
    } catch (error: any) {
      showError(error)
    } finally {
      setGenerating(false)
    }
  }

  const handleViewDetail = async (bill: AdminMonthlyBill) => {
    setCurrentBill(bill)
    setDetailVisible(true)
  }

  const handleReview = (bill: AdminMonthlyBill, action: 'approve' | 'reject') => {
    setReviewBill(bill)
    setReviewAction(action)
    setReviewComment('')
    setReviewModalVisible(true)
  }

  const handleReviewSubmit = async () => {
    if (!reviewBill) return
    setSubmitting(true)
    try {
      await billingApi.reviewMonthlyBill(reviewBill.id, {
        action: reviewAction,
        comment: reviewComment || undefined,
      })
      messageApi.success(reviewAction === 'approve' ? '审核通过' : '审核记录已保存')
      setReviewModalVisible(false)
      fetchBills()
    } catch (error: any) {
      showError(error)
    } finally {
      setSubmitting(false)
    }
  }

  const handlePublish = async (billId: string) => {
    try {
      await billingApi.publishMonthlyBill(billId)
      messageApi.success('账单已发布')
      fetchBills()
    } catch (error: any) {
      showError(error)
    }
  }

  const columns = [
    {
      title: '用户名',
      dataIndex: 'username',
      key: 'username',
      width: 120,
    },
    {
      title: '邮箱',
      dataIndex: 'email',
      key: 'email',
      width: 180,
      ellipsis: true,
    },
    {
      title: '充值金额',
      dataIndex: 'total_recharge',
      key: 'total_recharge',
      width: 120,
      render: (val: number) => <Text type="success">+¥{val.toFixed(2)}</Text>,
    },
    {
      title: '消费金额',
      dataIndex: 'total_consumption',
      key: 'total_consumption',
      width: 120,
      render: (val: number) => <Text type="danger">-¥{val.toFixed(2)}</Text>,
    },
    {
      title: '净变化',
      dataIndex: 'net_change',
      key: 'net_change',
      width: 120,
      render: (val: number) => (
        <Text type={val >= 0 ? 'success' : 'danger'}>
          {val >= 0 ? '+' : ''}¥{val.toFixed(2)}
        </Text>
      ),
    },
    {
      title: '调用次数',
      dataIndex: 'total_calls',
      key: 'total_calls',
      width: 100,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => (
        <Tag color={STATUS_COLORS[status] || 'default'}>
          {STATUS_TEXT[status] || status}
        </Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      render: (_: any, record: AdminMonthlyBill) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleViewDetail(record)}
          >
            详情
          </Button>
          {(record.status === 'generated' || record.status === 'pending') && (
            <>
              <Button
                type="link"
                size="small"
                icon={<CheckOutlined />}
                onClick={() => handleReview(record, 'approve')}
              >
                审核
              </Button>
            </>
          )}
          {record.status === 'reviewed' && (
            <Button
              type="link"
              size="small"
              icon={<UploadOutlined />}
              onClick={() => handlePublish(record.id)}
            >
              发布
            </Button>
          )}
        </Space>
      ),
    },
  ]

  // 生成月份选项
  const monthOptions = Array.from({ length: 12 }, (_, i) => ({
    value: i + 1,
    label: `${i + 1}月`,
  }))

  return (
    <div className={styles.container}>
      {contextHolder}
      <ErrorModalComponent />

      <div className={styles.header}>
        <div>
          <Title level={4}>月度账单管理</Title>
          <Text type="secondary">生成、审核和发布用户月度账单</Text>
        </div>
        <Space>
          <Select
            value={selectedYear}
            onChange={setSelectedYear}
            style={{ width: 100 }}
            options={Array.from({ length: 5 }, (_, i) => ({
              value: dayjs().year() - i,
              label: `${dayjs().year() - i}年`,
            }))}
          />
          <Select
            value={selectedMonth}
            onChange={setSelectedMonth}
            style={{ width: 80 }}
            options={monthOptions}
          />
          <Select
            value={selectedStatus}
            onChange={setSelectedStatus}
            style={{ width: 120 }}
            allowClear
            placeholder="选择状态"
            options={Object.entries(STATUS_TEXT).map(([value, label]) => ({
              value,
              label,
            }))}
          />
          <Button
            icon={<FileTextOutlined />}
            onClick={handleGenerate}
            loading={generating}
          >
            生成{selectedYear}年{selectedMonth}月账单
          </Button>
          <Button icon={<ReloadOutlined />} onClick={fetchBills}>
            刷新
          </Button>
        </Space>
      </div>

      <Card className={styles.tableCard}>
        <Table
          dataSource={bills}
          columns={columns}
          rowKey="id"
          loading={loading}
          pagination={{
            current: pagination.page,
            pageSize: pagination.page_size,
            total: pagination.total,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
            onChange: (page, pageSize) => setPagination({ ...pagination, page, page_size: pageSize }),
          }}
          locale={{ emptyText: <Empty description="暂无月度账单" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
        />
      </Card>

      {/* 详情抽屉 */}
      <Drawer
        title={`${currentBill?.year}年${currentBill?.month}月账单详情`}
        open={detailVisible}
        onClose={() => setDetailVisible(false)}
        width={600}
      >
        {currentBill && (
          <Descriptions column={2} bordered size="small">
            <Descriptions.Item label="用户">{currentBill.username}</Descriptions.Item>
            <Descriptions.Item label="邮箱">{currentBill.email}</Descriptions.Item>
            <Descriptions.Item label="期初余额">
              ¥{currentBill.beginning_balance.toFixed(2)}
            </Descriptions.Item>
            <Descriptions.Item label="期末余额">
              ¥{currentBill.ending_balance.toFixed(2)}
            </Descriptions.Item>
            <Descriptions.Item label="充值金额">
              <Text type="success">+¥{currentBill.total_recharge.toFixed(2)}</Text>
            </Descriptions.Item>
            <Descriptions.Item label="消费金额">
              <Text type="danger">-¥{currentBill.total_consumption.toFixed(2)}</Text>
            </Descriptions.Item>
            <Descriptions.Item label="净变化">
              <Text type={currentBill.net_change >= 0 ? 'success' : 'danger'}>
                {currentBill.net_change >= 0 ? '+' : ''}¥{currentBill.net_change.toFixed(2)}
              </Text>
            </Descriptions.Item>
            <Descriptions.Item label="状态">
              <Tag color={STATUS_COLORS[currentBill.status]}>
                {STATUS_TEXT[currentBill.status]}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="调用次数">{currentBill.total_calls}</Descriptions.Item>
            <Descriptions.Item label="Token使用">
              {currentBill.total_tokens.toLocaleString()}
            </Descriptions.Item>
            <Descriptions.Item label="生成时间" span={2}>
              {currentBill.generated_at ? dayjs(currentBill.generated_at).format('YYYY-MM-DD HH:mm:ss') : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="审核时间" span={2}>
              {currentBill.reviewed_at ? dayjs(currentBill.reviewed_at).format('YYYY-MM-DD HH:mm:ss') : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="发布时间" span={2}>
              {currentBill.published_at ? dayjs(currentBill.published_at).format('YYYY-MM-DD HH:mm:ss') : '-'}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Drawer>

      {/* 审核弹窗 */}
      <Modal
        title={reviewAction === 'approve' ? '审核通过' : '审核记录'}
        open={reviewModalVisible}
        onCancel={() => setReviewModalVisible(false)}
        onOk={handleReviewSubmit}
        okText={reviewAction === 'approve' ? '确认通过' : '确认'}
        confirmLoading={submitting}
      >
        <Form layout="vertical">
          <Form.Item label="用户">
            <Input value={reviewBill?.username} disabled />
          </Form.Item>
          <Form.Item label="账单周期">
            <Input value={`${reviewBill?.year}年${reviewBill?.month}月`} disabled />
          </Form.Item>
          <Form.Item label="审核备注">
            <Input.TextArea
              rows={3}
              value={reviewComment}
              onChange={(e) => setReviewComment(e.target.value)}
              placeholder="请输入审核备注（可选）"
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
