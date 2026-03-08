# 需求文档

## 介绍

Kiro 代理服务在流式响应时，从 Kiro API 接收到数据到用户看到 token 之间存在明显延迟。当前实现（kiro_proxy/handlers/anthropic.py 的 _handle_stream 函数）中，每个 chunk 都需要完整解析 AWS event-stream 二进制格式、JSON 解码 payload、构造 SSE JSON 字符串并序列化，这些操作累积成显著的单 token 输出延迟。本功能旨在降低每个 token 的响应延迟，提升流式输出的实时性。

## 术语表

- **Token_Latency**: Token 延迟，从 Kiro API 返回数据到用户看到 token 的时间间隔
- **Stream_Parser**: AWS event-stream 格式解析器，负责将二进制流解析为结构化数据
- **SSE_Generator**: SSE 事件生成器，负责将解析后的数据转换为 Server-Sent Events 格式
- **Event_Stream**: AWS 事件流格式，一种二进制消息协议
- **Chunk**: 从上游 API 接收的单个数据块

## 需求

### 需求 1: 加速 Event-Stream 解析

**用户故事:** 作为用户，我希望减少每个 chunk 的解析时间，以便更快看到 token 输出。

#### 验收标准

1. THE Stream_Parser SHALL 使用 memoryview 操作替代字节切片以减少内存分配
2. THE Stream_Parser SHALL 使用 struct.unpack 替代 int.from_bytes 以加速字节解析
3. WHEN 解析 event-stream 头部时，THE Stream_Parser SHALL 一次性读取所有头部字段而非多次切片
4. THE Stream_Parser SHALL 跳过不需要的字段解析（如 CRC 校验）
5. FOR ALL 有效的 event-stream 数据，解析后再序列化 SHALL 产生等效的结构（round-trip property）

### 需求 2: 减少 JSON 编解码开销

**用户故事:** 作为用户，我希望最小化 JSON 处理时间，以便降低 token 输出延迟。

#### 验收标准

1. THE SSE_Generator SHALL 使用预构建的字符串模板而非每次 json.dumps 构造完整对象
2. WHEN 生成 SSE 事件时，THE SSE_Generator SHALL 仅对变化的内容字段进行 JSON 转义
3. THE SSE_Generator SHALL 缓存固定的 JSON 片段（如 "type":"content_block_delta"）
4. THE Stream_Parser SHALL 使用增量 JSON 解析提取 content 字段而非解析完整 payload
5. FOR ALL 生成的 SSE 事件，JSON 解析结果 SHALL 与原始数据语义等价（metamorphic property）

### 需求 3: 优化数据流转路径

**用户故事:** 作为用户，我希望减少数据在处理管道中的停留时间，以便实时看到 token。

#### 验收标准

1. WHEN 从上游接收到 chunk 时，THE System SHALL 立即开始解析而非等待完整 chunk
2. THE System SHALL 使用零拷贝技术在解析和输出之间传递数据
3. THE System SHALL 避免在内存中累积 full_response 和 full_content（除非需要记录）
4. WHEN 解析出 content 时，THE System SHALL 立即 yield 而非等待 chunk 处理完成
5. FOR ALL 流式处理，输出顺序 SHALL 与接收顺序严格一致（invariant property）

### 需求 4: 保持协议兼容性

**用户故事:** 作为 API 用户，我希望优化不影响现有功能，以便无缝升级。

#### 验收标准

1. THE System SHALL 保持与现有 Anthropic API 的完全兼容
2. THE System SHALL 输出与优化前相同的 SSE 事件序列和内容
3. WHEN 遇到解析错误时，THE System SHALL 记录错误并继续处理后续数据
4. THE System SHALL 正确处理所有现有的 event-stream 消息类型
5. FOR ALL 有效输入，优化后的输出 SHALL 与优化前的输出完全一致（equivalence property）
