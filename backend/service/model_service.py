#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：model_service.py
@Author ：zlh
@Date ：2026-09-10 16:36 
"""
import asyncio
from langchain_core.messages import HumanMessage
from pydantic import ValidationError
from backend.config.settings import Settings
from backend.service.errors import ModelError, is_transient
from backend.graph.llm.deepseek import get_deepseek


class ModelService:
    def __init__(self, settings=None, factory=None):
        self.settings = settings or Settings()
        self.factory = factory or self._default_factory
        # structured后的llm
        self._models = {}
        # llm并发量
        self._semaphore = asyncio.Semaphore(self.settings.llm_concurrency)
        self.calls = 0

    def _default_factory(self, schema):
        return get_deepseek(self.settings.timeout_seconds).with_structured_output(schema, include_raw=True)
    
    async def generate(self, schema, messages):
        if schema not in self._models:
            self._models[schema] = self.factory(schema)
        model = self._models[schema]
        messages = list(messages)
        # 默认失败重试2次
        for attempt in range(self.settings.llm_attempts):
            try:
                async with self._semaphore:
                    self.calls += 1
                    async with asyncio.timeout(self.settings.timeout_seconds):
                        response = await model.ainvoke(messages)
                parsed = response.get('parsed') if isinstance(response, dict) and 'parsed' in response else response
                if parsed is None or isinstance(response, dict) and response.get('parsing_error') is not None:
                    raise ValueError('llm输出为空')
                return schema.model_validate(parsed)
            except (ValidationError, ValueError):
                if attempt + 1 == self.settings.llm_attempts:
                    raise ModelError('llm输出格式不符合规范') from None
                messages.append(HumanMessage(content='上一次输出未通过结构校验。请重新输出完整 schema，包含所有必填字段；未知事实使用 schema 允许的空值，不要编造。'))
            except ModelError:
                raise
            except Exception as exc:
                if is_transient(exc) and attempt + 1 < self.settings.llm_attempts:
                    await asyncio.sleep(min(.25 * 2 ** attempt, 2))
                    continue
                raise ModelError(f'Model request failed ({type(exc).__name__})') from None