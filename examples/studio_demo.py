#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：studio_demo.py
@Author ：zlh
@Date ：2026-09-13 18:12 
"""
import asyncio
from uuid import uuid4

STAGES = [
    ('plan', '理解目标与制定搜索计划', '正在把你的要求整理为公司和岗位搜索策略'),
    ('companies', '发现与筛选公司', '正在搜索公开资料，合并重复公司并评估匹配度'),
    ('people', '寻找关键联系人', '正在目标公司中寻找与岗位相关的真实人员'),
    ('verify', '核验信息与整理证据', '正在检查职位、任职关系和公开来源'),
    ('review', '研究完成，等待你的审核', '请选择值得进一步联系的人'),
]

DEMO = [
    ('Evelyn Carter','Northfield Dairy','Engineering Director','Manchester, UK',.94,'EC'),
    ('Oliver Bennett','Meadow & Co.','Head of Operations','Bristol, UK',.89,'OB'),
    ('Amelia Clarke','Oakwell Foods','Production Manager','Leeds, UK',.83,'AC'),
    ('William Hayes','Northfield Dairy','Procurement Manager','Manchester, UK',.91,'WH'),
    ('Sophie Morgan','Westbrook Creamery','Process Engineering Lead','Birmingham, UK',.87,'SM'),
    ('James Ellis','Meadow & Co.','Plant Manager','Bristol, UK',.78,'JE'),
]


async def research(query, *, demo, emit, delay=.65):
    if demo:
        for stage, title, detail in STAGES[:-1]:
            await emit(stage, title, detail)
            await asyncio.sleep(delay)
        leads = [{'id':uuid4().hex, 'name':name, 'company':company, 'title':title, 'location':location,
            'confidence':confidence, 'employment':'current', 'summary':'公开职业资料显示其负责工程或运营相关工作，适合进一步了解业务需求。',
            'evidence':[{'title':'演示资料 · 职业身份与任职信息','url':'https://example.com/team','snippet':'这是虚构演示数据，供体验完整流程使用。'}],
            'missing':['采购决策权限仍需沟通确认'], 'conflicts':[], 'demo_index':i}
            for i,(name,company,title,location,confidence,_) in enumerate(DEMO)]
        return leads, {'physical_calls':12,'companies':4,'enriched_leads':6}, 'completed'
    raise ValueError('This fixture is demo-only')
