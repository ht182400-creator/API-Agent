/**
 * 数据分析页面
 */

import { useState, useEffect } from 'react'
import { Card, Row, Col, Typography, Space } from 'antd'
import { BarChartOutlined, PieChartOutlined } from '@ant-design/icons'
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Cell } from 'recharts'
import styles from './Analytics.module.css'

const { Title, Text } = Typography

const COLORS = ['#1677ff', '#52c41a', '#faad14', '#ff4d4f', '#722ed1']

export default function OwnerAnalytics() {
  const [loading] = useState(false)

  // 示例数据
  const weeklyData = [
    { date: '周一', calls: 1200, revenue: 120 },
    { date: '周二', calls: 1500, revenue: 150 },
    { date: '周三', calls: 1800, revenue: 180 },
    { date: '周四', calls: 1400, revenue: 140 },
    { date: '周五', calls: 2000, revenue: 200 },
    { date: '周六', calls: 2500, revenue: 250 },
    { date: '周日', calls: 2200, revenue: 220 },
  ]

  const hourlyData = Array.from({ length: 24 }, (_, i) => ({
    hour: `${i}:00`,
    calls: Math.floor(Math.random() * 500) + 100,
  }))

  const sourceData = [
    { name: 'Web', value: 35 },
    { name: 'iOS', value: 25 },
    { name: 'Android', value: 20 },
    { name: 'API', value: 15 },
    { name: '其他', value: 5 },
  ]

  return (
    <div className={styles.container}>
      <Title level={4}>数据分析</Title>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={16}>
          <Card title="调用趋势（本周）" className={styles.chartCard}>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={weeklyData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis yAxisId="left" orientation="left" stroke="#1677ff" />
                <YAxis yAxisId="right" orientation="right" stroke="#52c41a" />
                <Tooltip />
                <Bar yAxisId="left" dataKey="calls" fill="#1677ff" name="调用量" />
                <Line yAxisId="right" type="monotone" dataKey="revenue" stroke="#52c41a" name="收益" />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="调用来源分布" className={styles.pieCard}>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={sourceData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={100}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                >
                  {sourceData.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </Card>
        </Col>
      </Row>

      <Card title="24小时调用分布" className={styles.chartCard}>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={hourlyData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="hour" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="calls" fill="#1677ff" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </Card>
    </div>
  )
}
