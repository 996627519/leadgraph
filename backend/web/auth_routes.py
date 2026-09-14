import asyncio
import secrets
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from backend.service.auth_service import RateLimitError

SESSION_COOKIE = 'lg_session'
CSRF_COOKIE = 'lg_csrf'


class Credentials(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


def csrf_response(payload, request, *, secure=False, rotate=False):
    token = request.cookies.get(CSRF_COOKIE) if not rotate else None
    token = token or secrets.token_urlsafe(32)
    response = JSONResponse({**payload, 'token': token}, headers={'Cache-Control': 'no-store'})
    response.set_cookie(CSRF_COOKIE, token, httponly=True, samesite='strict', secure=secure, path='/')
    return response


def mount_auth(app, auth, *, secure=False, allow_registration=True):
    @app.get('/api/auth/csrf')
    async def csrf(request: Request):
        return csrf_response({'registration_enabled': allow_registration}, request, secure=secure)

    @app.post('/api/auth/register', status_code=201)
    async def register(request: Request, data: Credentials):
        if not allow_registration:
            raise HTTPException(403, '当前不开放注册，请联系管理员创建账号。')
        try:
            auth.limit(request.client.host if request.client else 'local', data.username, register=True)
        except RateLimitError as exc:
            raise HTTPException(429, str(exc)) from None
        return await asyncio.to_thread(auth.register, data.username, data.password)

    @app.post('/api/auth/login')
    async def login(request: Request, data: Credentials):
        try:
            auth.limit(request.client.host if request.client else 'local', data.username)
        except RateLimitError as exc:
            raise HTTPException(429, str(exc)) from None
        try:
            token, user = await asyncio.to_thread(auth.login, data.username, data.password)
        except ValueError:
            raise HTTPException(401, '用户名或密码不正确。') from None
        # 轮换会话，避免复用登录前或之前账号的令牌。
        await asyncio.to_thread(auth.logout, request.cookies.get(SESSION_COOKIE))
        response = csrf_response({'user': user}, request, secure=secure, rotate=True)
        response.set_cookie(SESSION_COOKIE, token, max_age=auth.ttl, httponly=True,
                            samesite='strict', secure=secure, path='/')
        return response

    @app.post('/api/auth/logout')
    async def logout(request: Request):
        await asyncio.to_thread(auth.logout, request.cookies.get(SESSION_COOKIE))
        response = csrf_response({'message': '已退出登录'}, request, secure=secure, rotate=True)
        response.delete_cookie(SESSION_COOKIE, path='/', secure=secure, httponly=True, samesite='strict')
        return response
