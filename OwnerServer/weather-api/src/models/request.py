"""
Weather API 请求模型
定义 API 请求参数的数据结构
"""
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class TemperatureUnit(str, Enum):
    """温度单位枚举"""
    CELSIUS = "c"      # 摄氏度
    FAHRENHEIT = "f"   # 华氏度


class Language(str, Enum):
    """返回语言枚举"""
    CHINESE = "zh-CN"
    ENGLISH = "en"


class WeatherCurrentRequest(BaseModel):
    """
    实时天气请求模型
    
    用于获取指定城市的当前天气数据
    """
    city: str = Field(
        ...,
        description="城市名称（支持中文或拼音）",
        example="北京",
        min_length=1,
        max_length=50
    )
    language: Language = Field(
        default=Language.CHINESE,
        description="返回语言"
    )
    unit: TemperatureUnit = Field(
        default=TemperatureUnit.CELSIUS,
        description="温度单位"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "city": "北京",
                "language": "zh-CN",
                "unit": "c"
            }
        }


class WeatherForecastRequest(BaseModel):
    """
    天气预报请求模型
    
    用于获取指定城市的天气预报数据
    """
    city: str = Field(
        ...,
        description="城市名称",
        example="北京",
        min_length=1,
        max_length=50
    )
    days: int = Field(
        default=3,
        ge=1,
        le=7,
        description="预报天数（1-7天）"
    )
    unit: TemperatureUnit = Field(
        default=TemperatureUnit.CELSIUS,
        description="温度单位"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "city": "北京",
                "days": 3,
                "unit": "c"
            }
        }


class AQICityRequest(BaseModel):
    """
    空气质量查询请求模型
    
    用于获取指定城市的空气质量数据
    """
    city: str = Field(
        ...,
        description="城市名称",
        example="北京",
        min_length=1,
        max_length=50
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "city": "北京"
            }
        }


class AlertCityRequest(BaseModel):
    """
    天气预警查询请求模型
    
    用于获取指定城市的天气预警信息
    """
    city: str = Field(
        ...,
        description="城市名称",
        example="北京",
        min_length=1,
        max_length=50
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "city": "北京"
            }
        }
