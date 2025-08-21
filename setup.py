"""
Setup script for Domain Management System
"""

from setuptools import setup, find_packages

setup(
    name="domain-management-system",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "SQLAlchemy>=2.0.0",
        "psycopg2-binary>=2.9.5",
        "pytest>=7.4.0",
        "pytest-asyncio>=0.21.0",
        "pytest-mock>=3.11.0",
    ],
    python_requires=">=3.8",
)