import asyncio
import json
import httpx
import pytest
from backend.service.quota_service import QuotaService, parse_deepseek, parse_tavily, budget


def test_precise_balances_and_missing_limits():
    assert parse_deepseek({'balance_infos':[{'currency':'CNY','total_balance':'12.34000001'}]})['balances'][0]['total'] == '12.34000001'
    data = parse_tavily({'key': {'usage': 20}, 'account': {'plan_usage': 120, 'plan_limit': 100}})
    assert data['key']['remaining'] is None
    assert data['plan']['remaining'] == '0'
    assert data['paygo']['remaining'] is None
    assert budget(0, 0)['remaining'] == '0'
    assert budget(True, 100)['remaining'] is None
    assert budget('NaN', 100)['remaining'] is None


@pytest.mark.asyncio
async def test_cache_merges_concurrent_refreshes_partial_failure_and_no_secrets(monkeypatch):
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'test-deepseek-secret')
    monkeypatch.setenv('TAVILY_API_KEY', 'test-tavily-secret')
    calls = []
    def handler(request):
        calls.append(request)
        if request.url.host == 'api.deepseek.com':
            return httpx.Response(200, json={'balance_infos':[{'currency':'CNY','total_balance':'1.25'}]})
        return httpx.Response(429, json={'private':'test-tavily-secret'})
    clock = [0]
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = QuotaService(client, clock=lambda: clock[0])
        results = await asyncio.gather(*(service.get() for _ in range(10)))
        assert len(calls) == 2
        assert results[0]['deepseek']['status'] == 'ok'
        assert results[0]['tavily']['status'] == 'unavailable'
        assert results[1]['cached'] is True
        assert 'secret' not in json.dumps(results)
        clock[0] = 91
        await service.get()
        assert len(calls) == 4


@pytest.mark.asyncio
async def test_missing_keys_no_requests(monkeypatch):
    for key in ['DEEPSEEK_API_KEY','deepseek_api_key','TAVILY_API_KEY','tavily_api_key']:
        monkeypatch.delenv(key, raising=False)
    def forbidden(request):
        raise AssertionError('No request without configured key')
    async with httpx.AsyncClient(transport=httpx.MockTransport(forbidden)) as client:
        data = await QuotaService(client).get()
    assert data['deepseek']['status'] == data['tavily']['status'] == 'not_configured'
