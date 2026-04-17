"""Admin Logs API - 管理员日志管理接口"""

from typing import Optional, List
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Query, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.schemas.response import BaseResponse, PaginatedResponse
from src.services.auth_service import get_current_admin_user
from src.config.logging_config import (
    get_log_files,
    read_log_content,
    get_log_stats,
    backup_manager,
    LOG_DIR,
    BACKUP_DIR,
)

router = APIRouter()


# ==================== 请求/响应模型 ====================

class LogFileInfo(BaseModel):
    """日志文件信息"""
    name: str
    path: str
    module: str
    size: int
    size_formatted: str
    modified_at: str


class LogLine(BaseModel):
    """日志行"""
    line_number: int
    timestamp: str
    level: str
    module: str
    message: str
    raw: str
    color: str


class LogContentResponse(BaseModel):
    """日志内容响应"""
    lines: List[LogLine]
    total: int
    start_line: int
    max_lines: int
    error: Optional[str] = None


class LogStats(BaseModel):
    """日志统计信息"""
    total_files: int
    total_size: int
    total_size_formatted: str
    backup_count: int
    backup_size: int
    backup_size_formatted: str
    config: dict


class BackupFileInfo(BaseModel):
    """备份文件信息"""
    name: str
    path: str
    size: int
    size_formatted: str
    created_at: str
    modified_at: str


class BackupConfigUpdate(BaseModel):
    """备份配置更新"""
    max_file_size_mb: Optional[int] = None
    max_backup_files: Optional[int] = None
    auto_cleanup: Optional[bool] = None
    cleanup_threshold: Optional[int] = None
    enabled: Optional[bool] = None


# ==================== API端点 ====================

@router.get("/files", response_model=BaseResponse[List[LogFileInfo]])
async def list_log_files(
    current_user: dict = Depends(get_current_admin_user),
):
    """
    获取日志文件列表

    返回所有日志文件的信息，包括主日志和各模块日志。
    仅限管理员访问。
    """
    files = get_log_files()
    return BaseResponse(data=files)


@router.get("/content", response_model=BaseResponse[LogContentResponse])
async def get_log(
    file_path: str = Query(..., description="日志文件路径"),
    start_line: int = Query(0, ge=0, description="起始行号"),
    max_lines: int = Query(500, ge=1, le=2000, description="最大读取行数"),
    level: Optional[str] = Query(None, description="日志级别过滤 (DEBUG/INFO/WARNING/ERROR/CRITICAL)"),
    keyword: Optional[str] = Query(None, description="关键词过滤"),
    current_user: dict = Depends(get_current_admin_user),
):
    """
    读取日志文件内容

    支持分页、级别过滤和关键词搜索。
    仅限管理员访问。
    """
    # 验证文件路径安全性
    safe_path = LOG_DIR / Path(file_path).name
    if not str(safe_path).startswith(str(LOG_DIR)):
        raise HTTPException(status_code=403, detail="非法文件路径")

    content = read_log_content(
        file_path=str(safe_path),
        start_line=start_line,
        max_lines=max_lines,
        level_filter=level,
        keyword=keyword,
    )

    if content.get("error"):
        raise HTTPException(status_code=400, detail=content["error"])

    return BaseResponse(data=content)


@router.get("/stats", response_model=BaseResponse[LogStats])
async def get_statistics(
    current_user: dict = Depends(get_current_admin_user),
):
    """
    获取日志统计信息

    返回日志文件数量、总大小、备份信息等统计。
    仅限管理员访问。
    """
    stats = get_log_stats()
    return BaseResponse(data=stats)


@router.get("/backups", response_model=BaseResponse[List[BackupFileInfo]])
async def list_backups(
    current_user: dict = Depends(get_current_admin_user),
):
    """
    获取备份文件列表

    返回所有日志备份文件。
    仅限管理员访问。
    """
    backups = backup_manager.get_backup_files()
    return BaseResponse(data=backups)


@router.get("/backups/{filename}")
async def download_backup(
    filename: str,
    current_user: dict = Depends(get_current_admin_user),
):
    """
    下载备份文件

    仅限管理员访问。
    """
    backup_path = BACKUP_DIR / filename
    if not backup_path.exists():
        raise HTTPException(status_code=404, detail="备份文件不存在")

    return FileResponse(
        path=backup_path,
        filename=filename,
        media_type="text/plain",
    )


@router.delete("/backups/{filename}")
async def delete_backup(
    filename: str,
    current_user: dict = Depends(get_current_admin_user),
):
    """
    删除备份文件

    仅限管理员访问。
    """
    success = backup_manager.delete_backup(filename)
    if not success:
        raise HTTPException(status_code=400, detail="删除失败")

    return BaseResponse(message="删除成功")


@router.post("/backups/cleanup")
async def cleanup_backups(
    current_user: dict = Depends(get_current_admin_user),
):
    """
    手动清理旧备份文件

    触发手动清理，将超过配置的备份文件删除。
    仅限管理员访问。
    """
    from src.config.logging_config import LogBackupManager
    manager = LogBackupManager()
    manager._cleanup_old_backups()

    return BaseResponse(message="清理完成")


@router.get("/config", response_model=BaseResponse[dict])
async def get_backup_config(
    current_user: dict = Depends(get_current_admin_user),
):
    """
    获取日志备份配置

    返回当前的备份配置参数。
    仅限管理员访问。
    """
    return BaseResponse(data=backup_manager.config)


@router.put("/config", response_model=BaseResponse[dict])
async def update_backup_config(
    config: BackupConfigUpdate,
    current_user: dict = Depends(get_current_admin_user),
):
    """
    更新日志备份配置

    修改自动备份的参数。
    仅限管理员访问。
    """
    # 验证参数
    if config.max_file_size_mb is not None:
        if config.max_file_size_mb < 1 or config.max_file_size_mb > 500:
            raise HTTPException(status_code=400, detail="文件大小限制应在1-500MB之间")

    if config.max_backup_files is not None:
        if config.max_backup_files < 10 or config.max_backup_files > 1000:
            raise HTTPException(status_code=400, detail="备份文件数量应在10-1000之间")

    if config.cleanup_threshold is not None:
        if config.cleanup_threshold < 50 or config.cleanup_threshold > 100:
            raise HTTPException(status_code=400, detail="清理阈值应在50-100之间")

    # 更新配置
    update_data = config.model_dump(exclude_none=True)
    backup_manager.save_config(update_data)

    return BaseResponse(data=backup_manager.config, message="配置已更新")


@router.post("/backup/{module}")
async def manual_backup(
    module: str,
    current_user: dict = Depends(get_current_admin_user),
):
    """
    手动备份指定模块的日志

    立即备份指定模块的日志文件并创建时间戳备份。
    仅限管理员访问。
    """
    from src.config.logging_config import MODULE_LOG_DIR, LogBackupManager

    if module == "main":
        log_file = LOG_DIR / "api_platform.log"
    else:
        log_file = MODULE_LOG_DIR / f"{module}.log"

    if not log_file.exists():
        raise HTTPException(status_code=404, detail="日志文件不存在")

    manager = LogBackupManager()
    backup_path = manager.perform_backup(log_file)

    if backup_path:
        return BaseResponse(message=f"备份成功: {backup_path.name}")
    else:
        raise HTTPException(status_code=500, detail="备份失败")
