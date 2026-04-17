-- ============================================
-- 测试数据 SQL 文件
-- 使用方法: psql -U api_user -d api_platform -f init_test_data.sql
-- ============================================

-- 1. 创建测试用户
INSERT INTO users (id, email, password_hash, phone, user_type, user_status, email_verified, vip_level, vip_expire_at, created_at, last_login_at)
VALUES
    ('11111111-1111-1111-1111-111111111111', 'admin@example.com', '240be518fabd2724ddb6f04eeb9d5b1e051a0940f0f1d9e5a3c6d0b0a9d5c6e0', '13800000001', 'admin', 'active', true, 3, NOW() + INTERVAL '365 days', NOW(), NOW()),
    ('22222222-2222-2222-2222-222222222222', 'owner@example.com', '8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918', '13800000002', 'owner', 'active', true, 2, NOW() + INTERVAL '180 days', NOW() - INTERVAL '30 days', NOW() - INTERVAL '2 hours'),
    ('33333333-3333-3333-3333-333333333333', 'developer@example.com', '4d034a4e8f4e49c6a0a8d5f5c5e7f2c3e4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f', '13800000003', 'developer', 'active', true, 1, NOW() + INTERVAL '90 days', NOW() - INTERVAL '15 days', NOW() - INTERVAL '1 hour'),
    ('44444444-4444-4444-4444-444444444444', 'test@example.com', 'ecd718070d1967ca9b32f43eb4317105e1f8322881e6aad5e8f4fc5e4a6f72', '13800000004', 'developer', 'active', false, 0, NULL, NOW() - INTERVAL '7 days', NULL)
ON CONFLICT (email) DO UPDATE SET
    password_hash = EXCLUDED.password_hash,
    phone = EXCLUDED.phone,
    user_type = EXCLUDED.user_type,
    user_status = EXCLUDED.user_status,
    vip_level = EXCLUDED.vip_level;

-- 2. 创建测试账户
INSERT INTO accounts (id, user_id, account_type, balance, frozen_balance, total_recharge, total_consume, created_at)
VALUES
    ('aaaa1111-1111-1111-1111-111111111111', '11111111-1111-1111-1111-111111111111', 'balance', '10000.00', '0.00', '10000.00', '0.00', NOW()),
    ('aaaa2222-2222-2222-2222-222222222222', '22222222-2222-2222-2222-222222222222', 'balance', '5000.00', '0.00', '5000.00', '0.00', NOW() - INTERVAL '30 days'),
    ('aaaa3333-3333-3333-3333-333333333333', '33333333-3333-3333-3333-333333333333', 'balance', '100.00', '0.00', '100.00', '0.00', NOW() - INTERVAL '15 days'),
    ('aaaa4444-4444-4444-4444-444444444444', '44444444-4444-4444-4444-444444444444', 'balance', '50.00', '0.00', '50.00', '0.00', NOW() - INTERVAL '7 days')
ON CONFLICT DO NOTHING;

-- 3. 创建测试 API 仓库
INSERT INTO repositories (id, owner_id, owner_type, name, slug, description, repo_type, protocol, endpoint_url, api_docs_url, status, total_calls, active_keys, avg_latency_ms, success_rate, sla_uptime, sla_latency_p99, created_at)
VALUES
    ('bbbb1111-1111-1111-1111-111111111111', '22222222-2222-2222-2222-222222222222', 'internal', 'OpenAI GPT-4 API', 'openai-gpt4', 'OpenAI GPT-4 官方 API 接口，支持文本生成、代码编写等', 'ai', 'http', 'https://api.openai.com/v1', 'https://platform.openai.com/docs', 'online', 150000, 25, 1500, '99.5%', '99.9%', 3000, NOW() - INTERVAL '60 days'),
    ('bbbb2222-2222-2222-2222-222222222222', '22222222-2222-2222-2222-222222222222', 'internal', 'Claude AI API', 'anthropic-claude', 'Anthropic Claude AI 接口，支持长文本处理', 'ai', 'http', 'https://api.anthropic.com/v1', 'https://docs.anthropic.com', 'online', 80000, 15, 2500, '99.8%', '99.9%', 5000, NOW() - INTERVAL '45 days'),
    ('bbbb3333-3333-3333-3333-333333333333', '22222222-2222-2222-2222-222222222222', 'internal', '图像识别服务', 'vision-api', '基于深度学习的图像识别和分类 API', 'ai', 'http', 'https://api.example.com/vision', 'https://api.example.com/docs', 'online', 30000, 8, 800, '99.2%', '99.5%', 2000, NOW() - INTERVAL '30 days')
ON CONFLICT (slug) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    total_calls = EXCLUDED.total_calls;

