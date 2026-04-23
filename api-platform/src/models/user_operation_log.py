"""
User Operation Log model - 用户操作日志模型

用于记录用户在界面上的操作流程，便于追踪用户行为和排查问题。
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, DateTime, Text, Index, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB

from src.config.database import Base


class UserOperationLog(Base):
    """
    用户操作日志表 - 记录用户在界面上的每个操作
    
    用途：
    - 追踪用户操作流程
    - 排查问题根因
    - 分析用户行为
    - 审计合规
    """

    __tablename__ = "user_operation_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # 用户信息
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    username = Column(String(100), nullable=True, index=True)
    email = Column(String(255), nullable=True, index=True)
    session_id = Column(String(100), nullable=True, index=True)
    
    # 操作信息
    action = Column(String(100), nullable=False, index=True)  # 操作类型
    action_name = Column(String(200), nullable=True)  # 操作名称（中文）
    category = Column(String(50), nullable=False, index=True)  # 操作分类
    
    # 页面信息
    page = Column(String(255), nullable=True)  # 当前页面路径
    page_name = Column(String(200), nullable=True)  # 页面名称（中文）
    referrer = Column(String(500), nullable=True)  # 来源页面
    url_params = Column(JSONB, default=dict)  # URL参数
    
    # 请求信息
    method = Column(String(10), nullable=True)  # HTTP方法
    endpoint = Column(String(500), nullable=True)  # API端点
    request_data = Column(JSONB, default=dict)  # 请求数据（脱敏后）
    response_status = Column(String(20), nullable=True)  # 响应状态：success, failed, error
    
    # 变更信息
    old_values = Column(JSONB, default=dict)  # 变更前的值
    new_values = Column(JSONB, default=dict)  # 变更后的值
    
    # 环境信息
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    device_type = Column(String(50), nullable=True)  # desktop, mobile, tablet
    browser = Column(String(100), nullable=True)
    os = Column(String(100), nullable=True)
    
    # 结果信息
    success = Column(Boolean, default=True)  # 操作是否成功
    error_code = Column(String(50), nullable=True)  # 错误码
    error_message = Column(Text, nullable=True)  # 错误信息
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    duration_ms = Column(String(20), nullable=True)  # 操作耗时（毫秒）

    # 复合索引
    __table_args__ = (
        Index('idx_user_op_user_time', 'user_id', 'created_at'),
        Index('idx_user_op_session_time', 'session_id', 'created_at'),
        Index('idx_user_op_category_time', 'category', 'created_at'),
        Index('idx_user_op_action_time', 'action', 'created_at'),
    )

    def __repr__(self):
        return f"<UserOperationLog {self.user_id} {self.action} at {self.created_at}>"


# ==================== 操作分类常量 ====================

class OperationCategory:
    """操作分类常量"""
    # 认证相关
    AUTH = "auth"  # 登录、登出、注册
    TRIAL = "trial"  # 试用相关
    UPGRADE = "upgrade"  # 升级相关
    
    # 开发者功能
    API_KEY = "api_key"  # API Key管理
    REPOSITORY = "repository"  # 仓库管理
    QUOTA = "quota"  # 配额管理
    BILLING = "billing"  # 账单管理
    PAYMENT = "payment"  # 支付充值
    
    # 导航浏览
    NAVIGATION = "navigation"  # 页面导航
    VIEW = "view"  # 页面查看
    
    # 系统操作
    SYSTEM = "system"  # 系统操作


# ==================== 操作类型常量 ====================

class OperationAction:
    """操作类型常量"""
    
    # === 认证相关 ===
    LOGIN = "login"  # 登录
    LOGOUT = "logout"  # 登出
    REGISTER = "register"  # 注册
    
    # === 试用相关 ===
    VIEW_TRIAL_PAGE = "view_trial_page"  # 查看试用页面
    CLAIM_TRIAL = "claim_trial"  # 领取试用金额
    TRIAL_SUCCESS = "trial_success"  # 试用领取成功
    TRIAL_FAILED = "trial_failed"  # 试用领取失败
    
    # === 升级相关 ===
    VIEW_UPGRADE_PAGE = "view_upgrade_page"  # 查看升级页面
    CLICK_UPGRADE_BUTTON = "click_upgrade_button"  # 点击升级按钮
    UPGRADE_SUCCESS = "upgrade_success"  # 升级成功
    UPGRADE_FAILED = "upgrade_failed"  # 升级失败
    
    # === API Key ===
    VIEW_KEYS_PAGE = "view_keys_page"  # 查看Keys页面
    CREATE_API_KEY = "create_api_key"  # 创建API Key
    DELETE_API_KEY = "delete_api_key"  # 删除API Key
    COPY_API_KEY = "copy_api_key"  # 复制API Key
    
    # === 仓库 ===
    VIEW_REPOS_PAGE = "view_repos_page"  # 查看仓库列表
    VIEW_REPO_DETAIL = "view_repo_detail"  # 查看仓库详情
    CREATE_REPO = "create_repo"  # 创建仓库
    
    # === 充值 ===
    VIEW_RECHARGE_PAGE = "view_recharge_page"  # 查看充值页面
    SELECT_PACKAGE = "select_package"  # 选择套餐
    CREATE_ORDER = "create_order"  # 创建订单
    PAYMENT_PENDING = "payment_pending"  # 支付待处理
    PAYMENT_SUCCESS = "payment_success"  # 支付成功
    PAYMENT_FAILED = "payment_failed"  # 支付失败
    
    # === 导航 ===
    PAGE_VIEW = "page_view"  # 页面浏览
    MENU_CLICK = "menu_click"  # 菜单点击
    BUTTON_CLICK = "button_click"  # 按钮点击
    LINK_CLICK = "link_click"  # 链接点击
    
    # === 系统 ===
    API_REQUEST = "api_request"  # API请求
    REFRESH_PAGE = "refresh_page"  # 刷新页面
    ERROR_PAGE = "error_page"  # 错误页面


# ==================== 操作名称映射 ====================

ACTION_NAMES = {
    # 认证
    OperationAction.LOGIN: "登录",
    OperationAction.LOGOUT: "登出",
    OperationAction.REGISTER: "注册",
    
    # 试用
    OperationAction.VIEW_TRIAL_PAGE: "查看试用页面",
    OperationAction.CLAIM_TRIAL: "领取试用金额",
    OperationAction.TRIAL_SUCCESS: "试用领取成功",
    OperationAction.TRIAL_FAILED: "试用领取失败",
    
    # 升级
    OperationAction.VIEW_UPGRADE_PAGE: "查看升级页面",
    OperationAction.CLICK_UPGRADE_BUTTON: "点击升级按钮",
    OperationAction.UPGRADE_SUCCESS: "升级为开发者成功",
    OperationAction.UPGRADE_FAILED: "升级为开发者失败",
    
    # API Key
    OperationAction.VIEW_KEYS_PAGE: "查看API Keys页面",
    OperationAction.CREATE_API_KEY: "创建API Key",
    OperationAction.DELETE_API_KEY: "删除API Key",
    OperationAction.COPY_API_KEY: "复制API Key",
    
    # 仓库
    OperationAction.VIEW_REPOS_PAGE: "查看仓库市场",
    OperationAction.VIEW_REPO_DETAIL: "查看仓库详情",
    OperationAction.CREATE_REPO: "创建仓库",
    
    # 充值
    OperationAction.VIEW_RECHARGE_PAGE: "查看充值页面",
    OperationAction.SELECT_PACKAGE: "选择充值套餐",
    OperationAction.CREATE_ORDER: "创建充值订单",
    OperationAction.PAYMENT_PENDING: "发起支付",
    OperationAction.PAYMENT_SUCCESS: "支付成功",
    OperationAction.PAYMENT_FAILED: "支付失败",
    
    # 导航
    OperationAction.PAGE_VIEW: "页面浏览",
    OperationAction.MENU_CLICK: "菜单点击",
    OperationAction.BUTTON_CLICK: "按钮点击",
    OperationAction.LINK_CLICK: "链接点击",
    
    # 系统
    OperationAction.API_REQUEST: "API请求",
    OperationAction.REFRESH_PAGE: "刷新页面",
    OperationAction.ERROR_PAGE: "错误页面",
}


def get_action_name(action: str) -> str:
    """获取操作名称"""
    return ACTION_NAMES.get(action, action)
