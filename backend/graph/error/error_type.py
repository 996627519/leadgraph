#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：error_type.py
@Author ：zlh
@Date ：2026-09-07 15:58 
"""
from enum import Enum

class ErrorType(str, Enum):
    # 临时性错误
    TRANSIENT = "transient"
    # 结构化输出错误
    STRUCTURED_OUTPUT = "structured_output"
    # 上下文错误
    CONTEXT = "context"
    # 数据不足
    DATA_INSUFFICIENT = "data_insufficient"
    # 代码逻辑错误
    CODE_ERROR = "code_error"
    # 位置错误
    UNKNOWN = "unknown"