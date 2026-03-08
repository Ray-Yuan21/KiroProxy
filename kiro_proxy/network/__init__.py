"""网络优化模块

提供 HTTP 客户端池和连接复用功能。
"""

from .client_pool import get_http_client, close_http_client

__all__ = ['get_http_client', 'close_http_client']
