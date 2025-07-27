"""
LessLLM - A lightweight LLM API proxy framework
"""

__version__ = "0.1.0"
__author__ = "LessLLM Team"

from .config import Config, configure
from .server import start_server

__all__ = [
    "Config",
    "configure", 
    "start_server",
    "__version__"
]