/**
 * 消费明细页面
 * V2.6 更新：支持多种计费模式显示（按次数/按Token/包月）
 */

import React, { useState, useEffect } from 'react'
import '../../styles/cyber-theme.css'
import {
  Card,
  Table,
  Space,
  DatePicker,
  Select,
  Button,
  Statistic,
  Row,
  Col,
  message,
  Tag,
  Typography,
  Tabs,
  Progress,
  Empty,
  Tooltip,
  Badge,
} from 'antd'
import {
  BarChartOutlined,
  DollarOutlined,
  ApartmentOutlined,
  SearchOutlined,
  ReloadOutlined,
  ProjectOutlined,
  UnorderedListOutlined,
  CalendarOutlined,
  ThunderboltOutlined,
  CrownOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { billingApi, ConsumptionDetail, UserUsage } from '../../api/billing'
import { useDevice } from '../../hooks/useDevice'
import styles from './ConsumptionDetails.module.css'

const { RangePicker } = DatePicker
const { Text } = Typography

// 计费模式枚举
type BillingModel = 'per_call' | 'per_token' | 'subscription'

// 计费模式配置
const BILLING_MODEL_CONFIG: Record<BillingModel, { label: string; icon: React.ReactNode; color: string }> = {
  per_call: { label: '按次计费', icon: <ThunderboltOutlined />, color: '#1677ff' },
  per_token: { label: '按Token计费', icon: <BarChartOutlined />, color: '#722ed1' },
  subscription: { label: '包月/包年', icon: <CrownOutlined />, color: '#faad14' },
}

// 按仓库聚合的数据类型
interface RepoSummary {
  repo_id: string
  repo_name: string
  billing_model: BillingModel
  call_count: number
  total_tokens: number
  total_cost: number
}

// 按接口聚合的数据类型
interface EndpointSummary {
  endpoint: string
  repo_name: string
  billing_model: BillingModel
  call_count: number
  total_tokens: number
  total_cost: number
}

// 按日期聚合的数据类型
interface DailySummary {
  date: string
  call_count: number
  total_tokens: number
  total_cost: number
}

const ConsumptionDetails: React.FC = () => {
  const { isMobile } = useDevice()
  const [activeTab, setActiveTab] = useState<string>('repo')
  const [loading, setLoading] = useState(false)
  const [details, setDetails] = useState<ConsumptionDetail[]>([])
  const [pagination, setPagination] = useState({
    page: 1,
    page_size: 20,
    total: 0,
  })
  const [dateRange, setDateRange] = useState<[string | null, string | null]>([null, null])
  const [selectedRepo, setSelectedRepo] = useState<string | undefined>(undefined)
  const [billingModel, setBillingModel] = useState<BillingModel>('per_call')

  // 仓库汇总数据
  const [repoSummary, setRepoSummary] = useState<RepoSummary[]>([])
  const [repoTotal, setRepoTotal] = useState({ call_count: 0, total_tokens: 0, total_cost: 0 })

  // 接口汇总数据
  const [endpointSummary, setEndpointSummary] = useState<EndpointSummary[]>([])

  // 日期汇总数据
  const [dailySummary, setDailySummary] = useState<DailySummary[]>([])

  // 加载仓库汇总数据
  const loadRepoSummary = async () => {
    try {
      const response = await billingApi.getUsage()
      if (response?.by_repository) {
        // 判断计费模式
        const hasTokens = response.by_repository.some((r: any) => (r.total_tokens || 0) > 0)
        setBillingModel(hasTokens ? 'per_token' : 'per_call')

        const repos = response.by_repository.map((r: any) => ({
          repo_id: r.repo_id,
          repo_name: r.repo_name || '未知仓库',
          billing_model: (r.total_tokens || 0) > 0 ? 'per_token' as BillingModel : 'per_call' as BillingModel,
          call_count: r.call_count || 0,
          total_tokens: r.total_tokens || 0,
          total_cost: r.total_cost || 0,
        }))
        setRepoSummary(repos)

        const totals = repos.reduce((acc: any, r: any) => ({
          call_count: acc.call_count + r.call_count,
          total_tokens: acc.total_tokens + r.total_tokens,
          total_cost: acc.total_cost + r.total_cost,
        }), { call_count: 0, total_tokens: 0, total_cost: 0 })
        setRepoTotal(totals)
      }
    } catch (error) {
      console.error('加载仓库汇总失败:', error)
    }
  }

  // 加载消费明细
  const loadDetails = async () => {
    setLoading(true)
    try {
      const params: any = {
        page: pagination.page,
        page_size: pagination.page_size,
      }

      if (selectedRepo) params.repo_id = selectedRepo
      if (dateRange[0]) params.start_date = dateRange[0]
      if (dateRange[1]) params.end_date = dateRange[1]

      const response = await billingApi.getConsumptionDetails(params)
      if (response) {
        setDetails(response.items || [])
        setPagination({
          ...pagination,
          total: response.pagination?.total || 0,
        })

        // 按接口聚合
        const endpointMap: Record<string, EndpointSummary> = {}
        const dailyMap: Record<string, DailySummary> = {}

        ;(response.items || []).forEach((item: ConsumptionDetail) => {
          const hasTokens = (item.tokens_used || 0) > 0
          const model: BillingModel = hasTokens ? 'per_token' : 'per_call'

          // 按接口聚合
          const key = `${item.endpoint}-${item.repo_name}`
          if (!endpointMap[key]) {
            endpointMap[key] = {
              endpoint: item.endpoint,
              repo_name: item.repo_name || '未知',
              billing_model: model,
              call_count: 0,
              total_tokens: 0,
              total_cost: 0,
            }
          }
          endpointMap[key].call_count++
          endpointMap[key].total_tokens += item.tokens_used || 0
          endpointMap[key].total_cost += item.cost || 0

          // 按日期聚合
          const date = item.created_at?.split('T')[0] || '未知'
          if (!dailyMap[date]) {
            dailyMap[date] = { date, call_count: 0, total_tokens: 0, total_cost: 0 }
          }
          dailyMap[date].call_count++
          dailyMap[date].total_tokens += item.tokens_used || 0
          dailyMap[date].total_cost += item.cost || 0
        })

        setEndpointSummary(Object.values(endpointMap))
        setDailySummary(Object.values(dailyMap).sort((a, b) => b.date.localeCompare(a.date)))
      }
    } catch (error) {
      message.error('加载消费明细失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadRepoSummary()
  }, [])

  useEffect(() => {
    if (activeTab === 'detail') {
      loadDetails()
    }
  }, [pagination.page, pagination.page_size, activeTab])

  // 处理日期范围变化
  const handleDateChange = (dates: any, dateStrings: [string, string]) => {
    setDateRange(dateStrings)
  }

  // 处理仓库变化
  const handleRepoChange = (value: string) => {
    setSelectedRepo(value || undefined)
  }

  // 查询按钮
  const handleSearch = () => {
    setPagination({ ...pagination, page: 1 })
    loadDetails()
  }

  // 重置按钮
  const handleReset = () => {
    setDateRange([null, null])
    setSelectedRepo(undefined)
    setPagination({ ...pagination, page: 1 })
    loadDetails()
  }

  // 明细表格列 - 根据计费模式动态显示
  const detailColumns: ColumnsType<ConsumptionDetail> = [
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (time: string) => {
        const date = new Date(time)
        return `${date.toLocaleDateString()} ${date.toLocaleTimeString()}`
      },
    },
    {
      title: '仓库',
      dataIndex: 'repo_name',
      key: 'repo_name',
      width: 100,
      render: (name: string) => <Tag color="blue">{name || '未知'}</Tag>,
    },
    {
      title: '接口',
      dataIndex: 'endpoint',
      key: 'endpoint',
      width: 140,
      ellipsis: true,
      render: (endpoint: string) => (
        <Text code style={{ fontSize: 11 }}>
          {endpoint || '-'}
        </Text>
      ),
    },
    {
      title: '调用者',
      dataIndex: 'tester',
      key: 'tester',
      width: 100,
      render: (tester: string) => (
        <Tag color="purple">{tester || '-'}</Tag>
      ),
    },
    {
      title: '请求参数',
      dataIndex: 'request_params',
      key: 'request_params',
      width: 200,
      ellipsis: true,
      render: (params: string) => {
        if (!params) return <Text type="secondary">-</Text>
        try {
          const parsed = JSON.parse(params)
          const preview = Object.entries(parsed)
            .slice(0, 3)
            .map(([k, v]) => `${k}=${String(v).substring(0, 15)}`)
            .join(', ')
          return (
            <Tooltip title={<pre style={{ margin: 0, fontSize: 11 }}>{JSON.stringify(parsed, null, 2)}</pre>}>
              <Text style={{ fontSize: 11, color: '#64748b' }}>
                {Object.keys(parsed).length > 3 ? `${preview}...` : preview}
              </Text>
            </Tooltip>
          )
        } catch {
          return <Text style={{ fontSize: 11 }} ellipsis={{ tooltip: params }}>{params}</Text>
        }
      },
    },
    // 根据计费模式显示/隐藏Tokens列
    ...(billingModel === 'per_token' ? [{
      title: '使用 Tokens',
      dataIndex: 'tokens_used',
      key: 'tokens_used',
      width: 100,
      align: 'right' as const,
      render: (tokens: number) => (
        <Tooltip title={`${tokens?.toLocaleString() || 0} Tokens`}>
          <Text style={{ color: '#722ed1' }}>
            {(tokens || 0).toLocaleString()}
          </Text>
        </Tooltip>
      ),
    }] : []),
    {
      title: '费用',
      dataIndex: 'cost',
      key: 'cost',
      width: 80,
      align: 'right' as const,
      render: (cost: number) => (
        <Text type="danger">
          ¥{Math.abs(cost || 0).toFixed(billingModel === 'per_token' ? 4 : 2)}
        </Text>
      ),
    },
  ]

  // 仓库汇总表格列
  const repoColumns: ColumnsType<RepoSummary> = [
    {
      title: '仓库',
      dataIndex: 'repo_name',
      key: 'repo_name',
      render: (name: string, record) => (
        <Space direction="vertical" size={0}>
          <Space>
            <Tag color="blue">{name}</Tag>
            <Tag icon={BILLING_MODEL_CONFIG[record.billing_model].icon} 
                 color={record.billing_model === 'per_call' ? 'blue' : 
                        record.billing_model === 'per_token' ? 'purple' : 'gold'}>
              {BILLING_MODEL_CONFIG[record.billing_model].label}
            </Tag>
          </Space>
          <Text type="secondary" style={{ fontSize: 11 }}>
            ID: {record.repo_id?.substring(0, 8)}...
          </Text>
        </Space>
      ),
    },
    {
      title: '调用次数',
      dataIndex: 'call_count',
      key: 'call_count',
      align: 'right',
      sorter: (a, b) => a.call_count - b.call_count,
      render: (count: number) => count?.toLocaleString() || 0,
    },
    ...(billingModel === 'per_token' ? [{
      title: '总 Tokens',
      dataIndex: 'total_tokens',
      key: 'total_tokens',
      align: 'right',
      sorter: (a: RepoSummary, b: RepoSummary) => a.total_tokens - b.total_tokens,
      render: (tokens: number) => tokens?.toLocaleString() || 0,
    }] : []),
    {
      title: '总费用',
      dataIndex: 'total_cost',
      key: 'total_cost',
      align: 'right',
      sorter: (a, b) => a.total_cost - b.total_cost,
      render: (cost: number) => (
        <Text type="danger" strong>¥{Math.abs(cost || 0).toFixed(billingModel === 'per_token' ? 4 : 2)}</Text>
      ),
    },
    {
      title: '占比',
      key: 'percent',
      width: 150,
      render: (_, record) => {
        const percent = repoTotal.call_count > 0
          ? (record.call_count / repoTotal.call_count) * 100
          : 0
        return (
          <Progress 
            percent={percent} 
            size="small" 
            format={() => `${percent.toFixed(1)}%`}
            strokeColor={percent > 50 ? '#1677ff' : '#52c41a'}
          />
        )
      },
    },
  ]

  // 接口汇总表格列
  const endpointColumns: ColumnsType<EndpointSummary> = [
    {
      title: '接口',
      dataIndex: 'endpoint',
      key: 'endpoint',
      ellipsis: true,
      render: (endpoint: string) => (
        <Text code style={{ fontSize: 11 }}>{endpoint || '-'}</Text>
      ),
    },
    {
      title: '仓库',
      dataIndex: 'repo_name',
      key: 'repo_name',
      width: 120,
      render: (name: string) => <Tag color="green">{name}</Tag>,
    },
    {
      title: '调用次数',
      dataIndex: 'call_count',
      key: 'call_count',
      align: 'right',
      sorter: (a, b) => a.call_count - b.call_count,
      render: (count: number) => count?.toLocaleString() || 0,
    },
    ...(billingModel === 'per_token' ? [{
      title: '总 Tokens',
      dataIndex: 'total_tokens',
      key: 'total_tokens',
      align: 'right',
      render: (tokens: number) => tokens?.toLocaleString() || 0,
    }] : []),
    {
      title: '总费用',
      dataIndex: 'total_cost',
      key: 'total_cost',
      align: 'right',
      render: (cost: number) => (
        <Text type="danger">¥{Math.abs(cost || 0).toFixed(billingModel === 'per_token' ? 4 : 2)}</Text>
      ),
    },
  ]

  // 日期汇总表格列
  const dailyColumns: ColumnsType<DailySummary> = [
    {
      title: '日期',
      dataIndex: 'date',
      key: 'date',
      width: 120,
      sorter: (a, b) => a.date.localeCompare(b.date),
      render: (date: string) => <Badge color="#1677ff" text={date} />,
    },
    {
      title: '调用次数',
      dataIndex: 'call_count',
      key: 'call_count',
      align: 'right',
      sorter: (a, b) => a.call_count - b.call_count,
      render: (count: number) => count?.toLocaleString() || 0,
    },
    ...(billingModel === 'per_token' ? [{
      title: '总 Tokens',
      dataIndex: 'total_tokens',
      key: 'total_tokens',
      align: 'right',
      sorter: (a: DailySummary, b: DailySummary) => a.total_tokens - b.total_tokens,
      render: (tokens: number) => tokens?.toLocaleString() || 0,
    }] : []),
    {
      title: '总费用',
      dataIndex: 'total_cost',
      key: 'total_cost',
      align: 'right',
      sorter: (a, b) => a.total_cost - b.total_cost,
      render: (cost: number) => (
        <Text type="danger" strong>¥{Math.abs(cost || 0).toFixed(billingModel === 'per_token' ? 4 : 2)}</Text>
      ),
    },
  ]

  // 汇总统计行
  const summaryStats = [
    {
      title: '总调用次数',
      value: repoTotal.call_count,
      color: '#1677ff',
      icon: <ThunderboltOutlined />,
    },
    ...(billingModel === 'per_token' ? [{
      title: '总 Tokens',
      value: repoTotal.total_tokens,
      color: '#722ed1',
      icon: <BarChartOutlined />,
    }] : []),
    {
      title: '总费用',
      value: Math.abs(repoTotal.total_cost || 0),
      color: '#ff4d4f',
      icon: null,
      precision: billingModel === 'per_token' ? 4 : 2,
    },
  ]

  // Tab 配置
  const tabItems = [
    {
      key: 'repo',
      label: (
        <span>
          <ProjectOutlined />
          按仓库
        </span>
      ),
      children: (
        <>
          {/* 汇总统计 */}
          <Row gutter={16} style={{ marginBottom: 16 }}>
            {summaryStats.map((stat, index) => (
              <Col span={billingModel === 'per_token' ? 8 : 12} key={index}>
                <Card className={styles.summaryCard} style={{ borderTop: `3px solid ${stat.color}` }}>
                  <div className={styles.statItem}>
                    <div className={styles.statLabel}>{stat.title}</div>
                    <div className={styles.statValue} style={{ color: stat.color }}>
                      <span style={{ marginRight: 4 }}>{stat.icon}</span>
                      {stat.title === '总费用' ? '¥' : ''}{stat.value?.toLocaleString() ?? 0}
                    </div>
                  </div>
                </Card>
              </Col>
            ))}
          </Row>
          {/* 仓库列表 */}
          {repoSummary.length > 0 ? (
            isMobile ? (
              // 移动端：卡片列表
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {repoSummary.map((repo) => {
                  const percent = repoTotal.call_count > 0
                    ? (repo.call_count / repoTotal.call_count) * 100
                    : 0
                  return (
                    <Card key={repo.repo_id} size="small" style={{ borderRadius: 8, boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }} bodyStyle={{ padding: 12 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
                        <Tag color="blue" style={{ marginInlineEnd: 0 }}>{repo.repo_name}</Tag>
                        <Tag icon={BILLING_MODEL_CONFIG[repo.billing_model].icon}
                          color={repo.billing_model === 'per_call' ? 'blue' :
                                 repo.billing_model === 'per_token' ? 'purple' : 'gold'}>
                          {BILLING_MODEL_CONFIG[repo.billing_model].label}
                        </Tag>
                      </div>
                      <div style={{ fontSize: 12, color: '#666', marginBottom: 8 }}>
                        <div>调用次数：<Text strong>{repo.call_count?.toLocaleString() || 0}</Text> 次</div>
                        {billingModel === 'per_token' && (
                          <div>Tokens：<Text>{(repo.total_tokens || 0).toLocaleString()}</Text></div>
                        )}
                        <div>费用：<Text type="danger" strong>¥{Math.abs(repo.total_cost || 0).toFixed(billingModel === 'per_token' ? 4 : 2)}</Text></div>
                        <div style={{ marginTop: 8 }}>
                          <Progress percent={percent} size="small" format={() => `${percent.toFixed(1)}%`} strokeColor={percent > 50 ? '#1677ff' : '#52c41a'} />
                        </div>
                      </div>
                    </Card>
                  )
                })}
              </div>
            ) : (
              // 桌面端：表格
              <Table
                columns={repoColumns}
                dataSource={repoSummary}
                rowKey="repo_id"
                pagination={false}
                size="small"
              />
            )
          ) : (
            <Empty description="暂无仓库使用数据" />
          )}
        </>
      ),
    },
    {
      key: 'endpoint',
      label: (
        <span>
          <UnorderedListOutlined />
          按接口
        </span>
      ),
      children: (
        <>
          {/* 筛选器 */}
          <div className={styles.filters} style={{ marginBottom: 16 }}>
            <Space>
              <Select
                placeholder="选择仓库"
                allowClear
                style={{ width: 200 }}
                value={selectedRepo}
                onChange={handleRepoChange}
                options={repoSummary.map(r => ({ label: r.repo_name, value: r.repo_id }))}
              />
              <RangePicker onChange={handleDateChange} />
              <Button type="primary" icon={<SearchOutlined />} onClick={handleSearch}>
                查询
              </Button>
              <Button icon={<ReloadOutlined />} onClick={handleReset}>
                重置
              </Button>
            </Space>
          </div>
          {/* 接口列表 */}
          {endpointSummary.length > 0 ? (
            isMobile ? (
              // 移动端：卡片列表
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {endpointSummary.map((endpoint) => (
                  <Card key={endpoint.endpoint} size="small" style={{ borderRadius: 8, boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }} bodyStyle={{ padding: 12 }}>
                    <div style={{ marginBottom: 8 }}>
                      <Tag color="green" style={{ marginInlineEnd: 0 }}>{endpoint.repo_name}</Tag>
                    </div>
                    <Text code style={{ fontSize: 11, display: 'block', marginBottom: 8 }}>{endpoint.endpoint || '-'}</Text>
                    <div style={{ fontSize: 12, color: '#666' }}>
                      <div>调用次数：<Text strong>{endpoint.call_count?.toLocaleString() || 0}</Text> 次</div>
                      {billingModel === 'per_token' && (
                        <div>Tokens：<Text>{(endpoint.total_tokens || 0).toLocaleString()}</Text></div>
                      )}
                      <div>费用：<Text type="danger">¥{Math.abs(endpoint.total_cost || 0).toFixed(billingModel === 'per_token' ? 4 : 2)}</Text></div>
                    </div>
                  </Card>
                ))}
              </div>
            ) : (
              // 桌面端：表格
              <Table
                columns={endpointColumns}
                dataSource={endpointSummary}
                rowKey="endpoint"
                pagination={{ pageSize: 10, showTotal: (total) => `共 ${total} 个接口` }}
                size="small"
              />
            )
          ) : (
            <Empty description="暂无接口使用数据，请先点击查询" />
          )}
        </>
      ),
    },
    {
      key: 'detail',
      label: (
        <span>
          <CalendarOutlined />
          按日期
        </span>
      ),
      children: (
        <>
          {/* 筛选器 */}
          <div className={styles.filters} style={{ marginBottom: 16 }}>
            <Space>
              <RangePicker onChange={handleDateChange} />
              <Button type="primary" icon={<SearchOutlined />} onClick={handleSearch}>
                查询
              </Button>
              <Button icon={<ReloadOutlined />} onClick={handleReset}>
                重置
              </Button>
            </Space>
          </div>
          {/* 日期列表 */}
          {isMobile ? (
            // 移动端：卡片列表
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {dailySummary.map((day) => (
                <Card key={day.date} size="small" style={{ borderRadius: 8, boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }} bodyStyle={{ padding: 12 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
                    <Badge color="#1677ff" text={day.date} />
                  </div>
                  <div style={{ fontSize: 12, color: '#666' }}>
                    <div>调用次数：<Text strong>{day.call_count?.toLocaleString() || 0}</Text> 次</div>
                    {billingModel === 'per_token' && (
                      <div>Tokens：<Text>{(day.total_tokens || 0).toLocaleString()}</Text></div>
                    )}
                    <div>费用：<Text type="danger" strong>¥{Math.abs(day.total_cost || 0).toFixed(billingModel === 'per_token' ? 4 : 2)}</Text></div>
                  </div>
                </Card>
              ))}
            </div>
          ) : (
            // 桌面端：表格
            <Table
              columns={dailyColumns}
              dataSource={dailySummary}
              rowKey="date"
              pagination={{ pageSize: 10, showTotal: (total) => `共 ${total} 天` }}
              size="small"
            />
          )}
        </>
      ),
    },
  ]

  return (
    <div className={`${styles.container} bamboo-bg-pattern`}>
      <Card
        title={
          <Space>
            <BarChartOutlined />
            <span>消费明细</span>
          </Space>
        }
        extra={
          <Space>
            <Text type="secondary">计费模式：</Text>
            <Tag icon={BILLING_MODEL_CONFIG[billingModel].icon} 
                 color={billingModel === 'per_call' ? 'blue' : 
                        billingModel === 'per_token' ? 'purple' : 'gold'}>
              {BILLING_MODEL_CONFIG[billingModel].label}
            </Tag>
          </Space>
        }
      >
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={tabItems}
        />
      </Card>

      {/* 实时调用明细 */}
      {activeTab === 'detail' && (
        <Card title="实时调用明细" style={{ marginTop: 16 }}>
          {isMobile ? (
            // 移动端：卡片列表
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {details.map((detail) => (
                <Card key={detail.id} size="small" style={{ borderRadius: 8, boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }} bodyStyle={{ padding: 12 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                    <Tag color="blue" style={{ marginInlineEnd: 0 }}>{detail.repo_name || '未知'}</Tag>
                    <Text code style={{ fontSize: 10 }}>{detail.endpoint?.substring(0, 20)}...</Text>
                  </div>
                  <div style={{ fontSize: 12, color: '#666' }}>
                    <div>时间：{detail.created_at ? new Date(detail.created_at).toLocaleString() : '-'}</div>
                    <div>调用者：<Tag color="purple" style={{ marginInlineEnd: 0 }}>{detail.tester || '-'}</Tag></div>
                    {billingModel === 'per_token' && (
                      <div>Tokens：<Text style={{ color: '#722ed1' }}>{(detail.tokens_used || 0).toLocaleString()}</Text></div>
                    )}
                    <div>费用：<Text type="danger">¥{Math.abs(detail.cost || 0).toFixed(billingModel === 'per_token' ? 4 : 2)}</Text></div>
                  </div>
                </Card>
              ))}
            </div>
          ) : (
            // 桌面端：表格
            <Table
              columns={detailColumns}
              dataSource={details}
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
            />
          )}
        </Card>
      )}
    </div>
  )
}

export default ConsumptionDetails
