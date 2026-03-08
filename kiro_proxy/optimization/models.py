"""核心数据模型"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ParsedEvent:
    """解析出的 event-stream 事件
    
    Attributes:
        event_type: 事件类型，如 'assistantResponseEvent', 'toolUseEvent'
        content: 文本内容（如果是 content delta 事件）
        tool_id: 工具调用 ID（如果是 tool use 事件）
        tool_name: 工具名称（如果是 tool use 事件）
        tool_input: 工具输入（如果是 tool use 事件）
        raw_payload: 原始 payload 字节（慢速路径使用）
    """
    
    event_type: str
    content: Optional[str] = None
    tool_id: Optional[str] = None
    tool_name: Optional[str] = None
    tool_input: Optional[str] = None
    raw_payload: Optional[bytes] = None
    
    @property
    def is_content_delta(self) -> bool:
        """是否为 content delta 事件
        
        Returns:
            如果是包含文本内容的 assistantResponseEvent，返回 True
        """
        return self.content is not None and self.event_type == 'assistantResponseEvent'
