#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：exception.py
@Author ：zlh
@Date ：2026-09-07 16:27 
"""
class LeadGraphError(Exception):
    """LeadGraph 项目的基础异常类"""
    pass

class StructuredOutputError(LeadGraphError):
    """LLM 返回结果无法解析为指定的 Structured Output。"""
    pass

class StructuredOutputRetryError(StructuredOutputError):
    """Structured Output 多次修复/重试后仍然失败。"""

    def __init__(
        self,
        message: str,
        attempts: int,
        last_error: Exception | None = None,
        raw_output: str | None = None,
    ):
        super().__init__(message)

        self.attempts = attempts
        self.last_error = last_error
        self.raw_output = raw_output