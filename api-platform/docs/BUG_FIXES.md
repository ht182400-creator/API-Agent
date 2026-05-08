# Bug 修复记录

## 2026-05-09

### 问题1: 账单查询接口日期过滤参数未生效

**严重程度**: 中

**问题描述**:
- `/api/v1/billing/bills` 接口定义了 `start_date` 和 `end_date` 参数，但代码中完全没有使用这些参数进行数据过滤
- 导致账单列表始终按 id 倒序返回最新记录，无法查看历史数据

**问题文件**: `src/api/v1/billing.py`

**修复内容**:
1. 后端：重构查询构建逻辑，将 `query` 和 `count_query` 的基础条件统一管理
2. 后端：添加日期范围过滤逻辑，正确将北京时间转换为 UTC 进行查询
3. 前端 `web/src/pages/developer/Billing.tsx`：
   - 修复分页问题：添加 `useEffect` 监听 `page`/`pageSize`/`dateRange` 变化
   - 新增日期范围筛选器（RangePicker）组件
   - 日期变化时自动重置到第一页

**数据库验证**:
- production 环境账单分布：
  - 5月9日：32条
  - 5月8日：37条
  - 5月7日：4条
  - 总计 73 条

---

### 问题2: 修复过程中引入的变量未定义错误

**严重程度**: 高

**问题描述**:
- 初次修复时，`count_query` 在第 242、253 行被使用，但定义在第 258 行
- 导致运行时错误：`cannot access local variable 'count_query' where it is not associated with a value`

**修复内容**:
- 将 `count_query` 的定义提前到使用之前
- 使用数组方式管理基础查询条件，确保 `query` 和 `count_query` 条件一致

---

## 时区问题说明

### 当前系统的时区处理方式

系统采用 **UTC 内部存储 + 本地时间显示** 的方式：

```
存入流程:
Python datetime.now() → 生成北京时间 (Asia/Shanghai)
    ↓
PostgreSQL TIMESTAMP WITH TIME ZONE → 转换为 UTC 存储
    ↓
例如: 北京时间 16:46 → 数据库存储为 UTC 08:46

查询流程:
前端传参: start_date=2026-05-08 (北京时间)
    ↓
后端转换: 北京时间 → UTC (减去 8 小时)
    ↓
start_utc = 2026-05-07 16:00:00 (UTC)
    ↓
SQL 查询: WHERE created_at >= '2026-05-07 16:00:00' AND created_at <= '2026-05-08 15:59:59'

返回流程:
数据库返回: UTC 时间 2026-05-08T08:46:29+00:00
    ↓
前端 dayjs() → 自动转换为本地时间显示
    ↓
显示为: 2026-05-08 16:46:29 (北京时间)
```

### 为什么需要时区转换？

**根本原因**: PostgreSQL 的 `TIMESTAMP WITH TIME ZONE` 内部统一以 UTC 存储

**好处**:
1. 多时区环境下一致性更好
2. 避免夏令时等边界情况问题
3. 数据库层面的统一处理

**代价**:
- 存入取出需要转换（当前由 PostgreSQL 自动处理）
- 查询时需要手动转换北京时间为 UTC

### 当前实现是否正确？

**是的，当前实现是正确的**。虽然系统统一在中文环境下运行，但：
- 数据库统一用 UTC 存储是最佳实践
- 时区转换代码虽然看似多余，但是必要的
- 前端 dayjs() 会自动处理显示转换

---

## 优化建议

### 1. 数据库时区配置优化

**方案A: 将会话时区设置为 Asia/Shanghai**

```sql
-- 在数据库连接后执行
SET TimeZone = 'Asia/Shanghai';
```

这样 `TIMESTAMP WITH TIME ZONE` 会以北京时间存储和返回，但仍然以 UTC 内部存储。

**方案B: 改用 TIMESTAMP WITHOUT TIMEZONE**

如果确定系统只在中国运行，可以直接存储北京时间：

```sql
ALTER TABLE bills ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE;
```

**缺点**: 不支持跨时区场景

### 2. 统一时区工具函数

在 `src/utils/datetime.py` 中创建统一工具：

```python
from datetime import datetime, timezone, timedelta

CHINA_TZ = timezone(timedelta(hours=8))

def now_china() -> datetime:
    """获取当前北京时间"""
    return datetime.now(CHINA_TZ)

def to_utc(dt: datetime) -> datetime:
    """北京时间转UTC"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=CHINA_TZ)
    return dt.astimezone(timezone.utc)

def from_utc(dt: datetime) -> datetime:
    """UTC转北京时间"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(CHINA_TZ)
```

### 3. 前端统一时区处理

在 `web/src/utils/datetime.ts` 中：

```typescript
import dayjs from 'dayjs'
import timezone from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'

dayjs.extend(utc)
dayjs.extend(timezone)
dayjs.tz.setDefault('Asia/Shanghai')

export function formatChinaTime(utcStr: string): string {
  return dayjs(utcStr).tz().format('YYYY-MM-DD HH:mm:ss')
}
```

### 4. API 文档注释

在 `billing.py` 的接口注释中明确说明时区处理：

```python
@router.get("/bills")
async def get_bills(
    start_date: str = Query(None, description="开始日期 (北京时间，格式: YYYY-MM-DD)"),
    end_date: str = Query(None, description="结束日期 (北京时间，格式: YYYY-MM-DD)"),
    # ...
):
    """
    获取账单列表
    
    注意:
    - 日期参数为北京时间
    - 数据库内部以 UTC 存储
    - 返回的时间字段为 UTC ISO 格式，前端会自动转换为本地时间显示
    """
```

### 5. 添加时区配置项

在 `.env` 中添加：

```
# 时区配置
TIMEZONE=Asia/Shanghai
```

在 `settings.py` 中读取：

```python
class Settings:
    timezone: str = "Asia/Shanghai"
```

---

## 测试验证

### 验证步骤

1. 插入测试数据
2. 使用日期筛选查询
3. 验证返回的时间格式
4. 验证前端显示时间

### 测试脚本

```python
# scripts/test_timezone.py
# 验证时区转换正确性
```
