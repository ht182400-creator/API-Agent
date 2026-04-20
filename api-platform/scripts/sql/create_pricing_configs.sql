-- ============================================
-- 计费配置表 DDL 脚本
-- pricing_configs 表
--
-- 支持三种计费模式：
-- 1. call - 按调用次数计费
-- 2. token - 按Token数计费
-- 3. package - 套餐包计费
--
-- 使用方法:
--   psql -U api_user -d api_platform -f scripts/sql/create_pricing_configs.sql
-- ============================================

-- 1. 创建表
CREATE TABLE IF NOT EXISTS pricing_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- 仓库关联 (NULL表示全局默认配置)
    repo_id UUID REFERENCES repositories(id) ON DELETE CASCADE,

    -- 计费模式: call(按调用), token(按Token), package(套餐包)
    pricing_type VARCHAR(20) NOT NULL,

    -- ===== 按调用计费模式 (pricing_type='call') =====
    price_per_call DECIMAL(10, 4),          -- 每次调用价格
    free_calls INTEGER DEFAULT 0,           -- 免费调用次数

    -- ===== 按Token计费模式 (pricing_type='token') =====
    price_per_1k_input_tokens DECIMAL(10, 4),  -- 每1K输入Token价格
    price_per_1k_output_tokens DECIMAL(10, 4), -- 每1K输出Token价格
    free_input_tokens INTEGER DEFAULT 0,    -- 免费输入Token数
    free_output_tokens INTEGER DEFAULT 0,  -- 免费输出Token数

    -- ===== 套餐包计费模式 (pricing_type='package') =====
    packages JSONB DEFAULT '[]'::jsonb,    -- 套餐包定义
    default_package_id VARCHAR(50),         -- 默认选中的套餐包ID

    -- ===== 通用配置 =====
    pricing_tiers JSONB DEFAULT '[]'::jsonb,   -- 阶梯定价配置
    vip_discounts JSONB DEFAULT '{}'::jsonb,    -- VIP等级折扣配置

    -- 优先级 (数字越小优先级越高)
    priority INTEGER DEFAULT 100,

    -- 生效时间范围
    valid_from TIMESTAMP,
    valid_until TIMESTAMP,

    -- 状态: active(生效), inactive(失效), deprecated(废弃)
    status VARCHAR(20) DEFAULT 'active',

    -- 备注
    description TEXT,

    -- 审计字段
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,

    -- 索引
    CONSTRAINT pricing_configs_repo_id_fkey FOREIGN KEY (repo_id) REFERENCES repositories(id) ON DELETE CASCADE
);

-- 2. 创建索引
CREATE INDEX IF NOT EXISTS idx_pricing_configs_repo_id ON pricing_configs(repo_id);
CREATE INDEX IF NOT EXISTS idx_pricing_configs_pricing_type ON pricing_configs(pricing_type);
CREATE INDEX IF NOT EXISTS idx_pricing_configs_status ON pricing_configs(status);
CREATE INDEX IF NOT EXISTS idx_pricing_configs_priority ON pricing_configs(priority);

-- 3. 创建唯一约束 (同一仓库同一计费模式只能有一条激活配置)
CREATE UNIQUE INDEX IF NOT EXISTS idx_pricing_configs_unique_active
    ON pricing_configs(repo_id, pricing_type)
    WHERE status = 'active';

-- 4. 添加注释
COMMENT ON TABLE pricing_configs IS '计费配置表 - 支持灵活的计费模式配置';
COMMENT ON COLUMN pricing_configs.repo_id IS '关联的仓库ID，NULL表示全局默认配置';
COMMENT ON COLUMN pricing_configs.pricing_type IS '计费模式: call(按调用), token(按Token), package(套餐包)';
COMMENT ON COLUMN pricing_configs.price_per_call IS '每次调用价格';
COMMENT ON COLUMN pricing_configs.free_calls IS '免费调用次数';
COMMENT ON COLUMN pricing_configs.price_per_1k_input_tokens IS '每1K输入Token价格';
COMMENT ON COLUMN pricing_configs.price_per_1k_output_tokens IS '每1K输出Token价格';
COMMENT ON COLUMN pricing_configs.free_input_tokens IS '免费输入Token数';
COMMENT ON COLUMN pricing_configs.free_output_tokens IS '免费输出Token数';
COMMENT ON COLUMN pricing_configs.packages IS '套餐包定义，格式: [{"name":"基础套餐","calls":1000,"price":10.00,"period_days":30}]';
COMMENT ON COLUMN pricing_configs.pricing_tiers IS '阶梯定价配置，格式: [{"min_calls":0,"max_calls":10000,"discount":1.0}]';
COMMENT ON COLUMN pricing_configs.vip_discounts IS 'VIP等级折扣配置，格式: {"1":1.0,"2":0.95,"3":0.9}';
COMMENT ON COLUMN pricing_configs.priority IS '配置优先级，数字越小优先级越高';
COMMENT ON COLUMN pricing_configs.valid_from IS '配置生效开始时间';
COMMENT ON COLUMN pricing_configs.valid_until IS '配置生效结束时间';
COMMENT ON COLUMN pricing_configs.status IS '状态: active(生效), inactive(失效), deprecated(废弃)';

-- 5. 创建更新时间触发器
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_pricing_configs_updated_at ON pricing_configs;
CREATE TRIGGER update_pricing_configs_updated_at
    BEFORE UPDATE ON pricing_configs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 提交
COMMIT;

-- 6. 验证
SELECT 'pricing_configs table created successfully!' AS result;
SELECT COUNT(*) AS table_count FROM pricing_configs;
