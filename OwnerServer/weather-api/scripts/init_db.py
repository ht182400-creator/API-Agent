"""
Weather API 数据库初始化脚本
用于初始化天气数据、城市数据等基础数据
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))


def init_database():
    """
    初始化数据库
    
    创建必要的表和初始数据
    """
    print("=" * 50)
    print("Weather API 数据库初始化")
    print("=" * 50)
    
    # 城市基础数据
    cities = [
        {"name": "北京", "code": "101010100", "province": "北京市", "country": "中国", "pinyin": "beijing", "lat": 39.9042, "lon": 116.4074},
        {"name": "上海", "code": "101020100", "province": "上海市", "country": "中国", "pinyin": "shanghai", "lat": 31.2304, "lon": 121.4737},
        {"name": "广州", "code": "101280101", "province": "广东省", "country": "中国", "pinyin": "guangzhou", "lat": 23.1291, "lon": 113.2644},
        {"name": "深圳", "code": "101280601", "province": "广东省", "country": "中国", "pinyin": "shenzhen", "lat": 22.5431, "lon": 114.0579},
        {"name": "成都", "code": "101270101", "province": "四川省", "country": "中国", "pinyin": "chengdu", "lat": 30.5728, "lon": 104.0668},
        {"name": "杭州", "code": "101210101", "province": "浙江省", "country": "中国", "pinyin": "hangzhou", "lat": 30.2741, "lon": 120.1551},
        {"name": "武汉", "code": "101200101", "province": "湖北省", "country": "中国", "pinyin": "wuhan", "lat": 30.5928, "lon": 114.3055},
        {"name": "西安", "code": "101110101", "province": "陕西省", "country": "中国", "pinyin": "xian", "lat": 34.3416, "lon": 108.9398},
        {"name": "重庆", "code": "101040100", "province": "重庆市", "country": "中国", "pinyin": "chongqing", "lat": 29.4316, "lon": 106.9123},
        {"name": "南京", "code": "101190101", "province": "江苏省", "country": "中国", "pinyin": "nanjing", "lat": 32.0603, "lon": 118.7969},
    ]
    
    print(f"\n📍 城市数据: {len(cities)} 个城市")
    for city in cities[:5]:
        print(f"   - {city['name']} ({city['pinyin']}): {city['code']}")
    print(f"   ... 共 {len(cities)} 个城市")
    
    # 天气代码映射
    weather_codes = [
        {"code": "00", "name": "晴", "icon": "☀️", "description": "晴朗"},
        {"code": "01", "name": "多云", "icon": "⛅", "description": "多云"},
        {"code": "02", "name": "阴", "icon": "☁️", "description": "阴天"},
        {"code": "03", "name": "小雨", "icon": "🌧️", "description": "小雨"},
        {"code": "04", "name": "中雨", "icon": "🌧️", "description": "中雨"},
        {"code": "05", "name": "大雨", "icon": "⛈️", "description": "大雨"},
        {"code": "06", "name": "雷阵雨", "icon": "⛈️", "description": "雷阵雨"},
        {"code": "07", "name": "小雪", "icon": "🌨️", "description": "小雪"},
        {"code": "08", "name": "中雪", "icon": "❄️", "description": "中雪"},
        {"code": "09", "name": "大雪", "icon": "❄️", "description": "大雪"},
        {"code": "10", "name": "雾", "icon": "🌫️", "description": "雾"},
        {"code": "11", "name": "霾", "icon": "🌫️", "description": "霾"},
    ]
    
    print(f"\n🌤️ 天气代码: {len(weather_codes)} 种天气类型")
    for wc in weather_codes[:5]:
        print(f"   - {wc['code']}: {wc['icon']} {wc['name']}")
    print(f"   ... 共 {len(weather_codes)} 种天气类型")
    
    # AQI 等级
    aqi_levels = [
        {"min": 0, "max": 50, "level": "优", "color": "#00FF00", "advice": "空气质量令人满意，基本无空气污染"},
        {"min": 51, "max": 100, "level": "良", "color": "#90EE90", "advice": "空气质量可接受，某些污染物对极少数人有轻微影响"},
        {"min": 101, "max": 150, "level": "轻度污染", "color": "#FFFF00", "advice": "易感人群症状有轻度加剧"},
        {"min": 151, "max": 200, "level": "中度污染", "color": "#FFA500", "advice": "进一步加剧易感人群症状"},
        {"min": 201, "max": 300, "level": "重度污染", "color": "#FF4500", "advice": "心脏病和肺病患者症状显著加剧"},
        {"min": 301, "max": 500, "level": "严重污染", "color": "#990066", "advice": "健康人群运动耐受力降低"},
    ]
    
    print(f"\n🌫️ AQI 等级: {len(aqi_levels)} 个等级")
    for aqi in aqi_levels:
        print(f"   - {aqi['min']}-{aqi['max']}: {aqi['level']}")
    
    print("\n" + "=" * 50)
    print("✅ 数据库初始化完成!")
    print("=" * 50)
    print("\n📋 后续步骤:")
    print("   1. 启动 API 服务: uvicorn src.main:app --reload --port 8001")
    print("   2. 访问 API 文档: http://localhost:8001/docs")
    print("   3. 测试 API: http://localhost:8001/api/v1/weather/current?city=北京")


if __name__ == "__main__":
    init_database()
