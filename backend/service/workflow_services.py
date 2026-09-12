#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：workflow_services.py
@Author ：zlh
@Date ：2026-09-10 16:50 
"""
from backend.config.settings import Settings
from backend.service.model_service import ModelService
from backend.service.search_service import SearchService


class WorkflowServices:
    def __init__(self, settings=None, search=None, model=None):
        self.settings = settings or Settings.from_ini()
        self.search = search or SearchService(self.settings)
        self.model = model or ModelService(self.settings)
