// 会话只保存在 HttpOnly Cookie 中；页面不保存密码或登录凭据。
export async function authenticate() {
    const root = document.querySelector('#auth-root');
    document.querySelector('.app-shell').hidden = true;
    root.hidden = false;
    root.innerHTML = '<div class="auth-loading"><span class="spinner"></span>正在连接工作空间…</div>';
    let csrf;
    async function request(path, data) {
        const response = await fetch('/api' + path, {
            method: data ? 'POST' : 'GET',
            headers: {'Content-Type': 'application/json', 'X-Studio-Token': csrf?.token || ''},
            body: data ? JSON.stringify(data) : undefined
        });
        const result = await response.json();
        if (!response.ok) throw Error(typeof result.detail === 'string' ? result.detail : '请检查输入后重试。');
        return result;
    }
    try {
        csrf = await request('/auth/csrf');
        const response = await fetch('/api/session');
        if (response.ok) return await response.json();
        if (response.status !== 401) throw Error('后台服务暂时无法连接。');
    } catch {
        root.innerHTML = '<div class="auth-card"><h1>暂时无法连接</h1><p>请确认后台与 MySQL 已启动，再刷新页面。</p><button class="button green" id="auth-retry">重新连接</button></div>';
        root.querySelector('button').onclick = () => location.reload();
        return new Promise(() => {});
    }
    return new Promise(resolve => {
        let registering = false;
        const draw = () => {
            root.innerHTML = `<section class="auth-story"><span class="auth-wordmark">LeadGraph <small>STUDIO</small></span><span class="auth-kicker">每一段好对话，都从了解开始。</span><h1>发现对的人。<br>开启下一次合作。</h1><p>从线索研究、人工审核，到一封经过你确认的邮件。<br>让每一步联系，都有依据。</p><div class="auth-journey"><span>01 · 发现</span><i></i><span>02 · 了解</span><i></i><span>03 · 对话</span></div><div class="auth-orbit" aria-hidden="true"><b>LG</b><i></i><i></i></div></section><section class="auth-card"><span class="auth-kicker">你的专属工作空间</span><h2>${registering ? '创建账户' : '欢迎回来'}</h2><p>${registering ? '创建账户，开始你的第一项客户研究。' : '登录后继续研究，查看你的联系人和邮件。'}</p><form id="auth-form"><label>用户名<input name="username" required minlength="3" maxlength="32" pattern="[A-Za-z0-9_][A-Za-z0-9_.-]{2,31}" autocomplete="username" placeholder="3–32 位字母、数字、下划线" autofocus></label><label>密码<input name="password" type="password" required minlength="${registering ? 10 : 1}" maxlength="128" autocomplete="${registering ? 'new-password' : 'current-password'}" placeholder="${registering ? '至少 10 个字符' : '请输入密码'}"></label><p class="auth-error" role="alert"></p><button type="submit" class="button green">${registering ? '创建并登录' : '登录工作空间'}<span>→</span></button></form>${csrf.registration_enabled ? `<button type="button" class="auth-switch">${registering ? '已有账户？返回登录' : '还没有账户？创建账户'}</button>` : '<p class="auth-hint">请联系管理员创建账户。</p>'}<p class="auth-hint">你的任务与其他账户独立保存。</p></section>`;
            root.querySelector('.auth-switch')?.addEventListener('click', () => { registering = !registering; draw(); });
            root.querySelector('form').addEventListener('submit', async event => {
                event.preventDefault();
                event.stopPropagation();
                const form = event.currentTarget, button = form.querySelector('button');
                const data = Object.fromEntries(new FormData(form));
                button.disabled = true;
                form.querySelector('.auth-error').textContent = '';
                try {
                    if (registering) {
                        await request('/auth/register', data);
                        registering = false;
                    }
                    csrf = await request('/auth/login', data);
                    form.reset();
                    resolve(await request('/session'));
                } catch (error) {
                    form.querySelector('.auth-error').textContent = error.message;
                    button.disabled = false;
                }
            });
        };
        draw();
    });
}
