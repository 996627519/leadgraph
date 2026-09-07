#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：node_error.py
@Author ：zlh
@Date ：2026-09-07 16:01 
"""
from pydantic import BaseModel

from backend.graph.error.error_type import ErrorType


class NodeError(BaseModel):
    node_name: str

    error_type: ErrorType

    error_class: str
    error_message: str

    retryable: bool

    attempt: int

    raw_output: str | None = None