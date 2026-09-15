/**
 * 「基本信息」Tab —— P1-4 巨型组件拆分（纯搬运，零行为改变）
 *
 * 由 `../Repos.tsx` 抽出（原占约 87 行）。内容：图标上传/预览 + 6 个表单字段
 * （仓库标识 / 显示名称 / 描述 / 仓库类型 / 协议类型 / API端点地址）。
 *
 * ⚠️ 与 `LimitsTab` 同样**必须在 `<Form>` 内使用**：内容全部是 `Form.Item`，
 *    且字段值由父级 `Form` 的 `form` 实例管理（这里只用 `name` 绑定，不持有状态）。
 *
 * ⚠️ `beforeUpload` 回调的语义不变：返回 `false` 表示"由我们自己处理，不要真的上传"，
 *    `handleLogoChange` 内部走 FileReader 转 base64 后写入表单。
 */
import { Button, Form, Input, Select, Typography, Upload } from 'antd'
import { DeleteOutlined, UploadOutlined } from '@ant-design/icons'

const { Text } = Typography

export interface BasicInfoTabProps {
  /** 当前图标预览（base64 / url）；为空则显示上传按钮 */
  logoPreview: string
  /** 编辑已有仓库时，「仓库标识」不可修改 */
  nameDisabled: boolean
  onLogoChange: (file: File) => boolean
  onRemoveLogo: () => void
}

export function BasicInfoTab({
  logoPreview,
  nameDisabled,
  onLogoChange,
  onRemoveLogo,
}: BasicInfoTabProps) {
  return (
    <>
      {/* 仓库图标上传 */}
      <Form.Item label="仓库图标">
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          {logoPreview ? (
            <div
              style={{
                width: 72,
                height: 72,
                borderRadius: 8,
                overflow: 'hidden',
                border: '1px solid #d1d5db',
                position: 'relative',
              }}
            >
              <img
                src={logoPreview}
                alt="仓库图标预览"
                style={{ width: '100%', height: '100%', objectFit: 'cover' }}
              />
              <Button
                type="text"
                size="small"
                icon={<DeleteOutlined />}
                onClick={onRemoveLogo}
                style={{
                  position: 'absolute',
                  top: 2,
                  right: 2,
                  background: 'rgba(0,0,0,0.5)',
                  color: '#fff',
                  borderRadius: '50%',
                  width: 24,
                  height: 24,
                  minWidth: 24,
                  padding: 0,
                }}
              />
            </div>
          ) : (
            <Upload accept="image/*" showUploadList={false} beforeUpload={onLogoChange}>
              <Button icon={<UploadOutlined />}>上传图标</Button>
            </Upload>
          )}
          {logoPreview && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              点击删除按钮可重新上传
            </Text>
          )}
          {!logoPreview && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              建议 64x64 像素，不超过 200KB
            </Text>
          )}
        </div>
      </Form.Item>

      <Form.Item
        name="name"
        label="仓库标识"
        rules={[{ required: true, message: '请输入仓库标识' }]}
      >
        <Input placeholder="如：weather-api (唯一标识)" disabled={nameDisabled} />
      </Form.Item>
      <Form.Item
        name="display_name"
        label="显示名称"
        rules={[{ required: true, message: '请输入显示名称' }]}
      >
        <Input placeholder="如：天气 API" />
      </Form.Item>
      <Form.Item name="description" label="描述">
        <Input.TextArea rows={3} placeholder="简要描述您的API服务" />
      </Form.Item>
      <Form.Item
        name="repo_type"
        label="仓库类型"
        rules={[{ required: true, message: '请选择仓库类型' }]}
      >
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
    </>
  )
}
