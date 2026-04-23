/**
 * 仓库市场页面 - 开发者视角
 * 展示所有可用的API仓库
 */

import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Row, Col, Input, Select, Tag, Button, Empty, Spin, Typography, Space, Statistic, Tooltip, Badge, Alert } from 'antd'
import { SearchOutlined, ApiOutlined, ThunderboltOutlined, DollarOutlined, EyeOutlined, RocketOutlined } from '@ant-design/icons'
import { repoApi, Repository } from '../../api/repo'
import { useError } from '../../contexts/ErrorContext'
import { useAuthStore } from '../../stores/auth'
import styles from './Repos.module.css'

const { Title, Text, Paragraph } = Typography

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

export default function Repos() {
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const [repos, setRepos] = useState<Repository[]>([])
  const [loading, setLoading] = useState(true)
  const [searchText, setSearchText] = useState('')
  const [typeFilter, setTypeFilter] = useState<string | undefined>()
  const { showError } = useError()
  
  // 判断是否是普通用户（不是开发者）
  const isNormalUser = user?.user_type === 'user'

  useEffect(() => {
    fetchRepos()
  }, [typeFilter])

  const fetchRepos = async () => {
    setLoading(true)
    try {
      const data = await repoApi.list({
        page: 1,
        page_size: 100,
        type: typeFilter
      })
      setRepos(data.items)
    } catch (error: any) {
      showError(error, fetchRepos)
    } finally {
      setLoading(false)
    }
  }

  // 过滤仓库
  const filteredRepos = repos.filter(repo => {
    const searchLower = searchText.toLowerCase()
    return (
      repo.name.toLowerCase().includes(searchLower) ||
      repo.display_name?.toLowerCase().includes(searchLower) ||
      repo.description?.toLowerCase().includes(searchLower)
    )
  })

  // 跳转到仓库详情
  const goToRepoDetail = (slug: string) => {
    navigate(`/developer/repos/${slug}`)
  }

  if (loading) {
    return (
      <div className={styles.loading}>
        <Spin size="large" tip="加载仓库列表..." />
      </div>
    )
  }

  return (
    <div className={styles.container}>
      {/* 普通用户升级引导 */}
      {isNormalUser && (
        <Alert
          type="info"
          showIcon
          icon={<RocketOutlined />}
          message="升级为开发者，解锁更多功能"
          description="成为开发者后，您可以创建API Keys、调用API、查看使用统计等功能。"
          action={
            <Button type="primary" size="small" onClick={() => navigate('/user')}>
              前往升级
            </Button>
          }
          style={{ marginBottom: 16 }}
        />
      )}
      {/* 页面标题和统计 */}
      <div className={styles.header}>
        <div>
          <Title level={3} style={{ marginBottom: 4 }}>API仓库市场</Title>
          <Text type="secondary">浏览和发现可用的API服务</Text>
        </div>
        <Row gutter={16} className={styles.statsRow}>
          <Col>
            <Statistic title="可用仓库" value={repos.length} prefix={<ApiOutlined />} />
          </Col>
          <Col>
            <Statistic 
              title="API端点" 
              value={repos.reduce((acc, repo) => acc + (repo.endpoints?.length || 0), 0)} 
              prefix={<ThunderboltOutlined />} 
            />
          </Col>
        </Row>
      </div>

      {/* 筛选器 */}
      <Card className={styles.filterCard}>
        <Space size="large" wrap>
          <Input
            placeholder="搜索仓库名称、描述..."
            prefix={<SearchOutlined />}
            style={{ width: 280 }}
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            allowClear
          />
          <Select
            placeholder="筛选类型"
            style={{ width: 160 }}
            allowClear
            value={typeFilter}
            onChange={setTypeFilter}
          >
            <Select.Option value="psychology">心理问答</Select.Option>
            <Select.Option value="translation">翻译服务</Select.Option>
            <Select.Option value="vision">图像识别</Select.Option>
            <Select.Option value="stock">股票行情</Select.Option>
            <Select.Option value="ai">AI服务</Select.Option>
          </Select>
        </Space>
      </Card>

      {/* 仓库列表 */}
      {filteredRepos.length === 0 ? (
        <Empty description="暂无仓库" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      ) : (
        <Row gutter={[16, 16]}>
          {filteredRepos.map((repo) => (
            <Col xs={24} sm={12} lg={8} xl={6} key={repo.id}>
              <Card 
                className={styles.repoCard}
                hoverable
                onClick={() => goToRepoDetail(repo.slug)}
                actions={[
                  <Tooltip title="查看详情" key="view">
                    <Button type="text" icon={<EyeOutlined />} onClick={(e) => { e.stopPropagation(); goToRepoDetail(repo.slug) }}>
                      查看详情
                    </Button>
                  </Tooltip>
                ]}
              >
                {/* 卡片头部 - Logo和名称 */}
                <div className={styles.cardHeader}>
                  <div className={styles.repoLogo}>
                    {repo.display_name?.charAt(0) || repo.name.charAt(0).toUpperCase()}
                  </div>
                  <div className={styles.repoInfo}>
                    <Text strong className={styles.repoName}>
                      {repo.display_name || repo.name}
                    </Text>
                    <Space size={4}>
                      <Tag color={repo.status === 'online' ? 'green' : 'orange'} style={{ margin: 0 }}>
                        {repo.status === 'online' ? '已上线' : '未上线'}
                      </Tag>
                      <Text type="secondary" className={styles.repoType}>{repo.type}</Text>
                    </Space>
                  </div>
                </div>

                {/* 描述 */}
                {repo.description && (
                  <Paragraph className={styles.description} ellipsis={{ rows: 2 }}>
                    {repo.description}
                  </Paragraph>
                )}

                {/* 端点预览 */}
                <div className={styles.endpointsPreview}>
                  <Text type="secondary" className={styles.endpointsLabel}>
                    <ApiOutlined /> API端点 ({repo.endpoints?.length || 0})
                  </Text>
                  <div className={styles.endpointTags}>
                    {repo.endpoints?.slice(0, 3).map((ep, idx) => (
                      <Tag key={idx} color={getMethodColor(ep.method)} className={styles.endpointTag}>
                        {ep.method} {ep.path}
                      </Tag>
                    ))}
                    {repo.endpoints && repo.endpoints.length > 3 && (
                      <Tag>+{repo.endpoints.length - 3}</Tag>
                    )}
                  </div>
                </div>

                {/* 底部信息 */}
                <div className={styles.cardFooter}>
                  <Tooltip title={`限流: ${repo.limits?.rpm || 1000} 次/分钟`}>
                    <div className={styles.footerItem}>
                      <ThunderboltOutlined />
                      <Text>{repo.limits?.rpm || 1000}/分</Text>
                    </div>
                  </Tooltip>
                  {repo.pricing && (
                    <Tooltip title={`${repo.pricing.type === 'free' ? '免费' : `${repo.pricing.price_per_token || repo.pricing.price_per_call}元/次`}`}>
                      <div className={styles.footerItem}>
                        <DollarOutlined />
                        <Text>
                          {repo.pricing.type === 'free' ? '免费' : '付费'}
                        </Text>
                      </div>
                    </Tooltip>
                  )}
                </div>
              </Card>
            </Col>
          ))}
        </Row>
      )}
    </div>
  )
}
