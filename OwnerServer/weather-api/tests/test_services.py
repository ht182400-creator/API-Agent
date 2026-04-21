"""
Weather Service 测试文件
测试天气服务的业务逻辑
"""
import pytest
from src.services.weather_service import WeatherService, weather_service


class TestWeatherService:
    """天气服务测试类"""
    
    def setup_method(self):
        """每个测试方法前执行"""
        self.service = WeatherService()
    
    def test_get_city_info_chinese(self):
        """测试城市信息查询 - 中文"""
        city_info = self.service._get_city_info("北京")
        assert city_info is not None
        assert city_info["code"] == "101010100"
        assert city_info["country"] == "中国"
    
    def test_get_city_info_pinyin(self):
        """测试城市信息查询 - 拼音"""
        city_info = self.service._get_city_info("beijing")
        assert city_info is not None
        assert city_info["code"] == "101010100"
    
    def test_get_city_info_not_found(self):
        """测试城市信息查询 - 不存在的城市"""
        city_info = self.service._get_city_info("不存在城市")
        assert city_info is None
    
    def test_celsius_to_fahrenheit(self):
        """测试温度转换"""
        # 0°C = 32°F
        assert self.service._celsius_to_fahrenheit(0) == 32.0
        # 100°C = 212°F
        assert self.service._celsius_to_fahrenheit(100) == 212.0
        # 25°C = 77°F
        assert self.service._celsius_to_fahrenheit(25) == 77.0
    
    @pytest.mark.asyncio
    async def test_get_current_weather_success(self):
        """测试获取实时天气 - 成功"""
        data = await self.service.get_current_weather("北京")
        
        assert data["city"] == "北京"
        assert data["city_code"] == "101010100"
        assert "temperature" in data
        assert "weather" in data
        assert "humidity" in data
        assert "wind_speed" in data
    
    @pytest.mark.asyncio
    async def test_get_current_weather_city_not_found(self):
        """测试获取实时天气 - 城市未找到"""
        with pytest.raises(ValueError):
            await self.service.get_current_weather("不存在的城市")
    
    @pytest.mark.asyncio
    async def test_get_forecast_success(self):
        """测试获取天气预报 - 成功"""
        data = await self.service.get_forecast("北京", days=3)
        
        assert data["city"] == "北京"
        assert "forecasts" in data
        assert len(data["forecasts"]) == 3
        
        # 验证预报数据结构
        forecast = data["forecasts"][0]
        assert "date" in forecast
        assert "temp_high" in forecast
        assert "temp_low" in forecast
        assert "weather" in forecast
    
    @pytest.mark.asyncio
    async def test_get_forecast_all_days(self):
        """测试获取天气预报 - 7天"""
        data = await self.service.get_forecast("上海", days=7)
        assert len(data["forecasts"]) == 7
    
    @pytest.mark.asyncio
    async def test_get_aqi_success(self):
        """测试获取空气质量 - 成功"""
        data = await self.service.get_aqi("北京")
        
        assert data["city"] == "北京"
        assert "aqi" in data
        assert "level" in data
        assert "pollutants" in data
    
    @pytest.mark.asyncio
    async def test_get_alerts_success(self):
        """测试获取天气预警 - 成功"""
        data = await self.service.get_alerts("北京")
        
        assert data["city"] == "北京"
        assert "has_alerts" in data
        assert "alerts" in data
        assert "alerts_count" in data


class TestWeatherCodes:
    """天气代码映射测试"""
    
    def test_weather_codes_exist(self):
        """测试天气代码定义"""
        service = WeatherService()
        
        assert "00" in service.WEATHER_CODES
        assert "01" in service.WEATHER_CODES
        assert "03" in service.WEATHER_CODES
    
    def test_weather_code_info(self):
        """测试天气代码信息"""
        service = WeatherService()
        
        sunny = service.WEATHER_CODES["00"]
        assert sunny["name"] == "晴"
        assert sunny["icon"] == "☀️"
    
    def test_rain_code(self):
        """测试雨天代码"""
        service = WeatherService()
        
        rain = service.WEATHER_CODES["03"]
        assert rain["name"] == "小雨"


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
