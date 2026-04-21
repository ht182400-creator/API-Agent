"""
天气数据服务
负责从数据源获取天气数据
"""
from datetime import datetime
from typing import Optional, Dict, Any
from loguru import logger
from ..models.request import TemperatureUnit


class WeatherService:
    """天气数据服务类"""
    
    # 模拟城市数据库（实际应从数据库或配置获取）
    CITIES_DB = {
        "北京": {"code": "101010100", "country": "中国", "pinyin": "beijing"},
        "上海": {"code": "101020100", "country": "中国", "pinyin": "shanghai"},
        "广州": {"code": "101280101", "country": "中国", "pinyin": "guangzhou"},
        "深圳": {"code": "101280601", "country": "中国", "pinyin": "shenzhen"},
        "beijing": {"code": "101010100", "country": "中国", "pinyin": "beijing"},
        "shanghai": {"code": "101020100", "country": "中国", "pinyin": "shanghai"},
    }
    
    # 天气代码映射
    WEATHER_CODES = {
        "00": {"name": "晴", "icon": "☀️"},
        "01": {"name": "多云", "icon": "⛅"},
        "02": {"name": "阴", "icon": "☁️"},
        "03": {"name": "小雨", "icon": "🌧️"},
        "04": {"name": "中雨", "icon": "🌧️"},
        "05": {"name": "大雨", "icon": "⛈️"},
        "06": {"name": "雷阵雨", "icon": "⛈️"},
        "07": {"name": "小雪", "icon": "🌨️"},
        "08": {"name": "中雪", "icon": "❄️"},
        "09": {"name": "大雪", "icon": "❄️"},
        "10": {"name": "雾", "icon": "🌫️"},
        "11": {"name": "霾", "icon": "🌫️"},
    }
    
    def __init__(self):
        """初始化天气服务"""
        self._init_logger()
    
    def _init_logger(self):
        """初始化日志记录器"""
        logger.add(
            "logs/weather_service_{time}.log",
            rotation="1 day",
            retention="7 days",
            level="INFO"
        )
    
    def _celsius_to_fahrenheit(self, celsius: float) -> float:
        """摄氏度转华氏度"""
        return round(celsius * 9 / 5 + 32, 1)
    
    def _get_city_info(self, city: str) -> Optional[Dict[str, str]]:
        """
        获取城市信息
        
        Args:
            city: 城市名称（中文或拼音）
        
        Returns:
            城市信息字典，包含 code, country, pinyin
        """
        city_info = self.CITIES_DB.get(city)
        if city_info:
            return city_info
        # 尝试模糊匹配
        for name, info in self.CITIES_DB.items():
            if city.lower() == info.get("pinyin", "").lower():
                return info
        return None
    
    def _get_weekday(self, date_str: str) -> str:
        """获取星期几"""
        weekday_map = {
            0: "星期一", 1: "星期二", 2: "星期三",
            3: "星期四", 4: "星期五", 5: "星期六", 6: "星期日"
        }
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d")
            return weekday_map[date.weekday()]
        except:
            return "星期一"
    
    async def get_current_weather(
        self,
        city: str,
        unit: str = "c"
    ) -> Dict[str, Any]:
        """
        获取实时天气数据
        
        Args:
            city: 城市名称
            unit: 温度单位
        
        Returns:
            实时天气数据字典
        """
        try:
            # 查询城市信息
            city_info = self._get_city_info(city)
            if not city_info:
                raise ValueError(f"城市 '{city}' 未找到")
            
            # 模拟天气数据（实际应调用外部 API 获取）
            temp_c = 25
            weather_code = "00"
            weather_info = self.WEATHER_CODES.get(weather_code, {"name": "晴", "icon": "☀️"})
            
            data = {
                "city": city,
                "city_code": city_info["code"],
                "country": city_info["country"],
                "weather": weather_info["name"],
                "weather_code": weather_code,
                "temperature": temp_c,
                "temperature_f": self._celsius_to_fahrenheit(temp_c),
                "feels_like": temp_c + 2,
                "humidity": 45,
                "humidity_percent": 45,
                "wind_speed": 12,
                "wind_speed_unit": "km/h",
                "wind_direction": "南风",
                "wind_direction_degree": 180,
                "pressure": 1013,
                "visibility": 10,
                "uv_index": 6,
                "aqi": 58,
                "aqi_level": "良",
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "sunrise": "05:42",
                "sunset": "18:56"
            }
            
            logger.info(f"获取实时天气成功: {city}")
            return data
            
        except Exception as e:
            logger.error(f"获取实时天气失败: {city}, 错误: {str(e)}")
            raise
    
    async def get_forecast(
        self,
        city: str,
        days: int = 3,
        unit: str = "c"
    ) -> Dict[str, Any]:
        """
        获取天气预报数据
        
        Args:
            city: 城市名称
            days: 预报天数
            unit: 温度单位
        
        Returns:
            天气预报数据字典
        """
        try:
            # 查询城市信息
            city_info = self._get_city_info(city)
            if not city_info:
                raise ValueError(f"城市 '{city}' 未找到")
            
            # 模拟7天预报数据
            forecasts = []
            for i in range(7):
                date = datetime.now()
                date = date.replace(day=date.day + i)
                date_str = date.strftime("%Y-%m-%d")
                
                temp_high = 28 - i
                temp_low = 16 + i % 3
                
                forecasts.append({
                    "date": date_str,
                    "weekday": self._get_weekday(date_str),
                    "weather": "晴" if i % 2 == 0 else "多云",
                    "weather_code": "00" if i % 2 == 0 else "01",
                    "weather_icon": "☀️" if i % 2 == 0 else "⛅",
                    "temp_high": temp_high,
                    "temp_low": temp_low,
                    "temp_high_f": self._celsius_to_fahrenheit(temp_high),
                    "temp_low_f": self._celsius_to_fahrenheit(temp_low),
                    "humidity": 45 + i % 10,
                    "wind": "南风3-4级",
                    "wind_speed": 12,
                    "uv_index": 6 - i % 2,
                    "air_quality": {"aqi": 58 + i * 5, "level": "良"}
                })
            
            data = {
                "city": city,
                "city_code": city_info["code"],
                "forecast_days": days,
                "forecasts": forecasts[:days],
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            logger.info(f"获取天气预报成功: {city}, 天数: {days}")
            return data
            
        except Exception as e:
            logger.error(f"获取天气预报失败: {city}, 错误: {str(e)}")
            raise
    
    async def get_aqi(self, city: str) -> Dict[str, Any]:
        """
        获取空气质量数据
        
        Args:
            city: 城市名称
        
        Returns:
            空气质量数据字典
        """
        try:
            # 查询城市信息
            city_info = self._get_city_info(city)
            if not city_info:
                raise ValueError(f"城市 '{city}' 未找到")
            
            data = {
                "city": city,
                "city_code": city_info["code"],
                "aqi": 58,
                "level": "良",
                "level_color": "#90EE90",
                "primary_pollutant": "PM2.5",
                "health_advice": "空气质量良好，可以正常进行户外活动",
                "pollutants": {
                    "pm25": {"value": 35, "level": "良", "level_color": "#90EE90"},
                    "pm10": {"value": 68, "level": "良", "level_color": "#90EE90"},
                    "so2": {"value": 10, "level": "优", "level_color": "#00FF00"},
                    "no2": {"value": 45, "level": "良", "level_color": "#90EE90"},
                    "co": {"value": 0.8, "unit": "mg/m³"},
                    "o3": {"value": 120, "unit": "μg/m³"}
                },
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            logger.info(f"获取空气质量成功: {city}")
            return data
            
        except Exception as e:
            logger.error(f"获取空气质量失败: {city}, 错误: {str(e)}")
            raise
    
    async def get_alerts(self, city: str) -> Dict[str, Any]:
        """
        获取天气预警数据
        
        Args:
            city: 城市名称
        
        Returns:
            天气预警数据字典
        """
        try:
            # 查询城市信息
            city_info = self._get_city_info(city)
            if not city_info:
                raise ValueError(f"城市 '{city}' 未找到")
            
            # 模拟无预警数据
            data = {
                "city": city,
                "has_alerts": False,
                "alerts_count": 0,
                "alerts": [],
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            logger.info(f"获取天气预警成功: {city}")
            return data
            
        except Exception as e:
            logger.error(f"获取天气预警失败: {city}, 错误: {str(e)}")
            raise


# 全局服务实例
weather_service = WeatherService()
