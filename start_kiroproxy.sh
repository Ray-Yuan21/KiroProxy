#!/bin/zsh
cd /Users/rubil/work/tool/KiroProxy

# 启用流式性能优化（默认启用）
export ENABLE_STREAM_OPTIMIZATION=true

# 过滤 system 提示词（默认启用）
export FILTER_SYSTEM_PROMPT=true

/Users/rubil/miniconda/miniconda3/envs/ybr/bin/python run.py 4399
