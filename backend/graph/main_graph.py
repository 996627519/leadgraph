#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：main_graph.py
@Author ：zlh
@Date ：2026-09-05 16:47 
"""
import asyncio
import logging
from functools import partial
from uuid import uuid4
from langgraph.graph import StateGraph, START, END
from backend.graph.states.lead_graph_state import LeadGraphState
from backend.graph.states.person_enrichment_state import EnrichedLead
from backend.graph.company_graph import get_company_graph
from backend.graph.person_graph import get_person_graph
from backend.graph.enrichment_graph import get_enrichment_graph
from backend.graph.router.router import send_company_work, send_company_score, send_person_work, send_person_enrichment
from backend.graph.node.target_parser_node import target_parser_node
from backend.graph.node.company_planner import company_planner
from backend.graph.node.company_merge import company_merge
from backend.graph.node.company_score import company_score
from backend.graph.node.company_rank import company_rank
from backend.graph.node.person_planner import person_planner
from backend.graph.node.person_merge import person_merge
from backend.graph.node.lead_gate import lead_gate
from backend.graph.node.common import worker_error
from backend.service.errors import ServiceError, BudgetExhausted
from backend.service.workflow_services import WorkflowServices

logger = logging.getLogger(__name__)

def create_graph(checkpointer=None, *, services=None):
    services = services or WorkflowServices()
    company_graph = get_company_graph(services)
    person_graph = get_person_graph(services)
    enrichment_graph = get_enrichment_graph(services)

    # 初始化
    def initialize(state):
        if state.get('status'):
            raise ValueError('该thread正在运行，只允许resume')
        text = state.get('user_input', '').strip()
        if not text:
            raise ValueError('用户输入不能为空')
        return {
            'run_id': state.get('run_id') or uuid4().hex,
            'user_input': text,
            'status': 'running',
            'company_candidates': [],
            'merged_company': [],
            'company_score': [],
            'ranked_companies': [],
            'lead_candidates': [],
            'merged_leads': [],
            'selected_leads': [],
            'skipped_leads': [],
            'enriched_leads': [],
            'errors': []}

    """
    通用错误防护机制，将service error转成状态更新，出错graph继续执行，只有到fatal=true的节点才结束运行
    """
    def guarded(fn, *, output=None, fatal=False):
        async def call(state):
            try:
                return await fn(state, services=services)
            except ServiceError as exc:
                task = state.get('company')
                update = {'errors': [worker_error(fn.__name__, getattr(task, 'name', ''), exc)]}
                if output:
                    update[output] = []
                if fatal:
                    update.update(status='failed', summary=f'{fn.__name__} failed')
                return update
        return call
    # 提取company work子图的结果
    async def company_worker(state):
        try:
            result = await company_graph.ainvoke(state)
            return {'company_candidates': result.get('company_candidates', []), 'errors': result.get('errors', [])}
        except ServiceError as exc:
            return {'company_candidates': [], 'errors': [worker_error('company_worker', state['task'].id, exc)]}

    """
    提取person work子图的结果
    顺序遍历所有候选人，找到至少一个有evidence+title+employment_status为在职的lead就停止，减少多余搜索资源，有最多重试次数
    """
    async def person_worker(state):
        candidates, errors = [], []
        for task in state['tasks']:
            try:
                result = await person_graph.ainvoke({'task': task, 'run_id': state['run_id']})
                found = result.get('lead_candidates', [])
                errors.extend(result.get('errors', []))
                candidates.extend(found)
                if any(lead.evidence and lead.title and lead.employment_status == 'current' for lead in found):
                    break
            except ServiceError as exc:
                errors.append(worker_error('person_worker', task.id, exc))
                if isinstance(exc, BudgetExhausted):
                    break
        return {'lead_candidates': candidates, 'errors': errors}

    # 失败留线索，补全失败时confidence置为0，下游仍能收到线索，但是可信度为低
    async def enrichment_worker(state):
        try:
            result = await enrichment_graph.ainvoke(state)
            return {'enriched_leads': result.get('enriched_lead', []), 'errors': result.get('errors', [])}
        except ServiceError as exc:
            fallback = EnrichedLead(lead=state['lead'], confidence=0, summary='补全服务失败；保留已有线索供复核。',
                                    missing_information=['Enrichment failed'], stop_reason='model_failed')
            return {'enriched_leads': [fallback], 'errors': [worker_error('enrichment_worker', state['lead'].name, exc)]}

    """
    1. 结果排序，按lead.name小写排序
    2. 状态裁决，failed、needs_input保留状态，有错误+有结果 partial，有错误+无结果 failed，无错误+有结果 completed，无错误+无结果 completed_empty
    3. 指标汇总，从searchservice.metrics(run_id)拿到搜索指标，（physical_calls / cache_hits 等），再补上 LLM 调用数、公司数、合并线索数、补全线索数。
    4. summary生成，失败或需要输入时用上游给的summary，否则自动拼一段中文摘要
    5. 日志，记录run_id/status/物理搜索次数，便于线上排查
    """
    def finalize(state):
        results = sorted(state.get('enriched_leads', []), key=lambda x: (x.lead.name.casefold(), tuple(sorted(x.lead.company_names))))
        errors = state.get('errors', [])
        status = state.get('status')
        if status not in {'failed', 'needs_input'}:
            status = 'partial' if errors and results else 'failed' if errors else 'completed' if results else 'completed_empty'
        metrics = services.search.metrics(state['run_id'])
        metrics['llm_calls'] = getattr(services.model, 'calls', None)
        metrics.update(companies=len(state.get('ranked_companies', [])), merged_leads=len(state.get('merged_leads', [])), enriched_leads=len(results))
        summary = state.get('summary') if status in {'failed', 'needs_input'} else f'得到 {len(results)} 条补全线索；跳过 {len(state.get("skipped_leads", []))} 条；{len(errors)} 个服务问题。'
        logger.info('leadgraph_finished run_id=%s status=%s search_calls=%s', state['run_id'], status, metrics['physical_calls'])
        return {'status': status, 'summary': summary or '服务失败，请查看 errors。', 'metrics': metrics, 'results': results}

    # 构建图
    builder = StateGraph(LeadGraphState)
    for name, fn in [
        ('initialize', initialize),
        ('target_parser', guarded(target_parser_node, fatal=True)),
        ('company_planner', guarded(company_planner, fatal=True)),
        ('company_work', company_worker),
        ('company_merge', company_merge),
        ('company_score', guarded(company_score, output='company_score')),
        ('company_rank', partial(company_rank, services=services)),
        ('person_planner', guarded(person_planner, fatal=True)),
        ('person_work', person_worker),
        ('person_merge', person_merge),
        ('lead_gate', partial(lead_gate, services=services)),
        ('enrichment_work', enrichment_worker),
        ('finalize', finalize)
    ]:
        builder.add_node(name, fn)
    builder.add_edge(START, 'initialize')
    builder.add_edge('initialize', 'target_parser')
    builder.add_conditional_edges('target_parser', lambda s: 'company_planner' if s['status'] == 'running' else 'finalize')
    builder.add_conditional_edges('company_planner', send_company_work)
    builder.add_edge('company_work', 'company_merge')
    builder.add_conditional_edges('company_merge', send_company_score)
    builder.add_edge('company_score', 'company_rank')
    builder.add_edge('company_rank', 'person_planner')
    builder.add_conditional_edges('person_planner', send_person_work)
    builder.add_edge('person_work', 'person_merge')
    builder.add_edge('person_merge', 'lead_gate')
    builder.add_conditional_edges('lead_gate', send_person_enrichment)
    builder.add_edge('enrichment_work', 'finalize')
    builder.add_edge('finalize', END)
    return builder.compile(checkpointer=checkpointer)


# 运行入口
async def run_pipeline(user_input, *, services=None, settings=None, checkpointer=None, thread_id=None):
    services = services or WorkflowServices(settings)
    graph = create_graph(checkpointer, services=services)
    run_id = uuid4().hex
    config = {'configurable': {'thread_id': thread_id or run_id}, 'recursion_limit': 100,
              'max_concurrency': max(services.settings.search_concurrency, services.settings.llm_concurrency)}
    try:
        return await graph.ainvoke({'user_input': user_input, 'run_id': run_id}, config=config)
    finally:
        await services.search.aclose()


async def test_graph():
    checkpointer = MemorySaver()
    graph = create_graph(checkpointer)
    user_input = "我是一名销售，主要销售牛奶大型消毒设备，需要寻找英国地区，牛奶行业的公司人员，将设备销售给他们，尽量寻找对面有联系方式的人，比如领英平台的邮箱。"
    task_id = "task001"
    config = {
        "configurable": {
            "thread_id": task_id
        }
    }
    async for event in graph.astream(
            {
                "user_input": user_input
            },
            config=config
    ): print(event)

if __name__ == "__main__":
    asyncio.run(test_graph())
