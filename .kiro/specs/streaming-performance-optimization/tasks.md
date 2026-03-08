# 实施计划：流式性能优化

## 概述

本实施计划将优化 Kiro 代理服务的流式响应性能，通过引入 FastEventStreamParser、SSEEventBuilder 和 OptimizedStreamHandler 三个核心组件，降低单 token 延迟至少 30%。实施策略采用快速路径（content delta）和慢速路径（其他事件）分离，使用 memoryview、struct.unpack、模板化输出等技术实现零拷贝和立即 yield。

## 任务

- [x] 1. 创建核心数据模型和工具模块
  - 创建 `kiro_proxy/optimization/` 目录
  - 实现 `ParsedEvent` 数据类，包含 event_type、content、tool_id 等字段
  - 实现 `is_content_delta` 属性方法
  - _需求: 1.5, 2.5_

- [-] 2. 实现 FastEventStreamParser 解析器
  - [x] 2.1 实现基础解析器结构
    - 创建 `kiro_proxy/optimization/parser.py`
    - 实现 `FastEventStreamParser` 类，使用 `struct.Struct('>II')` 预编译头部格式
    - 实现 `__init__` 方法，初始化 buffer 和 struct
    - _需求: 1.1, 1.2, 1.3_
  
  - [x] 2.2 实现增量 feed 方法
    - 实现 `feed(chunk: bytes) -> Iterator[ParsedEvent]` 方法
    - 使用 memoryview 避免字节切片的内存拷贝
    - 处理跨 chunk 边界的不完整消息（缓存到下一个 chunk）
    - 边接收边解析，立即 yield 解析出的事件
    - _需求: 1.1, 1.2, 3.1, 3.2_
  
  - [x] 2.3 实现快速 content 提取
    - 实现 `parse_content_fast(payload_view: memoryview) -> Optional[str]` 方法
    - 使用增量 JSON 解析只提取 content 字段，不解析完整 payload
    - 处理 `assistantResponseEvent.content` 和直接 `content` 两种格式
    - _需求: 2.4, 3.2_
  
  - [ ] 2.4 编写 FastEventStreamParser 单元测试
    - 测试解析单个完整消息
    - 测试解析跨 chunk 边界的消息
    - 测试处理空 chunk
    - 测试处理损坏的消息头
    - 测试处理无效的 JSON
    - _需求: 1.5, 4.3_

- [-] 3. 实现 SSEEventBuilder 构造器
  - [x] 3.1 实现基础构造器结构
    - 创建 `kiro_proxy/optimization/builder.py`
    - 实现 `SSEEventBuilder` 类
    - 定义 `CONTENT_DELTA_TEMPLATE` 预构建模板字符串
    - 实现 `__init__` 方法，构建 JSON 转义表
    - _需求: 2.1, 2.2, 2.3_
  
  - [x] 3.2 实现快速 JSON 转义
    - 实现 `escape_json_string(s: str) -> str` 方法
    - 使用预构建转义表处理特殊字符（引号、换行、反斜杠、制表符等）
    - 返回带引号的转义后字符串
    - _需求: 2.2_
  
  - [x] 3.3 实现 content delta 事件构造
    - 实现 `build_content_delta(content: str) -> str` 方法
    - 使用模板字符串和 escape_json_string 构造完整 SSE 事件
    - 避免使用 json.dumps 序列化完整对象
    - _需求: 2.1, 2.2, 2.3_
  
  - [ ] 3.4 编写 SSEEventBuilder 单元测试
    - 测试构造 content_block_delta 事件
    - 测试转义特殊字符（引号、换行、反斜杠）
    - 测试处理空字符串
    - 测试处理 Unicode 字符
    - _需求: 2.5_

- [ ] 4. 检查点 - 核心组件验证
  - 确保所有测试通过，询问用户是否有问题

- [-] 5. 实现优化的流式处理管道
  - [x] 5.1 创建优化的流式处理函数
    - 在 `kiro_proxy/handlers/anthropic.py` 中创建 `_handle_stream_optimized` 函数
    - 复制 `_handle_stream` 的函数签名和重试逻辑框架
    - 保持相同的错误处理、账号切换、配额管理逻辑
    - _需求: 4.1, 4.2_
  
  - [x] 5.2 集成 FastEventStreamParser 和 SSEEventBuilder
    - 在 generate() 函数中实例化 parser 和 builder
    - 替换原有的 chunk 解析逻辑为 `parser.feed(chunk)`
    - 实现快速路径：检测 `event.is_content_delta`，使用 `builder.build_content_delta` 立即 yield
    - 实现慢速路径：处理 tool_use、message_start 等事件，保持原有完整解析逻辑
    - _需求: 3.1, 3.2, 3.4_
  
  - [x] 5.3 移除数据累积优化内存使用
    - 移除 `full_response` 累积（除非需要用于最终解析）
    - 保留 `full_content` 用于日志记录和 flow_monitor
    - 确保 flow_monitor.add_chunk 在快速路径中正确调用
    - _需求: 3.3_
  
  - [x] 5.4 处理 tool_use 和结束事件
    - 在流式处理结束后，使用 `parse_event_stream_full` 解析完整响应
    - 生成 tool_use 相关的 SSE 事件（content_block_start、content_block_delta、content_block_stop）
    - 生成 message_delta 和 message_stop 事件
    - 调用 flow_monitor.complete_flow 记录完整响应
    - _需求: 4.1, 4.4_
  
  - [ ] 5.5 编写优化流式处理的集成测试
    - 测试完整的流式处理流程
    - 测试错误恢复场景
    - 测试与原始实现的输出对比
    - _需求: 4.2, 4.5_

