/**
 * 管理员对账管理页面
 * V2.6 新增 - 对账核心功能 + 阶段三：定时对账与报表导出
 */

import { useState, useEffect } from 'react'
import '../../styles/cyber-theme.css'
import { Card, Tabs, Table, Button, Space, Tag, Modal, Form, Select, Input, DatePicker, 
         Row, Col, Statistic, message, Spin, Typography, Alert, Descriptions, Badge, 
         Timeline, Progress, Divider } from 'antd'
import { 
  ReloadOutlined, 
  PlayCircleOutlined, 
  SearchOutlined, 
  CheckCircleOutlined, 
  ExclamationCircleOutlined,
  SyncOutlined,
  ClockCircleOutlined,
  DownloadOutlined,
  HistoryOutlined,
  SettingOutlined
} from '@ant-design/icons'
import dayjs from 'dayjs'
import { adminReconciliationApi, 
         ExecuteReconciliationRequest,
         ReconciliationResultItem,
         DisputeItem,
         ReconciliationHistoryItem,
         CHANNEL_OPTIONS,
         DISPUTE_TYPE_OPTIONS,
         HANDLE_STATUS_OPTIONS,
         RECONCILIATION_STATUS_OPTIONS,
         // 阶段三新增
         SchedulerStatus,
         TriggerReconciliationResponse,
         ReportItem,
         ReportResponse,
} from '../../api/adminReconciliation'
import { useErrorModal } from '../../components/ErrorModal'
import { useAuthStore } from '../../stores/auth'
import styles from './Reconciliation.module.css'

const { Title, Text } = Typography
const { RangePicker } = DatePicker
const { TextArea } = Input

// 状态颜色映射
const STATUS_COLORS: Record<string, string> = {
  pending: 'default',
  processing: 'processing',
  completed: 'success',
  disputed: 'warning',
  resolved: 'success',
  ignored: 'default',
}

// 状态名称映射
const STATUS_NAMES: Record<string, string> = {
  pending: '待处理',
  processing: '对账中',
  completed: '已完成',
  disputed: '有差异',
  resolved: '已解决',
  ignored: '已忽略',
}

