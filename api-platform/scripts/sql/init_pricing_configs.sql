-- ============================================
-- 计费配置表初始数据脚本
-- pricing_configs 表 - 预设配置
--
-- 使用方法:
--   psql -U api_user -d api_platform -f scripts/sql/init_pricing_configs.sql
-- ============================================

BEGIN;

-- 1. 删除现有数据 (可选，保留则注释掉)
-- DELETE FROM pricing_configs;

-- 2. 插入全局默认计费配置

-- 2.1 全局默认 - 按调用计费
INSERT INTO pricing_configs (
    id,
    repo_id,
    pricing_type,
    price_per_call,
    free_calls,
    pricing_tiers,
    vip_discounts,
    priority,
    status,
    description,
    created_at
) VALUES (
    'd0000001-0000-0000-0000-000000000001',
    NULL,  -- 全局配置
    'call',
    0.0100,  -- 默认0.01元/调用
    0,
    '[{"min_calls": 0, "max_calls": 10000, "discount": 1.0}, {"min_calls": 10001, "max_calls": 100000, "discount": 0.95}, {"min_calls": 100001, "max_calls": null, "discount": 0.9}]'::jsonb,
    '{"0": 1.0, "1": 1.0, "2": 0.98, "3": 0.95}'::jsonb,
    100,
    'active',
    '全局默认按调用计费配置',
    CURRENT_TIMESTAMP
) ON CONFLICT DO NOTHING;

-- 2.2 全局默认 - 按Token计费 (参考OpenAI定价)
INSERT INTO pricing_configs (
    id,
    repo_id,
    pricing_type,
    price_per_1k_input_tokens,
    price_per_1k_output_tokens,
    free_input_tokens,
    free_output_tokens,
    pricing_tiers,
    vip_discounts,
    priority,
    status,
    description,
    created_at
) VALUES (
    'd0000001-0000-0000-0000-000000000002',
    NULL,  -- 全局配置
    'token',
    0.0030,  -- $3/1M 输入 ≈ ¥0.03/1K (参考价)
    0.0060,  -- $6/1M 输出 ≈ ¥0.06/1K (参考价)
    0,
    0,
    '[{"min_calls": 0, "max_calls": 1000000, "discount": 1.0}, {"min_calls": 1000001, "max_calls": 10000000, "discount": 0.95}, {"min_calls": 10000001, "max_calls": null, "discount": 0.9}]'::jsonb,
    '{"0": 1.0, "1": 1.0, "2": 0.98, "3": 0.95}'::jsonb,
    100,
    'active',
    '全局默认按Token计费配置 (参考OpenAI GPT-4o)',
    CURRENT_TIMESTAMP
) ON CONFLICT DO NOTHING;

-- 2.3 全局默认 - 套餐包计费
INSERT INTO pricing_configs (
    id,
    repo_id,
    pricing_type,
    packages,
    default_package_id,
    priority,
    status,
    description,
    created_at
) VALUES (
    'd0000001-0000-0000-0000-000000000003',
    NULL,  -- 全局配置
    'package',
    '[
        {"id": "package_free", "name": "免费版", "calls": 100, "price": 0.00, "period_days": 30, "features": ["基础API调用", "100次/月"]},
        {"id": "package_basic", "name": "基础版", "calls": 5000, "price": 29.90, "period_days": 30, "features": ["全部API调用", "5000次/月", "技术支持"]},
        {"id": "package_pro", "name": "专业版", "calls": 50000, "price": 199.00, "period_days": 30, "features": ["全部API调用", "50000次/月", "优先支持", "统计报表"]},
        {"id": "package_enterprise", "name": "企业版", "calls": 500000, "price": 999.00, "period_days": 30, "features": ["全部API调用", "500000次/月", "专属支持", "高级统计", "定制开发"]}
    ]'::jsonb,
    'package_basic',
    100,
    'active',
    '全局默认套餐包计费配置',
    CURRENT_TIMESTAMP
) ON CONFLICT DO NOTHING;

-- 3. 示例：特定仓库的计费配置

-- 3.1 OpenAI GPT-4 API - 按Token计费 (repo_id 示例)
-- 注意：实际使用时替换为真实的仓库ID
-- INSERT INTO pricing_configs (
--     repo_id,
--     pricing_type,
--     price_per_1k_input_tokens,
--     price_per_1k_output_tokens,
--     priority,
--     status,
--     description
-- ) VALUES (
--     'bbbb1111-1111-1111-1111-111111111111',  -- 替换为真实仓库ID
--     'token',
--     0.0030,
--     0.0060,
--     10,  -- 优先级高于全局配置
--     'active',
--     'OpenAI GPT-4 API 按Token计费'
-- );

-- 3.2 图像识别服务 - 按调用计费 (repo_id 示例)
-- INSERT INTO pricing_configs (
--     repo_id,
--     pricing_type,
--     price_per_call,
--     free_calls,
--     priority,
--     status,
--     description
-- ) VALUES (
--     'bbbb3333-3333-3333-3333-333333333333',  -- 替换为真实仓库ID
--     'call',
--     0.0500,
--     100,
--     10,
--     'active',
--     '图像识别服务按调用计费'
-- );

-- 4. 提交事务
COMMIT;

-- 5. 验证数据
SELECT 'Initial pricing configs inserted successfully!' AS result;
SELECT id, pricing_type, price_per_call, price_per_1k_input_tokens, status, description FROM pricing_configs;
