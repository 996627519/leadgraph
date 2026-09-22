#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：research_agent 
@File ：search_service.py
@Author ：zlh
@Date ：2026-07-20 15:33 
"""
import asyncio
import copy
import json
import os
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote
from dotenv import load_dotenv
from backend.config.settings import Settings
from backend.service.errors import BudgetExhausted, SearchError, is_transient
from dataclasses import asdict
from langchain_mcp_adapters.client import MultiServerMCPClient


"""
异步搜索模块
功能：
1. 请求合并
2. 缓存
3. 限流
4. 预算控制
5. 重试
6. 指标统计
"""
# 结果归一化
def normalize_response(value):
    if isinstance(value, str):
        try:
            return normalize_response(json.loads(value))
        except (ValueError, RecursionError) as exc:
            raise SearchError('非法JSON') from exc
    if hasattr(value, 'model_dump'):
        value = value.model_dump(by_alias=True)
    if isinstance(value, dict):
        if value.get('isError') or value.get('is_error') or value.get('error'):
            raise SearchError('搜索引擎出错')
        if 'results' in value:
            if not isinstance(value['results'], list) or not all(isinstance(x, dict) for x in value['results']):
                raise SearchError('搜索结果必须是list')
            return value
        for key in ('structuredContent', 'structured_content', 'content'):
            if value.get(key) is not None:
                return normalize_response(value[key])
        if 'text' in value:
            return normalize_response(value['text'])
    if isinstance(value, list):
        for block in value:
            if isinstance(block, dict) and 'text' in block:
                try:
                    return normalize_response(block['text'])
                except SearchError:
                    continue
        raise SearchError('搜索结果格式不规范')
    raise SearchError('不支持的搜索结果格式')


# 初始化 MCP 客户端，惰性初始化，只初始化一次
class TavilyMCPProvider:
    def __init__(self):
        self._tool = None
        self._lock = asyncio.Lock()
        self._client = None

    async def __call__(self, **arguments):
        async with self._lock:
            if self._tool is None:
                load_dotenv(Path(__file__).parents[1] / 'config' / '.env')
                key = os.getenv('TAVILY_API_KEY') or os.getenv('tavily_api_key')
                if not key:
                    raise SearchError('TAVILY_API_KEY未配置')
                self._client = MultiServerMCPClient({'tavily': {
                    'transport': 'http',
                    'url': 'https://mcp.tavily.com/mcp/?tavilyApiKey=' + quote(key, safe=''),
                }})
                available = await self._client.get_tools()
                requested = os.getenv('TAVILY_TOOL_NAME')
                names = {requested} if requested else {'tavily_search', 'tavily-search'}
                matches = [tool for tool in available if tool.name in names]
                if len(matches) != 1:
                    raise SearchError('未找到指定工具，请确保TAVILY_TOOL_NAME配置正确')
                self._tool = matches[0]
        return await self._tool.ainvoke(arguments)


# 统计数据
@dataclass
class SearchMetrics:
    # 真实打到搜索引擎的次数
    physical_calls: int = 0
    # 命中缓存
    cache_hits: int = 0
    # 被合并的并发重复请求
    coalesced_requests: int = 0
    # 失败次数
    failures: int = 0
    # 是否因预算耗尽被拒
    budget_exhausted: bool = False
    # 按 stage 分类的物理调用数
    calls_by_stage: dict = field(default_factory=dict)


class SearchService:
    def __init__(self, settings=None, provider=None):
        self.settings = settings or Settings()
        self.provider = provider or TavilyMCPProvider()
        # 并发上限
        self._semaphore = asyncio.Semaphore(self.settings.search_concurrency)
        # LRU + TTL 缓存
        # 有效期：900 秒
        # 最多条目：256
        self._cache = OrderedDict()
        # 进行中的请求（同 key 合并）
        self._inflight = {}
        # run_id → SearchMetrics
        self._metrics = {}

    def metrics(self, run_id):
        return asdict(self._metrics.setdefault(run_id, SearchMetrics()))

    """
    query: 搜索词
    run_id: 归属于哪个运行
    stage: 属于公司搜索，人物搜索，还是补全
    max_results: 一次最多返回多少结果
    search_depth: 搜索深度
    """
    async def search(self, query, *, run_id, stage='search', max_results=5, search_depth='basic'):
        query = ' '.join(str(query).split())
        if not query:
            return {'results': []}
        key = (query, max_results, search_depth)
        metrics = self._metrics.setdefault(run_id, SearchMetrics())
        cached = self._cache.get(key)
        # 命中key，且缓存未到期，则复用结果
        if cached and cached[0] > time.monotonic():
            self._cache.move_to_end(key)
            metrics.cache_hits += 1
            return copy.deepcopy(cached[1])
        # 命中，但是缓存已到期，删除缓存
        if cached:
            del self._cache[key]
        flight_key = (run_id, key)
        # 同一个runid和key搜索已经在运行，则等待结果，不同run之间需要隔离，不同run间的预算/异常不同
        if flight_key in self._inflight:
            metrics.coalesced_requests += 1
            return copy.deepcopy(await asyncio.shield(self._inflight[flight_key]))
        task = asyncio.create_task(self._request(key, run_id, stage))
        self._inflight[flight_key] = task
        def completed(done):
            self._inflight.pop(flight_key, None)
            if not done.cancelled():
                done.exception()
        task.add_done_callback(completed)
        return copy.deepcopy(await asyncio.shield(task))

    # 实际搜索入口
    async def _request(self, key, run_id, stage):
        metrics = self._metrics[run_id]
        for attempt in range(self.settings.search_attempts):
            try:
                # 并发上限为4
                async with self._semaphore:
                    if metrics.physical_calls >= self.settings.max_search_calls:
                        metrics.budget_exhausted = True
                        raise BudgetExhausted('搜索额度已耗尽')
                    metrics.physical_calls += 1
                    metrics.calls_by_stage[stage] = metrics.calls_by_stage.get(stage, 0) + 1
                    async with asyncio.timeout(self.settings.timeout_seconds):
                        raw = await self.provider(query=key[0], max_results=key[1], search_depth=key[2])
                    result = normalize_response(raw)
                self._cache[key] = (time.monotonic() + self.settings.cache_ttl_seconds, result)
                self._cache.move_to_end(key)
                while len(self._cache) > self.settings.cache_max_entries:
                    self._cache.popitem(last=False)
                return result
            except BudgetExhausted:
                raise
            except Exception as exc:
                metrics.failures += 1
                # 最多重试两次
                if is_transient(exc) and attempt + 1 < self.settings.search_attempts:
                    await asyncio.sleep(min(.25 * 2 ** attempt, 2))
                    continue
                raise SearchError(f'搜索失败 ({type(exc).__name__})') from None

    """
    收尾方法
    负责：找出尚未完成的搜索任务取消它们然后等待取消结束
    """
    async def aclose(self):
        pending = list(self._inflight.values())
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)


async def tavily_search(query, max_results=5, search_depth='basic'):
    service = SearchService()
    try:
        return await service.search(query, run_id='one-shot', max_results=max_results, search_depth=search_depth)
    finally:
        await service.aclose()


# if __name__ == "__main__":
#     result = asyncio.run(
#     )
