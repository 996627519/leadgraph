#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：research_agent 
@File ：deepseek.py
@Author ：zlh
@Date ：2026-07-18 12:36 
"""
from langchain_deepseek import ChatDeepSeek
import os
from dotenv import load_dotenv
from pathlib import Path

current_dir = Path(__file__).parent
env_path = current_dir/'..'/'..'/'config'/ '.env'
load_dotenv(env_path)
def get_deepseek():
    llm = ChatDeepSeek(
                model="deepseek-v4-flash",
                api_key=os.environ.get("deepseek_api_key"),  # 从 platform.deepseek.com 获取
                extra_body={"thinking": {"type": "disabled"}}, #如果使用langchain的with_structured方法则不能开启思考模式
                max_retries=2
            )
    return llm

def get_structured_deepseek(class_type):
    structured_llm = get_deepseek().with_structured_output(class_type, include_raw=True)
    return structured_llm