"""流式性能优化模块

提供优化的 event-stream 解析器和 SSE 事件构造器，
降低流式响应的 token 输出延迟。
"""

from .models import ParsedEvent
from .parser import FastEventStreamParser
from .builder import SSEEventBuilder

__all__ = ['ParsedEvent', 'FastEventStreamParser', 'SSEEventBuilder']
