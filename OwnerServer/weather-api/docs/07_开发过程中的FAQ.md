# Owner 平台 - 开发 FAQ 问题详解

## 文档控制

| 项目 | 内容 |
|------|------|
| 文档编号 | FAQ-OWNER-2026-001 |
| 版本号 | V1.0 |
| 创建日期 | 2026-04-21 |
| 更新日期 | 2026-04-21 14:29 |
| 关联文档 | [06_Owner平台操作指南.md](./06_Owner平台操作指南.md) |

---

## FAQ 汇总列表

> 新增 FAQ 时，请在此处添加条目并同步更新

| 序号 | 问题标题 | 关键词 | 优先级 | 状态 | 发现时间 |
|:----:|----------|--------|:------:|:----:|----------|
| 101 | Owner仓库编辑端点配置中状态字段显示异常 | Switch、状态、checkbox、enabled | P1 | ✅ 已修复 | 2026-04-21 14:26 |
| 102 | Owner仓库端点保存后列表显示为0个端点 | 端点、列表、刷新、.data | P0 | ✅ 已修复 | 2026-04-21 18:27 |
| 103 | Admin仓库管理点击详情返回工作台 | 详情、路由、navigate、/repo | P1 | ✅ 已修复 | 2026-04-21 18:39 |

**优先级说明**：P0=紧急/影响核心功能，P1=重要/影响常用功能，P2=一般/影响体验，P3=轻微/不影响功能

---

## 问题101：Owner仓库编辑端点配置中状态字段显示异常

### 101.1 问题描述

**发现时间**：2026-04-21 14:26

在 Owner 平台的仓库编辑弹窗中，切换到「端点配置」Tab，点击编辑端点时，状态字段只显示一个勾选框，没有显示"启用"或"禁用"的中文标签。

**问题截图**：
- 预期显示：带有"启用"/"禁用"标签的 Switch 开关控件
- 实际显示：仅一个简陋的 checkbox 勾选框

### 101.2 问题原因

端点编辑表单中使用了 `<Input type="checkbox" />` 组件：

```tsx
<Form.Item name="enabled" label="状态" valuePropName="checked">
  <Input type="checkbox" />
</Form.Item>
```

在 Ant Design 的 Form.Item 中使用 `valuePropName="checked"` 时，checkbox 无法正确渲染状态标签。

### 101.3 解决方案

**修改文件**：`web/src/pages/owner/Repos.tsx`

1. 添加 Switch 组件导入：
```tsx
import { ..., Switch } from 'antd'
```

2. 将 checkbox 替换为 Switch 组件：
```tsx
<Form.Item name="enabled" label="状态" valuePropName="checked">
  <Switch checkedChildren="启用" unCheckedChildren="禁用" />
</Form.Item>
```

### 101.4 涉及文件清单

| 文件路径 | 修改类型 | 说明 |
|----------|----------|------|
| `web/src/pages/owner/Repos.tsx` | 修改 | 添加 Switch 导入，替换 checkbox 为 Switch 组件 |

### 101.5 验证方法

1. 登录 Owner 平台 (`http://localhost:3000`)
2. 进入「仓库管理」页面
3. 点击仓库列表中的「编辑」按钮
4. 切换到「端点配置」Tab
5. 点击任意端点的「编辑」按钮
6. 验证状态字段显示为 Switch 开关控件，带有"启用"/"禁用"标签

---

## 问题102：Owner仓库端点保存后列表显示为0个端点

### 102.1 问题描述

**发现时间**：2026-04-21 18:27

在 Owner 平台的仓库编辑弹窗中，添加端点并保存后：
1. 提示"端点添加成功"
2. 但端点列表仍显示"0 个端点"
3. 再次点击编辑端点时，显示顺序仍从0开始

### 102.2 问题原因

前端 API 调用返回数据处理逻辑错误：

```typescript
// 错误代码
const endpointsRes = await repoApi.getEndpoints(editingRepo.id)
setEndpoints(endpointsRes.data || [])  // ❌ 错误

// 原因：api.get() 已经自动提取了 response.data
// endpointsRes 直接就是 Endpoint[] 数组，没有 .data 属性
```

### 102.3 解决方案

**修改文件**：`web/src/pages/owner/Repos.tsx`

修复 `loadRepoConfig`、`handleSaveEndpoint`、`handleDeleteEndpoint` 三个函数：

```typescript
// 修复前
const endpointsRes = await repoApi.getEndpoints(editingRepo.id)
setEndpoints(endpointsRes.data || [])

// 修复后
const endpointsData = await repoApi.getEndpoints(editingRepo.id)
setEndpoints(endpointsData || [])

// 限流配置同样修复
const limitsData = await repoApi.getLimits(repoId)
setLimits(limitsData || {})
```

### 102.4 涉及文件清单

| 文件路径 | 修改类型 | 说明 |
|----------|----------|------|
| `web/src/pages/owner/Repos.tsx` | 修改 | 修复 API 返回数据访问方式 |

### 102.5 验证方法

1. 登录 Owner 平台
2. 进入「仓库管理」页面
3. 编辑任意仓库，切换到「端点配置」Tab
4. 添加第一个端点，保存后验证列表显示"1 个端点"
5. 再添加第二个端点，保存后验证列表显示"2 个端点"
6. 验证端点显示顺序正确递增

---

## 问题103：Admin仓库管理点击详情返回工作台

### 103.1 问题描述

**发现时间**：2026-04-21 18:39

在 Admin 平台的仓库管理页面，点击仓库的"详情"按钮后：
1. 页面没有显示仓库详情
2. 而是直接跳转回 Admin 工作台

### 103.2 问题原因

1. Admin `handleViewDetail` 导航到 `/repo/${slug}`
2. 但该路由在 App.tsx 中**未定义**
3. 页面跳转到不存在的路由，被权限守卫拦截
4. 最终重定向回默认页面（Admin 工作台）

### 103.3 解决方案

**修改文件1**：`src/App.tsx`

在 Admin 路由中添加仓库详情页面路由：

```tsx
<Route path="repos/:slug" element={<DeveloperRepoDetail />} />
```

**修改文件2**：`src/pages/admin/Repos.tsx`

修正详情按钮的导航路由：

```tsx
// 修改前
const handleViewDetail = (repo: Repository) => {
  navigate(`/repo/${repo.slug}`)
}

// 修改后
const handleViewDetail = (repo: Repository) => {
  navigate(`/admin/repos/${repo.slug}`)
}
```

### 103.4 涉及文件清单

| 文件路径 | 修改类型 | 说明 |
|----------|----------|------|
| `src/App.tsx` | 修改 | 添加 Admin 仓库详情路由 |
| `src/pages/admin/Repos.tsx` | 修改 | 修正详情导航路由 |

### 103.5 验证方法

1. 登录 Admin 平台
2. 进入「仓库管理」页面
3. 点击任意仓库的"详情"按钮
4. 验证页面正确显示仓库详情信息（名称、描述、端点等）

---

**文档结束**
