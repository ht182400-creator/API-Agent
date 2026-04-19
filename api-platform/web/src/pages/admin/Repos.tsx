/**
 * 管理员仓库管理页面
 * 功能：审核仓库、上线/下线管理
 */

import { Table, Tag, Button, Space, Modal, Input, message, Statistic, Card, Row, Col } from 'antd'
import { CheckCircleOutlined, CloseCircleOutlined, ArrowUpOutlined, ArrowDownOutlined, ExclamationCircleOutlined } from '@ant-design/icons'
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { repoApi, Repository } from '../../api/repo'
import styles from './Repos.module.css'

const { TextArea } = Input

export default function AdminRepos() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [repos, setRepos] = useState<Repository[]>([])
  const [pagination, setPagination] = useState({ page: 1, page_size: 20, total: 0 })
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined)
  
  // 审核弹窗
  const [approveModalVisible, setApproveModalVisible] = useState(false)
  const [rejectModalVisible, setRejectModalVisible] = useState(false)
  const [selectedRepo, setSelectedRepo] = useState<Repository | null>(null)
  const [comment, setComment] = useState('')
  const [actionLoading, setActionLoading] = useState(false)

  // 统计数据
  const [stats, setStats] = useState({
    pending: 0,
    approved: 0,
    online: 0,
    offline: 0,
    rejected: 0,
  })

  // 加载仓库列表
  const loadRepos = async () => {
    setLoading(true)
    try {
      const res = await repoApi.adminList({
        status: statusFilter,
        page: pagination.page,
        page_size: pagination.page_size,
      })
      // API 拦截器已提取 data 字段，直接使用
      setRepos(res.items || [])
      setPagination(prev => ({
        ...prev,
        total: res.pagination?.total || 0,
      }))
    } catch (err: any) {
      console.error('加载仓库列表失败', err)
      message.error(err.userMessage || err.message || '加载失败')
    } finally {
      setLoading(false)
    }
  }

  // 加载统计数据
  const loadStats = async () => {
    try {
      const statuses = ['pending', 'approved', 'online', 'offline', 'rejected']
      const newStats = { ...stats }
      
      for (const status of statuses) {
        const res = await repoApi.adminList({ status, page: 1, page_size: 1 })
        // API 拦截器已提取 data 字段，直接使用
        newStats[status as keyof typeof stats] = res.pagination?.total || 0
      }
      
      setStats(newStats)
    } catch (err) {
      console.error('加载统计失败', err)
    }
  }

  useEffect(() => {
    loadRepos()
    loadStats()
  }, [statusFilter, pagination.page])

  // 审核通过
  const handleApprove = async () => {
    if (!selectedRepo) return
    setActionLoading(true)
    try {
      await repoApi.adminApprove(selectedRepo.id, { comment })
      message.success('审核通过成功')
      setApproveModalVisible(false)
      setSelectedRepo(null)
      setComment('')
      loadRepos()
      loadStats()
    } catch (err: any) {
      message.error(err.userMessage || err.message || '操作失败')
    } finally {
      setActionLoading(false)
    }
  }

  // 审核拒绝
  const handleReject = async () => {
    if (!selectedRepo) return
    setActionLoading(true)
    try {
      await repoApi.adminReject(selectedRepo.id, { reason: comment })
      message.success('已拒绝该仓库')
      setRejectModalVisible(false)
      setSelectedRepo(null)
      setComment('')
      loadRepos()
      loadStats()
    } catch (err: any) {
      message.error(err.userMessage || err.message || '操作失败')
    } finally {
      setActionLoading(false)
    }
  }

  // 上线
  const handleOnline = async (repo: Repository) => {
    Modal.confirm({
      title: '确认上线',
      icon: <ExclamationCircleOutlined />,
      content: `确定要上线仓库 "${repo.display_name || repo.name}" 吗？`,
      okText: '确认上线',
      cancelText: '取消',
      onOk: async () => {
        try {
          await repoApi.adminOnline(repo.id)
          message.success('仓库已上线')
          loadRepos()
          loadStats()
        } catch (err: any) {
          message.error(err.userMessage || err.message || '操作失败')
        }
      },
    })
  }

  // 下线
  const handleOffline = async (repo: Repository) => {
    Modal.confirm({
      title: '确认下线',
      icon: <ExclamationCircleOutlined />,
      content: `确定要下线仓库 "${repo.display_name || repo.name}" 吗？`,
      okText: '确认下线',
      cancelText: '取消',
      onOk: async () => {
        try {
          await repoApi.adminOffline(repo.id)
          message.success('仓库已下线')
          loadRepos()
          loadStats()
        } catch (err: any) {
          message.error(err.userMessage || err.message || '操作失败')
        }
      },
    })
  }

  // 查看详情
  const handleViewDetail = (repo: Repository) => {
    navigate(`/repo/${repo.slug}`)
  }

  // 状态标签
  const getStatusTag = (status: string) => {
    const statusMap: Record<string, { color: string; text: string }> = {
      pending: { color: 'orange', text: '待审核' },
      approved: { color: 'blue', text: '已审核' },
      rejected: { color: 'red', text: '已拒绝' },
      online: { color: 'green', text: '已上线' },
      offline: { color: 'default', text: '已下线' },
    }
    const config = statusMap[status] || { color: 'default', text: status }
    return <Tag color={config.color}>{config.text}</Tag>
  }

  const columns = [
    {
      title: '仓库名称',
      dataIndex: 'display_name',
      key: 'display_name',
      render: (_: any, record: Repository) => (
        <div>
          <div style={{ fontWeight: 500 }}>{record.display_name || record.name}</div>
          <div style={{ color: '#999', fontSize: 12 }}>{record.name}</div>
        </div>
      ),
    },
    {
      title: '所有者',
      dataIndex: ['owner', 'name'],
      key: 'owner',
      width: 120,
    },
    {
      title: '分类',
      dataIndex: 'type',
      key: 'type',
      width: 100,
      render: (type: string) => {
        const typeMap: Record<string, string> = {
          psychology: '心理',
          stock: '股票',
          ai: 'AI',
          translation: '翻译',
          vision: '视觉',
          custom: '自定义',
        }
        return <Tag>{typeMap[type] || type}</Tag>
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: getStatusTag,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 170,
      render: (time: string) => time ? new Date(time).toLocaleString('zh-CN') : '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 280,
      fixed: 'right' as const,
      render: (_: any, record: Repository) => {
        const actions = []
        
        // 待审核状态 - 可以批准或拒绝
        if (record.status === 'pending') {
          actions.push(
            <Button
              key="approve"
              type="link"
              size="small"
              icon={<CheckCircleOutlined />}
              onClick={() => {
                setSelectedRepo(record)
                setApproveModalVisible(true)
              }}
            >
              通过
            </Button>,
            <Button
              key="reject"
              type="link"
              size="small"
              danger
              icon={<CloseCircleOutlined />}
              onClick={() => {
                setSelectedRepo(record)
                setRejectModalVisible(true)
              }}
            >
              拒绝
            </Button>
          )
        }
        
        // 已审核状态 - 可以上线
        if (record.status === 'approved') {
          actions.push(
            <Button
              key="online"
              type="link"
              size="small"
              icon={<ArrowUpOutlined />}
              onClick={() => handleOnline(record)}
            >
              上线
            </Button>
          )
        }
        
        // 已上线状态 - 可以下线
        if (record.status === 'online') {
          actions.push(
            <Button
              key="offline"
              type="link"
              size="small"
              danger
              icon={<ArrowDownOutlined />}
              onClick={() => handleOffline(record)}
            >
              下线
            </Button>
          )
        }
        
        // 已拒绝状态 - 可以重新审核
        if (record.status === 'rejected') {
          actions.push(
            <Button
              key="re-approve"
              type="link"
              size="small"
              icon={<CheckCircleOutlined />}
              onClick={() => {
                setSelectedRepo(record)
                setApproveModalVisible(true)
              }}
            >
              重新审核
            </Button>
          )
        }
        
        // 已下线状态 - 可以上线
        if (record.status === 'offline') {
          actions.push(
            <Button
              key="re-online"
              type="link"
              size="small"
              icon={<ArrowUpOutlined />}
              onClick={() => handleOnline(record)}
            >
              上线
            </Button>
          )
        }
        
        // 详情按钮
        actions.push(
          <Button
            key="detail"
            type="link"
            size="small"
            onClick={() => handleViewDetail(record)}
          >
            详情
          </Button>
        )
        
        return <Space size="small">{actions}</Space>
      },
    },
  ]

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h2>仓库管理</h2>
        <div style={{ marginBottom: 16 }}>
          <Space wrap>
            <Button onClick={() => setStatusFilter(undefined)} type={!statusFilter ? 'primary' : 'default'}>
              全部 ({stats.pending + stats.approved + stats.online + stats.offline + stats.rejected})
            </Button>
            <Button onClick={() => setStatusFilter('pending')} type={statusFilter === 'pending' ? 'primary' : 'default'}>
              待审核 ({stats.pending})
            </Button>
            <Button onClick={() => setStatusFilter('approved')} type={statusFilter === 'approved' ? 'primary' : 'default'}>
              已审核 ({stats.approved})
            </Button>
            <Button onClick={() => setStatusFilter('online')} type={statusFilter === 'online' ? 'primary' : 'default'}>
              已上线 ({stats.online})
            </Button>
            <Button onClick={() => setStatusFilter('offline')} type={statusFilter === 'offline' ? 'primary' : 'default'}>
              已下线 ({stats.offline})
            </Button>
            <Button onClick={() => setStatusFilter('rejected')} type={statusFilter === 'rejected' ? 'primary' : 'default'}>
              已拒绝 ({stats.rejected})
            </Button>
          </Space>
        </div>
      </div>

      <Table
        dataSource={repos}
        columns={columns}
        rowKey="id"
        loading={loading}
        pagination={{
          current: pagination.page,
          pageSize: pagination.page_size,
          total: pagination.total,
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (total) => `共 ${total} 条`,
          onChange: (page, pageSize) => {
            setPagination({ ...pagination, page, page_size: pageSize })
          },
        }}
        scroll={{ x: 1000 }}
      />

      {/* 审核通过弹窗 */}
      <Modal
        title="审核通过"
        open={approveModalVisible}
        onOk={handleApprove}
        onCancel={() => {
          setApproveModalVisible(false)
          setSelectedRepo(null)
          setComment('')
        }}
        confirmLoading={actionLoading}
        okText="确认通过"
        cancelText="取消"
      >
        <div style={{ marginBottom: 16 }}>
          <p>
            确认通过仓库 <strong>{selectedRepo?.display_name || selectedRepo?.name}</strong> 的审核？
          </p>
        </div>
        <div>
          <label style={{ display: 'block', marginBottom: 8 }}>备注（可选）</label>
          <TextArea
            rows={3}
            placeholder="输入审核备注..."
            value={comment}
            onChange={(e) => setComment(e.target.value)}
          />
        </div>
      </Modal>

      {/* 审核拒绝弹窗 */}
      <Modal
        title="审核拒绝"
        open={rejectModalVisible}
        onOk={handleReject}
        onCancel={() => {
          setRejectModalVisible(false)
          setSelectedRepo(null)
          setComment('')
        }}
        confirmLoading={actionLoading}
        okText="确认拒绝"
        okButtonProps={{ danger: true }}
        cancelText="取消"
      >
        <div style={{ marginBottom: 16 }}>
          <p>
            确认拒绝仓库 <strong>{selectedRepo?.display_name || selectedRepo?.name}</strong> 的审核？
          </p>
        </div>
        <div>
          <label style={{ display: 'block', marginBottom: 8 }}>拒绝原因（可选）</label>
          <TextArea
            rows={3}
            placeholder="输入拒绝原因，以便仓库所有者了解情况..."
            value={comment}
            onChange={(e) => setComment(e.target.value)}
          />
        </div>
      </Modal>
    </div>
  )
}