export default function AdminReconciliation() {
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('execute')
  const [executing, setExecuting] = useState(false)
  const [reconciliationResult, setReconciliationResult] = useState<ReconciliationResultItem | null>(null)
  
  // 差异记录状态
  const [disputes, setDisputes] = useState<DisputeItem[]>([])
  const [disputeTotal, setDisputeTotal] = useState(0)
  const [disputePage, setDisputePage] = useState(1)
  const [disputePageSize, setDisputePageSize] = useState(10)
  const [disputeLoading, setDisputeLoading] = useState(false)
  
  // 历史记录状态
  const [history, setHistory] = useState<ReconciliationHistoryItem[]>([])
  const [historyTotal, setHistoryTotal] = useState(0)
  const [historyPage, setHistoryPage] = useState(1)
  const [historyPageSize, setHistoryPageSize] = useState(10)
  const [historyLoading, setHistoryLoading] = useState(false)
  
  // 处理差异弹窗
  const [handleModalVisible, setHandleModalVisible] = useState(false)
  const [currentDispute, setCurrentDispute] = useState<DisputeItem | null>(null)
  const [handleForm] = Form.useForm()
  
  // 查询表单状态
  const [queryDate, setQueryDate] = useState<string>(dayjs().format('YYYY-MM-DD'))
  const [queryChannel, setQueryChannel] = useState<string>('alipay')
  const [disputeFilters, setDisputeFilters] = useState({
    dispute_type: undefined as string | undefined,
    handle_status: undefined as string | undefined,
  })
  const [historyFilters, setHistoryFilters] = useState({
    channel: undefined as string | undefined,
    status: undefined as string | undefined,
    start_date: undefined as string | undefined,
    end_date: undefined as string | undefined,
  })

  // ==================== 阶段三新增状态 ====================
  const [schedulerStatus, setSchedulerStatus] = useState<SchedulerStatus | null>(null)
  const [schedulerLoading, setSchedulerLoading] = useState(false)
  const [triggering, setTriggering] = useState(false)
  const [reportLoading, setReportLoading] = useState(false)
  const [reportData, setReportData] = useState<ReportResponse | null>(null)
  const [reportFilters, setReportFilters] = useState({
    start_date: dayjs().subtract(7, 'day').format('YYYY-MM-DD'),
    end_date: dayjs().format('YYYY-MM-DD'),
    channel: undefined as string | undefined,
  })

  const { showError, ErrorModal: ErrorModalComponent } = useErrorModal()
  const [messageApi, contextHolder] = message.useMessage()

  // 加载对账结果
  const loadResult = async () => {
    setLoading(true)
    try {
      const result = await adminReconciliationApi.getReconciliationResult({
        date: queryDate,
        channel: queryChannel
      })
      setReconciliationResult(result)
    } catch (error: any) {
      if (error?.response?.status !== 404) {
        showError(error, loadResult)
      }
      setReconciliationResult(null)
    } finally {
      setLoading(false)
    }
  }

  // 执行对账
  const handleExecute = async () => {
    setExecuting(true)
    try {
      await adminReconciliationApi.executeReconciliation({
        date: queryDate,
        channel: queryChannel
      } as ExecuteReconciliationRequest)
      messageApi.success('对账执行成功')
      await loadResult()
    } catch (error: any) {
      showError(error, handleExecute)
    } finally {
      setExecuting(false)
    }
  }

  // 加载差异记录
  const loadDisputes = async () => {
    setDisputeLoading(true)
    try {
      const response = await adminReconciliationApi.getDisputes({
        reconciliation_id: reconciliationResult?.reconciliation_id,
        dispute_type: disputeFilters.dispute_type,
        handle_status: disputeFilters.handle_status,
        page: disputePage,
        page_size: disputePageSize,
      })
      setDisputes(response.items || [])
      setDisputeTotal(response.pagination?.total || 0)
    } catch (error: any) {
      showError(error, loadDisputes)
    } finally {
      setDisputeLoading(false)
    }
  }

  // 加载历史记录
  const loadHistory = async () => {
    setHistoryLoading(true)
    try {
      const response = await adminReconciliationApi.getHistory({
        channel: historyFilters.channel,
        status: historyFilters.status,
        start_date: historyFilters.start_date,
        end_date: historyFilters.end_date,
        page: historyPage,
        page_size: historyPageSize,
      })
      setHistory(response.items || [])
      setHistoryTotal(response.pagination?.total || 0)
    } catch (error: any) {
      showError(error, loadHistory)
    } finally {
      setHistoryLoading(false)
    }
  }

  // 处理差异
  const handleDisputeAction = async () => {
    try {
      const values = await handleForm.validateFields()
      await adminReconciliationApi.handleDispute(currentDispute!.id, {
        handle_status: values.handle_status,
        handle_remark: values.handle_remark,
      })
      messageApi.success('差异处理成功')
      setHandleModalVisible(false)
      handleForm.resetFields()
      loadDisputes()
    } catch (error: any) {
      showError(error, handleDisputeAction)
    }
  }

  // 打开处理弹窗
  const openHandleModal = (dispute: DisputeItem) => {
    setCurrentDispute(dispute)
    handleForm.setFieldsValue({
      handle_status: dispute.handle_status,
      handle_remark: '',
    })
    setHandleModalVisible(true)
  }

  // ==================== 阶段三新增功能 ====================
  
  // 加载调度器状态
  const loadSchedulerStatus = async () => {
    setSchedulerLoading(true)
    try {
      const response = await adminReconciliationApi.getSchedulerStatus()
      setSchedulerStatus(response)
    } catch (error: any) {
      showError(error, loadSchedulerStatus)
    } finally {
      setSchedulerLoading(false)
    }
  }

  // 手动触发对账
  const handleTriggerReconciliation = async () => {
    setTriggering(true)
    try {
      const result = await adminReconciliationApi.triggerReconciliation({
        date: dayjs().subtract(1, 'day').format('YYYY-MM-DD'),
        channels: ['alipay', 'wechat', 'bankcard'],
      })
      messageApi.success(`对账任务已触发，状态: ${result.status}`)
      await loadSchedulerStatus()
      await loadHistory()
    } catch (error: any) {
      showError(error, handleTriggerReconciliation)
    } finally {
      setTriggering(false)
    }
  }

  // 生成报表
  const loadReport = async () => {
    setReportLoading(true)
    try {
      const response = await adminReconciliationApi.generateReport({
        start_date: reportFilters.start_date,
        end_date: reportFilters.end_date,
        channel: reportFilters.channel,
      })
      setReportData(response)
    } catch (error: any) {
      showError(error, loadReport)
    } finally {
      setReportLoading(false)
    }
  }

  // 下载报表
  const handleDownloadReport = () => {
    const url = adminReconciliationApi.getDownloadUrl({
      start_date: reportFilters.start_date,
      end_date: reportFilters.end_date,
      channel: reportFilters.channel,
      format: 'csv',
    })
    window.open(url, '_blank')
    messageApi.success('报表下载已开始')
  }

  // Tab切换
  const handleTabChange = (key: string) => {
    setActiveTab(key)
    if (key === 'disputes' && reconciliationResult) {
      loadDisputes()
    } else if (key === 'history') {
      loadHistory()
    } else if (key === 'scheduler') {
      loadSchedulerStatus()
    } else if (key === 'report') {
      loadReport()
    }
  }

  // 初始化
  useEffect(() => {
    loadResult()
  }, [])

  useEffect(() => {
    if (activeTab === 'disputes' && reconciliationResult) {
      loadDisputes()
    }
  }, [disputePage, disputePageSize, disputeFilters, reconciliationResult])

  useEffect(() => {
    if (activeTab === 'history') {
      loadHistory()
    }
  }, [historyPage, historyPageSize, historyFilters])

  // 差异记录表格列
  const disputeColumns = [
    {
      title: '差异类型',
      dataIndex: 'dispute_type',
      key: 'dispute_type',
      render: (type: string, record: DisputeItem) => (
        <Tag color={type === 'long' ? 'blue' : type === 'short' ? 'orange' : 'red'}>
          {record.dispute_type_name}
        </Tag>
      ),
    },
    {
      title: '本地订单号',
      dataIndex: 'local_order_no',
      key: 'local_order_no',
    },
    {
      title: '渠道交易号',
      dataIndex: 'channel_trade_no',
      key: 'channel_trade_no',
    },
    {
      title: '本地金额',
      dataIndex: 'local_amount',
      key: 'local_amount',
      render: (amount: number) => amount != null ? `¥${amount.toFixed(2)}` : '-',
    },
    {
      title: '差异金额',
      dataIndex: 'diff_amount',
      key: 'diff_amount',
      render: (amount: number) => (
        amount != null ? (
          <Text type={amount > 0 ? 'success' : 'danger'}>
            {amount > 0 ? '+' : ''}{amount.toFixed(2)}
          </Text>
        ) : '-'
      ),
    },
    {
      title: '处理状态',
      dataIndex: 'handle_status',
      key: 'handle_status',
      render: (status: string) => (
        <Badge status={STATUS_COLORS[status] as any} text={STATUS_NAMES[status]} />
      ),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: DisputeItem) => (
        record.handle_status === 'pending' && (
          <Button type="link" size="small" onClick={() => openHandleModal(record)}>
            处理
          </Button>
        )
      ),
    },
  ]

  // 历史记录表格列
  const historyColumns = [
    {
      title: '对账日期',
      dataIndex: 'reconcile_date',
      key: 'reconcile_date',
      render: (date: string) => dayjs(date).format('YYYY-MM-DD'),
    },
    {
      title: '渠道',
      dataIndex: 'channel_name',
      key: 'channel_name',
    },
    {
      title: '匹配/长款/短款',
      key: 'match',
      render: (_: any, record: ReconciliationHistoryItem) => (
        <Space>
          <Tag color="green">{record.match_count}</Tag>
          <Tag color="blue">{record.long_count}</Tag>
          <Tag color="orange">{record.short_count}</Tag>
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string, record: ReconciliationHistoryItem) => (
        <Badge status={STATUS_COLORS[status] as any} text={record.status_name} />
      ),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: ReconciliationHistoryItem) => (
        <Button 
          type="link" 
          size="small"
          onClick={() => {
            setQueryDate(dayjs(record.reconcile_date).format('YYYY-MM-DD'))
            setQueryChannel(record.channel)
            loadResult()
            setActiveTab('execute')
          }}
        >
          查看详情
        </Button>
      ),
    },
  ]

  // 报表表格列
  const reportColumns = [
    {
      title: '对账日期',
      dataIndex: 'reconcile_date',
      key: 'reconcile_date',
    },
    {
      title: '渠道',
      dataIndex: 'channel_name',
      key: 'channel_name',
    },
    {
      title: '平台交易',
      key: 'platform',
      render: (_: any, record: ReportItem) => (
        <Text>{record.platform_trade_count}笔 ¥{record.platform_trade_amount.toFixed(2)}</Text>
      ),
    },
    {
      title: '匹配率',
      dataIndex: 'match_rate',
      key: 'match_rate',
      render: (rate: number) => (
        <Progress percent={rate} size="small" format={(p) => `${p}%`} />
      ),
    },
    {
      title: '待处理',
      dataIndex: 'pending_dispute_count',
      key: 'pending_dispute_count',
      render: (count: number) => count > 0 ? <Badge count={count} style={{ backgroundColor: '#faad14' }} /> : '-',
    },
  ]

  return (
    <div className={`${styles.container} bamboo-bg-pattern`}>
      {contextHolder}
      <ErrorModalComponent />

      <div className={styles.header}>
        <Title level={4}>对账管理</Title>
        <Space>
          <Select
            value={queryChannel}
            onChange={setQueryChannel}
            options={CHANNEL_OPTIONS}
            style={{ width: 120 }}
          />
          <DatePicker
            value={dayjs(queryDate)}
            onChange={(date) => setQueryDate(date?.format('YYYY-MM-DD') || queryDate)}
            placeholder="选择日期"
          />
          <Button icon={<ReloadOutlined />} onClick={loadResult}>刷新</Button>
        </Space>
      </div>

      <Tabs 
        activeKey={activeTab} 
        onChange={handleTabChange}
        items={[
          {
            key: 'execute',
            label: '执行对账',
            children: (
              <div>
                {loading ? (
                  <div className={styles.loadingContainer}>
                    <Spin size="large" tip="加载中..." />
                  </div>
                ) : reconciliationResult ? (
                  <Card className={styles.resultCard}>
                    <Descriptions title="对账结果" bordered column={4}>
                      <Descriptions.Item label="对账日期">{dayjs(reconciliationResult.reconcile_date).format('YYYY-MM-DD')}</Descriptions.Item>
                      <Descriptions.Item label="渠道">{reconciliationResult.channel_name}</Descriptions.Item>
                      <Descriptions.Item label="状态" span={2}>
                        <Badge status={STATUS_COLORS[reconciliationResult.status] as any} text={STATUS_NAMES[reconciliationResult.status]} />
                      </Descriptions.Item>
                    </Descriptions>
                    
                    <Row gutter={16} className={styles.statsRow}>
                      <Col span={6}><Statistic title="平台交易" value={reconciliationResult.platform_trade_count} suffix="笔" /></Col>
                      <Col span={6}><Statistic title="渠道交易" value={reconciliationResult.channel_trade_count} suffix="笔" /></Col>
                      <Col span={6}><Statistic title="匹配" value={reconciliationResult.match_count} suffix="笔" valueStyle={{ color: '#52c41a' }} /></Col>
                      <Col span={6}><Statistic title="差异" value={reconciliationResult.amount_diff_count} suffix="笔" valueStyle={{ color: reconciliationResult.amount_diff_count > 0 ? '#ff4d4f' : '#52c41a' }} /></Col>
                    </Row>

                    {reconciliationResult.amount_diff_count > 0 && (
                      <Alert message="存在金额差异" description={`共有 ${reconciliationResult.amount_diff_count} 笔订单存在金额差异，请前往"差异记录"页面处理。`} type="warning" showIcon style={{ marginTop: 16 }} />
                    )}
                  </Card>
                ) : (
                  <Card><Alert message="暂无对账数据" description={`${queryDate} 暂无对账记录，请点击"执行对账"按钮。`} type="info" showIcon /></Card>
                )}

                <Card className={styles.executeCard}>
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Text type="secondary">点击下方按钮将对账系统与渠道进行数据比对。</Text>
                    <Button type="primary" icon={executing ? <SyncOutlined spin /> : <PlayCircleOutlined />} onClick={handleExecute} loading={executing} size="large">
                      {executing ? '对账执行中...' : '执行对账'}
                    </Button>
                  </Space>
                </Card>
              </div>
            ),
          },
          {
            key: 'disputes',
            label: (
              <Space>差异记录 {disputeTotal > 0 && <Badge count={disputeTotal} style={{ backgroundColor: '#faad14' }} />}</Space>
            ),
            children: (
              <Card>
                <div className={styles.filterBar}>
                  <Space wrap>
                    <Select placeholder="差异类型" allowClear style={{ width: 140 }} options={DISPUTE_TYPE_OPTIONS} onChange={(value) => setDisputeFilters(f => ({ ...f, dispute_type: value }))} />
                    <Select placeholder="处理状态" allowClear style={{ width: 120 }} options={HANDLE_STATUS_OPTIONS} onChange={(value) => setDisputeFilters(f => ({ ...f, handle_status: value }))} />
                    <Button icon={<SearchOutlined />} onClick={loadDisputes}>查询</Button>
                  </Space>
                </div>
                <Table columns={disputeColumns} dataSource={disputes} rowKey="id" loading={disputeLoading}
                  pagination={{ current: disputePage, pageSize: disputePageSize, total: disputeTotal, showSizeChanger: true, showTotal: (total) => `共 ${total} 条`, onChange: (page, size) => { setDisputePage(page); setDisputePageSize(size) }, }} />
              </Card>
            ),
          },
          {
            key: 'history',
            label: '历史记录',
            children: (
              <Card>
                <div className={styles.filterBar}>
                  <Space wrap>
                    <Select placeholder="渠道" allowClear style={{ width: 120 }} options={CHANNEL_OPTIONS} onChange={(value) => setHistoryFilters(f => ({ ...f, channel: value }))} />
                    <RangePicker onChange={(dates) => { setHistoryFilters(f => ({ ...f, start_date: dates?.[0]?.format('YYYY-MM-DD'), end_date: dates?.[1]?.format('YYYY-MM-DD') })) }} />
                    <Button icon={<SearchOutlined />} onClick={loadHistory}>查询</Button>
                  </Space>
                </div>
                <Table columns={historyColumns} dataSource={history} rowKey="id" loading={historyLoading}
                  pagination={{ current: historyPage, pageSize: historyPageSize, total: historyTotal, showSizeChanger: true, showTotal: (total) => `共 ${total} 条`, onChange: (page, size) => { setHistoryPage(page); setHistoryPageSize(size) }, }} />
              </Card>
            ),
          },
          // ==================== 阶段三新增 Tab ====================
          {
            key: 'scheduler',
            label: <Space><ClockCircleOutlined />定时对账</Space>,
            children: (
              <Card>
                <Row gutter={24}>
                  <Col span={12}>
                    <Card title="调度器状态" size="small">
                      {schedulerLoading ? <Spin tip="加载中..." /> : schedulerStatus ? (
                        <Space direction="vertical" style={{ width: '100%' }}>
                          <Space><Text type="secondary">运行状态：</Text><Badge status={schedulerStatus.is_running ? 'processing' : 'default'} text={schedulerStatus.is_running ? '执行中' : '空闲'} /></Space>
                          <Space><Text type="secondary">上次运行：</Text><Text>{schedulerStatus.last_run_time ? dayjs(schedulerStatus.last_run_time).format('YYYY-MM-DD HH:mm:ss') : '从未运行'}</Text></Space>
                          <Space><Text type="secondary">任务记录：</Text><Text>{schedulerStatus.task_count} 条</Text></Space>
                          <Divider />
                          <Button type="primary" icon={<PlayCircleOutlined />} onClick={handleTriggerReconciliation} loading={triggering} disabled={schedulerStatus.is_running}>
                            {triggering ? '触发中...' : '立即执行对账'}
                          </Button>
                        </Space>
                      ) : <Text type="secondary">加载失败</Text>}
                    </Card>
                  </Col>
                  <Col span={12}>
                    <Card title="定时规则" size="small">
                      <Descriptions column={1} size="small">
                        <Descriptions.Item label="执行时间">每天 04:00 (T+1)</Descriptions.Item>
                        <Descriptions.Item label="对账范围">前一日所有渠道交易</Descriptions.Item>
                        <Descriptions.Item label="支持渠道">支付宝、微信支付、银行卡</Descriptions.Item>
                      </Descriptions>
                    </Card>
                  </Col>
                </Row>
                {schedulerStatus && schedulerStatus.tasks.length > 0 && (
                  <Card title="最近执行记录" size="small" style={{ marginTop: 16 }}>
                    <Timeline items={schedulerStatus.tasks.slice(0, 5).map(task => ({
                      color: task.status === 'completed' ? 'green' : 'red',
                      children: (
                        <Space>
                          <Text>{dayjs(task.executed_at).format('YYYY-MM-DD HH:mm:ss')}</Text>
                          <Tag>{task.date}</Tag>
                          <Tag color={task.status === 'completed' ? 'success' : 'error'}>{task.status === 'completed' ? '成功' : '失败'}</Tag>
                        </Space>
                      ),
                    }))} />
                  </Card>
                )}
              </Card>
            ),
          },
          {
            key: 'report',
            label: <Space><DownloadOutlined />报表导出</Space>,
            children: (
              <Card>
                <div className={styles.filterBar}>
                  <Space wrap>
                    <RangePicker value={[dayjs(reportFilters.start_date), dayjs(reportFilters.end_date)]} onChange={(dates) => { setReportFilters(f => ({ ...f, start_date: dates?.[0]?.format('YYYY-MM-DD') || f.start_date, end_date: dates?.[1]?.format('YYYY-MM-DD') || f.end_date })) }} />
                    <Select placeholder="渠道" allowClear style={{ width: 120 }} options={CHANNEL_OPTIONS} onChange={(value) => setReportFilters(f => ({ ...f, channel: value }))} />
                    <Button type="primary" icon={<SearchOutlined />} onClick={loadReport} loading={reportLoading}>生成报表</Button>
                    <Button icon={<DownloadOutlined />} onClick={handleDownloadReport} disabled={!reportData || reportData.items.length === 0}>下载 CSV</Button>
                  </Space>
                </div>
                {reportLoading ? (
                  <div className={styles.loadingContainer}><Spin size="large" tip="生成报表中..." /></div>
                ) : reportData ? (
                  <>
                    <Card size="small" style={{ marginBottom: 16 }}>
                      <Row gutter={16}>
                        <Col span={6}><Statistic title="对账天数" value={reportData.summary.total_count} suffix="天" /></Col>
                        <Col span={6}><Statistic title="总平台金额" value={reportData.summary.total_platform_amount} precision={2} prefix="¥" /></Col>
                        <Col span={6}><Statistic title="总匹配数" value={reportData.summary.total_match_count} suffix="笔" valueStyle={{ color: '#52c41a' }} /></Col>
                        <Col span={6}><Statistic title="待处理差异" value={reportData.summary.total_pending} suffix="笔" valueStyle={{ color: reportData.summary.total_pending > 0 ? '#faad14' : '#52c41a' }} /></Col>
                      </Row>
                    </Card>
                    <Table columns={reportColumns} dataSource={reportData.items} rowKey={(record) => `${record.reconcile_date}-${record.channel}`} pagination={false} size="small" />
                  </>
                ) : (
                  <Alert message='请选择日期范围并点击"生成报表"按钮' description="报表将显示选定日期范围内的对账汇总数据" type="info" showIcon />
                )}
              </Card>
            ),
          },
        ]}
      />

      {/* 处理差异弹窗 */}
      <Modal title="处理差异" open={handleModalVisible} onOk={handleDisputeAction} onCancel={() => { setHandleModalVisible(false); handleForm.resetFields() }} okText="确认处理" cancelText="取消">
        {currentDispute && (
          <Form form={handleForm} layout="vertical">
            <Descriptions column={1} bordered size="small">
              <Descriptions.Item label="差异类型"><Tag>{currentDispute.dispute_type_name}</Tag></Descriptions.Item>
              <Descriptions.Item label="本地订单号">{currentDispute.local_order_no}</Descriptions.Item>
              <Descriptions.Item label="差异金额"><Text type="danger">{currentDispute.diff_amount?.toFixed(2)}</Text></Descriptions.Item>
            </Descriptions>
            <Form.Item name="handle_status" label="处理状态" rules={[{ required: true, message: '请选择处理状态' }]}>
              <Select options={HANDLE_STATUS_OPTIONS.filter(s => s.value !== 'pending')} />
            </Form.Item>
            <Form.Item name="handle_remark" label="处理说明">
              <TextArea rows={3} placeholder="请输入处理说明..." />
            </Form.Item>
          </Form>
        )}
      </Modal>
    </div>
  )
}
