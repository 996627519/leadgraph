#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：conftest.py
@Author ：zlh
@Date ：2026-09-14 10:43 
"""
import pytest

@pytest.fixture(autouse=True)
def no_live_services(monkeypatch, tmp_path):
    monkeypatch.setenv('LEADGRAPH_CHECKPOINT_DB', str(tmp_path/'pipeline-checkpoints.sqlite3'))
    from backend.service.search_service import TavilyMCPProvider
    from backend.service.model_service import ModelService
    async def forbidden(*args, **kwargs):
        raise AssertionError('Live search is forbidden during tests')
    def forbidden_model(*args, **kwargs):
        raise AssertionError('Live model is forbidden during tests')
    monkeypatch.setattr(TavilyMCPProvider, '__call__', forbidden)
    monkeypatch.setattr(ModelService, '_default_factory', forbidden_model)
