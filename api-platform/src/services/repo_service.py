"""
Repository Service - 仓库服务
完整的API实现逻辑
"""

import uuid
import httpx
import json
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from src.models.repository import Repository
from src.models.api_key import APIKey
from src.models.billing import Account, Bill, Quota
from src.core.exceptions import (
    NotFoundError,
    ValidationError,
    QuotaExceededError,
    RateLimitError,
    RepositoryUnavailableError,
    RepositoryTimeoutError,
)
from src.adapters.base import BaseAdapter, AdapterResponse
from src.adapters.http_adapter import HTTPAdapter
from src.adapters.grpc_adapter import GRPCAdapter


class RepoService:
    """仓库服务 - 核心业务逻辑"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._adapters: Dict[str, BaseAdapter] = {
            "http": HTTPAdapter(),
            "grpc": GRPCAdapter(),
        }

    async def list_repositories(
        self,
        page: int = 1,
        page_size: int = 20,
        category: Optional[str] = None,
        search: Optional[str] = None,
        is_public: bool = True,
        owner_id: Optional[str] = None,
    ) -> Tuple[List[Repository], int]:
        """
        获取仓库列表

        Args:
            page: 页码
            page_size: 每页数量
            category: 分类筛选
            search: 搜索关键词
            is_public: 是否公开
            owner_id: 所有者ID

        Returns:
            (仓库列表, 总数)
        """
        query = select(Repository)
        count_query = select(func.count(Repository.id))

        # 筛选条件
        filters = []
        if is_public is not None:
            filters.append(Repository.is_public == is_public)
        if category:
            filters.append(Repository.category == category)
        if owner_id:
            filters.append(Repository.owner_id == owner_id)
        if search:
            filters.append(
                or_(
                    Repository.name.ilike(f"%{search}%"),
                    Repository.description.ilike(f"%{search}%"),
                )
            )

        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))

        # 统计总数
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        # 分页
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        query = query.order_by(Repository.created_at.desc())

        result = await self.db.execute(query)
        repositories = result.scalars().all()

        return list(repositories), total

    async def get_repository(self, repo_id: str) -> Repository:
        """
        获取仓库详情

        Args:
            repo_id: 仓库ID

        Returns:
            仓库对象
        """
        result = await self.db.execute(
            select(Repository).where(Repository.id == repo_id)
        )
        repo = result.scalar_one_or_none()

        if not repo:
            raise NotFoundError(f"仓库不存在: {repo_id}")

        return repo

    async def get_repository_by_name(self, repo_name: str) -> Repository:
        """
        通过名称获取仓库

        Args:
            repo_name: 仓库名称

        Returns:
            仓库对象
        """
        result = await self.db.execute(
            select(Repository).where(Repository.name == repo_name)
        )
        repo = result.scalar_one_or_none()

        if not repo:
            raise NotFoundError(f"仓库不存在: {repo_name}")

        return repo

    async def create_repository(
        self,
        owner_id: str,
        name: str,
        description: str,
        category: str,
        adapter_type: str = "http",
        endpoint: str = "",
        auth_type: str = "none",
        auth_config: Optional[Dict] = None,
        pricing: Optional[Dict] = None,
        rate_limit: Optional[Dict] = None,
        is_public: bool = True,
        config: Optional[Dict] = None,
    ) -> Repository:
        """
        创建仓库

        Args:
            owner_id: 所有者ID
            name: 仓库名称
            description: 描述
            category: 分类
            adapter_type: 适配器类型
            endpoint: API端点
            auth_type: 认证类型
            auth_config: 认证配置
            pricing: 定价配置
            rate_limit: 速率限制
            is_public: 是否公开
            config: 其他配置

        Returns:
            创建的仓库对象
        """
        # 检查名称唯一性
        existing = await self.db.execute(
            select(Repository).where(Repository.name == name)
        )
        if existing.scalar_one_or_none():
            raise ValidationError(f"仓库名称已存在: {name}")

        # 创建仓库
        repo = Repository(
            name=name,
            display_name=name,
            description=description,
            category=category,
            owner_id=owner_id,
            adapter_type=adapter_type,
            endpoint=endpoint,
            auth_type=auth_type,
            auth_config=auth_config or {},
            pricing=pricing or {},
            rate_limit=rate_limit or {"rpm": 100, "rph": 1000},
            is_public=is_public,
            config=config or {},
            status="active",
        )

        self.db.add(repo)
        await self.db.flush()
        await self.db.refresh(repo)

        return repo

    async def update_repository(
        self,
        repo_id: str,
        owner_id: str,
        **kwargs,
    ) -> Repository:
        """
        更新仓库

        Args:
            repo_id: 仓库ID
            owner_id: 所有者ID（用于权限校验）
            **kwargs: 更新字段

        Returns:
            更新后的仓库
        """
        repo = await self.get_repository(repo_id)

        # 权限校验
        if repo.owner_id != owner_id:
            raise ValidationError("无权操作此仓库")

        # 更新字段
        allowed_fields = [
            "description", "category", "endpoint", "auth_type",
            "auth_config", "pricing", "rate_limit", "is_public", "config"
        ]
        for field in allowed_fields:
            if field in kwargs:
                setattr(repo, field, kwargs[field])

        repo.updated_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(repo)

        return repo

    async def delete_repository(self, repo_id: str, owner_id: str) -> bool:
        """
        删除仓库

        Args:
            repo_id: 仓库ID
            owner_id: 所有者ID

        Returns:
            是否成功
        """
        repo = await self.get_repository(repo_id)

        if repo.owner_id != owner_id:
            raise ValidationError("无权操作此仓库")

        await self.db.delete(repo)
        await self.db.flush()

        return True

    async def call_repository(
        self,
        repo_name: str,
        endpoint: str,
        method: str = "POST",
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        timeout: int = 30,
        api_key_id: Optional[str] = None,
        user_id: Optional[str] = None,
        tester: Optional[str] = None,
    ) -> AdapterResponse:
        """
        调用仓库API

        Args:
            repo_name: 仓库名称
            endpoint: 端点名称
            method: HTTP方法
            params: 请求参数
            headers: 请求头
            timeout: 超时时间
            api_key_id: API Key ID
            user_id: 用户ID
            tester: 测试人员用户名

        Returns:
            适配器响应

        Raises:
            QuotaExceededError: 配额超限
            RateLimitError: 速率限制
            RepositoryUnavailableError: 仓库不可用
        """
        # 获取仓库
        repo = await self.get_repository_by_name(repo_name)

        # 检查仓库状态
        if repo.status != "active":
            raise RepositoryUnavailableError(f"仓库已下线: {repo_name}")

        # 获取适配器
        adapter = self._adapters.get(repo.adapter_type)
        if not adapter:
            raise ValidationError(f"不支持的适配器类型: {repo.adapter_type}")

        # 构建请求URL
        request_url = f"{repo.endpoint.rstrip('/')}/{endpoint.lstrip('/')}"

        # 构建认证头
        auth_headers = self._build_auth_headers(repo, headers or {})

        # 调用适配器
        try:
            response = await adapter.request(
                method=method,
                url=request_url,
                params=params,
                headers=auth_headers,
                timeout=timeout,
            )
        except httpx.TimeoutException:
            raise RepositoryTimeoutError(f"仓库响应超时: {repo_name}")
        except httpx.HTTPError as e:
            raise RepositoryUnavailableError(f"仓库请求失败: {str(e)}")

        # 记录调用日志
        await self._log_api_call(
            repo_id=str(repo.id),
            api_key_id=api_key_id,
            user_id=user_id,
            endpoint=endpoint,
            method=method,
            request_params=params,
            response_status=response.status,
            response_time=response.elapsed_ms,
            tester=tester,
        )

        # 扣减配额/计费
        await self._process_billing(
            repo_id=str(repo.id),
            api_key_id=api_key_id,
            user_id=user_id,
            response=response,
        )

        return response

    async def check_rate_limit(
        self,
        api_key_id: str,
        repo_id: Optional[str] = None,
    ) -> Tuple[bool, Dict]:
        """
        检查速率限制

        Args:
            api_key_id: API Key ID
            repo_id: 仓库ID（可选）

        Returns:
            (是否允许, 限制信息)
        """
        result = await self.db.execute(
            select(APIKey).where(APIKey.id == api_key_id)
        )
        api_key = result.scalar_one_or_none()

        if not api_key:
            return True, {}

        # 获取当前使用量
        now = datetime.utcnow()
        window_start = now - timedelta(minutes=1)

        # 这里应该查询Redis获取实时计数
        # 简化处理，直接检查配置
        current_rpm = 0  # 从Redis获取

        if current_rpm >= api_key.rate_limit_rpm:
            return False, {
                "limit_type": "rpm",
                "limit": api_key.rate_limit_rpm,
                "remaining": 0,
                "retry_after": 60,
            }

        return True, {}

    def _build_auth_headers(
        self,
        repo: Repository,
        headers: Dict,
    ) -> Dict:
        """构建认证头"""
        auth_headers = dict(headers)

        if repo.auth_type == "bearer":
            auth_headers["Authorization"] = f"Bearer {repo.auth_config.get('token', '')}"
        elif repo.auth_type == "api_key":
            auth_key = repo.auth_config.get("api_key", "")
            auth_header = repo.auth_config.get("header_name", "X-API-Key")
            auth_headers[auth_header] = auth_key
        elif repo.auth_type == "hmac":
            # HMAC签名逻辑
            pass

        return auth_headers

    async def _log_api_call(
        self,
        repo_id: str,
        api_key_id: Optional[str],
        user_id: Optional[str],
        endpoint: str,
        method: str,
        request_params: Optional[Dict],
        response_status: int,
        response_time: float,
        tester: Optional[str] = None,
    ) -> None:
        """记录API调用日志"""
        from src.models.billing import APICallLog
        import json

        # 将请求参数转为JSON字符串存储
        params_json = json.dumps(request_params) if request_params else None

        log = APICallLog(
            repo_id=uuid.UUID(repo_id),
            api_key_id=uuid.UUID(api_key_id) if api_key_id else None,
            user_id=uuid.UUID(user_id) if user_id else None,
            endpoint=endpoint,
            method=method,
            request_params=params_json,
            tester=tester,
            status_code=response_status,
            response_time=str(response_time),
        )

        self.db.add(log)
        await self.db.flush()

    async def _process_billing(
        self,
        repo_id: str,
        api_key_id: Optional[str],
        user_id: Optional[str],
        response: AdapterResponse,
    ) -> None:
        """处理计费"""
        # 获取仓库定价
        repo = await self.get_repository(repo_id)
        pricing = repo.pricing

        if not pricing:
            return

        # 计算费用
        billing_type = pricing.get("type", "per_call")
        cost = 0.0

        if billing_type == "per_call":
            cost = pricing.get("price", 0.0)
        elif billing_type == "per_token":
            tokens = response.data.get("usage", {}).get("tokens", 0)
            price_per_token = pricing.get("price_per_token", 0.0)
            cost = tokens * price_per_token
        elif billing_type == "per_volume":
            # 按流量计费
            volume = len(json.dumps(response.data))
            price_per_mb = pricing.get("price_per_mb", 0.0)
            cost = (volume / 1024 / 1024) * price_per_mb

        if cost > 0 and api_key_id:
            await self._deduct_balance(
                api_key_id=api_key_id,
                amount=cost,
                description=f"API调用: {repo_id}",
            )

    async def _deduct_balance(
        self,
        api_key_id: str,
        amount: float,
        description: str,
    ) -> None:
        """扣减账户余额"""
        result = await self.db.execute(
            select(Account).where(Account.api_key_id == api_key_id)
        )
        account = result.scalar_one_or_none()

        if not account:
            return

        if account.balance < amount:
            raise QuotaExceededError("余额不足")

        # 扣减余额
        account.balance -= amount

        # 记录账单
        bill = Bill(
            account_id=account.id,
            bill_type="consumption",
            amount=-amount,
            balance_after=account.balance,
            description=description,
        )
        self.db.add(bill)

        await self.db.flush()

    async def get_repo_stats(self, repo_id: str) -> Dict[str, Any]:
        """
        获取仓库统计信息

        Args:
            repo_id: 仓库ID

        Returns:
            统计数据
        """
        repo = await self.get_repository(repo_id)

        # 统计调用量
        from src.models.billing import APICallLog

        today = datetime.utcnow().date()
        week_ago = datetime.utcnow() - timedelta(days=7)

        # 今日调用量
        today_result = await self.db.execute(
            select(func.count(APICallLog.id)).where(
                and_(
                    APICallLog.repo_id == uuid.UUID(repo_id),
                    func.date(APICallLog.created_at) == today,
                )
            )
        )
        today_calls = today_result.scalar()

        # 本周调用量
        week_result = await self.db.execute(
            select(func.count(APICallLog.id)).where(
                and_(
                    APICallLog.repo_id == uuid.UUID(repo_id),
                    APICallLog.created_at >= week_ago,
                )
            )
        )
        week_calls = week_result.scalar()

        # 总调用量
        total_result = await self.db.execute(
            select(func.count(APICallLog.id)).where(
                APICallLog.repo_id == uuid.UUID(repo_id)
            )
        )
        total_calls = total_result.scalar()

        return {
            "repo_id": repo_id,
            "today_calls": today_calls,
            "week_calls": week_calls,
            "total_calls": total_calls,
            "status": repo.status,
        }
