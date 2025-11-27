"""Setup configuration for fastapi-easy"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="fastapi-easy",
    version="0.1.3",
    author="FastAPI-Easy Team",
    description="A modern CRUD framework for FastAPI",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ardss/fastapi-easy",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: GNU Affero General Public License v3",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "fastapi>=0.100.0",
        "pydantic>=2.0.0",
        "pymongo>=4.0.0",
        "motor>=3.0.0",
    ],
    extras_require={
        "sqlalchemy": ["sqlalchemy>=2.0.0"],
        "tortoise": ["tortoise-orm>=0.19.0"],
        "sqlmodel": ["sqlmodel>=0.0.8"],
        "mongo": ["motor>=3.3.0"],
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
    },
)
