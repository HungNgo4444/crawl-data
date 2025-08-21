"""
GWEN-3 Client Package for Vietnamese Content Analysis
Provides Ollama API integration for domain parsing template generation
Author: James (Dev Agent)
Date: 2025-08-11
"""

__version__ = "1.0.0"
__author__ = "James (Dev Agent)"

from .ollama_client import OllamaGWEN3Client
from .model_wrapper import GWEN3ModelWrapper
from .health_check import GWEN3HealthChecker

__all__ = [
    "OllamaGWEN3Client",
    "GWEN3ModelWrapper", 
    "GWEN3HealthChecker"
]