# 开发调试脚本归档（scripts/dev）

本目录用于**归档**一次性调试、排查、验证脚本。它们不参与应用运行，
也不属于自动化测试套件（`pytest` 的 `testpaths` 仅指向 `tests/`）。

> 背景（评审项 P1-7）：这些脚本原散落在 `api-platform/` 根目录，与正式配置、
> 入口脚本混在一起，影响可读性并容易误提交。2026-09-15 统一归入本目录
> （使用 `git mv` 保留文件历史，**未删除任何代码**）。

---

## 使用前提

1. 工作在 `api-platform` 目录下，且已配置好 `.env`（数据库连接、Redis 等）；
2. 运行前确认后端/数据库状态，多数脚本会**直连数据库**；
3. 这些脚本是**排查工具**，可能硬编码了开发库信息或打印敏感数据，**不要用于生产环境**。

```bash
cd api-platform
python scripts/dev/<脚本名>.py
```

---

## 脚本清单

| 脚本 | 用途 |
|------|------|
| `check_users.py` / `check_all_users.py` | 查询用户表（用户名、邮箱、类型、状态） |
| `check_user_bills.py` / `check_bill_user.py` / `check_bills_detail.py` | 账单与账户数据核对 |
| `check_tz.py` / `check_py_tz.py` / `check_times.py` | 时区/时间处理排查（UTC 统一改造期间使用） |
| `check_sim_env.py` | 检查模拟/生产环境标识与配置 |
| `check_test19.py` / `check_test9.py` | 特定测试账号/场景的数据核对 |
| `debug_login.py` / `debug_api.py` | 登录与接口调试 |
| `test_login.py` / `test_bcrypt.py` | 登录、密码哈希（bcrypt）验证 |
| `test_billing_api.py` / `test_analytics.py` / `test_api_date.py` / `test_date_filter.py` | 计费、分析、日期筛选接口的手工验证 |
| `test_direct.py` / `full_test.py` | 直连测试 / 全流程手工回归 |
| `update_pwd.py` / `update_pwd_sync.py` / `verify_pwd.py` / `verify_update.py` | 密码批量更新与校验（仅开发库） |
| `fix_mock_payment.py` | 模拟支付相关数据修复 |
| `read_log.py` | 日志文件读取 |
| `query_db.py` | 直连数据库执行查询（需自行修改 SQL） |

---

## 已迁移到正式位置的脚本

| 原路径 | 新路径 | 说明 |
|--------|--------|------|
| `api-platform/convert_key.py` | `scripts/convert_key.py` | **正式工具**：支付宝私钥 PKCS1 格式转换（被《支付渠道配置指南》引用） |
| `api-platform/migrate_trial_fields.py` | `scripts/migrate_trial_fields.py` | 一次性数据迁移脚本 |
| `api-platform/run_test.ps1` | `scripts/run_test.ps1` | 测试运行封装（输出到 `test_output.txt`） |

---

## 已归档的生成产物

`final_result.txt`、`result.txt`、`test_output.txt`、以及根目录的 `*.log`
已移动到 `api-platform/logs/artifacts/`（`logs/` 已被 `.gitignore` 忽略）。

---

## 约定

- **新增一次性脚本请直接放入本目录**，不要放到 `api-platform/` 根目录；
- 若某脚本被证明是长期有效的正式工具，请提升到 `scripts/` 并在文档中登记；
- 本目录脚本不受 `pytest` 收集，文件名以 `test_` 开头也不会被误当作测试用例。
