"""优化的 AWS event-stream 解析器

使用 memoryview 和 struct.unpack 加速解析，
支持增量处理和零拷贝操作。
"""

import struct
import json
from typing import Iterator, Optional
from .models import ParsedEvent


class FastEventStreamParser:
    """优化的 AWS event-stream 解析器
    
    使用预编译的 struct 格式和 memoryview 减少内存分配，
    支持增量解析和快速 content 提取。
    """
    
    def __init__(self):
        """初始化解析器"""
        # 预编译 struct 格式：>II = 大端序，两个 unsigned int (4 bytes each)
        # 第一个是 total_length，第二个是 headers_length
        self._struct_header = struct.Struct('>II')
        
        # 缓冲区用于存储跨 chunk 边界的不完整消息
        self._buffer = bytearray()
    
    def feed(self, chunk: bytes) -> Iterator[ParsedEvent]:
        """增量解析 chunk，立即 yield 解析出的事件
        
        Args:
            chunk: 从网络接收的字节数据
            
        Yields:
            ParsedEvent: 解析出的事件对象
        """
        # 将新 chunk 追加到缓冲区
        self._buffer.extend(chunk)
        
        # 使用 memoryview 避免字节切片的内存拷贝
        view = memoryview(self._buffer)
        pos = 0
        
        while pos < len(view):
            # 检查是否有足够的字节读取头部（12 bytes: 4+4+4 for prelude+crc）
            if pos + 12 > len(view):
                break
            
            # 使用预编译的 struct 一次性解析头部
            try:
                total_len, headers_len = self._struct_header.unpack(view[pos:pos+8])
            except struct.error:
                # 头部损坏，跳过这个字节并尝试下一个位置
                pos += 1
                continue
            
            # 验证消息长度的合理性
            if total_len == 0 or total_len > len(view) - pos:
                # 消息不完整，等待更多数据
                break
            
            # 跳过 prelude CRC (4 bytes)
            # 计算 payload 位置
            payload_start = pos + 12 + headers_len
            payload_end = pos + total_len - 4  # 减去 message CRC
            
            if payload_start < payload_end:
                # 提取 payload（使用 memoryview 零拷贝）
                payload_view = view[payload_start:payload_end]
                
                # 尝试快速提取 content（直接返回字符串，不创建 ParsedEvent）
                content = self._extract_content_fast(payload_view)
                if content:
                    # 只为 content delta 创建事件对象
                    yield ParsedEvent(
                        event_type='assistantResponseEvent',
                        content=content
                    )
            
            # 移动到下一个消息
            pos += total_len
        
        # 保留未处理的字节到缓冲区
        if pos > 0:
            self._buffer = bytearray(view[pos:])
    
    def _extract_content_fast(self, payload_view: memoryview) -> Optional[str]:
        """快速提取 content 字段（内联优化）
        
        Args:
            payload_view: payload 的 memoryview
            
        Returns:
            提取的 content 字符串，如果不存在返回 None
        """
        try:
            # 将 memoryview 转换为 bytes 进行 JSON 解析
            payload_bytes = bytes(payload_view)
            payload = json.loads(payload_bytes.decode('utf-8'))
            
            # 快速路径：只提取 content
            if 'assistantResponseEvent' in payload:
                event = payload['assistantResponseEvent']
                if isinstance(event, dict) and 'content' in event:
                    content = event['content']
                    if isinstance(content, str):
                        return content
            
            # 备用路径：直接 content
            if 'content' in payload:
                content = payload['content']
                if isinstance(content, str):
                    return content
            
            return None
            
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None
    
    def _parse_event(self, payload_view: memoryview) -> Optional[ParsedEvent]:
        """解析单个事件
        
        Args:
            payload_view: payload 的 memoryview
            
        Returns:
            ParsedEvent 对象，如果解析失败返回 None
        """
        try:
            # 将 memoryview 转换为 bytes 进行 JSON 解析
            payload_bytes = bytes(payload_view)
            payload = json.loads(payload_bytes.decode('utf-8'))
            
            # 快速路径：提取 content
            content = self.parse_content_fast(payload)
            if content:
                return ParsedEvent(
                    event_type='assistantResponseEvent',
                    content=content
                )
            
            # 慢速路径：检查其他事件类型
            # toolUseEvent
            if 'toolUseId' in payload:
                return ParsedEvent(
                    event_type='toolUseEvent',
                    tool_id=payload.get('toolUseId', ''),
                    tool_name=payload.get('name', ''),
                    tool_input=payload.get('input', ''),
                    raw_payload=payload_bytes
                )
            
            # 其他事件类型保留原始 payload
            return ParsedEvent(
                event_type='unknown',
                raw_payload=payload_bytes
            )
            
        except (json.JSONDecodeError, UnicodeDecodeError):
            # JSON 解析失败，返回 None
            return None
    
    def parse_content_fast(self, payload: dict) -> Optional[str]:
        """快速提取 content 字段，不完整解析 JSON
        
        Args:
            payload: 已解析的 payload 字典
            
        Returns:
            提取的 content 字符串，如果不存在返回 None
        """
        # 尝试两种格式：
        # 1. assistantResponseEvent.content
        if 'assistantResponseEvent' in payload:
            event = payload['assistantResponseEvent']
            if isinstance(event, dict) and 'content' in event:
                content = event['content']
                if isinstance(content, str):
                    return content
        
        # 2. 直接 content
        if 'content' in payload:
            content = payload['content']
            if isinstance(content, str):
                return content
        
        return None
