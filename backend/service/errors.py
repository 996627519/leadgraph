#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：errors.py
@Author ：zlh
@Date ：2026-09-10 16:37 
"""
import httpx

class ServiceError(Exception):
    """外部服务故障，隔离处理"""


class SearchError(ServiceError):
    pass


class BudgetExhausted(SearchError):
    pass


class ModelError(ServiceError):
    pass


def is_transient(error):
    status = getattr(error, 'status_code', None)
    response = getattr(error, 'response', None)
    if status is None and response is not None:
        status = getattr(response, 'status_code', None)
    return (
            isinstance(error, (TimeoutError, ConnectionError, httpx.TransportError))
            or (status in (408, 429) or isinstance(status, int) and status >= 500)
            or type(error).__name__ in {'RateLimitError', 'APIConnectionError', 'APITimeoutError'}
    )