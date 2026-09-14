#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：research_agent 
@File ：deepseek.py
@Author ：zlh
@Date ：2026-07-18 12:36 
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from backend.service.errors import ModelError
from langchain_deepseek import ChatDeepSeek

load_dotenv(Path(__file__).parents[2] / 'config' / '.env')

def get_deepseek(timeout=60):
    key = os.getenv('DEEPSEEK_API_KEY') or os.getenv('deepseek_api_key')
    if not key:
        raise ModelError('未找到deepseek api key')
    return ChatDeepSeek(
        extra_body={"thinking": {"type": "disabled"}},
        model=os.getenv('DEEPSEEK_MODEL', 'deepseek-v4-flash'),
        api_key=key,
        max_retries=0,
        timeout=timeout
    )


def get_structured_deepseek(class_type):
    return get_deepseek().with_structured_output(class_type, include_raw=True)