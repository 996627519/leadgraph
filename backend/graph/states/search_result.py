#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：search_result.py
@Author ：zlh
@Date ：2026-09-11 22:28 
"""
from pydantic import BaseModel

class SearchResult(BaseModel):
    task_id: str | None = None
    title: str = ''
    url: str
    snippet: str = ''
    domain: str | None = None
    provider: str | None = None
    source: str | None = None
    score: float | None = None

class WorkerError(BaseModel):
    stage: str
    task_id: str = ''
    error_class: str
    message: str
    retryable: bool = False
