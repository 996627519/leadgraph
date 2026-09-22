#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：email_service.py
@Author ：zlh
@Date ：2026-09-14 10:30 
"""
import os
import re
import smtplib
import ssl
import asyncio
import hashlib
import json
import sqlite3
from pathlib import Path
from email.message import EmailMessage
from email.utils import formatdate, make_msgid

EMAIL = re.compile(r'^[A-Za-z0-9.!#$%&\x27*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,63}$')

"""
1. 校验类型
2. 校验长度
3. 检查基本邮件格式
4. 排除连续两个点
"""
def valid_email(value):
    return isinstance(value, str) and len(value) <= 254 and bool(EMAIL.fullmatch(value)) and '..' not in value


# 读取 SMTP 主机、端口、账号、密码、发件人和连接方式。如果端口不是合法整数，先变成 0，后续就会判定配置未就绪。
def mail_config():
    try:
        port = int(os.getenv('SMTP_PORT', '465'))
    except ValueError:
        port = 0
    return {
        'host': os.getenv('SMTP_HOST', ''), 'port': port,
        'username': os.getenv('SMTP_USERNAME', ''), 'password': os.getenv('SMTP_PASSWORD', ''),
        'from': os.getenv('SMTP_FROM', ''), 'security': os.getenv('SMTP_SECURITY', 'ssl'),
    }


# 检查必要配置是否齐全，端口是否有效，连接模式是否支持
def mail_ready():
    c = mail_config()
    return bool(c['host'] and 1 <= c['port'] <= 65535 and c['username'] and c['password'] and valid_email(c['from']) and c['security'] in {'ssl', 'starttls'})

"""
SMTP操作
检查配置
检查地址和主题
检查发邮件地址是否和草稿一致
构造EmailMessage
建立加密连接
登录
提交邮件
返回发送结果
"""
def submit_mail(draft, *, demo=False, smtp_factory=None):
    if demo:
        return {'status': 'simulated', 'message_id': make_msgid(domain='demo.invalid')}
    if not mail_ready():
        return {'status': 'failed', 'error': 'SMTP 尚未正确配置。'}
    if not valid_email(draft['recipient']) or '\n' in draft['subject'] or '\r' in draft['subject']:
        return {'status': 'failed', 'error': '收件地址或主题不合法。'}
    config = mail_config()
    if draft.get('sender') != config['from']:
        return {'status': 'failed', 'error': '发件地址已改变，请重新生成并审核邮件。'}
    message = EmailMessage()
    message['From'], message['To'], message['Subject'] = config['from'], draft['recipient'], draft['subject']
    message['Date'], message['Message-ID'] = formatdate(localtime=False), make_msgid()
    message.set_content(draft['body'])
    client, submitted = None, False
    try:
        if smtp_factory:
            client = smtp_factory()
        elif config['security'] == 'ssl':
            client = smtplib.SMTP_SSL(config['host'], config['port'], timeout=30, context=ssl.create_default_context())
        else:
            client = smtplib.SMTP(config['host'], config['port'], timeout=30)
            client.ehlo()
            client.starttls(context=ssl.create_default_context())
            client.ehlo()
        client.login(config['username'], config['password'])
        submitted = True
        refused = client.send_message(message, to_addrs=[draft['recipient']])
        if refused:
            return {'status': 'failed', 'error': '邮箱服务器拒绝了收件地址。'}
        return {'status': 'sent', 'message_id': message['Message-ID']}
    except (smtplib.SMTPRecipientsRefused, smtplib.SMTPDataError):
        return {'status': 'failed', 'error': '邮箱服务器明确拒绝了这封邮件。'}
    except Exception:
        return {'status': 'unknown' if submitted else 'failed',
                'error': '发送结果不确定，请检查发件记录；系统不会自动重发。' if submitted else '连接或认证失败，请检查 SMTP 配置。'}
    finally:
        if client is not None:
            try:
                client.close()
            except Exception:
                pass


# 检查准备发送的草稿和审核通过的那一份是否相同
def draft_digest(draft):
    fields = {key: draft[key] for key in ('id', 'revision', 'sender', 'recipient', 'subject', 'body')}
    return hashlib.sha256(json.dumps(fields, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


class EmailService:
    """SMTP 服务 + 持久发送台账。图重放也不会自动重复投递。"""
    def __init__(self, path=None, transport=None, *, ledger=None):
        self.ledger = ledger
        self.path = Path(path or os.getenv('LEADGRAPH_MAIL_DB', 'data/mail.sqlite3'))
        self.transport = transport or submit_mail

    def _connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=10)
        db.execute('''CREATE TABLE IF NOT EXISTS deliveries (
            run_id TEXT NOT NULL, draft_id TEXT NOT NULL, recipient TEXT NOT NULL,
            digest TEXT NOT NULL, result TEXT NOT NULL,
            PRIMARY KEY (run_id, draft_id), UNIQUE (run_id, recipient))''')
        return db

    # 图节点发送邮件的入口
    async def send_once(self, run_id, draft, approval, *, demo=False):
        if not approval or approval != draft_digest(draft):
            raise ValueError('审核内容与当前邮件不一致，禁止发送。')
        return await asyncio.to_thread(self._submit_once, run_id, dict(draft), approval, demo)

    """
    同一任务 + 同一草稿：不能重复领取
    同一任务 + 同一收件地址：不能重复领取
    
    先写入 sending 并提交事务
    ↓
    再调用 SMTP
    ↓
    最后写入 sent / failed / unknown
    
    如果再遇到相同草稿：
    - 已有确定结果：返回旧结果。
    - 已经是 sending 但没有最终结果：提示不确定，不自动重发。
    - 内容版本不一致：拒绝。
    - 同一任务里相同收件人已有其他记录：拒绝。
    """
    def _submit_once(self, run_id, draft, approval, demo):
        if self.ledger is not None:
            previous = self.ledger.claim_delivery(run_id, draft, approval)
            if previous is not None:
                return previous
            try:
                result = self.transport(draft, demo=demo)
            except Exception:
                result = {'status': 'unknown', 'error': '发送结果不确定，请核查发件记录。'}
            self.ledger.finish_delivery(run_id, draft['id'], result)
            return result
        db = self._connect()
        try:
            db.execute('BEGIN IMMEDIATE')
            previous = db.execute('SELECT digest, result FROM deliveries WHERE run_id=? AND draft_id=?',
                                  (run_id, draft['id'])).fetchone()
            if previous:
                if previous[0] != approval:
                    raise ValueError('这封邮件已有其他版本的发送记录。')
                result = json.loads(previous[1])
                if result['status'] == 'sending':
                    result = {'status': 'unknown', 'error': '曾进入发送但结果未记录，请人工核查；不会自动重发。'}
                return result
            try:
                db.execute('INSERT INTO deliveries VALUES (?,?,?,?,?)',
                           (run_id, draft['id'], draft['recipient'].casefold(), approval,
                            json.dumps({'status': 'sending'})))
            except sqlite3.IntegrityError:
                raise ValueError('此任务中相同收件地址已有发送记录。') from None
            db.commit()  # 先持久化领取，再执行网络副作用。
        finally:
            db.close()
        try:
            result = self.transport(draft, demo=demo)
        except Exception:
            result = {'status': 'unknown', 'error': '发送结果不确定，请核对邮箱记录。'}
        db = self._connect()
        try:
            db.execute('UPDATE deliveries SET result=? WHERE run_id=? AND draft_id=?',
                       (json.dumps(result, ensure_ascii=False), run_id, draft['id']))
            db.commit()
        finally:
            db.close()
        return result

    def results(self, run_id):
        if self.ledger is not None:
            return self.ledger.delivery_results(run_id)
        db = self._connect()
        try:
            rows = db.execute('SELECT draft_id, result FROM deliveries WHERE run_id=?', (run_id,)).fetchall()
            return {key: json.loads(value) for key, value in rows}
        finally:
            db.close()
