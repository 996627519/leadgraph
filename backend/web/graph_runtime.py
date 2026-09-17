#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：graph_runtime.py
@Author ：zlh
@Date ：2026-09-14 10:32
HTTP 与图之间的适配：只驱动图和投影展示数据，不执行外联业务。
"""
import asyncio
import logging
import traceback
from copy import deepcopy
from langgraph.types import Command
from backend.graph.main_graph import create_graph
from backend.service.workflow_services import WorkflowServices
from backend.graph.utils.outreach_validation import validate_review, validate_contact, validate_mail
from backend.persistend.studio_store import now

BUSY = {'researching', 'contacts_searching', 'drafting', 'sending'}
VALIDATORS = {'review': validate_review, 'contacts': validate_contact, 'compose': validate_mail}
NODE_STAGES = {
    'target_parser': ('plan', '正在理解目标', '将要求整理为公司与岗位搜索策略'),
    'company_planner': ('plan', '正在制定搜索计划', '限制查询数量并明确搜索方向'),
    'company_work': ('companies', '正在搜索公司', '查找公开来源与匹配企业'),
    'company_score': ('companies', '正在评估公司', '根据目标画像筛选公司'),
    'person_planner': ('people', '正在规划人员搜索', '寻找相关岗位的联系人'),
    'person_work': ('people', '正在寻找关键联系人', '优先有公开任职证据的人员'),
    'enrichment_work': ('verify', '正在核验与补全资料', '检查证据、缺失和冲突'),
    'human_review': ('review', '等待你审核联系人', '选择人选后，图才会继续查询邮箱'),
    'contact_search': ('contacts', '正在查找公开联系方式', '仅搜索已选择的人员'),
    'contact_review': ('contacts', '等待你核对邮箱', '确认地址归属并填写沟通意图'),
    'mail_write': ('compose', '正在生成个性化邮件', '依据你提供的关键词与联系人事实'),
    'mail_review': ('compose', '等待你审核邮件', '可以编辑，确认后图才进入发送节点'),
    'mail_skip': ('send', '流程已结束', '你选择不发送剩余邮件'),
    'mail_send': ('send', '正在逐封提交邮件', '已通过最终确认，发送服务记录每封结果'),
}


def log_failure(run_id, phase, exc):
    # 不输出异常文本或局部变量，避免 SQL 参数、API 密钥进入日志。
    frames = traceback.extract_tb(exc.__traceback__)
    location = f'{frames[-1].filename}:{frames[-1].lineno}' if frames else 'unknown'
    logging.getLogger(__name__).error('Graph task failed run_id=%s phase=%s exception=%s location=%s',
                                     run_id, phase, type(exc).__name__, location)


class GraphRuntime:
    def __init__(self, store, checkpointer, email, *, services_factory=None, demo_delay=.65):
        self.store, self.checkpointer, self.email = store, checkpointer, email
        self.services_factory, self.demo_delay = services_factory, demo_delay
        self.tasks, self.locks = {}, {}

    def config(self, run_id):
        return {'configurable': {'thread_id': run_id}, 'recursion_limit': 100, 'max_concurrency': 4}

    async def graph(self, run_id):
        run = await asyncio.to_thread(self.store.get, run_id)
        services = self.services_factory(run) if self.services_factory else WorkflowServices(email=self.email)
        services.email = self.email
        services.demo_delay = self.demo_delay
        async def emit(stage, title, detail):
            def append(item):
                item['stage'] = stage
                item['events'].append({'seq': len(item['events']) + 1, 'stage': stage,
                                       'title': title, 'detail': detail, 'time': now()})
            await asyncio.to_thread(self.store.mutate, run_id, append)
        services.emit = emit
        async def observer(name, action):
            if name in NODE_STAGES:
                await emit(*NODE_STAGES[name])
        try:
            return create_graph(self.checkpointer, services=services, observer=observer), services
        except BaseException:
            await services.search.aclose()
            raise

    async def snapshot(self, run_id):
        graph, services = await self.graph(run_id)
        try:
            return await graph.aget_state(self.config(run_id))
        finally:
            await services.search.aclose()

    async def sync(self, run_id):
        snapshot = await self.snapshot(run_id)
        values = snapshot.values
        if not values:
            await asyncio.to_thread(self.store.mutate, run_id, lambda r: r.update(status='interrupted', notice='图尚未开始执行，可以恢复此任务。'))
            return await asyncio.to_thread(self.store.get, run_id)
        interrupts = [i for task in snapshot.tasks for i in task.interrupts]
        kind = interrupts[0].value['kind'] if interrupts else None
        error = interrupts[0].value.get('error', '') if interrupts else ''
        deliveries = await asyncio.to_thread(self.email.results, run_id)
        def project(run):
            for graph_key, display_key in [('review_leads', 'leads'), ('approved', 'approved'),
                                           ('contacts', 'contacts'), ('drafts', 'drafts'),
                                           ('brief', 'brief'), ('metrics', 'metrics')]:
                if graph_key in values:
                    run[display_key] = deepcopy(values[graph_key])
            run['graph_next'] = list(snapshot.next)
            run['interrupt_kind'] = kind
            run['notice'] = error or values.get('notice', '')
            run['outreach_status'] = values.get('outreach_status', '')
            if kind:
                run['status'] = kind
                run['stage'] = kind
            elif not snapshot.next:
                run['status'] = 'compose' if run['drafts'] else 'review' if run['leads'] else 'error'
                if values.get('outreach_status') == 'cancelled':
                    run.update(status='cancelled', notice='已取消联系。')
                elif run['status'] == 'error':
                    run['notice'] = values.get('summary') or '未找到可审核的人员，请调整条件。'
            else:
                run.update(status='interrupted', notice='图任务尚未完成，可恢复已保存的执行位置。')
            # 仅投影发送台账；不会通过修改展示数据库绕过图审核。
            for draft in run['drafts']:
                result = deliveries.get(draft['id'])
                if result and result['status'] != 'sending':
                    draft.update(result)
                elif result and run['status'] == 'interrupted':
                    draft.update(status='unknown', error='服务在发送时中断，请核实发件记录。')
        await asyncio.to_thread(self.store.mutate, run_id, project)
        return await asyncio.to_thread(self.store.get, run_id)

    def lock(self, run_id):
        return self.locks.setdefault(run_id, asyncio.Lock())

    async def validate(self, run_id, kind, payload):
        snapshot = await self.snapshot(run_id)
        interrupts = [i for t in snapshot.tasks for i in t.interrupts]
        if not interrupts or interrupts[0].value['kind'] != kind:
            raise ValueError('当前图不在这个审核节点，请刷新页面。')
        VALIDATORS[kind](snapshot.values, payload)

    async def _drive(self, run_id, graph_input):
        services = None
        phase = 'initialize'
        try:
            graph, services = await self.graph(run_id)
            phase = 'execute'
            async for update in graph.astream(graph_input, self.config(run_id), stream_mode='updates'):
                # 只投影已经由图节点提交的输出，使长任务过程中也能显示已完成部分。
                for name, values in update.items():
                    if name == '__interrupt__' or not isinstance(values, dict):
                        continue
                    fields = {('leads' if k == 'review_leads' else k): deepcopy(v)
                              for k, v in values.items()
                              if k in {'review_leads', 'approved', 'contacts', 'drafts', 'brief', 'metrics'}}
                    if fields:
                        await asyncio.to_thread(self.store.mutate, run_id, lambda r: r.update(fields))
            return await self.sync(run_id)
        except asyncio.CancelledError:
            await asyncio.to_thread(self.store.mutate, run_id, lambda r: r.update(status='interrupted', notice='执行已停止，检查点已保留。'))
            raise
        except Exception as exc:
            log_failure(run_id, phase, exc)
            try:
                await self.sync(run_id)
            except Exception as sync_error:
                # 图模块缺失时，读取检查点也可能失败；仍须将任务标为可恢复。
                log_failure(run_id, 'sync_after_error', sync_error)
            await asyncio.to_thread(self.store.mutate, run_id, lambda r: r.update(status='interrupted', notice='图执行未完成，请检查服务配置后恢复。'))
            return await asyncio.to_thread(self.store.get, run_id)
        finally:
            if services is not None:
                try:
                    await services.search.aclose()
                except Exception as close_error:
                    log_failure(run_id, 'close', close_error)

    def spawn(self, run_id, graph_input):
        async def run():
            async with self.lock(run_id):
                await self._drive(run_id, graph_input)
        task = asyncio.create_task(run())
        self.tasks[run_id] = task
        def done(finished):
            self.tasks.pop(run_id, None)
            if not finished.cancelled():
                error = finished.exception()
                if error is not None:
                    log_failure(run_id, 'background', error)
        task.add_done_callback(done)

    async def resume(self, run_id, kind, payload, *, background_status=None):
        if run_id in self.tasks or self.lock(run_id).locked():
            raise ValueError('当前操作尚未完成，请稍后再试。')
        async with self.lock(run_id):
            await self.validate(run_id, kind, payload)
            if background_status:
                await asyncio.to_thread(self.store.mutate, run_id, lambda r: r.update(status=background_status, notice=''))
                self.spawn(run_id, Command(resume=payload))
                return await asyncio.to_thread(self.store.get, run_id)
            return await self._drive(run_id, Command(resume=payload))

    async def continue_saved(self, run_id):
        if run_id in self.tasks or self.lock(run_id).locked():
            raise ValueError('这个图任务正在执行。')
        async with self.lock(run_id):
            snapshot = await self.snapshot(run_id)
            if not snapshot.values:
                run = await asyncio.to_thread(self.store.get, run_id)
                await asyncio.to_thread(self.store.mutate, run_id, lambda r: r.update(status='researching', notice=''))
                self.spawn(run_id, {'user_input': run['query'], 'run_id': run_id, 'mode': run['mode']})
                return await asyncio.to_thread(self.store.get, run_id)
            if not snapshot.next or any(t.interrupts for t in snapshot.tasks):
                raise ValueError('请通过当前人工审核页面继续。')
            status = 'sending' if 'mail_send' in snapshot.next else 'researching'
            await asyncio.to_thread(self.store.mutate, run_id, lambda r: r.update(status=status, notice=''))
            self.spawn(run_id, None)
            return await asyncio.to_thread(self.store.get, run_id)
