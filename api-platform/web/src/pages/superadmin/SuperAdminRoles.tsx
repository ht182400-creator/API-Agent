/**
 * 超级管理员 - 角色权限管理页面
 * 数据从数据库获取
 */

import { useState, useEffect } from 'react'
import '../../styles/cyber-theme.css'
import { Card, Table, Tag, Button, Space, Modal, Tree, Checkbox, message, Typography, Spin } from 'antd'
import { SafetyCertificateOutlined, EditOutlined, UnorderedListOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { roleApi, RoleItem, PERMISSION_DEFINITIONS } from '../../api/superadmin'

const { Title, Text } = Typography
const { TreeNode } = Tree

// 权限分组
const permissionGroups: Record<string, string[]> = {
  '用户管理': ['user:read', 'user:write', 'user:delete', 'user:manage', 'user:role'],
  'API Keys': ['api:read', 'api:write', 'api:delete', 'api:manage'],
  '仓库管理': ['repo:read', 'repo:write', 'repo:delete', 'repo:approve', 'repo:manage'],
  '账单管理': ['billing:read', 'billing:write', 'billing:manage', 'billing:recharge'],
  '日志查看': ['log:read', 'log:all'],
  '系统管理': ['system:settings', 'system:logs'],
  '开发者功能': ['dev:apikeys', 'dev:quota', 'dev:billing'],
  '仓库所有者': ['owner:repo', 'owner:analytics', 'owner:settlement'],
}

// 权限中文名映射
const permissionLabels: Record<string, string> = {}
Object.entries(PERMISSION_DEFINITIONS).forEach(([key, def]) => {
  permissionLabels[key] = def.name
})

export default function SuperAdminRoles() {
  const [roles, setRoles] = useState<RoleItem[]>([])
  const [loading, setLoading] = useState(true)
  const [editModalVisible, setEditModalVisible] = useState(false)
  const [viewModalVisible, setViewModalVisible] = useState(false)
  const [editingRole, setEditingRole] = useState<RoleItem | null>(null)
  const [viewingRole, setViewingRole] = useState<RoleItem | null>(null)
  const [selectedPermissions, setSelectedPermissions] = useState<string[]>([])

  useEffect(() => {
    loadRoles()
  }, [])

  const loadRoles = async () => {
    try {
      setLoading(true)
      const data = await roleApi.list()
      setRoles(data || [])
    } catch (error) {
      console.error('加载角色列表失败:', error)
      message.error('加载角色列表失败')
    } finally {
      setLoading(false)
    }
  }

  const handleEditRole = (role: RoleItem) => {
    setEditingRole(role)
    setSelectedPermissions(role.permissions.includes('*') ? [] : role.permissions)
    setEditModalVisible(true)
  }

  const handleViewPermissions = (role: RoleItem) => {
    setViewingRole(role)
    setViewModalVisible(true)
  }

  const handleSaveRole = () => {
    // TODO: 调用 API 保存角色权限
    message.success(`角色 ${editingRole?.display_name} 权限已更新（模拟保存）`)
    setEditModalVisible(false)
  }

  const onPermissionChange = (checkedKeys: any) => {
    setSelectedPermissions(checkedKeys)
  }

  const renderTreeNodes = () => {
    return Object.entries(permissionGroups).map(([groupName, permissions]) => (
      <TreeNode key={groupName} title={groupName}>
        {permissions.map(perm => (
          <TreeNode key={perm} title={permissionLabels[perm] || perm} />
        ))}
      </TreeNode>
    ))
  }

  const columns: ColumnsType<RoleItem> = [
    { 
      title: '角色标识', 
      dataIndex: 'name', 
      key: 'name', 
      render: (name: string) => <Tag color="blue">{name}</Tag> 
    },
    { title: '显示名称', dataIndex: 'display_name', key: 'display_name' },
    { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
    { 
      title: '用户数', 
      dataIndex: 'user_count', 
      key: 'user_count', 
      render: (count: number) => <Tag color="green">{count}</Tag> 
    },
    { 
      title: '权限数量', 
      key: 'permCount',
      render: (_, record) => (
        <span>
          {record.permissions.includes('*') ? (
            <Tag color="red">全部权限</Tag>
          ) : (
            `${record.permissions.length} 项`
          )}
        </span>
      )
    },
    { 
      title: '系统角色', 
      key: 'isSystem',
      render: (_, record) => (
        record.is_system ? <Tag color="purple">系统</Tag> : <Tag>自定义</Tag>
      )
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space>
          {record.is_system && record.name !== 'super_admin' ? (
            <Button type="link" icon={<EditOutlined />} onClick={() => handleEditRole(record)}>
              编辑
            </Button>
          ) : null}
          <Button type="link" icon={<UnorderedListOutlined />} onClick={() => handleViewPermissions(record)}>
            查看权限
          </Button>
        </Space>
      ),
    },
  ]

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 400 }}>
        <Spin size="large" />
      </div>
    )
  }

  return (
    <div style={{ padding: 24 }} className="bamboo-bg-pattern">
      <div style={{ marginBottom: 24 }}>
        <Title level={2}><SafetyCertificateOutlined /> 角色权限管理</Title>
        <Text type="secondary">管理系统角色和细粒度权限</Text>
      </div>

      <Card>
        <Table 
          columns={columns} 
          dataSource={roles} 
          rowKey="id" 
          pagination={false}
        />
      </Card>

      {/* 查看权限弹窗 */}
      <Modal
        title={`${viewingRole?.display_name} 权限列表`}
        open={viewModalVisible}
        onCancel={() => setViewModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setViewModalVisible(false)}>
            关闭
          </Button>
        ]}
        width={600}
      >
        {viewingRole?.permissions.includes('*') ? (
          <Text type="secondary" style={{ fontSize: 16 }}>
            该角色拥有所有权限（*）
          </Text>
        ) : (
          <div style={{ maxHeight: 400, overflow: 'auto' }}>
            {Object.entries(permissionGroups).map(([group, perms]) => {
              const rolePerms = viewingRole?.permissions.filter(p => perms.includes(p)) || []
              if (rolePerms.length === 0) return null
              
              return (
                <div key={group} style={{ marginBottom: 16 }}>
                  <Text strong>{group}:</Text>
                  <div style={{ marginTop: 8 }}>
                    {rolePerms.map(perm => (
                      <Tag key={perm} color="green" style={{ margin: 4 }}>
                        {permissionLabels[perm] || perm}
                      </Tag>
                    ))}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </Modal>

      {/* 编辑权限弹窗 */}
      <Modal
        title={`编辑角色: ${editingRole?.display_name}`}
        open={editModalVisible}
        onOk={handleSaveRole}
        onCancel={() => setEditModalVisible(false)}
        width={700}
        okText="保存"
        cancelText="取消"
      >
        <div style={{ marginBottom: 16 }}>
          <Text strong>选择权限:</Text>
          <Text type="secondary" style={{ marginLeft: 8 }}>（勾选表示授予该权限）</Text>
        </div>
        <Tree
          checkable
          defaultExpandAll
          checkedKeys={selectedPermissions}
          onCheck={onPermissionChange}
        >
          {renderTreeNodes()}
        </Tree>
        <div style={{ marginTop: 16, color: '#999', fontSize: 12 }}>
          提示: 超级管理员角色拥有所有权限，无法编辑
        </div>
      </Modal>
    </div>
  )
}
