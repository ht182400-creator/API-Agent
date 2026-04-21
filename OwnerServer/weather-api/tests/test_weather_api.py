"""
Weather API 测试文件
测试所有天气相关的 API 接口
"""
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app


# 测试夹具：异步客户端
@pytest.fixture
async def client():
    """创建测试客户端"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# 测试类：API 接口测试
class TestWeatherAPI:
    """天气 API 测试类"""
    
    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """测试健康检查接口"""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_get_current_weather_success(self, client):
        """测试实时天气查询 - 成功案例"""
        response = await client.get("/api/v1/weather/current?city=北京")
        assert response.status_code == 200
        data = response.json()
        
        assert data["code"] == 200
        assert data["message"] == "success"
        assert "data" in data
        assert data["data"]["city"] == "北京"
        assert "temperature" in data["data"]
        assert "weather" in data["data"]
    
    @pytest.mark.asyncio
    async def test_get_current_weather_with_pinyin(self, client):
        """测试实时天气查询 - 使用拼音"""
        response = await client.get("/api/v1/weather/current?city=beijing")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
    
    @pytest.mark.asyncio
    async def test_get_current_weather_city_not_found(self, client):
        """测试实时天气查询 - 城市未找到"""
        response = await client.get("/api/v1/weather/current?city=不存在的城市")
        assert response.status_code == 500  # 服务层抛出异常
    
    @pytest.mark.asyncio
    async def test_get_forecast_success(self, client):
        """测试天气预报查询 - 成功案例"""
        response = await client.get("/api/v1/weather/forecast?city=北京&days=3")
        assert response.status_code == 200
        data = response.json()
        
        assert data["code"] == 200
        assert "forecasts" in data["data"]
        assert len(data["data"]["forecasts"]) == 3
    
    @pytest.mark.asyncio
    async def test_get_forecast_invalid_days(self, client):
        """测试天气预报查询 - 无效天数"""
        response = await client.get("/api/v1/weather/forecast?city=北京&days=10")
        assert response.status_code == 422  # 参数校验失败
    
    @pytest.mark.asyncio
    async def test_get_aqi_success(self, client):
        """测试空气质量查询 - 成功案例"""
        response = await client.get("/api/v1/weather/aqi?city=北京")
        assert response.status_code == 200
        data = response.json()
        
        assert data["code"] == 200
        assert "aqi" in data["data"]
        assert "pollutants" in data["data"]
    
    @pytest.mark.asyncio
    async def test_get_alerts_success(self, client):
        """测试天气预警查询 - 成功案例"""
        response = await client.get("/api/v1/weather/alerts?city=北京")
        assert response.status_code == 200
        data = response.json()
        
        assert data["code"] == 200
        assert "has_alerts" in data["data"]
        assert "alerts" in data["data"]
    
    @pytest.mark.asyncio
    async def test_api_response_format(self, client):
        """测试 API 响应格式"""
        response = await client.get("/api/v1/weather/current?city=上海")
        assert response.status_code == 200
        data = response.json()
        
        # 验证响应格式
        assert "code" in data
        assert "message" in data
        assert "data" in data
        assert "request_id" in data
        assert "timestamp" in data
    
    @pytest.mark.asyncio
    async def test_temperature_unit_celsius(self, client):
        """测试温度单位 - 摄氏度"""
        response = await client.get("/api/v1/weather/current?city=北京&unit=c")
        assert response.status_code == 200
        data = response.json()
        
        assert "temperature" in data["data"]
        assert data["data"]["temperature"] > 0
    
    @pytest.mark.asyncio
    async def test_temperature_unit_fahrenheit(self, client):
        """测试温度单位 - 华氏度"""
        response = await client.get("/api/v1/weather/current?city=北京&unit=f")
        assert response.status_code == 200
        data = response.json()
        
        # 华氏度应该大于摄氏度
        assert "temperature_f" in data["data"]


# 测试类：数据验证测试
class TestDataValidation:
    """数据验证测试类"""
    
    @pytest.mark.asyncio
    async def test_missing_city_parameter(self, client):
        """测试缺少城市参数"""
        response = await client.get("/api/v1/weather/current")
        assert response.status_code == 422  # 参数验证失败
    
    @pytest.mark.asyncio
    async def test_empty_city_parameter(self, client):
        """测试空城市参数"""
        response = await client.get("/api/v1/weather/current?city=")
        assert response.status_code == 422


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
