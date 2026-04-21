#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
设置 weather-api 仓库的后端地址
"""

import sys
import os
import io

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import Session
from src.models.repository import Repository

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/api_platform"
)


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    print("=" * 60)
    print("设置 weather-api 后端地址")
    print("=" * 60)
    
    engine = create_engine(DATABASE_URL, echo=False)
    
    with Session(engine) as db:
        # 查找 weather-api 仓库
        result = db.execute(select(Repository).where(Repository.slug == "weather-api"))
        repo = result.scalar_one_or_none()
        
        if not repo:
            print("ERROR: 未找到 weather-api 仓库！")
            return
        
        print(f"\n找到仓库: {repo.name}")
        print(f"当前后端地址: {repo.endpoint_url}")
        
        # 设置后端地址
        backend_url = "http://localhost:8001"
        db.execute(
            update(Repository)
            .where(Repository.id == str(repo.id))
            .values(endpoint_url=backend_url)
        )
        db.commit()
        
        print(f"新后端地址: {backend_url}")
        print("\nOK: 后端地址已设置！")
    
    print("\n" + "=" * 60)
    print("完成！现在可以测试 API 调用了。")
    print("=" * 60)


if __name__ == "__main__":
    main()
