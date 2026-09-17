/**
 * 备份设置弹窗（P1-4 拆分，纯搬运零行为改变）。
 *
 * 受控组件：`config` / `onChange(key, value)` / `onSave` 都由页面持有 ——
 * 弹窗**不碰任何请求**，只负责展示与收集改动（页面自己决定怎么存）。
 */
import { Button, Form, Modal, Slider, Switch, Typography } from 'antd'
import { SaveOutlined } from '@ant-design/icons'
import type { BackupConfig } from '../../../api/adminLogs'

const { Text } = Typography

export interface BackupConfigModalProps {
  open: boolean
  /** 当前配置（null 表示尚未加载完成 → 弹窗内不渲染表单，与拆分前一致） */
  config: BackupConfig | null
  configLoading: boolean
  /** 与页面 `handleConfigChange` 同签名：只上报改动，不负责持久化 */
  onChange: (key: keyof BackupConfig, value: any) => void
  onSave: () => void
  onClose: () => void
}

export default function BackupConfigModal({
  open,
  config,
  configLoading,
  onChange,
  onSave,
  onClose,
}: BackupConfigModalProps) {
  return (
    <Modal
      title="备份设置"
      open={open}
      onCancel={onClose}
      footer={[
        <Button key="cancel" onClick={onClose}>
          取消
        </Button>,
        <Button key="save" type="primary" icon={<SaveOutlined />} onClick={onSave} loading={configLoading}>
          保存
        </Button>,
      ]}
    >
      {config && (
        <Form layout="vertical">
          <Form.Item label="启用自动备份">
            <Switch checked={config.enabled} onChange={(checked) => onChange('enabled', checked)} />
          </Form.Item>

          <Form.Item label={`文件大小限制: ${config.max_file_size_mb} MB`}>
            <Slider
              min={1}
              max={100}
              value={config.max_file_size_mb}
              onChange={(value) => onChange('max_file_size_mb', value)}
              disabled={!config.enabled}
              marks={{
                10: '10MB',
                50: '50MB',
                100: '100MB',
              }}
            />
            <Text type="secondary">单个日志文件超过此大小后将自动备份并创建新文件</Text>
          </Form.Item>

          <Form.Item label={`最大备份数量: ${config.max_backup_files}`}>
            <Slider
              min={10}
              max={500}
              value={config.max_backup_files}
              onChange={(value) => onChange('max_backup_files', value)}
              disabled={!config.enabled}
              marks={{
                50: '50',
                100: '100',
                200: '200',
                500: '500',
              }}
            />
            <Text type="secondary">超过此数量的备份文件将被自动清理</Text>
          </Form.Item>

          <Form.Item label={`自动清理: ${config.auto_cleanup ? '启用' : '禁用'}`}>
            <Switch
              checked={config.auto_cleanup}
              onChange={(checked) => onChange('auto_cleanup', checked)}
              disabled={!config.enabled}
            />
          </Form.Item>

          <Form.Item label={`清理阈值: ${config.cleanup_threshold}%`}>
            <Slider
              min={50}
              max={100}
              value={config.cleanup_threshold}
              onChange={(value) => onChange('cleanup_threshold', value)}
              disabled={!config.enabled || !config.auto_cleanup}
              marks={{
                50: '50%',
                75: '75%',
                90: '90%',
              }}
            />
            <Text type="secondary">当备份文件达到最大数量的此百分比时自动清理</Text>
          </Form.Item>
        </Form>
      )}
    </Modal>
  )
}
