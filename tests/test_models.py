#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：test_models.py
@Author ：zlh
@Date ：2026-09-14 10:44 
"""
import asyncio
import pytest
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from backend.config.settings import Settings
from backend.service.model_service import ModelService
from backend.service.errors import ModelError

class Answer(BaseModel):
    value: int

@pytest.mark.asyncio
async def test_structure_retry_total_attempts_and_correction():
    class Model:
        calls=[]
        async def ainvoke(self,messages):
            self.calls.append(list(messages))
            return {'parsed':None} if len(self.calls)==1 else {'parsed':{'value':3}}
    model=Model()
    service=ModelService(Settings(llm_attempts=2),factory=lambda schema:model)
    result=await service.generate(Answer,[HumanMessage(content='x')])
    assert result.value==3
    assert len(model.calls)==2
    assert len(model.calls[-1])==2

@pytest.mark.asyncio
async def test_structure_retry_exhaustion_is_explicit():
    class Model:
        async def ainvoke(self,messages): return {'parsed':None}
    service=ModelService(Settings(llm_attempts=2),factory=lambda schema:Model())
    with pytest.raises(ModelError): await service.generate(Answer,[])
    assert service.calls==2

@pytest.mark.asyncio
async def test_model_concurrency_limit():
    class Model:
        active=0
        max_active=0
        async def ainvoke(self,messages):
            self.active+=1
            self.max_active=max(self.max_active,self.active)
            await asyncio.sleep(.002)
            self.active-=1
            return {'parsed':{'value':1}}
    model=Model()
    service=ModelService(Settings(llm_concurrency=2),factory=lambda schema:model)
    await asyncio.gather(*[service.generate(Answer,[]) for _ in range(8)])
    assert model.max_active==2
