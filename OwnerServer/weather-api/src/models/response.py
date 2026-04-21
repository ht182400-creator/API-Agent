"""
Weather API 响应模型
定义 API 响应数据的数据结构
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class BaseResponse(BaseModel):
    """基础响应模型"""
    code: int = Field(..., description="状态码，200表示成功")
    message: str = Field(..., description="响应消息")
    request_id: Optional[str] = Field(None, description="请求ID，用于追踪")
    timestamp: Optional[int] = Field(None, description="Unix时间戳")


class CurrentWeatherData(BaseModel):
    """实时天气数据"""
    city: str = Field(..., description="城市名称")
    city_code: str = Field(..., description="城市代码")
    country: str = Field(default="中国", description="国家")
    weather: str = Field(..., description="天气状况")
    weather_code: str = Field(..., description="天气代码")
    temperature: float = Field(..., description="温度（摄氏度）")
    temperature_f: float = Field(..., description="温度（华氏度）")
    feels_like: float = Field(..., description="体感温度")
    humidity: int = Field(..., description="湿度（百分比）")
    humidity_percent: int = Field(..., description="湿度百分比")
    wind_speed: float = Field(..., description="风速（km/h）")
    wind_speed_unit: str = Field(default="km/h", description="风速单位")
    wind_direction: str = Field(..., description="风向")
    wind_direction_degree: int = Field(..., description="风向角度")
    pressure: int = Field(..., description="气压（hPa）")
    visibility: float = Field(..., description="能见度（km）")
    uv_index: int = Field(default=0, description="紫外线指数")
    aqi: Optional[int] = Field(None, description="空气质量指数")
    aqi_level: Optional[str] = Field(None, description="空气质量等级")
    update_time: str = Field(..., description="数据更新时间")
    sunrise: Optional[str] = Field(None, description="日出时间")
    sunset: Optional[str] = Field(None, description="日落时间")


class ForecastDayData(BaseModel):
    """单日预报数据"""
    date: str = Field(..., description="日期（YYYY-MM-DD）")
    weekday: str = Field(..., description="星期几")
    weather: str = Field(..., description="天气状况")
    weather_code: str = Field(..., description="天气代码")
    weather_icon: str = Field(..., description="天气图标")
    temp_high: int = Field(..., description="最高温度")
    temp_low: int = Field(..., description="最低温度")
    temp_high_f: int = Field(..., description="最高温度（华氏度）")
    temp_low_f: int = Field(..., description="最低温度（华氏度）")
    humidity: int = Field(..., description="湿度")
    wind: str = Field(..., description="风力风向")
    wind_speed: float = Field(..., description="风速")
    uv_index: int = Field(default=0, description="紫外线指数")
    air_quality: Optional[dict] = Field(None, description="空气质量")


class ForecastData(BaseModel):
    """天气预报数据"""
    city: str = Field(..., description="城市名称")
    city_code: str = Field(..., description="城市代码")
    forecast_days: int = Field(..., description="预报天数")
    forecasts: List[ForecastDayData] = Field(..., description="逐日预报列表")
    update_time: str = Field(..., description="数据更新时间")


class PollutantData(BaseModel):
    """污染物数据"""
    value: float = Field(..., description="浓度值")
    level: Optional[str] = Field(None, description="等级")
    level_color: Optional[str] = Field(None, description="等级颜色")
    unit: Optional[str] = Field(None, description="单位")


class AQIData(BaseModel):
    """空气质量数据"""
    city: str = Field(..., description="城市名称")
    city_code: str = Field(..., description="城市代码")
    aqi: int = Field(..., description="空气质量指数")
    level: str = Field(..., description="空气质量等级")
    level_color: str = Field(..., description="等级颜色代码")
    primary_pollutant: Optional[str] = Field(None, description="主要污染物")
    health_advice: str = Field(..., description="健康建议")
    pollutants: dict = Field(..., description="各污染物浓度")
    update_time: str = Field(..., description="数据更新时间")


class AlertItem(BaseModel):
    """单条预警信息"""
    id: str = Field(..., description="预警ID")
    type: str = Field(..., description="预警类型")
    type_code: str = Field(..., description="预警类型代码")
    level: str = Field(..., description="预警级别")
    level_code: str = Field(..., description="预警级别代码")
    title: str = Field(..., description="预警标题")
    description: str = Field(..., description="预警详细描述")
    possible_effect: str = Field(..., description="可能影响")
    suggestions: List[str] = Field(default=[], description="防御指南")
    publish_time: str = Field(..., description="发布时间")
    start_time: str = Field(..., description="开始时间")
    end_time: str = Field(..., description="结束时间")
    source: str = Field(..., description="发布来源")


class AlertData(BaseModel):
    """天气预警数据"""
    city: str = Field(..., description="城市名称")
    has_alerts: bool = Field(..., description="是否有预警")
    alerts_count: int = Field(..., description="预警数量")
    alerts: List[AlertItem] = Field(default=[], description="预警列表")
    update_time: str = Field(..., description="数据更新时间")


class ErrorDetail(BaseModel):
    """错误详情"""
    code: str = Field(..., description="错误代码")
    details: Optional[str] = Field(None, description="错误详情")
    retry_after: Optional[int] = Field(None, description="重试等待秒数")
    limit_type: Optional[str] = Field(None, description="限制类型")
    current_usage: Optional[int] = Field(None, description="当前使用量")
    limit: Optional[int] = Field(None, description="限制值")


class ErrorResponse(BaseModel):
    """错误响应模型"""
    code: int = Field(..., description="状态码")
    message: str = Field(..., description="错误消息")
    error: ErrorDetail = Field(..., description="错误详情")
    request_id: Optional[str] = Field(None, description="请求ID")
