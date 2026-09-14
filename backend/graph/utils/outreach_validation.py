#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：outreach_validation.py
@Author ：zlh
@Date ：2026-09-13 18:13 
"""
from copy import deepcopy
from backend.graph.states.outreach_state import MailBrief, DraftEdit, SendRequest
from backend.service.email_service import valid_email, mail_ready, mail_config, draft_digest


def selection(state, payload):
    ids = payload.get('lead_ids', [])
    if not isinstance(ids, list) or not 1 <= len(ids) <= 30 or not all(isinstance(i, str) for i in ids):
        raise ValueError('请选择 1 到 30 位联系人。')
    if len(set(ids)) != len(ids) or not set(ids).issubset({x['id'] for x in state.get('review_leads', [])}):
        raise ValueError('联系人选择无效或重复。')
    if state.get('drafts'):
        raise ValueError('已有邮件草稿，请在现有草稿中完成操作，或新建研究。')
    return {'approved': list(dict.fromkeys(state.get('approved', []) + ids)),
            'contact_ids': ids, 'outreach_action': 'search', 'notice': ''}


def validate_review(state, payload):
    if payload.get('action') == 'cancel':
        return {'outreach_action': 'cancel', 'outreach_status': 'cancelled'}
    return selection(state, payload)


def validate_contact(state, payload):
    action = payload.get('action')
    if action == 'select':
        return selection(state, payload)
    if action == 'compose':
        brief = MailBrief.model_validate(payload.get('brief', {})).model_dump()
        ids = brief['lead_ids']
        if len(ids) != len(set(ids)) or not set(ids).issubset(state.get('approved', [])):
            raise ValueError('请先审核选中的联系人。')
        if any(not state.get('contacts', {}).get(i, {}).get('confirmed') for i in ids):
            raise ValueError('请先确认每位收件人的邮箱。')
        if any(d['lead_id'] in ids for d in state.get('drafts', [])):
            raise ValueError('选中的联系人已有草稿。')
        if state.get('mode') != 'demo' and not valid_email(mail_config()['from']):
            raise ValueError('请先配置 SMTP_FROM，再生成供审核的邮件。')
        return {'brief': brief, 'outreach_action': 'compose', 'notice': ''}
    if action != 'confirm_contact' or payload.get('confirmed') is not True:
        raise ValueError('请明确确认邮箱归属。')
    lead_id = payload.get('lead_id')
    email = str(payload.get('email', '')).strip()
    if lead_id not in state.get('approved', []):
        raise ValueError('请先审核这个联系人。')
    if not valid_email(email):
        raise ValueError('邮箱地址格式无效。')
    if any(d['lead_id'] == lead_id for d in state.get('drafts', [])):
        raise ValueError('已生成草稿的收件地址不能改变。')
    contacts = deepcopy(state.get('contacts', {}))
    contact = contacts.setdefault(lead_id, {'lead_id': lead_id, 'candidates': []})
    public = any(c['email'].casefold() == email.casefold() for c in contact['candidates'])
    contact.update(selected_email=email, confirmed=True, status='confirmed', origin='public' if public else 'manual')
    return {'contacts': contacts, 'outreach_action': 'review', 'notice': ''}


def validate_mail(state, payload):
    if payload.get('action') == 'skip':
        if payload.get('confirmed') is not True:
            raise ValueError('请确认不发送并结束流程。')
        return {'mail_approvals': {}, 'outreach_action': 'skip'}
    drafts = deepcopy(state.get('drafts', []))
    if payload.get('action') == 'edit':
        data = DraftEdit.model_validate(payload)
        draft = next((d for d in drafts if d['id'] == payload.get('id')), None)
        if not draft or draft['status'] != 'draft':
            raise ValueError('这封邮件不存在或已进入发送流程。')
        if draft['revision'] != data.revision:
            raise ValueError('草稿版本已改变，请刷新后重新核对。')
        if not data.subject.strip() or not data.body.strip() or '\r' in data.subject or '\n' in data.subject:
            raise ValueError('主题和正文不能为空，主题不能换行。')
        draft.update(subject=data.subject.strip(), body=data.body, revision=draft['revision'] + 1)
        return {'drafts': drafts, 'mail_approvals': {}, 'outreach_action': 'review', 'notice': ''}
    if payload.get('action') != 'send':
        raise ValueError('请选择编辑或确认发送。')
    data = SendRequest.model_validate(payload)
    requested = {x.id: x.revision for x in data.drafts}
    if len(requested) != len(data.drafts):
        raise ValueError('发送列表不能重复。')
    found = [d for d in drafts if d['id'] in requested]
    if len(found) != len(requested):
        raise ValueError('发送列表中有不存在的草稿。')
    previous = {d['recipient'].casefold() for d in drafts if d['status'] != 'draft'}
    approvals = {}
    for draft in found:
        if draft['status'] != 'draft' or draft['revision'] != requested[draft['id']]:
            raise ValueError('邮件已发送或版本已改变，请重新核对。')
        if draft['recipient'].casefold() in previous:
            raise ValueError('同一收件地址已有发送记录或重复草稿。')
        contact = state['contacts'].get(draft['lead_id'], {})
        if not contact.get('confirmed') or contact.get('selected_email') != draft['recipient']:
            raise ValueError('收件地址尚未确认或已经变化。')
        if state.get('mode') != 'demo' and (not mail_ready() or mail_config()['from'] != draft['sender']):
            raise ValueError('SMTP 配置不完整或发件地址已改变。')
        previous.add(draft['recipient'].casefold())
        approvals[draft['id']] = draft_digest(draft)
    return {'mail_approvals': approvals, 'outreach_action': 'send', 'notice': ''}
