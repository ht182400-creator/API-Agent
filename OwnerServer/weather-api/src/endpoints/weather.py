"""
Weather API 路由端点
定义天气相关的 API 接口
"""
from fastapi import APIRouter, Query, HTTPException
from datetime import datetime
from typing import Optional
from ..models.request import WeatherCurrentRequest, WeatherForecastRequest
from ..models.response import (
    BaseResponse, CurrentWeatherData, ForecastData, AQIData, AlertData
)
from ..services.weather_service import weather_service

# 创建路由
router = APIRouter(prefix="/weather", tags=["天气 API"])

# 响应模型
response_model = BaseResponse


def generate_request_id() -> str:
    """生成请求ID"""
    return f"req_{datetime.now().strftime('%Y%m%d%H%M%S')}"


@router.get(
    "/current",
    summary="实时天气查询",
    description="获取指定城市的当前天气数据"
)
async def get_current_weather(
    city: str = Query(..., description="城市名称（支持中文或拼音）", min_length=1),
    language: str = Query(default="zh-CN", description="返回语言"),
    unit: str = Query(default="c", description="温度单位: c=摄氏度, f=华氏度")
):
    """
    实时天气查询接口
    
    - **city**: 城市名称，支持中文或拼音
    - **language**: 返回语言，支持 zh-CN, en
    - **unit**: 温度单位，c=摄氏度，f=华氏度
    
    返回当前城市的实时天气数据，包括：
    - 温度、湿度、风力风向
    - 体感温度、能见度、气压
    - 空气质量指数
    """
    request_id = generate_request_id()
    
    try:
        # 调用天气服务获取数据
        data = await weather_service.get_current_weather(city, unit)
        
        return {
            "code": 200,
            "message": "success",
            "data": data,
            "request_id": request_id,
            "timestamp": int(datetime.now().timestamp())
        }
        
    except ValueError as e:
        # 城市未找到
        raise HTTPException(
            status_code=404,
            detail={
                "code": 404,
                "message": "城市未找到",
                "error": {
                    "code": "CITY_NOT_FOUND",
                    "details": str(e)
                },
                "request_id": request_id
            }
        )
    except Exception as e:
        # 服务器内部错误
        raise HTTPException(
            status_code=500,
            detail={
                "code": 500,
                "message": "服务器内部错误",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "details": str(e)
                },
                "request_id": request_id
            }
        )


@router.get(
    "/forecast",
    summary="天气预报查询",
    description="获取指定城市未来7天的天气预报"
)
async def get_weather_forecast(
    city: str = Query(..., description="城市名称", min_length=1),
    days: int = Query(default=3, ge=1, le=7, description="预报天数（1-7天）"),
    unit: str = Query(default="c", description="温度单位: c=摄氏度, f=华氏度")
):
    """
    天气预报查询接口
    
    - **city**: 城市名称
    - **days**: 预报天数，范围 1-7 天
    - **unit**: 温度单位
    
    返回未来指定天数的天气预报，包含：
    - 每日最高/最低温度
    - 天气状况、风力风向
    - 紫外线指数、空气质量
    """
    request_id = generate_request_id()
    
    try:
        data = await weather_service.get_forecast(city, days, unit)
        
        return {
            "code": 200,
            "message": "success",
            "data": data,
            "request_id": request_id,
            "timestamp": int(datetime.now().timestamp())
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail={
                "code": 404,
                "message": "城市未找到",
                "error": {
                    "code": "CITY_NOT_FOUND",
                    "details": str(e)
                },
                "request_id": request_id
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "code": 500,
                "message": "服务器内部错误",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "details": str(e)
                },
                "request_id": request_id
            }
        )


@router.get(
    "/aqi",
    summary="空气质量查询",
    description="获取指定城市的空气质量数据"
)
async def get_air_quality(
    city: str = Query(..., description="城市名称", min_length=1)
):
    """
    空气质量查询接口
    
    - **city**: 城市名称
    
    返回空气质量数据，包括：
    - AQI 指数及等级
    - PM2.5、PM10 等污染物浓度
    - 健康建议
    """
    request_id = generate_request_id()
    
    try:
        data = await weather_service.get_aqi(city)
        
        return {
            "code": 200,
            "message": "success",
            "data": data,
            "request_id": request_id,
            "timestamp": int(datetime.now().timestamp())
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail={
                "code": 404,
                "message": "城市未找到",
                "error": {
                    "code": "CITY_NOT_FOUND",
                    "details": str(e)
                },
                "request_id": request_id
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "code": 500,
                "message": "服务器内部错误",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "details": str(e)
                },
                "request_id": request_id
            }
        )


@router.get(
    "/alerts",
    summary="天气预警查询",
    description="获取指定城市的天气预警信息"
)
async def get_weather_alerts(
    city: str = Query(..., description="城市名称", min_length=1)
):
    """
    天气预警查询接口
    
    - **city**: 城市名称
    
    返回天气预警信息，包括：
    - 预警类型和级别
    - 预警详细描述
    - 防御指南
    """
    request_id = generate_request_id()
    
    try:
        data = await weather_service.get_alerts(city)
        
        return {
            "code": 200,
            "message": "success",
            "data": data,
            "request_id": request_id,
            "timestamp": int(datetime.now().timestamp())
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail={
                "code": 404,
                "message": "城市未找到",
                "error": {
                    "code": "CITY_NOT_FOUND",
                    "details": str(e)
                },
                "request_id": request_id
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "code": 500,
                "message": "服务器内部错误",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "details": str(e)
                },
                "request_id": request_id
            }
        )


@router.get(
    "/health",
    summary="健康检查",
    description="API 服务健康检查接口"
)
async def health_check():
    """
    健康检查接口
    
    返回 API 服务状态，用于监控和负载均衡检测
    """
    return {
        "status": "healthy",
        "service": "Weather API",
        "version": "1.0.0",
        "timestamp": int(datetime.now().timestamp())
    }
