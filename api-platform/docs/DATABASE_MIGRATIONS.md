# 数据库迁移工作流（Alembic）—— P1-8 迁移来源统一

**文档编号**：DB-MIG-2026-001
**日期**：2026-09-15
**状态**：已实施
**基线版本**：`fec917d3faaf`（baseline: current schema，与模型 100% 对齐，2026-09-15）

---

## 1. 一句话规则

> **模型（`src/models/*.py`）是唯一 schema 权威源；表结构变更一律走 Alembic；
> 禁止手写散装迁移脚本、禁止直接在生产库改表。**

## 2. 历史问题（为什么做这件事）

| 问题 | 后果 |
|------|------|
| 建表来源分裂：`create_all`（模型）+ `migrations/` 散装手写脚本并存 | 同一 schema 有两套"真相"，漂移无告警 |
| 旧 `migrations/versions/` 是**手写伪 alembic 文件**（`down_revision=None` 且注释"请自行设置"） | 从未真正接入迁移链，只是摆设 |
| 改模型后旧库不会自动跟上 | 本次 `payment.mock_mode` 播种变更等只能靠手工重建 |

## 3. 目录结构（改造后）

```
api-platform/
├── alembic.ini               # alembic 配置
├── alembic/
│   ├── env.py                # 连接串（settings + -x url 覆盖）、模型元数据、autogenerate 规则
│   └── versions/             # 迁移版本链（基线 fec917d3faaf 起）
├── scripts/
│   ├── init_db_with_data.py  # 已切换：建表走 alembic upgrade head（不再 create_all）
│   └── legacy_migrations/    # 旧散装脚本归档（9 个文件，仅历史记录，勿执行）
└── tests/test_alembic_infra.py  # 迁移基建守护测试（TC-MIG-001~003）
```

## 4. 日常流程

### 4.1 修改模型后生成迁移

```bash
cd api-platform
# 1. 修改 src/models/*.py
python -m alembic revision --autogenerate -m "add xxx column to yyy"
# 2. 人工审查生成的迁移文件（autogenerate 不完美：server_default、索引重命名等需校对）
# 3. 应用到开发库
python -m alembic upgrade head
```

> **审查要点**：autogenerate 检测不到 server_default 变更、列重命名（会变成 drop+add 导致数据丢失）；
> 列重命名请手改迁移文件为 `op.alter_column(..., new_column_name=...)`。

### 4.2 新环境初始化（空库）

```bash
# 建库（用 postgres 超管；api_user 无 CREATEDB 权限）
& psql -h localhost -U postgres -d postgres -c "CREATE DATABASE xxx OWNER api_user;"
# .env 指向该库后：
python scripts/init_db_with_data.py            # alembic upgrade head + 种子数据
```

### 4.3 存量库接入（已建表、无 alembic 历史）

```bash
# 先用临时空库验证基线与该库 schema 一致，再打戳（标记基线为已应用，不重复建表）：
python -m alembic -x url="postgresql+psycopg2://.../<db>" stamp head
```

**当前戳状态**（2026-09-15）：`api_platform_dev` / `api_platform_prod` 均已 stamp `fec917d3faaf`。

## 5. 与测试库的关系

`tests/conftest.py` 的测试库**继续使用 `Base.metadata.create_all`**（每个用例后 drop_all，
迁移链无意义且拖慢测试）。模型变更的迁移正确性由"开发库 upgrade + schema 对比"保障。

## 6. 踩坑记录

1. **drop 后必须删 `alembic_version`**：`init_db_with_data.py --drop` 曾只删业务表，
   残留的版本戳让 `upgrade head` 判定"已是最新"而什么都不建 → 业务表缺失。
   （已修复：drop_db 中 `DROP TABLE IF EXISTS alembic_version`）
2. **psql 多语句 `-c` 在同一事务块**：`DROP DATABASE`/`CREATE DATABASE` 不能在事务块内，
   需分开执行。
3. **`api_user` 无 CREATEDB 权限**：建库用 `postgres` 超管（密码见 conftest 注释）。
4. **Windows 下 psycopg2 连接错误的 GBK 消息**会以 `UnicodeDecodeError` 掩盖真实错误
   —— 见到该异常先检查"库是否存在/权限"，别被表象误导。

## 7. 验证记录（2026-09-15）

- 基线迁移 `fec917d3faaf` 在临时空库 `upgrade head` 后，与开发库
  `information_schema` 对比：**30 表一致、76+ 列零差异**（SCHEMA_MATCH = TRUE）
- `init_db_with_data.py --drop` 全流程（alembic 建表 + 种子）通过，
  dev 库 31 表（含 alembic_version）、种子 5 用户 / 2 账单
- 全量 pytest **244 passed**（测试库走 create_all 不受影响）
