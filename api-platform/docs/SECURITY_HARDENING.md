# 安全加固记录

**文档编号**：SEC-HARDEN-API-2026-001
**版本**：V1.0
**状态**：已实施
**关联文档**：[环境隔离与支付模式设计文档](./ENVIRONMENT_AND_PAYMENT_MODE.md)、[测试方案](./Test_ALL_PLAN.md)

---

## 1. 概述

本记录汇总平台按评审建议实施的第二轮安全加固，覆盖：

| 编号 | 项目 | 对应评审项 | 状态 |
|------|------|-----------|------|
| A | 敏感文件与凭据治理 | P0-4 | ✅ 已完成 |
| B | 仓库转发 SSRF 防护 | P0-5 | ✅ 已完成 |
| C | 管理员权限校验统一 | P1-3 | ✅ 已完成（并修复潜在 ImportError） |
| D | API 路由注册去重 | P1-1 | ✅ 已完成 |

第一轮（环境分层、生产强校验、模拟支付门控）见 [环境隔离与支付模式设计文档](./ENVIRONMENT_AND_PAYMENT_MODE.md)。

---

## 2. A — 敏感文件与凭据治理（P0-4）

### 2.1 问题

- `api-platform/keys/alipay_private_key.pem`、`alipay_private_key_pkcs1.pem`、`alipay_public_key.pem`
  **已提交进 git 仓库**（支付宝应用私钥泄露）。
- `OwnerServer/users.db` 已被跟踪。
- `.gitignore` 仅忽略 `*.db`，**未忽略 `keys/`、`*.pem`**，导致密钥可持续被提交。
- `.env` 已被忽略（无需处理），但 `.env.*` 变体未被覆盖。

> ⚠️ **风险等级：高**。私钥一旦进入版本库历史，即使删除文件，历史提交中仍可获取，
> 必须**视为已泄露并轮换密钥**。

### 2.2 处置

| 动作 | 内容 |
|------|------|
| 取消跟踪 | `git rm --cached api-platform/keys/*.pem OwnerServer/users.db`（本地文件保留） |
| 忽略规则 | `.gitignore` 新增 `keys/`、`*.pem`、`*.key`、`*.p8`、`*.p12`、`*.pfx`、`*.crt`、`*.cer`、`.env.*`（保留 `.env.example`） |
| 调试产物 | 追加忽略 `pytest_run.txt`、`diag*.txt`、`final_test.txt`、`test_run_output.txt` |

### 2.3 必须人工完成的操作（重要）

1. **轮换支付宝密钥**：登录蚂蚁金服开放平台，重新生成应用私钥/公钥并更新配置；
   旧的已提交密钥应作废。
2. **新克隆/部署环境**需自行放置 `keys/*.pem`（文件已被 `.gitignore` 排除，不会随仓库分发）。
3. **（可选）清理 git 历史**：若仓库曾推送到远端，建议使用 `git filter-repo` 或 BFG 清理历史中的密钥文件，
   否则历史提交仍可被检出。清理后需强制推送并通知所有协作者重新克隆。

---

## 3. B — 仓库转发 SSRF 防护（P0-5）

### 3.1 问题

平台按仓库配置的 `endpoint_url` 发起服务端出站请求（`/{repo_slug}/chat`、通用代理 `/{repo_slug}/{path}`）。
该地址若可任意填写，攻击者可将其指向：

- 内网服务（`http://10.x`、`http://192.168.x`）→ 内网信息探测；
- 环回地址（`http://127.0.0.1:6379`）→ 探测本机服务（Redis 等）；
- **云厂商元数据**（`http://169.254.169.254/latest/meta-data/`）→ **窃取实例凭据**。

### 3.2 方案

新增 `src/utils/url_safety.py`，提供 `ensure_outbound_url_allowed()`：

| 规则 | 说明 | 是否可关闭 |
|------|------|-----------|
| 协议白名单 | 仅允许 `http` / `https`，阻断 `file://`、`gopher://`、`dict://`、`ldap://` 等 | ❌ 始终生效 |
| 元数据地址 | `169.254.169.254`、`169.254.170.2`、`100.100.100.200`、`fd00:ec2::254` | ❌ 始终生效 |
| 元数据主机名 | `metadata`、`metadata.google.internal`、`instance-data` | ❌ 始终生效 |
| `*.localhost` | 一律阻断 | ❌ 始终生效 |
| 私网 / 环回 / 链路本地 / 保留地址 | `10/8`、`172.16/12`、`192.168/16`、`127/8`、`::1`、`169.254/16`、`fc00::/7` 等 | ✅ 由配置控制 |
| 域名解析校验 | 对域名做 DNS 解析，校验**每一个**解析结果，防止 `127.0.0.1.nip.io`、十进制 IP（`2130706433`）等绕过 | ✅ 由配置控制 |
| 解析失败 | **失败关闭（fail-closed）**，拒绝访问 | ❌ 始终生效 |

**配置开关**：`ALLOW_PRIVATE_REPO_ENDPOINTS`

| 取值 | 行为 |
|------|------|
| 不配置（默认） | 非生产环境允许私网（兼容本地示例 API），**生产环境自动禁止** |
| `false` | 始终禁止（最严格，生产推荐） |
| `true` | 始终允许（生产存在 SSRF 风险，会输出安全提示，仅限临时排查） |

### 3.3 接入点

