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
from backend.service.email_service import EmailService
from backend.service.outreach_service import OutreachService

class WorkflowServices:
    def __init__(self, settings=None, search=None, model=None, *, email=None, outreach=None, emit=None):
        self.settings = settings or Settings.from_ini()
        self.search = search or SearchService(self.settings)
        self.model = model or ModelService(self.settings)
        self.email = email or EmailService()
        self.outreach = outreach or OutreachService()
        self.emit = emit
