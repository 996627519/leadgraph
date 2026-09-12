#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：error_handle.py
@Author ：zlh
@Date ：2026-09-07 16:03 
"""
from backend.graph.llm.deepseek import get_structured_deepseek
from langchain_core.messages import SystemMessage, HumanMessage

from backend.graph.error.exception import StructuredOutputRetryError


# llm结构化输出错误，尝试重试
async def ainvoke_structured_with_retry(llm, schema, messages, max_attempts=2):
    service = ModelService(Settings(llm_attempts=max_attempts), factory=lambda _: llm)
    return await service.generate(schema, messages)

def invoke_structured_with_retry(llm, schema, messages, max_attempts=2):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(ainvoke_structured_with_retry(llm, schema, messages, max_attempts))
    raise RuntimeError('Use await ainvoke_structured_with_retry inside an async node')