| 位置 | 说明 |
|------|------|
| `src/api/v1/repositories.py` — `chat()` | 转发前校验 `/chat` 出站地址，被拒时返回 **403** |
| `src/api/v1/repositories.py` — 通用代理 | 转发前校验目标地址，被拒时返回 **403**（校验置于 `query_params`/`body` 取值之后，避免 `finally` 日志二次异常） |

---

## 4. C — 管理员权限校验统一（P1-3）

### 4.1 问题

`check_admin_permission` 存在**三份实现**，且其中一份并不存在：

| 位置 | 状态 |
|------|------|
| `src/api/v1/repositories.py` | 本地实现（可运行） |
| `src/api/v1/analytics.py` | 本地实现（可运行） |
| `src/services/auth_service.py` | **函数不存在**，但 `src/api/v1/payment.py` 两处 `from src.services.auth_service import check_admin_permission` → **运行时 ImportError** |

即：管理员的"创建充值套餐"与"退款"接口在调用时会因导入失败而报错。

### 4.2 处置

- 在 `src/services/auth_service.py` 中新增**唯一实现** `check_admin_permission(user)`，
  委托 `PermissionService.is_admin` 判定（以 `user_type` 为准，兼容历史 `role`），
  不通过则抛出 `AuthorizationError`。
- 删除 `repositories.py`、`analytics.py` 中的本地实现，统一改为 import 该函数。
- 顺带修复 `payment.py` 两处接口的 ImportError。

---

## 5. D — API 路由注册去重（P1-1）

### 5.1 问题

`src/api/__init__.py` 在挂载 `v1_router` 之外，**又单独 include 了** `admin_logs_router` 与 `analytics_router`：

| 后果 | 说明 |
|------|------|
| 重复注册 | `analytics` 路由被注册两次（路径相同，靠先注册者生效） |
| **无前缀暴露** | `admin_logs` 的 `/files`、`/content`、`/backups` 等被额外暴露在 `/api/v1/files` 等**非预期路径**下，与文档不符并扩大攻击面 |

### 5.2 处置

`src/api/__init__.py` 改为**只挂载 `v1_router`**，并在文件头写明"路由统一在 `api/v1/__init__.py` 注册"的约定，
避免后续再次重复挂载。

### 5.3 验证（运行时探测）

| 路径 | 修复前 | 修复后 | 说明 |
|------|:------:|:------:|------|
| `/api/v1/files` | 401 | **404** | 无前缀暴露已消除 |
| `/api/v1/content` | 401 | **404** | 同上 |
| `/api/v1/admin/logs/content` | 401 | 401 | 正确路径仍然可用 |
| `/api/v1/analytics/overview` | 401 | 401 | 单一注册 |

---

## 6. 测试用例

新增 `tests/test_url_safety.py`（39 条）：

| 用例区间 | 覆盖内容 |
|----------|----------|
| TC-SSRF-001~004 | 空地址 / 缺主机 / 非 http(s) 协议 / 协议白名单 |
| TC-SSRF-005~006 | 元数据 IP 与元数据主机名（允许私网时仍须拦截） |
| TC-SSRF-007~010 | 私网/环回地址放行策略、`*.localhost`、便捷判断 |
| TC-SSRF-011~014 | `ALLOW_PRIVATE_REPO_ENDPOINTS` 策略联动与安全提示 |
| TC-PERM-001~003 | 管理员权限函数唯一性、管理员通过、非管理员拒绝 |
| TC-ROUTE-001~002 | 无前缀暴露为 404、正确路径仍可用 |

运行：

```bash
cd api-platform
python -m pytest tests/test_url_safety.py -v
python -m pytest tests/ -v      # 全量：127 passed
```

---

## 7. 变更文件清单

| 文件 | 变更 |
|------|------|
| `.gitignore` | 新增密钥/证书/环境变量/调试产物忽略规则 |
| `src/utils/url_safety.py` | **新增**：SSRF 出站地址校验 |
| `src/utils/__init__.py` | 导出 url_safety |
| `src/config/settings.py` | 新增 `allow_private_repo_endpoints`、`private_repo_endpoints_allowed`、`collect_security_notices()` |
| `src/main.py` | 启动时输出非致命安全提示 |
| `src/services/auth_service.py` | 新增唯一入口 `check_admin_permission()` |
| `src/api/v1/repositories.py` | 接入 SSRF 校验（2 处）；删除本地权限函数，改用统一实现 |
| `src/api/v1/analytics.py` | 删除本地权限函数，改用统一实现 |
| `src/api/__init__.py` | 修复路由重复挂载与无前缀暴露 |
| `.env.example` | 新增「仓库出站地址安全」配置块（含完整说明） |
| `tests/test_url_safety.py` | **新增**：39 条用例 |

---

## 8. 遗留待办

- [ ] **轮换已泄露的支付宝密钥**（最高优先级，需人工操作）
- [ ] （可选）清理 git 历史中的密钥文件并强制推送
- [ ] 仓库创建/更新时对 `endpoint_url` 做**写入侧校验**（当前为请求侧校验，建议双重防护）
- [ ] SSRF 校验结果增加缓存，避免每次转发都做 DNS 解析
- [ ] 支付回调补充渠道 IP 白名单
- [ ] 限流迁移至 Redis（P0-3）
- [ ] `RepoService.call_repository` 为**死代码**且字段与模型漂移（`repo.endpoint` 应为 `repo.endpoint_url`），
      建议删除或对齐（P1-2）

---

**文档结束**