-- 4. 创建测试 API Keys
INSERT INTO api_keys (id, user_id, key_name, key_prefix, key_hash, auth_type, rate_limit_rpm, rate_limit_rph, daily_quota, status, total_calls, last_call_at, created_at)
VALUES
    ('cccc1111-1111-1111-1111-111111111111', '33333333-3333-3333-3333-333333333333', '开发环境 Key', 'sk_test_a', '8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918', 'api_key', 100, 1000, 1000, 'active', 150, NOW() - INTERVAL '6 hours', NOW() - INTERVAL '10 days'),
    ('cccc2222-2222-2222-2222-222222222222', '33333333-3333-3333-3333-333333333333', '生产环境 Key', 'sk_live_A', 'ecd718070d1967ca9b32f43eb4317105e1f8322881e6aad5e8f4fc5e4a6f72', 'api_key', 500, 10000, 50000, 'active', 50, NOW() - INTERVAL '1 hour', NOW() - INTERVAL '5 days'),
    ('cccc3333-3333-3333-3333-333333333333', '44444444-4444-4444-4444-444444444444', '测试 Key', 'sk_test_b', '240be518fabd2724ddb6f04eeb9d5b1e051a0940f0f1d9e5a3c6d0b0a9d5c6e0', 'api_key', 50, 500, 500, 'active', 20, NULL, NOW() - INTERVAL '3 days')
ON CONFLICT (key_hash) DO UPDATE SET
    key_name = EXCLUDED.key_name,
    status = EXCLUDED.status,
    total_calls = EXCLUDED.total_calls;

-- 5. 创建测试账单
INSERT INTO bills (bill_no, user_id, bill_type, amount, balance_before, balance_after, status, description, source_type, source_id, created_at)
VALUES
    ('BILL20240417001', '33333333-3333-3333-3333-333333333333', 'consume', '-5.50', '105.50', '100.00', 'completed', 'API 调用消费', 'api_call', 'cccc1111-1111-1111-1111-111111111111', NOW() - INTERVAL '6 hours'),
    ('BILL20240417002', '33333333-3333-3333-3333-333333333333', 'recharge', '100.00', '5.50', '105.50', 'completed', '账户充值', 'manual', NULL, NOW() - INTERVAL '15 days'),
    ('BILL20240417003', '44444444-4444-4444-4444-444444444444', 'consume', '-2.00', '52.00', '50.00', 'completed', 'API 调用消费', 'api_call', 'cccc3333-3333-3333-3333-333333333333', NOW() - INTERVAL '12 hours')
ON CONFLICT (bill_no) DO UPDATE SET
    amount = EXCLUDED.amount,
    balance_after = EXCLUDED.balance_after;

-- 6. 创建测试配额
INSERT INTO quotas (user_id, quota_type, quota_limit, quota_used, reset_type, reset_at, created_at)
VALUES
    ('33333333-3333-3333-3333-333333333333', 'daily', 1000, 150, 'daily', NOW() + INTERVAL '12 hours', NOW() - INTERVAL '1 day'),
    ('33333333-3333-3333-3333-333333333333', 'monthly', 30000, 5000, 'monthly', NOW() + INTERVAL '15 days', NOW() - INTERVAL '15 days'),
    ('44444444-4444-4444-4444-444444444444', 'daily', 500, 50, 'daily', NOW() + INTERVAL '8 hours', NOW() - INTERVAL '3 days')
ON CONFLICT DO NOTHING;

-- 7. 创建调用日志
INSERT INTO key_usage_logs (key_id, user_id, repo_id, endpoint, method, status_code, latency_ms, tokens_used, cost, ip_address, user_agent, created_at)
VALUES
    ('cccc1111-1111-1111-1111-111111111111', '33333333-3333-3333-3333-333333333333', 'bbbb1111-1111-1111-1111-111111111111', '/chat/completions', 'POST', 200, 1250, 50, '0.05', '192.168.1.100', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)', NOW() - INTERVAL '6 hours'),
    ('cccc2222-2222-2222-2222-222222222222', '33333333-3333-3333-3333-333333333333', 'bbbb1111-1111-1111-1111-111111111111', '/chat/completions', 'POST', 200, 2100, 120, '0.12', '192.168.1.100', 'Python/3.11 httpx/1.0', NOW() - INTERVAL '1 hour'),
    ('cccc3333-3333-3333-3333-333333333333', '44444444-4444-4444-4444-444444444444', 'bbbb2222-2222-2222-2222-222222222222', '/v1/messages', 'POST', 200, 3500, 2000, '0.50', '192.168.1.101', 'Claude-SDK/1.0', NOW() - INTERVAL '2 hours');

-- 提交事务
COMMIT;

-- 验证数据
SELECT 'Users:' as info, COUNT(*) as count FROM users
UNION ALL SELECT 'Accounts:', COUNT(*) FROM accounts
UNION ALL SELECT 'Repositories:', COUNT(*) FROM repositories
UNION ALL SELECT 'API Keys:', COUNT(*) FROM api_keys
UNION ALL SELECT 'Bills:', COUNT(*) FROM bills
UNION ALL SELECT 'Quotas:', COUNT(*) FROM quotas
UNION ALL SELECT 'Usage Logs:', COUNT(*) FROM key_usage_logs;
