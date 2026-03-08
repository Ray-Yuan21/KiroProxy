"""全局 HTTP 客户端池

提供复用的 httpx 客户端，避免每次请求都创建新连接。
优化 TCP/TLS 握手时间，预期节省 1-3 秒。
"""

import httpx
from typing import Optional


class ClientPool:
    """HTTP 客户端池管理器"""
    
    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None
    
    def get_client(self) -> httpx.AsyncClient:
        """获取全局客户端实例
        
        Returns:
            配置好的 httpx.AsyncClient 实例
        """
        if self._client is None or self._client.is_closed:
            self._client = self._create_client()
        return self._client
    
    def _create_client(self) -> httpx.AsyncClient:
        """创建配置好的客户端
        
        Returns:
            新的 httpx.AsyncClient 实例
        """
        return httpx.AsyncClient(
            verify=False,
            timeout=httpx.Timeout(
                connect=10.0,    # 连接超时
                read=300.0,      # 读取超时
                write=30.0,      # 写入超时
                pool=10.0        # 连接池超时
            ),
            limits=httpx.Limits(
                max_keepalive_connections=20,  # 保持活动的连接数
                max_connections=100,            # 最大连接数
                keepalive_expiry=30.0          # 连接保持时间（秒）
            ),
            http2=False,  # 暂时禁用 HTTP/2（需要安装 h2 包）
            follow_redirects=True
        )
    
    async def close(self):
        """关闭客户端"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None


# 全局客户端池实例
_client_pool = ClientPool()


def get_http_client() -> httpx.AsyncClient:
    """获取全局 HTTP 客户端
    
    使用示例:
        client = get_http_client()
        response = await client.get("https://example.com")
    
    Returns:
        配置好的 httpx.AsyncClient 实例
    """
    return _client_pool.get_client()


async def close_http_client():
    """关闭全局 HTTP 客户端
    
    在应用关闭时调用
    """
    await _client_pool.close()