- [ ] 6. 实现功能开关和降级策略
  - [x] 6.1 实现功能开关
    - 创建 `_should_use_optimized_stream(model: str) -> bool` 函数
    - 读取环境变量 `ENABLE_STREAM_OPTIMIZATION`（默认 "true"）
    - 在主处理函数中根据开关选择使用优化或原始实现
    - _需求: 4.2_
  
  - [ ] 6.2 实现错误降级逻辑
    - 在 `_handle_stream_optimized` 中捕获解析错误
    - 记录详细错误日志（error_type、position、partial_data）
    - 对单个 chunk 回退到原始解析逻辑
    - 如果错误率超过阈值，整个请求回退到原始实现
    - _需求: 4.3_
  
  - [ ] 6.3 编写降级策略测试
    - 测试功能开关的启用和禁用
    - 测试遇到解析错误时的降级行为
    - 测试错误率阈值触发的完整降级
    - _需求: 4.3_

- [ ] 7. 检查点 - 集成验证
  - 确保所有测试通过，询问用户是否有问题

- [ ] 8. 实现属性测试验证正确性
  - [ ] 8.1 设置 hypothesis 测试框架
    - 安装 hypothesis 库（如果尚未安装）
    - 创建 `tests/test_streaming_optimization_properties.py`
    - 配置 hypothesis 设置（最少 100 次迭代）
    - _需求: 1.5, 2.5, 3.5, 4.5_
  
  - [ ] 8.2 实现属性 1: Event-Stream 解析 Round-Trip 测试
    - **属性 1: Event-Stream 解析 Round-Trip**
    - **验证需求: 1.5**
    - 使用 `@given(valid_event_stream_data())` 生成测试数据
    - 解析 → 序列化 → 再解析，验证结果等价
    - 创建 `valid_event_stream_data()` 策略生成有效的 event-stream 数据
    - _需求: 1.5_
  
  - [ ] 8.3 实现属性 2: SSE 事件语义等价测试
    - **属性 2: SSE 事件语义等价**
    - **验证需求: 2.5**
    - 使用 `@given(text_content())` 生成测试数据
    - 构造 SSE 事件 → 解析 JSON → 验证 content 字段相同
    - 创建 `text_content()` 策略生成各种文本内容
    - _需求: 2.5_
  
  - [ ] 8.4 实现属性 3: 流式输出顺序不变量测试
    - **属性 3: 流式输出顺序不变量**
    - **验证需求: 3.5**
    - 使用 `@given(event_stream_sequence())` 生成测试数据
    - 验证输出 SSE 事件顺序与输入 event-stream 事件顺序一致
    - 创建 `event_stream_sequence()` 策略生成事件序列
    - _需求: 3.5_
  
  - [ ] 8.5 实现属性 4: 优化前后等价性测试
    - **属性 4: 优化前后等价性**
    - **验证需求: 4.2, 4.5**
    - 使用 `@given(valid_kiro_response())` 生成测试数据
    - 对比原始实现和优化实现的输出，验证完全一致
    - 创建 `valid_kiro_response()` 策略生成有效的 Kiro 响应数据
    - _需求: 4.2, 4.5_
  
  - [ ] 8.6 实现属性 5: 错误恢复能力测试
    - **属性 5: 错误恢复能力**
    - **验证需求: 4.3**
    - 使用 `@given(corrupted_event_stream())` 生成测试数据
    - 验证遇到解析错误后能继续处理后续有效数据
    - 创建 `corrupted_event_stream()` 策略生成包含损坏数据的流
    - _需求: 4.3_

- [ ] 9. 性能验证和基准测试
  - [ ] 9.1 创建性能测试脚本
    - 创建 `tests/benchmark_streaming.py`
    - 实现延迟测量（单 token 输出延迟）
    - 实现吞吐量测量（每秒处理的 token 数）
    - 实现内存使用测量（峰值内存）
    - _需求: 1.1, 1.2, 2.1, 3.2, 3.3_
  
  - [ ] 9.2 运行基准测试并验证目标
    - 对比优化前后的延迟（目标：降低 ≥ 30%）
    - 对比优化前后的内存使用（目标：降低 ≥ 20%）
    - 对比优化前后的吞吐量（目标：提升 ≥ 25%）
    - 记录测试结果并生成报告
    - _需求: 1.1, 1.2, 2.1, 3.2, 3.3_

- [ ] 10. 最终检查点
  - 确保所有测试通过，询问用户是否准备部署

## 注意事项

- 标记 `*` 的任务为可选任务，可以跳过以加快 MVP 交付
- 每个任务都引用了具体的需求编号以确保可追溯性
- 检查点任务确保增量验证，及时发现问题
- 属性测试使用 hypothesis 库，每个测试至少运行 100 次迭代
- 性能测试不是正确性测试，但验证优化目标是否达成
- 保持与现有 Anthropic API 的完全兼容性
- 实施过程中保留原始实现作为回退方案
