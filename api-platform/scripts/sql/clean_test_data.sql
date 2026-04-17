-- ============================================
-- 清空测试数据 SQL 文件
-- 使用方法: psql -U api_user -d api_platform -f clean_test_data.sql
-- ============================================

-- 开始事务
BEGIN;

-- 按外键依赖顺序删除数据
-- 1. 删除调用日志
DELETE FROM key_usage_logs;
-- 2. 删除账单
DELETE FROM bills;
-- 3. 删除配额
DELETE FROM quotas;
-- 4. 删除 API Keys
DELETE FROM api_keys;
-- 5. 删除账户
DELETE FROM accounts;
-- 6. 删除仓库
DELETE FROM repositories;
-- 7. 删除用户
DELETE FROM users;

-- 重置序列 (可选，取消注释以使用)
-- SELECT setval('bills_id_seq', 1, false);
-- SELECT setval('quotas_id_seq', 1, false);
-- SELECT setval('key_usage_logs_id_seq', 1, false);

-- 提交事务
COMMIT;

-- 验证结果
SELECT 
    'key_usage_logs' as table_name, COUNT(*) as remaining FROM key_usage_logs
UNION ALL SELECT 'bills', COUNT(*) FROM bills
UNION ALL SELECT 'quotas', COUNT(*) FROM quotas
UNION ALL SELECT 'api_keys', COUNT(*) FROM api_keys
UNION ALL SELECT 'accounts', COUNT(*) FROM accounts
UNION ALL SELECT 'repositories', COUNT(*) FROM repositories
UNION ALL SELECT 'users', COUNT(*) FROM users;
