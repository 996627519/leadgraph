#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：outreach_service.py
@Author ：zlh
@Date ：2026-09-14 10:30 
"""
import asyncio
import re
from uuid import uuid4
from pydantic import BaseModel, Field
from backend.graph.node.common import messages
from backend.graph.utils.evidence import canonical_url
from backend.service.model_service import ModelService
from backend.service.search_service import SearchService
from backend.config.settings import Settings
from backend.service.email_service import valid_email, mail_config
from backend.persistend.studio_store import now

EMAIL_PATTERN = re.compile(r'[A-Za-z0-9.!#$%&\x27*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,63}')


class MailText(BaseModel):
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=12000)


# 从搜索内容中提取邮箱
def extract_emails(results, name, company):
    found = {}
    for source in results:
        url = canonical_url(source.get('url'))
        text = str(source.get('content') or '')
        combined = f"{source.get('title', '')} {text}".casefold()
        if not url or name.casefold() not in combined or company.casefold() not in combined:
            continue
        for email in EMAIL_PATTERN.findall(text):
            email = email.rstrip('.,;:')
            if not valid_email(email):
                continue
            local = email.split('@')[0].casefold()
            kind = 'company' if local in {'info', 'sales', 'contact', 'hello', 'support', 'office', 'enquiries'} else 'unverified_person'
            found.setdefault(email.casefold(), {'email': email, 'source_url': url,
                'source_title': str(source.get('title') or '公开网页'), 'excerpt': text[:1200],
                'kind': kind, 'verification': 'public_candidate'})
    return list(found.values())


# 批量查询选中人的邮箱
async def lookup_contacts(leads, *, demo=False, service=None, progress=None):
    service = service or SearchService(Settings(max_search_calls=len(leads)*2, search_concurrency=3))
    run_id = uuid4().hex
    semaphore = asyncio.Semaphore(3)
    async def lookup(lead):
        async with semaphore:
            if demo:
                await asyncio.sleep(.45)
                index = lead.get('demo_index', 0)
                candidates = [] if index == 2 else [{'email': lead['name'].lower().replace(' ', '.')+'@example.com',
                    'source_url': 'https://example.com/team', 'source_title': '演示资料 · 虚构邮箱',
                    'excerpt': '此邮箱仅用于演示，不代表真实联系人。', 'kind': 'demo', 'verification': 'demo'}]
                result = {'lead_id':lead['id'], 'candidates':candidates, 'selected_email':None,
                          'status':'found' if candidates else 'not_found', 'confirmed':False}
            else:
                candidates, error = [], None
                queries = [f'"{lead["name"]}" "{lead["company"]}" email contact',
                           f'"{lead["name"]}" "{lead["company"]}" "@"']
                for query in queries:
                    try:
                        response = await service.search(query, run_id=run_id, stage='contacts')
                        candidates = extract_emails(response['results'], lead['name'], lead['company'])
                        if candidates:
                            break
                    except Exception:
                        error = '搜索服务暂不可用，可稍后重新查找或手动填写。'
                        break
                result = {'lead_id':lead['id'], 'candidates':candidates, 'selected_email':None,
                    'status':'found' if candidates else 'error' if error else 'not_found', 'confirmed':False, 'error':error}
            if progress:
                await progress(result)
            return result
    try:
        return await asyncio.gather(*(lookup(lead) for lead in leads))
    finally:
        await service.aclose()


# 并发生成邮件。
async def generate_drafts(leads, contacts, brief, *, demo=False, model=None, progress=None):
    model = model or ModelService(Settings(llm_concurrency=3))
    semaphore = asyncio.Semaphore(3)
    sender = 'studio@example.com' if demo else mail_config()['from']
    async def generate(lead):
        async with semaphore:
            if demo:
                await asyncio.sleep(.4)
                subject = f'关于 {lead["company"]} 的乳制品设备合作'
                if brief['language'] == 'en':
                    subject = f'A quick conversation about {lead["company"]}'
                    body = f'Hi {lead["name"].split()[0]},\n\nI came across your role at {lead["company"]} and wanted to introduce our team.\n\n{brief["keywords"]}\n\nWould you be open to a brief conversation to explore whether this could be relevant to your work?\n\nBest regards,\n{brief["signature"]}'
                else:
                    body = f'{lead["name"]}，您好：\n\n了解到您在 {lead["company"]} 担任 {lead["title"]}，希望与您交流潜在的合作机会。\n\n{brief["keywords"]}\n\n如果您感兴趣，是否方便安排一次简短的沟通？\n\n祝好！\n{brief["signature"]}'
                text = MailText(subject=subject, body=body)
            else:
                text = await model.generate(MailText, messages(
                    '你是一名 B2B 邮件写作助手。根据用户关键词、语气、语言与署名生成一封简洁的个性化邮件。'
                    '只引用提供的人员事实。不要编造合作经历、产品指标、折扣、采购权限或承诺。不要发送邮件。'
                    '未知信息省略，主题不得包含换行，正文为纯文本。', lead=lead, brief=brief))
            draft = {'id':uuid4().hex, 'lead_id':lead['id'], 'recipient':contacts[lead['id']]['selected_email'],
                'sender':sender, 'subject':text.subject.replace('\r',' ').replace('\n',' '), 'body':text.body,
                'revision':1, 'status':'draft', 'created_at':now()}
            if progress:
                await progress(draft)
            return draft
    # 所有任务同时开始，最后按传入的顺序收集起来
    results = await asyncio.gather(*(generate(lead) for lead in leads), return_exceptions=True)
    if any(isinstance(x, Exception) for x in results):
        raise RuntimeError('Some drafts failed to generate')
    return results


class OutreachService:
    # 将查询结果的列表转换为lead_id: 联系方式记录
    async def contacts(self, leads, *, demo=False):
        results = await lookup_contacts(leads, demo=demo)
        return {item['lead_id']: item for item in results}

    # 保留部分成功的草稿
    async def write(self, leads, contacts, brief, *, demo=False, model=None):
        completed = []
        async def collect(draft):
            completed.append(draft)
        try:
            await generate_drafts(leads, contacts, brief, demo=demo, model=model, progress=collect)
            return completed, ''
        except Exception:
            return completed, '部分草稿生成失败，已完成内容仍可审核。'