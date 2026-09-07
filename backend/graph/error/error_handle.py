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
def invoke_structured_with_retry(llm, schema, messages, max_attempts: int = 3):
    print("进入重试机制")
    last_error = None
    last_raw_output = None
    for attempt in range(1, max_attempts + 1):
        print(f"第 {attempt} 次重试")
        result = llm.invoke(messages)
        if result["parsed"] is not None and result["parsing_error"] is None:
            return result["parsed"]
        parsing_error  = result["parsing_error"]
        raw = result["raw"]
        last_error = parsing_error
        last_raw_output = raw

        if attempt >= max_attempts:
            break
    raise StructuredOutputRetryError(
        message=f"Structured output failed after {max_attempts} attempts.",
        attempts=max_attempts,
        last_error=last_error,
        raw_output=last_raw_output,
    )