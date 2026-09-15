/**
 * 「限流配置」Tab —— P1-4 巨型组件拆分（纯搬运，零行为改变）
 *
 * 由 `../Repos.tsx` 抽出（原占约 100 行）。只依赖 3 项：`limits` / `onChange` / `onSave`
 * → 是三个 Tab（基本信息 / 端点配置 / 限流配置）里依赖最松的一个，故先切。
 *
 * ⚠️ 本组件内含 `Form.Item`，**必须被渲染在 `<Form>` 内部**（父组件已经这么做）。
 *    若将来单独使用，需自行包一层 Form 或改用普通 `Row` 布局。
 *
 * ⚠️ 7 个数字输入目前是**逐字重复**的写法（label/value/onChange/placeholder 各一遍），
 *    后续可用一个字段配置数组 + `map` 生成，能砍掉约 60 行。
 *    本次是纯搬运，不做夹带重构 —— 留待单独一轮。
 */
import { Alert, Button, Col, Form, Input, Row } from 'antd'
import { UpdateLimitsRequest } from '../../../api/repo'

export interface LimitsTabProps {
  limits: UpdateLimitsRequest
  onChange: (next: UpdateLimitsRequest) => void
  onSave: () => void
}

export function LimitsTab({ limits, onChange, onSave }: LimitsTabProps) {
  return (
    <div>
      <Alert
        message="限流配置说明"
        description="设置API的访问频率限制，保护您的服务不被过度调用"
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />

      <Row gutter={16}>
        <Col span={12}>
          <Form.Item label="每分钟请求数 (RPM)">
            <Input
              type="number"
              value={limits.rpm}
              onChange={(e) => onChange({ ...limits, rpm: parseInt(e.target.value) || 0 })}
              placeholder="1000"
            />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item label="每小时请求数 (RPH)">
            <Input
              type="number"
              value={limits.rph}
              onChange={(e) => onChange({ ...limits, rph: parseInt(e.target.value) || 0 })}
              placeholder="10000"
            />
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={12}>
          <Form.Item label="每日请求数 (RPD)">
            <Input
              type="number"
              value={limits.rpd}
              onChange={(e) => onChange({ ...limits, rpd: parseInt(e.target.value) || 0 })}
              placeholder="100000"
            />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item label="突发限制">
            <Input
              type="number"
              value={limits.burst_limit}
              onChange={(e) => onChange({ ...limits, burst_limit: parseInt(e.target.value) || 0 })}
              placeholder="100"
            />
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={12}>
          <Form.Item label="并发限制">
            <Input
              type="number"
              value={limits.concurrent_limit}
              onChange={(e) =>
                onChange({ ...limits, concurrent_limit: parseInt(e.target.value) || 0 })
              }
              placeholder="10"
            />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item label="请求超时 (秒)">
            <Input
              type="number"
              value={limits.request_timeout}
              onChange={(e) => onChange({ ...limits, request_timeout: parseInt(e.target.value) || 0 })}
              placeholder="30"
            />
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={12}>
          <Form.Item label="连接超时 (秒)">
            <Input
              type="number"
              value={limits.connect_timeout}
              onChange={(e) => onChange({ ...limits, connect_timeout: parseInt(e.target.value) || 0 })}
              placeholder="10"
            />
          </Form.Item>
        </Col>
        <Col span={12}>
          <div style={{ paddingTop: 4 }}>
            <Button type="primary" onClick={onSave}>
              保存限流配置
            </Button>
          </div>
        </Col>
      </Row>
    </div>
  )
}
