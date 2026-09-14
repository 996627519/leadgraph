#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：test_studio_mail.py
@Author ：zlh
@Date ：2026-09-14 10:46 
"""
import smtplib
import pytest
from backend.service.email_service import submit_mail,valid_email,mail_ready
from backend.service.outreach_service import extract_emails


@pytest.fixture
def configured(monkeypatch):
    for key,value in {'SMTP_HOST':'smtp.example.com','SMTP_PORT':'465','SMTP_SECURITY':'ssl',
                      'SMTP_USERNAME':'user','SMTP_PASSWORD':'password','SMTP_FROM':'sender@example.com'}.items():
        monkeypatch.setenv(key,value)
    return {'recipient':'recipient@example.com','sender':'sender@example.com','subject':'Test','body':'Reviewed content'}


def test_demo_never_connects_smtp(monkeypatch):
    monkeypatch.setattr(smtplib,'SMTP_SSL',lambda *a,**k:(_ for _ in ()).throw(AssertionError('network forbidden')))
    assert submit_mail({},demo=True)['status']=='simulated'


def test_success_then_quit_error_does_not_turn_sent_into_failure(configured):
    class SMTP:
        def login(self,*args): pass
        def send_message(self,message,**kw):
            assert message['To']=='recipient@example.com'
            assert kw['to_addrs']==['recipient@example.com']
            assert 'Reviewed content' in message.get_content()
            return {}
        def close(self): raise OSError('close failed')
    assert submit_mail(configured,smtp_factory=SMTP)['status']=='sent'


def test_disconnect_after_submission_is_unknown_not_retryable(configured):
    class SMTP:
        def login(self,*args): pass
        def send_message(self,*args,**kw): raise TimeoutError()
        def close(self): pass
    assert submit_mail(configured,smtp_factory=SMTP)['status']=='unknown'


def test_auth_failure_is_definite_failure(configured):
    class SMTP:
        def login(self,*args): raise smtplib.SMTPAuthenticationError(535,b'denied')
        def close(self): pass
    assert submit_mail(configured,smtp_factory=SMTP)['status']=='failed'


def test_sender_changed_after_review_is_not_sent(configured):
    configured['sender']='old@example.com'
    assert submit_mail(configured)['status']=='failed'


def test_smtp_requires_encrypted_transport(configured,monkeypatch):
    monkeypatch.setenv('SMTP_SECURITY','plain')
    assert not mail_ready()


def test_email_extraction_requires_identity_and_literal_email():
    results=[{'url':'https://example.com/team','title':'Alice Jones at Alpha','content':'Alice Jones at Alpha. Contact alice@example.com'},
             {'url':'https://other.example','title':'Other company','content':'other@example.com'}]
    found=extract_emails(results,'Alice Jones','Alpha')
    assert [c['email'] for c in found]==['alice@example.com']
    assert found[0]['verification']=='public_candidate'


@pytest.mark.parametrize('value',['x\r\nBcc:y@example.com','plain','a@localhost','a@example.com, b@example.com'])
def test_email_validation(value): assert not valid_email(value)
