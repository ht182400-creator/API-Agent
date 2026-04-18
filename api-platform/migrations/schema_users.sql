-- =====================================================
-- 通用API服务平台 - 用户表结构 (V1.2)
-- 创建日期: 2026-04-18
-- 更新说明: 添加 username, role, permissions 字段
-- =====================================================

-- 1. 创建 PostgreSQL 扩展（如果不存在）
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 2. 创建用户表
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- 登录凭证
    username VARCHAR(50) UNIQUE,                           -- 用户名（唯一，可选）
    email VARCHAR(255) UNIQUE NOT NULL,                     -- 邮箱（唯一）
    password_hash VARCHAR(255),                            -- 密码哈希
    phone VARCHAR(20),                                     -- 手机号
    
    -- 用户类型和角色
    user_type VARCHAR(20) NOT NULL DEFAULT 'developer',   -- 用户类型: developer/owner/admin
    user_status VARCHAR(20) NOT NULL DEFAULT 'active',    -- 用户状态: active/disabled/deleted
    role VARCHAR(20) NOT NULL DEFAULT 'user',             -- 角色: super_admin/admin/developer/user
    permissions JSONB DEFAULT '[]'::jsonb,                 -- 细粒度权限列表
    
    -- OAuth 信息
    oauth_provider VARCHAR(50),                             -- OAuth 提供商
    oauth_id VARCHAR(255),                                  -- OAuth 用户ID
    
    -- 验证状态
    email_verified BOOLEAN DEFAULT FALSE,                   -- 邮箱已验证
    phone_verified BOOLEAN DEFAULT FALSE,                   -- 手机已验证
    
    -- VIP 信息
    vip_level INTEGER DEFAULT 0,                            -- VIP 等级
    vip_expire_at TIMESTAMP,                                -- VIP 到期时间
    
    -- 审计字段
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP,
    last_login_ip VARCHAR(50),
    
    -- 扩展字段
    extra JSONB DEFAULT '{}'::jsonb
);

-- 3. 创建索引
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_user_type ON users(user_type);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- =====================================================
-- 角色与权限说明
-- =====================================================
-- 
-- 角色 (role):
--   - super_admin: 超级管理员，拥有所有权限 (*)
--   - admin:       管理员，拥有大部分管理权限
--   - developer:   开发者，拥有 API 读写权限
--   - user:        普通用户，仅有只读权限
--
-- 权限标识 (permissions):
--   - *            所有权限（超级管理员）
--   - user:read    读取用户信息
--   - user:write   创建/更新用户
--   - user:delete  删除用户
--   - api:read     读取 API 密钥
--   - api:write    创建/更新 API 密钥
--   - api:delete   删除 API 密钥
--   - quota:manage 管理配额
--   - repo:manage  管理仓库
--
-- =====================================================
-- 
-- 4. 默认权限配置（用于参考）
-- =====================================================
--
-- -- 普通用户 (user)
-- ['user:read']
--
-- -- 开发者 (developer)
-- ['user:read', 'user:write', 'api:read', 'api:write']
--
-- -- 仓库所有者 (owner -> role: developer)
-- ['user:read', 'user:write', 'api:read', 'api:write', 'repo:manage']
--
-- -- 管理员 (admin)
-- ['user:read', 'user:write', 'user:delete', 'api:read', 'api:write', 'api:delete', 'quota:manage', 'repo:manage']
--
-- -- 超级管理员 (super_admin)
-- ['*']
--
-- =====================================================
