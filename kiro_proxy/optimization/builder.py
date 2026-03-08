"""优化的 SSE 事件构造器

使用预构建模板和最小化 JSON 操作，
避免重复序列化固定字段。
"""

import json


class SSEEventBuilder:
    """优化的 SSE 事件构造器
    
    使用预构建模板和最小化 JSON 操作，
    避免重复序列化固定字段。
    """
    
    # 预构建的模板字符串
    CONTENT_DELTA_TEMPLATE = 'data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":%s}}\n\n'
    
    def __init__(self):
        """初始化构造器"""
        pass
    
    def escape_json_string(self, s: str) -> str:
        """快速 JSON 字符串转义
        
        Args:
            s: 原始字符串
            
        Returns:
            转义后的 JSON 字符串（带引号）
        """
        # 直接使用 json.dumps 更快
        return json.dumps(s)
    
    def build_content_delta(self, content: str) -> str:
        """构造 content_block_delta 事件
        
        Args:
            content: 文本内容
            
        Returns:
            完整的 SSE 事件字符串
        """
        # 转义 content 字符串
        escaped_content = json.dumps(content)
        
        # 使用模板构造完整事件
        return self.CONTENT_DELTA_TEMPLATE % escaped_content
