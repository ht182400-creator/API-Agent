/**
 * 「仓库收入明细」弹窗 —— P1-4 巨型组件拆分（纯搬运，零行为改变）
 *
 * 由 `../Analytics.tsx` 抽出（原占约 214 行，是页面里最大的一块）。内容：
 *   ① 基本信息（仓库ID / Slug / 状态 / 创建时间）
 *   ② 汇总统计（总调用 / 成功 / 失败 / 总收入）
 *   ③ 成功率进度条
 *   ④ 趋势分析（天数选择 + 折线图 + 明细表格）
 *   ⑤ 数据更新时间
 *
 * ⚠️ 第 ④ 块的折线图与「概览」「趋势分析」Tab 的写法高度重复，
 *    连同 `buildRepoTrendChartData` 一起，后续可提为共用的 `TrendChart`。
 *
 * ✅ 已清理：`styles={{ body: { padding: 12 } }}` 已改为 `styles={{ body: { padding: 12 } }}`
 *    （antd v5 已废弃 `bodyStyle`，控制台会提示改用 `styles.body`）。视觉表现不变。
 */
import {
  Card,
  Col,
  Descriptions,
  Divider,
  Modal,
  Progress,
  Row,
  Select,
  Space,
  Spin,
  Statistic,
  Table,
  Tag,
  Typography,
} from 'antd'
import { LineChartOutlined } from '@ant-design/icons'
import {
  Line,
  LineChart,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'
import type { RepoDetailItem, RepoTrendData } from '../../../api/adminAnalytics'
import { TREND_DAYS_OPTIONS, statusColors, statusText } from './constants'
import { buildRepoTrendChartData } from './chartData'

const { Text } = Typography

export interface RepoDetailModalProps {
  open: boolean
  onClose: () => void
  loading: boolean
  repo: RepoDetailItem | null
  trendData: RepoTrendData | null
  days: number
  onDaysChange: (days: number) => void
}

export function RepoDetailModal({
  open,
  onClose,
  loading,
  repo,
  trendData,
  days,
  onDaysChange,
}: RepoDetailModalProps) {
  return (
    <Modal
      title={
        <Space>
          <LineChartOutlined />
          <span style={{ fontSize: 14 }}>仓库收入明细</span>
        </Space>
      }
      open={open}
      onCancel={onClose}
      footer={null}
      width="95%"
      style={{ maxWidth: 900 }}
      destroyOnHidden
    >
      <Spin spinning={loading}>
        {/* 基本信息 */}
        {repo && (
          <Descriptions
            size="small"
            column={{ xs: 1, sm: 2, md: 4 }}
            bordered
            style={{ marginBottom: 16 }}
          >
            <Descriptions.Item label="仓库ID">
              <Text code style={{ fontSize: 12 }}>
                {repo.repo_id}
              </Text>
            </Descriptions.Item>
            <Descriptions.Item label="Slug">
              <Text code style={{ fontSize: 12 }}>
                {repo.slug}
              </Text>
            </Descriptions.Item>
            <Descriptions.Item label="状态">
              <Tag color={statusColors[repo.status] || 'default'}>
                {statusText[repo.status] || repo.status}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="创建时间">
              <Text type="secondary" style={{ fontSize: 12 }}>
                {repo.created_at ? new Date(repo.created_at).toLocaleString('zh-CN') : '-'}
              </Text>
            </Descriptions.Item>
          </Descriptions>
        )}

        {/* 汇总统计 */}
        <Row gutter={[8, 8]} style={{ marginBottom: 16 }}>
          <Col xs={12} sm={12} md={6}>
            <Card size="small" styles={{ body: { padding: 12 } }}>
              <Statistic
                title="总调用"
                value={repo?.total_calls || 0}
                valueStyle={{ color: '#059669', fontSize: 18 }}
              />
            </Card>
          </Col>
          <Col xs={12} sm={12} md={6}>
            <Card size="small" styles={{ body: { padding: 12 } }}>
              <Statistic
                title="成功"
                value={repo?.success_calls || 0}
                valueStyle={{ color: '#52c41a', fontSize: 18 }}
              />
            </Card>
          </Col>
          <Col xs={12} sm={12} md={6}>
            <Card size="small" styles={{ body: { padding: 12 } }}>
              <Statistic
                title="失败"
                value={repo?.failed_calls || 0}
                valueStyle={{ color: '#ff4d4f', fontSize: 18 }}
              />
            </Card>
          </Col>
          <Col xs={12} sm={12} md={6}>
            <Card size="small" styles={{ body: { padding: 12 } }}>
              <Statistic
                title="总收入"
                value={repo?.total_cost || 0}
                prefix="¥"
                precision={2}
                valueStyle={{ color: '#faad14', fontSize: 18 }}
              />
            </Card>
          </Col>
        </Row>

        {/* 成功率 */}
        <Card size="small" style={{ marginBottom: 16 }}>
          <Space>
            <span>成功率：</span>
            <Progress
              percent={repo?.success_rate || 0}
              format={(p) => `${p?.toFixed(1)}%`}
              strokeColor={{ '0%': '#ff4d4f', '50%': '#faad14', '100%': '#52c41a' }}
              style={{ width: 200 }}
            />
            <Text type="secondary">
              (成功 {repo?.success_calls || 0} / 失败 {repo?.failed_calls || 0})
            </Text>
          </Space>
        </Card>

        <Divider />

        {/* 趋势图表 */}
        <Card
          title="趋势分析"
          extra={
            <Select
              value={days}
              onChange={onDaysChange}
              style={{ width: 120 }}
              options={TREND_DAYS_OPTIONS}
            />
          }
        >
          {trendData ? (
            <>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={buildRepoTrendChartData(trendData)}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="time" tick={{ fontSize: 12 }} />
                  <YAxis
                    yAxisId="left"
                    tick={{ fontSize: 12 }}
                    tickFormatter={(v) => (v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v)}
                  />
                  <YAxis
                    yAxisId="right"
                    orientation="right"
                    tick={{ fontSize: 12 }}
                    tickFormatter={(v) => `¥${v.toFixed(0)}`}
                  />
                  <RechartsTooltip
                    formatter={(value: number, name: string) => [
                      name === 'calls'
                        ? `${value.toLocaleString()} 次`
                        : name === 'revenue'
                          ? `¥${value.toFixed(2)}`
                          : `${value.toFixed(0)}ms`,
                      name === 'calls' ? '调用次数' : name === 'revenue' ? '收入' : '平均延迟',
                    ]}
                  />
                  <Legend />
                  <Line
                    yAxisId="left"
                    type="monotone"
                    dataKey="calls"
                    stroke="#10b981"
                    strokeWidth={2}
                    dot={{ r: 3 }}
                    name="调用次数"
                  />
                  <Line
                    yAxisId="right"
                    type="monotone"
                    dataKey="revenue"
                    stroke="#faad14"
                    strokeWidth={2}
                    dot={{ r: 3 }}
                    name="收入"
                  />
                </LineChart>
              </ResponsiveContainer>

              {/* 数据表格 */}
              <Table
                dataSource={trendData.labels
                  .map((label, index) => ({
                    key: index,
                    time: label,
                    calls: trendData.series.calls[index] || 0,
                    revenue: trendData.series.revenue[index] || 0,
                  }))
                  .reverse()}
                columns={[
                  { title: '日期', dataIndex: 'time', key: 'time', width: 100 },
                  {
                    title: '调用次数',
                    dataIndex: 'calls',
                    key: 'calls',
                    width: 100,
                    render: (v: number) => v.toLocaleString(),
                  },
                  {
                    title: '收入',
                    dataIndex: 'revenue',
                    key: 'revenue',
                    width: 80,
                    render: (v: number) => `¥${v.toFixed(2)}`,
                  },
                ]}
                pagination={false}
                size="small"
                scroll={{ x: 'max-content' }}
                tableLayout="fixed"
                style={{ marginTop: 16 }}
              />
            </>
          ) : (
            <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>暂无趋势数据</div>
          )}
        </Card>

        {/* 更新时间 */}
        {trendData && (
          <div style={{ marginTop: 12, textAlign: 'right' }}>
            <Text type="secondary" style={{ fontSize: 12 }}>
              数据更新时间: {new Date(trendData.generated_at).toLocaleString('zh-CN')}
            </Text>
          </div>
        )}
      </Spin>
    </Modal>
  )
}
