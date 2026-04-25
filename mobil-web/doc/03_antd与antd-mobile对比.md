# antd 与 antd-mobile 对比

## 文档信息

| 项目信息 | 详情 |
|---------|------|
| 文档名称 | antd 与 antd-mobile 对比 |
| 版本 | V1.0 |
| 日期 | 2026-04-25 |
| 用途 | 帮助选择合适的UI组件库 |

---

## 目录

1. [简介](#1-简介)
2. [核心差异对比](#2-核心差异对比)
3. [组件对比](#3-组件对比)
4. [适配方案](#4-适配方案)
5. [推荐方案](#5-推荐方案)

---

## 1. 简介

### 1.1 Ant Design (antd)

**定位**：企业级PC端UI组件库

**特点**：
- ✅ 组件丰富（60+组件）
- ✅ 设计规范完善
- ✅ 文档详细
- ❌ 移动端适配不佳
- ❌ 触摸交互不友好

### 1.2 Ant Design Mobile (antd-mobile)

**定位**：移动端UI组件库

**特点**：
- ✅ 专为移动端设计
- ✅ 触摸交互友好
- ✅ 体积小（~200KB）
- ✅ 支持手势
- ❌ 组件较少（40+组件）
- ❌ PC端显示不佳

---

## 2. 核心差异对比

### 2.1 基础对比

| 对比项 | Ant Design (antd) | Ant Design Mobile |
|--------|-------------------|-------------------|
| **包名** | `antd` | `antd-mobile` |
| **版本** | 5.x | 5.x |
| **设计语言** | Ant Design | Ant Design Mobile |
| **目标设备** | PC端 | 移动端 |
| **包大小** | ~2MB | ~200KB |
| **CSS方案** | CSS-in-JS | CSS-in-JS |
| **Tree Shaking** | 支持 | 支持 |
| **TypeScript** | 支持 | 支持 |
| **主题定制** | 支持 | 支持 |

### 2.2 技术对比

| 对比项 | Ant Design | Ant Design Mobile |
|--------|-------------|-------------------|
| **响应式** | 部分支持 | 完全支持 |
| **触摸优化** | 一般 | 优秀 |
| **手势支持** | 需第三方库 | 内置 |
| **虚拟键盘处理** | 需手动处理 | 自动处理 |
| **安全区域** | 需手动适配 | 自动适配 |
| **滚动容器** | 普通div | 优化滚动 |

---

## 3. 组件对比

### 3.1 共有组件

| 组件 | Ant Design | Ant Design Mobile | 差异说明 |
|------|-------------|-------------------|---------|
| **Button** | ✅ | ✅ | Mobile版触摸反馈更好 |
| **Input** | ✅ | ✅ | Mobile版支持清除按钮 |
| **Select** | ✅ (下拉) | ✅ (弹出选择器) | 交互方式不同 |
| **DatePicker** | ✅ (下拉) | ✅ (弹出) | Mobile版更适合触摸 |
| **Dialog** | ✅ (Modal) | ✅ (Popup) | Mobile版从底部弹出 |
| **Toast** | ❌ | ✅ | antd需使用message |
| **Swipe** | ❌ | ✅ | 轮播组件 |
| **Stepper** | ❌ | ✅ | 步进器 |
| **JumboTabs** | ❌ | ✅ | 选项卡 |

### 3.2 独有组件

**Ant Design 独有**：
- Table（表格）
- Form（表单，功能更强大）
- Upload（上传）
- Tree（树形控件）
- Timeline（时间轴）
- Statistic（统计）
- Result（结果页）

**Ant Design Mobile 独有**：
- SwipeAction（滑动操作）
- PullToRefresh（下拉刷新）
- InfiniteScroll（无限滚动）
- IndexBar（索引栏）
- PasscodeInput（密码输入）
- NumberKeyboard（数字键盘）

---

## 4. 适配方案

### 4.1 方案一：仅使用 antd（推荐用于简单适配）

**适用场景**：
- 快速适配
- 功能简单
- 不需要复杂移动端交互

**实施步骤**：

```typescript
/**
 * 使用antd + 响应式CSS
 */

// 1. 安装依赖
// npm install antd

// 2. 引入样式
import 'antd/dist/reset.css';
import 'antd/dist/antd.css';

// 3. 使用antd组件
import { Button, Input, Form } from 'antd';

const App: React.FC = () => {
  return (
    <div>
      <Button type="primary" block={isMobile}>
        按钮
      </Button>
      <Input size={isMobile ? 'large' : 'middle'} />
    </div>
  );
};
```

**优点**：
- ✅ 无需学习新组件库
- ✅ 组件功能强大
- ✅ 文档完善

**缺点**：
- ❌ 移动端体验一般
- ❌ 需要大量CSS适配

---

### 4.2 方案二：仅使用 antd-mobile（推荐用于移动端优先）

**适用场景**：
- 移动端优先
- 需要复杂移动端交互
- PC端访问量小

**实施步骤**：

```typescript
/**
 * 使用antd-mobile
 */

// 1. 安装依赖
// npm install antd-mobile

// 2. 引入样式
import 'antd-mobile/es/global';

// 3. 使用antd-mobile组件
import { Button, Input, Form, Toast } from 'antd-mobile';

const App: React.FC = () => {
  return (
    <div>
      <Button color="primary" block>
        按钮
      </Button>
      <Input placeholder="请输入" />
    </div>
  );
};
```

**优点**：
- ✅ 移动端体验优秀
- ✅ 触摸交互友好
- ✅ 体积小

**缺点**：
- ❌ PC端显示不佳
- ❌ 组件相对较少
- ❌ 需要重写部分代码

---

### 4.3 方案三：antd + antd-mobile 混合使用（推荐）

**适用场景**：
- 需要同时支持PC和移动端
- 希望移动端有更好的体验
- 可以接受较大的包体积

**实施步骤**：

```typescript
/**
 * 根据设备类型动态加载组件库
 */

import { useDevice } from '@/hooks/useDevice';

// 动态引入
const getButton = () => {
  const { isMobile } = useDevice();
  
  if (isMobile) {
    return dynamic(() => import('antd-mobile').then(mod => mod.Button));
  } else {
    return dynamic(() => import('antd').then(mod => mod.Button));
  }
};

const App: React.FC = () => {
  const Button = getButton();
  
  return <Button>按钮</Button>;
};
```

**更优方案：使用别名**

```typescript
/**
 * 配置webpack/vite别名
 */

// vite.config.ts
export default defineConfig({
  resolve: {
    alias: {
      '@/components': path.resolve(__dirname, './src/components'),
    },
  },
});

// 创建包装组件
// src/components/Button/index.tsx
import { useDevice } from '@/hooks/useDevice';

const Button: React.FC<any> = (props) => {
  const { isMobile } = useDevice();
  
  if (isMobile) {
    const { Button: MobileButton } = require('antd-mobile');
    return <MobileButton {...props} />;
  } else {
    const { Button: PCButton } = require('antd');
    return <PCButton {...props} />;
  }
};

export default Button;

// 使用
import Button from '@/components/Button';

const App = () => <Button type="primary">按钮</Button>;
```

**优点**：
- ✅ PC和移动端都有最佳体验
- ✅ 可以渐进式改造

**缺点**：
- ❌ 包体积增大
- ❌ 需要维护两套组件

---

## 5. 推荐方案

### 5.1 针对本项目（API Platform）的推荐

**推荐方案**：**方案一（仅使用antd）+ 响应式优化**

**理由**：
1. 现有项目已使用antd，无需重写
2. 通过响应式CSS可以解决大部分问题
3. 对于特定场景（如下拉刷新），可以引入少量antd-mobile组件

**实施计划**：

```
阶段1：使用antd + 响应式CSS适配
  - 所有组件使用antd
  - 通过CSS媒体查询适配移动端
  - 预计完成时间：2周

阶段2：引入antd-mobile特定组件（按需）
  - 下拉刷新：antd-mobile的PullToRefresh
  - 滑动操作：antd-mobile的SwipeAction
  - 无限滚动：antd-mobile的InfiniteScroll
  - 预计完成时间：1周

阶段3：性能优化
  - 按需加载antd-mobile组件
  - 使用动态import
  - 预计完成时间：3天
```

### 5.2 具体实施示例

**示例1：表格在移动端转换为Card列表**

```tsx
/**
 * 响应式表格
 * PC端：antd Table
 * 移动端：Card列表
 */
import { Table, Card } from 'antd';
import { useDevice } from '@/hooks/useDevice';

const ResponsiveTable: React.FC<{ data: any[] }> = ({ data }) => {
  const { isMobile } = useDevice();
  
  // 移动端：Card列表
  if (isMobile) {
    return (
      <div className="mobile-card-list">
        {data.map(item => (
          <Card key={item.id} size="small" className="data-card">
            <div className="card-row">
              <span className="label">名称：</span>
              <span className="value">{item.name}</span>
            </div>
            <div className="card-row">
              <span className="label">状态：</span>
              <Tag color={item.status === 'active' ? 'green' : 'red'}>
                {item.status}
              </Tag>
            </div>
            <div className="card-actions">
              <Button size="small">编辑</Button>
              <Button size="small" danger>删除</Button>
            </div>
          </Card>
        ))}
      </div>
    );
  }
  
  // PC端：Table
  return (
    <Table
      dataSource={data}
      columns={columns}
    />
  );
};
```

**示例2：引入antd-mobile的下拉刷新**

```tsx
/**
 * 下拉刷新列表
 */
import { PullToRefresh } from 'antd-mobile';
import { useDevice } from '@/hooks/useDevice';

const RefreshableList: React.FC = () => {
  const { isMobile } = useDevice();
  const [data, setData] = useState<any[]>([]);
  
  const loadData = async () => {
    const newData = await api.getList();
    setData(newData);
  };
  
  // 移动端：使用antd-mobile的下拉刷新
  if (isMobile) {
    return (
      <PullToRefresh onRefresh={loadData}>
        {data.map(item => (
          <div key={item.id}>{item.name}</div>
        ))}
      </PullToRefresh>
    );
  }
  
  // PC端：普通列表
  return (
    <div>
      <Button onClick={loadData}>刷新</Button>
      {data.map(item => (
        <div key={item.id}>{item.name}</div>
      ))}
    </div>
  );
};
```

---

## 6. 总结

### 6.1 选择建议

| 场景 | 推荐方案 |
|------|---------|
| **已有antd项目，快速适配** | 方案一：仅使用antd |
| **移动端优先的新项目** | 方案二：仅使用antd-mobile |
| **需要同时支持PC和移动端** | 方案三：混合使用 |
| **本项目（API Platform）** | 方案一 + 按需引入antd-mobile |

### 6.2 决策矩阵

| 考虑因素 | 仅antd | 仅antd-mobile | 混合使用 |
|---------|---------|---------------|---------|
| **开发成本** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| **移动端体验** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **PC端体验** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| **包体积** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **维护成本** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |

---

**文档结束**
