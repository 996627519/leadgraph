#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：app.py
@Author ：zlh
@Date ：2026-09-14 10:32
薄API层：用户操作统一转成 GraphRuntime 的 Command(resume=...)。
"""
import asyncio
import json
import os
import secrets
import time
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4
from urllib.parse import urlsplit
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field
from typing import Literal
from backend.persistend.checkpoint import checkpoint_path, open_checkpointer
from backend.persistend.studio_store import now
from backend.persistend.database import Database
from backend.service.auth_service import AuthService
from backend.service.quota_service import QuotaService
from backend.web.auth_routes import mount_auth, csrf_response, SESSION_COOKIE, CSRF_COOKIE
from backend.service.email_service import EmailService, mail_ready, mail_config
from backend.graph.states.outreach_state import MailBrief, DraftEdit, SendRequest
from backend.web.graph_runtime import GraphRuntime, BUSY

FRONTEND = Path(__file__).resolve().parents[2] / 'frontend'


class NewRun(BaseModel):
    query: str = Field(min_length=5, max_length=3000)
    mode: Literal['demo', 'live'] = 'demo'


class Selection(BaseModel):
    lead_ids: list[str] = Field(min_length=1, max_length=30)


class ContactEdit(BaseModel):
    email: str = Field(max_length=254)
    confirmed: Literal[True]


class SkipSend(BaseModel):
    confirmed: Literal[True]


def create_app(db_path=None, *, database=None, quota_service=None, services_factory=None, demo_delay=.65, send_fn=None):
    load_dotenv(Path(__file__).resolve().parents[1] / 'config/.env')
    # MySQL 保存用户、会话、业务历史、发送台账；SQLite 仅保存图检查点。
    path = checkpoint_path(db_path)
    store = database if database is not None else Database()
    email = EmailService(ledger=store, transport=send_fn)
    auth = AuthService(store)
    quota = quota_service or QuotaService()
    secure_cookie = os.getenv('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
    allow_registration = os.getenv('ALLOW_REGISTRATION', 'true').lower() == 'true'
    max_active_runs = int(os.getenv('LEADGRAPH_MAX_ACTIVE_RUNS', '3'))
    if not 1 <= max_active_runs <= 3:
        raise ValueError('LEADGRAPH_MAX_ACTIVE_RUNS 必须为 1 到 3。')
    allowed_hosts = [h.strip() for h in os.getenv('LEADGRAPH_ALLOWED_HOSTS',
        'localhost,127.0.0.1,[::1],testserver').split(',') if h.strip()]
    if not allowed_hosts or any(h == '*' or '://' in h or '/' in h for h in allowed_hosts):
        raise ValueError('LEADGRAPH_ALLOWED_HOSTS 请填写明确的 IP 或域名，不包含协议或路径。')

    @asynccontextmanager
    async def lifespan(app):
        await asyncio.to_thread(store.check)
        await asyncio.to_thread(store.prune_sessions, int(time.time()))
        async with open_checkpointer(path) as saver:
            runtime = GraphRuntime(store, saver, email, services_factory=services_factory, demo_delay=demo_delay)
            app.state.runtime = runtime
            for run in await asyncio.to_thread(store.list, limit=None):
                await runtime.sync(run['id'])
            yield
            for task in list(runtime.tasks.values()):
                task.cancel()
            await asyncio.gather(*list(runtime.tasks.values()), return_exceptions=True)
        if database is None:
            await asyncio.to_thread(store.close)

    app = FastAPI(title='LeadGraph Studio', lifespan=lifespan, docs_url=None, redoc_url=None)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)
    app.state.store = store
    app.state.auth = auth
    mount_auth(app, auth, secure=secure_cookie, allow_registration=allow_registration)

    @app.middleware('http')
    async def same_origin(request: Request, call_next):
        api_path = request.url.path
        public = {'/api/auth/csrf', '/api/auth/login', '/api/auth/register'}
        if api_path.startswith('/api'):
            if request.method not in {'GET', 'HEAD'}:
                origin = request.headers.get('origin')
                if origin and urlsplit(origin).netloc != request.headers.get('host'):
                    return JSONResponse({'detail': '请求来源不匹配。'}, status_code=403, headers={'Cache-Control': 'no-store'})
                cookie_token = request.cookies.get(CSRF_COOKIE, '')
                if not cookie_token or not secrets.compare_digest(request.headers.get('x-studio-token', ''), cookie_token):
                    return JSONResponse({'detail': '页面会话已失效，请刷新。'}, status_code=403, headers={'Cache-Control': 'no-store'})
            if api_path not in public:
                user = await asyncio.to_thread(auth.current, request.cookies.get(SESSION_COOKIE))
                if not user:
                    return JSONResponse({'detail': '请先登录。'}, status_code=401, headers={'Cache-Control': 'no-store'})
                request.state.user = user
                parts = api_path.split('/')
                if len(parts) >= 4 and parts[2] == 'runs' and parts[3]:
                    try:
                        await asyncio.to_thread(store.get_owned, parts[3], user['id'])
                    except KeyError:
                        return JSONResponse({'detail': '任务不存在。'}, status_code=404, headers={'Cache-Control': 'no-store'})
        response = await call_next(request)
        response.headers.update({
            'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer', 'X-Frame-Options': 'DENY',
            'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'",
        })
        if request.url.path.startswith('/api'):
            response.headers['Cache-Control'] = 'no-store'
        return response

    @app.exception_handler(KeyError)
    async def missing(request, exc):
        return JSONResponse({'detail': '任务或内容不存在。'}, status_code=404)

    @app.exception_handler(ValueError)
    async def conflict(request, exc):
        return JSONResponse({'detail': str(exc)}, status_code=409)

    @app.get('/api/session')
    async def session(request: Request):
        return csrf_response({'user': request.state.user, 'smtp_ready': mail_ready(), 'sender': mail_config()['from'],
            'research_ready': bool((os.getenv('DEEPSEEK_API_KEY') or os.getenv('deepseek_api_key')) and
                                   (os.getenv('TAVILY_API_KEY') or os.getenv('tavily_api_key')))}, request, secure=secure_cookie)

    @app.get('/api/usage')
    async def usage():
        return await quota.get()

    @app.get('/api/runs')
    async def history(request: Request):
        return [{k: r[k] for k in ('id', 'query', 'mode', 'status', 'stage', 'created_at', 'updated_at')} |
                {'lead_count': len(r['leads'])} for r in await asyncio.to_thread(store.list, user_id=request.state.user['id'])]

    admission_lock = asyncio.Lock()

    @app.post('/api/runs', status_code=202)
    async def new_run(data: NewRun, request: Request):
        async with admission_lock:
            runtime = app.state.runtime
            if len(runtime.tasks) >= max_active_runs:
                raise HTTPException(429, '请等待一个运行中的任务完成。')
            if not data.query.strip():
                raise ValueError('请输入具体要求。')
            run_id = uuid4().hex
            run = {'id': run_id, 'user_id': request.state.user['id'], 'query': data.query.strip(), 'mode': data.mode, 'status': 'researching', 'stage': 'plan',
                   'created_at': now(), 'updated_at': now(), 'version': 1, 'events': [], 'leads': [], 'approved': [],
                   'contacts': {}, 'drafts': [], 'metrics': {}, 'notice': '', 'graph_next': [], 'interrupt_kind': None}
            await asyncio.to_thread(store.create, run)
            runtime.spawn(run_id, {'user_input': run['query'], 'run_id': run_id, 'mode': data.mode})
            return run

    @app.get('/api/runs/{run_id}')
    async def get_run(run_id: str):
        return await asyncio.to_thread(store.get, run_id)

    @app.post('/api/runs/{run_id}/cancel')
    async def cancel(run_id: str):
        runtime = app.state.runtime
        if (await asyncio.to_thread(store.get, run_id))['status'] != 'researching' or run_id not in runtime.tasks:
            raise ValueError('仅运行中的研究可以停止。')
        runtime.tasks[run_id].cancel()
        return {'status': 'cancelling'}

    @app.post('/api/runs/{run_id}/continue', status_code=202)
    async def continue_saved(run_id: str):
        return await app.state.runtime.continue_saved(run_id)

    @app.post('/api/runs/{run_id}/contacts', status_code=202)
    async def contacts(run_id: str, data: Selection):
        run = await asyncio.to_thread(store.get, run_id)
        kind = 'contacts' if run.get('interrupt_kind') == 'contacts' else 'review'
        return await app.state.runtime.resume(run_id, kind, {'action': 'select', **data.model_dump()},
                                              background_status='contacts_searching')

    @app.patch('/api/runs/{run_id}/contacts/{lead_id}')
    async def edit_contact(run_id: str, lead_id: str, data: ContactEdit):
        return await app.state.runtime.resume(run_id, 'contacts',
                                              {'action': 'confirm_contact', 'lead_id': lead_id, **data.model_dump()})

    @app.post('/api/runs/{run_id}/drafts', status_code=202)
    async def drafts(run_id: str, data: MailBrief):
        return await app.state.runtime.resume(run_id, 'contacts', {'action': 'compose', 'brief': data.model_dump()},
                                              background_status='drafting')

    @app.patch('/api/runs/{run_id}/drafts/{draft_id}')
    async def edit_draft(run_id: str, draft_id: str, data: DraftEdit):
        return await app.state.runtime.resume(run_id, 'compose', {'action': 'edit', 'id': draft_id, **data.model_dump()})

    @app.post('/api/runs/{run_id}/send', status_code=202)
    async def send(run_id: str, data: SendRequest):
        run = await asyncio.to_thread(store.get, run_id)
        # 网络重试只读取已有结果，不再次唤醒发送节点。
        by_id = {d['id']: d for d in run['drafts']}
        if len({x.id for x in data.drafts}) == len(data.drafts) and all(
            x.id in by_id and by_id[x.id]['revision'] == x.revision and by_id[x.id]['status'] in {'sent', 'simulated', 'sending'}
            for x in data.drafts
        ):
            return run
        return await app.state.runtime.resume(run_id, 'compose', {'action': 'send', **data.model_dump()},
                                              background_status='sending')

    @app.post('/api/runs/{run_id}/skip-send')
    async def skip_send(run_id: str, data: SkipSend):
        run = await asyncio.to_thread(store.get, run_id)
        if run.get('outreach_status') == 'skipped':
            return run
        return await app.state.runtime.resume(run_id, 'compose', {'action': 'skip', 'confirmed': data.confirmed})

    @app.get('/api/runs/{run_id}/events')
    async def events(run_id: str, request: Request, after: int = 0):
        await asyncio.to_thread(store.get, run_id)
        async def stream():
            cursor = after
            next_auth_check = 0
            while not await request.is_disconnected():
                if time.monotonic() >= next_auth_check:
                    if not await asyncio.to_thread(auth.current, request.cookies.get(SESSION_COOKIE)):
                        break
                    next_auth_check = time.monotonic() + 15
                item = await asyncio.to_thread(store.get, run_id)
                for event in item['events']:
                    if event['seq'] > cursor:
                        cursor = event['seq']
                        yield f'id: {cursor}\nevent: progress\ndata: {json.dumps(event, ensure_ascii=False)}\n\n'
                yield f'event: snapshot\ndata: {json.dumps({"version": item["version"], "status": item["status"]})}\n\n'
                if item['status'] not in BUSY:
                    break
                await asyncio.sleep(.4)
        return StreamingResponse(stream(), media_type='text/event-stream', headers={'X-Accel-Buffering': 'no'})

    @app.get('/healthz', include_in_schema=False)
    async def health():
        try:
            await asyncio.to_thread(store.check)
        except Exception:
            return JSONResponse({'status': 'unavailable'}, status_code=503)
        return {'status': 'ok'}

    @app.get('/')
    async def index():
        return FileResponse(FRONTEND / 'index.html')

    app.mount('/assets', StaticFiles(directory=FRONTEND), name='assets')
    return app
