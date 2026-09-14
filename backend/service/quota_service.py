"""只读取服务商官方额度接口；账户余额不从本次搜索计数推算。"""
import asyncio
import os
import time
from copy import deepcopy
from decimal import Decimal, InvalidOperation
import httpx
from backend.persistend.studio_store import now


def amount(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        number = Decimal(str(value))
        return str(number) if number.is_finite() else None
    except InvalidOperation:
        return None


def budget(usage, limit):
    used, cap = amount(usage), amount(limit)
    # 缺少上限时保留未知，不能解释为 0 或无限。
    remaining = str(max(Decimal(0), Decimal(cap)-Decimal(used))) if used is not None and cap is not None else None
    return {'used': used, 'limit': cap, 'remaining': remaining}


def parse_deepseek(data):
    balances = []
    for entry in data.get('balance_infos', []):
        balances.append({'currency': str(entry.get('currency', '')), 'total': amount(entry.get('total_balance')),
                         'granted': amount(entry.get('granted_balance')), 'topped_up': amount(entry.get('topped_up_balance'))})
    if not balances:
        raise ValueError('No balance data')
    return {'balances': balances, 'is_available': data.get('is_available')}


def parse_tavily(data):
    key, account = data.get('key'), data.get('account')
    if not isinstance(key, dict) or not isinstance(account, dict):
        raise ValueError('No usage data')
    return {'unit': 'credits', 'key': budget(key.get('usage'), key.get('limit')),
            'plan': budget(account.get('plan_usage'), account.get('plan_limit')),
            'paygo': budget(account.get('paygo_usage'), account.get('paygo_limit')),
            'plan_name': str(account.get('current_plan', '')), 'search_used': amount(key.get('search_usage'))}


class QuotaService:
    def __init__(self, client=None, *, ttl=90, clock=time.monotonic):
        self.client = client
        self.ttl, self.clock = max(75, ttl), clock
        self.cache, self.lock = None, asyncio.Lock()

    async def _one(self, client, provider, url, key, parser):
        if not key:
            return {'provider': provider, 'status': 'not_configured', 'message': '尚未配置 API Key', 'checked_at': now()}
        try:
            response = await client.get(url, headers={'Authorization': 'Bearer ' + key})
            response.raise_for_status()
            return {'provider': provider, 'status': 'ok', 'checked_at': now(), **parser(response.json())}
        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code
            message = '额度查询认证失败' if code in {401, 403} else '服务商额度查询限流，请稍后刷新' if code == 429 else '服务商暂时无法提供额度'
        except Exception:
            message = '额度暂时无法读取，请稍后刷新'
        return {'provider': provider, 'status': 'unavailable', 'message': message, 'checked_at': now()}

    async def get(self):
        async with self.lock:
            if self.cache and self.clock() < self.cache[0]:
                return {**deepcopy(self.cache[1]), 'cached': True}
            client = self.client or httpx.AsyncClient(timeout=8, follow_redirects=False)
            try:
                deepseek, tavily = await asyncio.gather(
                    self._one(client, 'DeepSeek', 'https://api.deepseek.com/user/balance',
                              os.getenv('DEEPSEEK_API_KEY') or os.getenv('deepseek_api_key'), parse_deepseek),
                    self._one(client, 'Tavily', 'https://api.tavily.com/usage',
                              os.getenv('TAVILY_API_KEY') or os.getenv('tavily_api_key'), parse_tavily),
                )
            finally:
                if self.client is None:
                    await client.aclose()
            result = {'scope': 'workspace', 'deepseek': deepseek, 'tavily': tavily,
                      'cached': False, 'refresh_interval_seconds': self.ttl}
            self.cache = (self.clock()+self.ttl, result)
            return deepcopy(result)
