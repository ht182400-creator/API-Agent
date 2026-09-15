"""
仓库接口 —— 通用端点代理（catch-all 兜底路由，必须最后注册）

由 `scripts/dev/split_api_router.py` 从 `src/api/v1/repositories.py` 精确搬移生成，
函数体与原实现逐字一致（仅移动位置）。
"""

from fastapi import Depends, Request, HTTPException, APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from src.config.database import get_db
from src.schemas.response import BaseResponse
from src.utils.url_safety import ensure_outbound_url_allowed, OutboundURLBlocked
from src.utils.sanitize import sanitize
from src.models.repository import Repository
from src.api.v1.repositories._shared import calculate_and_charge

router = APIRouter()





@router.api_route("/{repo_slug}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_repository_endpoint(
    repo_slug: str,
    path: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    通用仓库端点代理
    
    动态代理请求到仓库的实际后端服务。
    支持 GET、POST、PUT、DELETE、PATCH 方法。
    
    Args:
        repo_slug: 仓库 slug
        path: 仓库内部路径（如 weather/current）
    
    Returns:
        后端服务响应
    """
    import httpx
    from src.services.auth_service import AuthService
    
    # 1. 获取仓库信息
    repo_result = await db.execute(select(Repository).where(Repository.slug == repo_slug))
    repo = repo_result.scalar_one_or_none()
    
    if not repo:
        raise HTTPException(status_code=404, detail=f"Repository '{repo_slug}' not found")
    
    # 2. 检查仓库状态
    if repo.status != "online":
        raise HTTPException(status_code=403, detail="Repository is not online")
    
    # 3. 如果没有配置后端URL，返回模拟响应
    if not repo.endpoint_url:
        return BaseResponse(
            code=200,
            message="Success",
            data={
                "mock": True,
                "repo": repo.name,
                "path": f"/{path}",
                "message": "后端服务未配置，返回模拟响应",
            }
        )
    
    # 4. 从请求头获取 API Key
    x_access_key = request.headers.get("X-Access-Key")
    
    # 5. 验证 API Key（必填）
    if not x_access_key:
        raise HTTPException(
            status_code=401,
            detail="API Key is required. Please provide X-Access-Key header."
        )
    
    auth_service = AuthService(db)
    try:
        user, key_obj = await auth_service.verify_api_key(x_access_key, repo_id=str(repo.id))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid API Key: {type(e).__name__}: {str(e)}")
    
    # 5. 转发请求到后端
    status_code = 200
    response_data = None
    response_time = 0
    
    try:
        # 构建后端 URL
        backend_url = f"{repo.endpoint_url.rstrip('/')}/{path}"
        
        # 获取查询参数
        query_params = dict(request.query_params)
        
        # 获取请求体
        body = await request.body()

        # 【安全】SSRF 防护：校验出站地址（协议/内网/元数据地址）
        # 注意：放在 query_params / body 之后，保证 finally 中的日志记录不会因
        #       变量未定义而二次报错。
        from src.config.settings import settings as _settings
        ensure_outbound_url_allowed(
            backend_url,
            allow_private=_settings.private_repo_endpoints_allowed,
        )

        import time
        start_time = time.time()
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 构建转发请求
            headers = dict(request.headers)
            headers.pop("host", None)  # 移除 host 头
            
            if x_access_key:
                headers["X-API-Key"] = x_access_key
            
            resp = await client.request(
                method=request.method,
                url=backend_url,
                params=query_params,
                content=body if body else None,
                headers=headers,
            )
            
            status_code = resp.status_code
            response_time = int((time.time() - start_time) * 1000)
            
            # 返回后端响应
            try:
                resp_data = resp.json()
                response_data = resp_data
                return resp_data
            except Exception:
                response_data = {"status_code": resp.status_code, "content": resp.text}
                return {"status_code": resp.status_code, "content": resp.text}
                
    except OutboundURLBlocked as e:
        status_code = 403
        response_data = {"error": f"仓库后端地址不被允许: {e}"}
        raise HTTPException(status_code=403, detail=f"仓库后端地址不被允许: {e}")
    except httpx.TimeoutException:
        status_code = 504
        response_data = {"error": "Backend service timeout"}
        raise HTTPException(status_code=504, detail="Backend service timeout")
    except httpx.RequestError as e:
        status_code = 502
        response_data = {"error": f"Backend service error: {str(e)}"}
        raise HTTPException(status_code=502, detail=f"Backend service error: {str(e)}")
    finally:
        # 6. 记录 API 调用日志并计费
        try:
            from src.models.billing import APICallLog, Quota
            # 【P1-4 拆分时修复的既有缺陷】下方 `datetime.now(timezone.utc)` 用到 timezone，
            # 但原实现只导入 datetime/timedelta —— 一旦走到该分支即 NameError（500）。
            # 该路径此前无测试覆盖，缺陷潜伏至今；本次拆分自检（未绑定名字扫描）将其暴露。
            from datetime import datetime, timedelta, timezone
            import json
            
            # 合并请求参数（查询参数 + 请求体）
            request_params = dict(query_params)
            if body:
                try:
                    body_params = json.loads(body.decode('utf-8'))
                    if isinstance(body_params, dict):
                        request_params.update(body_params)
                except Exception:
                    pass
            
            # 计算并扣除费用
            tokens_used = response_data.get("tokens_used", 0) if isinstance(response_data, dict) else 0
            call_cost, cost_description = await calculate_and_charge(
                db=db,
                user_id=user.id,
                repo_id=repo.id,
                api_key_id=key_obj.id,
                tokens_used=tokens_used,
            )
            
            # 使用北京时间记录，保存 request_id 用于追踪
            log_entry = APICallLog(
                repo_id=repo.id,
                api_key_id=key_obj.id,
                user_id=user.id,
                request_id=getattr(request.state, "request_id", None),
                endpoint=f"/{path}",
                method=request.method,
                request_params=json.dumps(sanitize(request_params), ensure_ascii=False) if request_params else None,
                tester=getattr(user, "username", None) or getattr(user, "name", None) or getattr(user, "email", None),
                status_code=status_code,
                response_time=str(response_time),
                cost=str(call_cost),
                created_at=datetime.now(timezone.utc),
            )
            db.add(log_entry)
            
            # 更新每日配额使用量
            now = datetime.now(timezone.utc)
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            quota_result = await db.execute(
                select(Quota).where(
                    and_(
                        Quota.key_id == key_obj.id,
                        Quota.quota_type == "daily",
                        Quota.reset_at >= today_start
                    )
                )
            )
            quota = quota_result.scalar_one_or_none()
            
            if quota:
                quota.quota_used += 1
            else:
                quota = Quota(
                    user_id=user.id,
                    key_id=key_obj.id,
                    repo_id=repo.id,
                    quota_type="daily",
                    quota_limit=key_obj.daily_quota or 0,
                    quota_used=1,
                    reset_type="daily",
                    reset_at=today_start + timedelta(days=1),
                )
                db.add(quota)
            
            await db.commit()
        except HTTPException:
            # HTTPException（如余额不足）正常抛出
            await db.rollback()
            raise
        except Exception as log_error:
            await db.rollback()
            print(f"Failed to log API call: {log_error}")
