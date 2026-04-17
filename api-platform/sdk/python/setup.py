"""
API Platform Python SDK - 安装配置
"""

from setuptools import setup, find_packages
import os

# 读取README
here = os.path.abspath(os.path.dirname(__file__))
readme_path = os.path.join(here, "README.md")
if os.path.exists(readme_path):
    with open(readme_path, encoding="utf-8") as f:
        long_description = f.read()
else:
    long_description = "API Platform Python SDK"

setup(
    name="api-platform-sdk",
    version="1.0.0",
    author="API Platform Team",
    author_email="support@platform.com",
    description="Official Python SDK for API Platform",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/api-platform/sdk",
    packages=find_packages(exclude=["tests", "tests.*"]),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.25.0",
    ],
    extras_require={
        "async": ["aiohttp>=0.21.0"],
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.18.0",
            "pytest-cov>=3.0.0",
            "black>=22.0.0",
            "isort>=5.10.0",
            "mypy>=0.950",
        ],
    },
    project_urls={
        "Bug Reports": "https://github.com/api-platform/sdk/issues",
        "Documentation": "https://docs.platform.com/sdk/python",
        "Source": "https://github.com/api-platform/sdk",
    },
)
