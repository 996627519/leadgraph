import {authenticate} from './auth.js';
const paths = {
    grid: 'M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z',
    compass: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18 M16 8l-3 5-5 3 3-5z',
    users: 'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2 M9 3a4 4 0 1 0 0 8 4 4 0 0 0 0-8 M17 4a4 4 0 0 1 0 7 M22 21v-2a4 4 0 0 0-3-3.9',
    mail: 'M3 5h18v14H3z M3 6l9 7 9-7',
    spark: 'M12 3l2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5z',
    plus: 'M12 5v14 M5 12h14',
    chevron: 'M7 10l5 5 5-5',
    arrow: 'M4 12h16 M14 6l6 6-6 6',
    refresh: 'M20 7v5h-5 M4 17v-5h5 M6 6a8 8 0 0 1 14 5 M18 18A8 8 0 0 1 4 13',
    settings: 'M9 3h6l1 3 3 1 2 5-2 5-3 1-1 3H9l-1-3-3-1-2-5 2-5 3-1z M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8',
    menu: 'M4 6h16 M4 12h16 M4 18h16',
    check: 'M5 12l4 4L19 6',
    search: 'M10.5 3a7.5 7.5 0 1 0 0 15 7.5 7.5 0 0 0 0-15 M16 16l5 5',
    building: 'M4 21V5h10v16 M14 10h6v11 M2 21h20 M7 8h4 M7 12h4 M7 16h4 M17 14h1 M17 17h1',
    pin: 'M20 10c0 6-8 11-8 11S4 16 4 10a8 8 0 1 1 16 0 M12 7a3 3 0 1 0 0 6 3 3 0 0 0 0-6',
    clock: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18 M12 7v5l3 2',
    shield: 'M12 3l8 3v6c0 5-8 9-8 9s-8-4-8-9V6z M8 12l3 3 5-6',
    send: 'M22 2L9 15 M22 2l-6 20-7-7-7-7z',
    close: 'M6 6l12 12 M6 18L18 6',
    link: 'M10 13a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-2 2 M14 11a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l2-2',
    edit: 'M16 3l5 5-12 12H4v-5z M13 6l5 5',
    info: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18 M12 11v6 M12 7h.01',
    download: 'M12 3v12 M7 10l5 5 5-5 M4 16v5h16v-5',
    copy: 'M8 8h13v13H8z M16 8V3H3v13h5',
    leaf: 'M20 3c-9 0-16 2-16 9a7 7 0 0 0 7 7c7 0 9-7 9-16 M4 21L16 9'
};
const icon = n => `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="${paths[n] || paths.spark}"/></svg>`;
document.querySelectorAll('[data-icon]').forEach(e => e.innerHTML = icon(e.dataset.icon));
const $ = s => document.querySelector(s), esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
}[c]));
const safeURL = s => {
    try {
        const u = new URL(s);
        return ['https:', 'http:'].includes(u.protocol) ? esc(u.href) : '#'
    } catch {
        return '#'
    }
};
const initials = name => name.split(' ').map(x => x[0]).slice(0, 2).join('');
const state = {
    session: null,
    usage: null,
    mode: 'demo',
    run: null,
    view: 'home',
    history: [],
    selected: new Set(),
    query: '',
    filter: '',
    quality: 'all',
    draftId: null,
    dirty: false,
    stream: null
};
let toastTimer, loadSequence = 0;

function toast(message) {
    $('#toast').textContent = message;
    $('#toast').classList.add('toast-visible');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => $('#toast').classList.remove('toast-visible'), 4500)
}

async function api(path, method = 'GET', data) {
    const session = state.session;
    const response = await fetch('/api' + path, {
        method,
        headers: {'Content-Type': 'application/json', 'X-Studio-Token': state.session?.token || ''},
        body: data === undefined ? undefined : JSON.stringify(data)
    });
    const result = await response.json();
    if (session !== state.session) throw Error('账户已切换，请重新操作。');
    if (response.status === 401) void boot();
    if (!response.ok) throw Error(typeof result.detail === 'string' ? result.detail : '输入内容不完整，请检查后重试。');
    return result
}

function busy() {
    return state.run && (['researching', 'contacts_searching', 'drafting', 'sending'].includes(state.run.status) || state.run.drafts.some(d => d.status === 'sending'))
}

function modeBanner() {
    return state.run?.mode === 'demo' ? `<div class="mode-banner">${icon('info')}这是演示任务：联系人与邮箱均为虚构数据，发送操作只会生成演示记录。</div>` : ''
}

function steps(index) {
    return `<div class="stepper">${['发现目标客户', '审核与查找邮箱', '生成与编辑邮件', '确认并发送'].map((t, i) => `<div class="step ${i === index ? 'active' : i < index ? 'done' : ''}"><span class="step-no">${i < index ? '✓' : `0${i + 1}`}</span>${t}</div>`).join('')}</div>`
}

function heading(title, description, action = '') {
    return `<div class="page-heading"><div><h1>${title}</h1><p>${description}</p></div>${action}</div>`
}

function empty(title, description) {
    return `<div class="empty-state"><div class="empty-icon">${icon('compass')}</div><h2>${title}</h2><p>${description}</p><button class="button green" data-action="home">${icon('plus')}开始一次新研究</button></div>`
}

function render() {
    if (!state.session) return;
    const labels = {
        home: '概览',
        research: '客户发现',
        review: '联系人审核',
        contacts: '联系方式',
        compose: '邮件工作台'
    };
    $('#page-label').textContent = labels[state.view] || '概览';
    $('#mode-button').innerHTML = `${state.mode === 'demo' ? '演示模式' : '真实服务'}${icon('chevron')}`;
    $('#side-count').textContent = state.run?.leads.length || '';
    document.querySelectorAll('[data-nav]').forEach(e => e.classList.toggle('active', e.dataset.nav === (state.view === 'contacts' ? 'review' : state.view)));
    const main = $('#main');
    main.classList.add('fade-in');
    if (state.view === 'home') main.innerHTML = home();
    else if (!state.run) main.innerHTML = empty('从一个清晰的目标开始', '新建一次研究，联系人和邮件会按任务保存在这里。');
    else if (state.view === 'research') main.innerHTML = progress();
    else if (state.view === 'review') main.innerHTML = review();
    else if (state.view === 'contacts') main.innerHTML = contacts();
    else main.innerHTML = compose();
    if (state.run?.status === 'interrupted') main.insertAdjacentHTML('afterbegin', `<div class="notice">执行位置已保存。恢复将继续图任务，未完成的搜索可能再次调用服务；已记录的邮件不会自动重发。 <button class="button small" data-action="continue">恢复图任务</button></div>`);
    if ($('#query')) $('#query').value = state.query;
    setTimeout(() => main.classList.remove('fade-in'), 320);
}

function home() {
    const total = state.history.reduce((n, r) => n + r.lead_count, 0);
    return `
<div class="welcome-row"><div><div class="eyebrow">A LITTLE RESEARCH. A BETTER CONVERSATION.</div><h1>你好，准备发现新的机会吗？</h1><p>从了解客户，到写下第一封邮件，LeadGraph 陪你走好每一步。</p></div><span class="date-chip">${new Date().toLocaleDateString('zh-CN', {
        month: 'long',
        day: 'numeric',
        weekday: 'long'
    })}</span></div>
${usagePanel()}<section class="hero"><div class="hero-copy"><div class="hero-tag">${icon('spark')} YOUR NEXT OPPORTUNITY</div><h2>找到对的人，<br>开启<em>有价值的对话。</em></h2><p>告诉我们你想寻找什么样的客户。<br>让研究更有方向，让每一封邮件都言之有物。</p></div><div class="hero-diagram" aria-hidden="true"><div class="orbit"></div><div class="diagram-core">${icon('leaf')}</div><div class="diagram-chip c1">${icon('search')}<div>理解你的目标<small>Start with an idea</small></div></div><div class="diagram-chip c2">${icon('building')}<div>发现合适的公司<small>Find the right fit</small></div></div><div class="diagram-chip c3">${icon('users')}<div>认识关键联系人<small>Know who matters</small></div></div><div class="diagram-chip c4">${icon('mail')}<div>开启新的对话<small>Make it personal</small></div></div><span class="diagram-star">✧</span></div></section>
<section class="entry-card"><div class="section-top"><h2 class="label-icon">${icon('compass')}开始一次客户研究</h2><span class="tag ${state.mode === 'demo' ? 'warn' : 'blue'}">${state.mode === 'demo' ? '演示模式 · 不消耗搜索额度' : '真实服务 · 使用已配置账号'}</span></div><form id="research-form"><div class="query-box"><textarea id="query" maxlength="3000" required minlength="5" aria-label="客户研究要求" placeholder="例如：寻找英国乳制品加工公司的工程经理或采购负责人，优先关注有大型生产线、可能需要消毒设备的企业。"></textarea><div class="query-tools"><span class="hint">${icon('info')}加上地区、行业与岗位，结果会更有针对性。</span><button class="button green" type="submit">开始研究${icon('arrow')}</button></div></div></form><div class="suggestions"><span>试试这些方向</span><button data-example="寻找英国乳制品加工公司的工程经理，关注生产线升级和消毒设备需求">英国乳制品 · 工程负责人</button><button data-example="寻找德国食品加工企业的采购经理，关注工业包装设备合作">德国食品加工 · 采购经理</button><button data-example="寻找新加坡软件公司的运营负责人，关注客户服务系统">新加坡 SaaS · 运营负责人</button></div></section>
<div class="stat-grid"><div class="stat"><span class="stat-icon">${icon('compass')}</span><div><strong>${state.history.length.toString().padStart(2, '0')}</strong><small>已创建的研究任务</small></div><span>全部记录</span></div><div class="stat"><span class="stat-icon blue">${icon('users')}</span><div><strong>${total.toString().padStart(2, '0')}</strong><small>已整理的联系人</small></div><span>等待好对话</span></div><div class="stat"><span class="stat-icon peach">${icon('shield')}</span><div><strong>你来决定</strong><small>审核后联系，确认后发送</small></div></div></div>
<div class="bottom-grid"><section class="panel"><div class="section-top"><h3>把复杂的事，变成清晰的四步。</h3></div><div class="mini-steps">${[['01', '描述目标', '告诉我们你的理想客户'], ['02', '审核联系人', '确认人选与公开邮箱'], ['03', '写好邮件', '关键词变成个性化草稿'], ['04', '确认发送', '每次联系都由你决定']].map(a => `<div class="mini-step"><span>${a[0]}</span><b>${a[1]}</b><p>${a[2]}</p></div>`).join('')}</div></section><section class="panel"><div class="section-top"><h3 class="label-icon">${icon('leaf')}给好结果一点提示</h3></div><ul class="note-list"><li>${icon('check')}写清楚行业、地区和你希望接触的岗位。</li><li>${icon('check')}把“必须满足”和“优先考虑”分开描述。</li><li>${icon('check')}先体验演示，再连接你的搜索与邮箱服务。</li></ul></section></div>`
}

function progress() {
    const r = state.run;
    const stageIdx = Math.max(0, ['plan', 'companies', 'people', 'verify', 'review'].indexOf(r.stage));
    const stageNames = ['理解目标与规划搜索', '发现与筛选目标公司', '寻找关键联系人', '核验资料与整理证据'];
    const latest = r.events.at(-1);
    if (r.status !== 'researching') {
        return modeBanner() + steps(0) + heading('你的研究已更新', esc(r.query)) + (r.leads.length ? `<div class="empty-state"><div class="empty-icon">${icon('check')}</div><h2>已整理 ${r.leads.length} 位联系人</h2><p>查看公开资料和信息可靠度，再决定联系谁。</p><button class="button green" data-action="review">查看研究结果${icon('arrow')}</button></div>` : empty('本次研究没有生成联系人', esc(r.notice || '请尝试明确岗位，或调整地区与行业条件。')))
    }
    return `${modeBanner()}${steps(0)}${heading('研究正在进行，好机会值得一点耐心。', esc(r.query), '<button class="button small ghost" data-action="cancel">停止研究</button>')}<div class="progress-layout"><section class="progress-card"><span class="working-pill"><i class="live-dot"></i>RESEARCH IN PROGRESS</span><div class="pulse-visual"><span class="halo"></span><span class="halo"></span><span class="halo"></span><div class="core">${icon('spark')}</div></div><h2>${esc(latest?.title || '正在理解你的目标')}</h2><p>${esc(latest?.detail || '我们正在为这次研究制定搜索计划。')}</p><div class="progress-mini">${[0, 1, 2, 3].map(i => `<i class="${i < stageIdx ? 'done' : i === stageIdx ? 'active' : ''}"></i>`).join('')}</div><span class="elapsed">阶段 ${Math.min(stageIdx + 1, 4)} / 4 · 已运行 <b id="elapsed">${elapsed()}</b></span></section><section class="panel"><div class="section-top"><h3>每一步，都有迹可循。</h3><span class="tag">实时进度</span></div><div class="timeline">${stageNames.map((n, i) => `<div class="timeline-row ${i < stageIdx ? 'done' : i === stageIdx ? 'active' : ''}"><span class="timeline-dot">${i < stageIdx ? '✓' : i + 1}</span><div><b>${n}</b><p>${i < stageIdx ? '已完成该阶段' : i === stageIdx ? '正在进行中…' : '等待前一步完成'}</p></div></div>`).join('')}</div></section></div><section class="panel live-log"><div class="section-top"><h3>研究动态</h3><span class="hint">页面可以离开，任务会继续运行</span></div>${r.events.slice(-5).reverse().map(e => `<div class="log-row"><time>${new Date(e.time).toLocaleTimeString('zh-CN', {hour12: false})}</time><span>${esc(e.title)}</span></div>`).join('') || '<p class="hint">正在准备研究环境…</p>'}</section>`
}

function filteredLeads() {
    return state.run.leads.filter(l => (`${l.name} ${l.company} ${l.title}`.toLowerCase().includes(state.filter.toLowerCase())) && (state.quality === 'all' || l.confidence >= .85))
}

function leadCards() {
    return filteredLeads().map((l, i) => `<article class="lead-card ${state.selected.has(l.id) ? 'selected' : ''}"><div class="card-top"><span class="avatar color${i % 4}">${esc(initials(l.name))}</span><input type="checkbox" data-lead="${l.id}" aria-label="选择 ${esc(l.name)}" ${state.selected.has(l.id) ? 'checked' : ''}></div><h3>${esc(l.name)}</h3><div class="lead-title">${esc(l.title)}</div><div class="company-line">${icon('building')}${esc(l.company)}</div><div class="location-line">${icon('pin')}${esc(l.location)}</div><div class="card-footer"><span class="confidence ${l.confidence < .85 ? 'medium' : ''}">证据可靠度 ${Math.round(l.confidence * 100)}%</span><button class="text-button" data-detail="${l.id}">查看资料${icon('arrow')}</button></div></article>`).join('') || '<div class="empty-state">没有符合筛选条件的联系人。</div>'
}

function review() {
    const r = state.run;
    if (!r.leads.length) return modeBanner() + empty('联系人还没有准备好', '研究完成后，会在这里展示人员信息和来源。');
    return `${modeBanner()}${steps(1)}${heading('好的人选，值得你亲自确认。', `已找到 ${r.leads.length} 位联系人。查看来源，选择你希望进一步了解的人。`, `<button class="button small" data-action="export">${icon('download')}导出资料</button>`)}${r.notice ? `<div class="notice">${esc(r.notice)}</div>` : ''}<div class="toolbar"><div class="search-input">${icon('search')}<input id="lead-search" aria-label="搜索联系人" placeholder="搜索姓名、公司或职位" value="${esc(state.filter)}"></div><select id="quality-filter" aria-label="可靠度筛选"><option value="all">所有可靠度</option><option value="high" ${state.quality === 'high' ? 'selected' : ''}>可靠度 ≥ 85%</option></select><label class="check-label"><input type="checkbox" id="select-all">选择当前结果</label></div><div class="lead-grid" id="lead-grid">${leadCards()}</div><div class="sticky-actions"><div class="selection-text">已选择 <strong id="selected-count">${state.selected.size}</strong> 位联系人<small>只有你选中的人会进入邮箱查找阶段。</small></div><div>${Object.keys(r.contacts).length ? '<button class="button small" data-action="contacts">查看已有邮箱</button> ' : ''}<button id="lookup-button" class="button green" data-action="lookup" ${!state.selected.size || busy() || r.drafts.length ? 'disabled' : ''}>查找联系方式${icon('arrow')}</button></div></div>`
}

function contactCard(l) {
    const c = state.run.contacts[l.id];
    if (!c) return `<article class="contact-card"><div class="contact-person"><span class="avatar">${esc(initials(l.name))}</span><div><h3>${esc(l.name)}</h3><p>${esc(l.company)}</p></div></div><div class="hint"><span class="spinner"></span>正在查找公开邮箱…</div></article>`;
    let value = c.selected_email || c.candidates[0]?.email || '';
    return `<article class="contact-card"><div class="contact-person"><span class="avatar">${esc(initials(l.name))}</span><div><h3>${esc(l.name)}</h3><p>${esc(l.company)}</p></div></div><div><form class="contact-input" data-contact-form="${l.id}"><input type="email" required aria-label="${esc(l.name)} 的邮箱" value="${esc(value)}" placeholder="未找到邮箱，可手动填写" ${c.confirmed ? 'disabled' : ''}><button class="button ${c.confirmed ? 'lime' : 'green'} small" ${c.confirmed || busy() ? 'disabled' : ''}>${c.confirmed ? '✓ 已确认' : '确认此邮箱'}</button></form>${c.candidates.length > 1 && !c.confirmed ? `<div class="contact-extra">候选地址：${c.candidates.map(x => `<button class="text-button" data-candidate="${esc(x.email)}" data-for="${l.id}">${esc(x.email)}</button>`).join('')}</div>` : ''}<div class="contact-extra">${c.confirmed ? '<span class="tag">由你审核确认</span>' : c.candidates.length ? '<span class="tag warn">公开候选 · 归属尚待确认</span>' : '<span class="tag gray">暂未发现邮箱</span>'}${c.candidates[0] ? `<button class="text-button" data-contact-source="${l.id}">${icon('link')}查看来源证据</button>` : '<span>可以填写你已确认的邮箱，继续下一步。</span>'}${c.error ? `<span>${esc(c.error)}</span>` : ''}</div></div></article>`
}

function contacts() {
    const r = state.run, leads = r.leads.filter(l => r.approved.includes(l.id)),
        confirmed = Object.values(r.contacts).filter(c => c.confirmed).length;
    if (!leads.length && r.status === 'contacts_searching') return modeBanner() + '<div class="loading-shell"><span class="spinner"></span>正在恢复图任务并查找已选人员的邮箱…</div>';
    if (!leads.length) return modeBanner() + empty('先选择你想联系的人', '审核联系人后，我们只为你选中的人员查找联系方式。');
    return `${modeBanner()}${steps(1)}${heading(r.status === 'contacts_searching' ? '正在为你寻找联系的入口。' : '找到邮箱，再多确认一步。', '公开邮箱只是候选信息。请查看来源、核对归属，或填写你已知的邮箱。', '<button class="button small" data-action="review">返回联系人</button>')}<div class="contacts-heading">${r.status === 'contacts_searching' ? '<span class="spinner"></span>' : ''}<b>${confirmed}</b> / ${leads.length} 位联系人的邮箱已确认</div>${r.notice ? `<div class="notice">${esc(r.notice)}</div>` : ''}<div class="contact-list">${leads.map(contactCard).join('')}</div><div class="sticky-actions"><div class="selection-text">让下一封邮件，发给<strong>对的人</strong><small>未确认邮箱的联系人不会进入邮件生成。</small></div><button class="button green" data-action="compose" ${!confirmed || busy() ? 'disabled' : ''}>开始撰写邮件${icon('arrow')}</button></div>`
}

function draftStatus(d) {
    const map = {
        draft: ['待审核', 'gray'],
        skipped: ['已选择不发送', 'gray'],
        sending: ['发送中', 'blue'],
        sent: ['已提交服务器', ''],
        simulated: ['演示已发送', ''],
        failed: ['提交失败', 'danger'],
        unknown: ['结果待核查', 'warn']
    };
    const [name, color] = map[d.status] || ['待审核', 'gray'];
    return `<span class="tag ${color}">${name}</span>`
}

function compose() {
    const r = state.run, available = r.leads.filter(l => r.contacts[l.id]?.confirmed);
    if (!available.length) return modeBanner() + empty('确认邮箱后，就可以开始写邮件了。', '先审核联系人并确认联系方式，再用关键词生成个性化草稿。');
    const drafting = r.status === 'drafting';
    if (!r.drafts.length) return `${modeBanner()}${steps(2)}${heading('你的想法，我们帮你写得更好。', `准备为 ${available.length} 位已确认邮箱的联系人撰写邮件。`, '<button class="button small" data-action="contacts">返回邮箱审核</button>')}<div class="compose-layout"><section class="recipient-list"><h3>收件人 · ${available.length}</h3>${available.map((l, i) => `<label class="recipient-item"><input type="checkbox" data-compose-lead="${l.id}" checked ${drafting ? 'disabled' : ''}><span><b>${esc(l.name)}</b><small>${esc(r.contacts[l.id].selected_email)}</small></span></label>`).join('')}</section><section class="panel"><div class="section-top"><h3 class="label-icon">${icon('edit')}这封邮件，你想说些什么？</h3></div>${r.notice ? `<div class="notice">${esc(r.notice)}</div>` : ''}<form id="brief-form"><div class="form-grid"><div class="form-field full"><label for="keywords">关键词或你想表达的内容</label><textarea id="keywords" rows="5" required minlength="3" maxlength="3000" placeholder="例如：我们提供大型牛奶消毒设备；希望了解对方的生产线升级计划；邀请进行 15 分钟线上交流。" ${drafting ? 'disabled' : ''}>${esc(r.brief?.keywords || '')}</textarea><small>可以写产品、合作方向、希望对方采取的行动。不会自动编造产品指标。</small></div><div class="form-field"><label for="mail-language">邮件语言</label><select id="mail-language"><option value="en">English · 英文</option><option value="zh">中文</option></select></div><div class="form-field"><label for="mail-tone">表达语气</label><select id="mail-tone"><option value="professional">专业得体</option><option value="friendly">友好自然</option><option value="concise">简洁直接</option></select></div><div class="form-field full"><label for="signature">你的署名</label><textarea id="signature" rows="2" required maxlength="1000" placeholder="你的姓名、公司与职位">${esc(r.brief?.signature || '')}</textarea></div></div><div class="editor-footer" style="margin-top:20px"><span>生成后可以逐封编辑，确认前不会发送。</span><button class="button green" ${drafting ? 'disabled' : ''}>${drafting ? '<span class="spinner"></span>正在撰写…' : icon('spark') + '生成邮件草稿'}</button></div></form></section></div>`;
    let draft = r.drafts.find(d => d.id === state.draftId) || r.drafts[0];
    state.draftId = draft.id;
    const unsent = r.drafts.filter(d => d.status === 'draft').length;
    return `${modeBanner()}${steps(r.drafts.some(d => d.status !== 'draft') ? 3 : 2)}${heading('让每封邮件，都带着你的表达。', `共 ${r.drafts.length} 封邮件。逐封核对后，再确认发送。`, `<button class="button small" data-action="contacts">查看收件人</button>`)}${r.notice ? `<div class="notice">${esc(r.notice)}</div>` : ''}${!unsent && !busy() && r.outreach_status !== 'skipped' && r.drafts.every(d => ['sent', 'simulated'].includes(d.status)) ? `<div class="notice">${r.mode === 'demo' ? '演示发送已完成，未投递任何真实邮件。' : '发送记录已更新。“已提交服务器”不代表收件人已收到或已阅读；请留意退信。'}</div>` : ''}<div class="compose-layout"><section class="recipient-list"><h3>邮件列表 · ${r.drafts.length}</h3>${r.drafts.map(d => {
        const l = r.leads.find(l => l.id === d.lead_id);
        return `<button class="recipient-item ${d.id === draft.id ? 'active' : ''}" data-draft="${d.id}"><span class="avatar">${esc(initials(l.name))}</span><span><b>${esc(l.name)}</b><small>${esc(d.recipient)}</small><small>${draftStatus(d)}</small></span></button>`
    }).join('')}</section><section class="draft-editor"><div class="section-top"><h3 class="label-icon">${icon('mail')}邮件草稿</h3>${draftStatus(draft)}</div><div class="mail-header"><span>发件人</span><b>${esc(draft.sender || '请配置 SMTP_FROM 后重新生成草稿')}</b></div><div class="mail-header"><span>收件人</span><b>${esc(draft.recipient)}</b></div><form id="draft-form"><div class="mail-header"><span>主题</span><input id="draft-subject" aria-label="邮件主题" required maxlength="200" value="${esc(draft.subject)}" ${draft.status !== 'draft' || busy() ? 'disabled' : ''}></div><textarea id="draft-body" aria-label="邮件正文" required maxlength="12000" ${draft.status !== 'draft' || busy() ? 'disabled' : ''}>${esc(draft.body)}</textarea><div class="editor-footer"><span id="save-state">已保存 · 版本 ${draft.revision}</span><div><button type="button" class="button small ghost" data-action="copy">${icon('copy')}复制</button><button type="submit" class="button small" ${draft.status !== 'draft' || busy() ? 'disabled' : ''}>保存修改</button></div></div></form>${draft.error ? `<div class="notice">${esc(draft.error)}</div>` : ''}</section></div><div class="sticky-actions"><div class="selection-text">还有 <strong>${unsent}</strong> 封邮件等待确认<small>${r.mode === 'demo' ? '演示模式只记录结果，不会真实投递。' : '逐封单独投递，不会向其他人公开收件地址。'}</small></div><div class="mail-actions">${r.interrupt_kind === 'compose' && !busy() ? '<button class="button" data-action="skip-send">不发送并结束</button>' : ''}<button class="button green" data-action="confirm-send" ${!unsent || busy() ? 'disabled' : ''}>核对并${r.mode === 'demo' ? '演示' : ''}发送${icon('send')}</button></div></div>`
}

function elapsed() {
    if (!state.run) return '00:00';
    const end = state.run.status === 'researching' ? Date.now() : new Date(state.run.updated_at).getTime();
    const s = Math.max(0, Math.floor((end - new Date(state.run.created_at)) / 1000));
    return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`
}

setInterval(() => {
    if ($('#elapsed')) $('#elapsed').textContent = elapsed()
}, 1000);

async function refreshHistory() {
    state.history = await api('/runs');
    $('#history').innerHTML = state.history.length ? state.history.slice(0, 7).map(r => `<button data-history="${r.id}" title="${esc(r.query)}">${esc(r.query)}</button>`).join('') : '<p class="history-empty">下一次机会，从这里开始。</p>'
}

function openStream() {
    state.stream?.close();
    if (!state.run || !busy()) return;
    const id = state.run.id;
    const source = new EventSource(`/api/runs/${id}/events?after=${state.run.events.at(-1)?.seq || 0}`);
    state.stream = source;
    source.addEventListener('snapshot', async e => {
        const info = JSON.parse(e.data);
        if (state.run?.id !== id) {
            source.close();
            return
        }
        if (info.version !== state.run.version) {
            const before = state.run.status;
            const fresh = await api('/runs/' + id);
            if (state.run?.id !== id || fresh.version < state.run.version) return;
            state.run = fresh;
            if (['researching', 'contacts_searching', 'drafting', 'sending'].includes(before) && !busy()) state.view = state.run.interrupt_kind === 'contacts' ? 'contacts' : state.run.drafts.length ? 'compose' : state.run.leads.length ? 'review' : 'research';
            if (!state.dirty) render();
            if (!busy()) {
                source.close();
                refreshHistory().catch(() => {
                });
            }
        }
    });
    source.onerror = () => {
        source.close();
        if (state.run?.id === id && busy()) setTimeout(() => reloadCurrent(), 2000)
    }
}

async function reloadCurrent() {
    if (!state.run) return;
    try {
        state.run = await api('/runs/' + state.run.id);
        if (!state.dirty) render();
        openStream()
    } catch {
        toast('连接暂时中断，已保存的内容不会丢失。')
    }
}

async function showRun(id) {
    if (!allowLeave()) return;
    const seq = ++loadSequence;
    const run = await api('/runs/' + id);
    if (seq !== loadSequence) return;
    document.querySelector('.sidebar').classList.remove('open');
    state.run = run;
    state.selected = new Set();
    state.draftId = null;
    state.filter = '';
    state.quality = 'all';
    state.view = run.status === 'researching' ? 'research' : run.drafts.length ? 'compose' : Object.keys(run.contacts).length ? 'contacts' : run.leads.length ? 'review' : 'research';
    render();
    openStream()
}

function allowLeave() {
    if (state.dirty) {
        toast('请先保存当前邮件的修改。');
        return false
    }
    return true
}

function go(view) {
    if (!allowLeave()) return;
    state.view = view;
    document.querySelector('.sidebar').classList.remove('open');
    render();
    window.scrollTo({top: 0, behavior: 'smooth'})
}

function modal(title, body, foot = '') {
    const dialog = $('#modal');
    $('#modal-content').innerHTML = `<div class="modal-head"><h2>${title}</h2><button class="icon-button" data-close aria-label="关闭弹窗">${icon('close')}</button></div><div class="modal-body">${body}</div>${foot ? `<div class="modal-foot">${foot}</div>` : ''}`;
    dialog.showModal()
}

function details(id) {
    const l = state.run.leads.find(l => l.id === id);
    modal(esc(l.name), `<div class="contact-person"><span class="avatar">${esc(initials(l.name))}</span><div><h3>${esc(l.title)}</h3><p>${esc(l.company)}</p></div></div><div class="detail-grid"><div><small>工作地点</small><b>${esc(l.location)}</b></div><div><small>证据可靠度</small><b>${Math.round(l.confidence * 100)}%</b></div><div><small>任职状态</small><b>${({
        current: '资料显示现任',
        former: '前任员工',
        unclear: '尚待确认'
    })[l.employment] || '尚待确认'}</b></div></div><p>${esc(l.summary)}</p>${l.missing.length ? `<div class="notice">尚待了解：${l.missing.map(esc).join('；')}</div>` : ''}${l.conflicts.length ? `<div class="notice">存在冲突：${l.conflicts.map(esc).join('；')}</div>` : ''}<h4>支持这些信息的来源</h4>${l.evidence.map(e => `<div class="source-card"><b>${esc(e.title)}</b><p>${esc(e.snippet)}</p><a href="${safeURL(e.url)}" target="_blank" rel="noopener noreferrer">${icon('link')}打开原始来源</a></div>`).join('')}`)
}

function settings() {
    modal('连接与发送设置', `<p>演示模式可直接体验完整流程。真实模式使用你在后台配置的搜索、模型和 SMTP 服务。</p><div class="settings-row">研究服务<span class="tag ${state.session.research_ready ? '' : 'warn'}">${state.session.research_ready ? '已填写配置' : '尚未配置'}</span></div><div class="settings-row">通用 SMTP<span class="tag ${state.session.smtp_ready ? '' : 'warn'}">${state.session.smtp_ready ? '配置已填写' : '尚未配置'}</span></div><div class="settings-row">发件地址<span>${esc(state.session.sender || '未设置')}</span></div><p>在 backend/config/.env 中填写以下配置，然后重启服务。界面只展示连接状态，不保存或显示密码。</p><pre class="settings-code">DEEPSEEK_API_KEY=…\nTAVILY_API_KEY=…\nSMTP_HOST=smtp.example.com\nSMTP_PORT=465\nSMTP_SECURITY=ssl\nSMTP_USERNAME=你的邮箱\nSMTP_PASSWORD=邮箱授权码\nSMTP_FROM=你的邮箱</pre><p>支持 SSL 和 STARTTLS。这里的状态仅检查配置是否填写，真实连接会在执行操作时验证。</p>`, `<button class="button green" data-close>知道了</button>`)
}

function confirmSend() {
    if (state.dirty) {
        toast('请先保存邮件修改，再核对发送。');
        return
    }
    const drafts = state.run.drafts.filter(d => d.status === 'draft');
    const demo = state.run.mode === 'demo';
    state.confirmation = {drafts: drafts.map(d => ({id: d.id, revision: d.revision})), confirmed: true};
    modal(demo ? '确认这次演示发送' : '最后确认：发送这些邮件', `<p>${demo ? '以下操作只会记录演示结果，不会向真实邮箱发信。' : '请再次核对每封邮件的收件人、主题与正文。确认后将逐封通过已配置的 SMTP 提交。'}</p>${drafts.map(d => `<div class="confirm-mail"><h3>${esc(d.subject)}</h3><p>从 ${esc(d.sender || '未配置')} → ${esc(d.recipient)}</p><pre>${esc(d.body)}</pre></div>`).join('')}<label class="check-label"><input type="checkbox" id="confirm-check">我已核对上述 ${drafts.length} 封邮件及收件地址，确认${demo ? '演示' : '真实'}发送。</label>`, `<button class="button" data-close>返回修改</button><button id="send-final" class="button green" disabled>${icon('send')}${demo ? '确认演示发送' : '确认发送 ' + drafts.length + ' 封'}</button>`)
}

document.addEventListener('click', async e => {
    const target = e.target.closest('button,a[data-action]');
    if (!target) return;
    try {
        if (target.hasAttribute('data-close')) {
            $('#modal').close();
            return
        }
        if (target.dataset.nav) {
            go(target.dataset.nav);
            return
        }
        if (target.dataset.history) {
            await showRun(target.dataset.history);
            return
        }
        if (target.dataset.example) {
            state.query = target.dataset.example;
            $('#query').value = state.query;
            $('#query').focus();
            return
        }
        if (target.dataset.detail) {
            details(target.dataset.detail);
            return
        }
        if (target.dataset.draft) {
            if (!allowLeave()) return;
            state.draftId = target.dataset.draft;
            render();
            return
        }
        if (target.dataset.candidate) {
            document.querySelector(`[data-contact-form="${target.dataset.for}"] input`).value = target.dataset.candidate;
            return
        }
        if (target.dataset.contactSource) {
            const c = state.run.contacts[target.dataset.contactSource];
            modal('邮箱来源 · 请核对归属', c.candidates.map(x => `<div class="source-card"><b>${esc(x.email)}</b><p>${esc(x.excerpt)}</p><a href="${safeURL(x.source_url)}" target="_blank" rel="noopener noreferrer">${icon('link')}${esc(x.source_title)}</a></div>`).join('') + '<p>同一页面同时出现姓名和邮箱，并不保证邮箱属于这个人。请核对原文后确认；公司通用邮箱也不等同于个人邮箱。</p>');
            return
        }
        if (target.id === 'logout-button') {
            if (!allowLeave()) return;
            await api('/auth/logout', 'POST', {});
            void boot();
            return;
        }
        if (target.id === 'usage-button' || target.dataset.action === 'refresh-usage') {
            target.disabled = true;
            await refreshUsage();
            target.disabled = false;
            if (target.id === 'usage-button') modal('账户余量', usagePanel());
            else if ($('#modal').open) $('#modal .quota-panel').outerHTML = usagePanel();
            return;
        }
        if (target.dataset.action === 'skip-send') {
            if (!allowLeave()) return;
            modal('结束本次流程', '<p>剩余邮件将保留为不发送记录，结束后无法继续发送。已经提交的邮件不受影响。</p>', '<button class="button" data-close>返回邮件</button><button class="button green" id="skip-final">确认不发送并结束</button>');
            return;
        }
        if (target.id === 'skip-final') {
            target.disabled = true;
            state.run = await api('/runs/' + state.run.id + '/skip-send', 'POST', {confirmed: true});
            $('#modal').close();
            render();
            await refreshHistory();
            toast('本次流程已结束，剩余邮件未发送。');
            return;
        }
        if (target.id === 'settings-button') {
            state.session = await api('/session');
            settings();
            return
        }
        if (target.id === 'refresh-history') {
            await refreshHistory();
            toast('任务列表已更新');
            return
        }
        if (target.id === 'mobile-menu') {
            document.querySelector('.sidebar').classList.toggle('open');
            return
        }
        if (target.id === 'mode-button') {
            if (!allowLeave()) return;
            modal('选择运行方式', `<p>演示模式使用虚构资料，适合体验完整流程。真实模式会调用已配置的搜索与模型服务。</p>`, `<button class="button ${state.mode === 'demo' ? 'green' : ''}" data-mode="demo">演示模式</button><button class="button ${state.mode === 'live' ? 'green' : ''}" data-mode="live">真实服务</button>`);
            return
        }
        if (target.dataset.mode) {
            state.mode = target.dataset.mode;
            $('#modal').close();
            render();
            toast('已切换，新建任务将使用' + (state.mode === 'demo' ? '演示模式' : '真实服务'));
            return
        }
        if (target.id === 'new-top' || target.dataset.action === 'home') {
            go('home');
            return
        }
        if (target.id === 'send-final') {
            target.disabled = true;
            const payload = state.confirmation;
            state.run = await api('/runs/' + state.run.id + '/send', 'POST', payload);
            $('#modal').close();
            render();
            openStream();
            return
        }
        const action = target.dataset.action;
        if (['review', 'contacts', 'compose'].includes(action)) {
            go(action);
            return
        }
        if (action === 'lookup') {
            target.disabled = true;
            state.run = await api('/runs/' + state.run.id + '/contacts', 'POST', {lead_ids: [...state.selected]});
            state.view = 'contacts';
            render();
            openStream();
            return
        }
        if (action === 'continue') {
            state.run = await api('/runs/' + state.run.id + '/continue', 'POST', {});
            render();
            openStream();
            return
        }
        if (action === 'cancel') {
            await api('/runs/' + state.run.id + '/cancel', 'POST', {});
            toast('正在停止研究');
            return
        }
        if (action === 'confirm-send') {
            confirmSend();
            return
        }
        if (action === 'copy') {
            const d = state.run.drafts.find(d => d.id === state.draftId);
            await navigator.clipboard.writeText(($('#draft-subject')?.value || d.subject) + '\n\n' + ($('#draft-body')?.value || d.body));
            toast('邮件已复制');
            return
        }
        if (action === 'export') {
            const blob = new Blob([JSON.stringify(state.run.leads, null, 2)], {type: 'application/json'});
            const url = URL.createObjectURL(blob), a = document.createElement('a');
            a.href = url;
            a.download = 'LeadGraph-contacts.json';
            a.click();
            setTimeout(() => URL.revokeObjectURL(url), 1000);
            toast('联系人资料已导出')
        }
    } catch (error) {
        target.disabled = false;
        toast(error.message)
    }
});
document.addEventListener('submit', async e => {
    e.preventDefault();
    const form = e.target, button = form.querySelector('button[type=submit],button:not([type])');
    if (button) button.disabled = true;
    try {
        if (form.id === 'research-form') {
            state.query = $('#query').value.trim();
            state.run = await api('/runs', 'POST', {query: state.query, mode: state.mode});
            state.selected = new Set();
            state.view = 'research';
            state.dirty = false;
            render();
            openStream();
            await refreshHistory();
            return
        }
        if (form.dataset.contactForm) {
            state.run = await api(`/runs/${state.run.id}/contacts/${form.dataset.contactForm}`, 'PATCH', {
                email: form.querySelector('input').value.trim(),
                confirmed: true
            });
            render();
            toast('邮箱已确认');
            return
        }
        if (form.id === 'brief-form') {
            const lead_ids = [...document.querySelectorAll('[data-compose-lead]:checked')].map(e => e.dataset.composeLead);
            state.run = await api(`/runs/${state.run.id}/drafts`, 'POST', {
                lead_ids,
                keywords: $('#keywords').value,
                language: $('#mail-language').value,
                tone: $('#mail-tone').value,
                signature: $('#signature').value
            });
            render();
            openStream();
            return
        }
        if (form.id === 'draft-form') {
            const draft = state.run.drafts.find(d => d.id === state.draftId);
            state.run = await api(`/runs/${state.run.id}/drafts/${draft.id}`, 'PATCH', {
                revision: draft.revision,
                subject: $('#draft-subject').value,
                body: $('#draft-body').value
            });
            state.dirty = false;
            render();
            toast('邮件修改已保存');
            return
        }
    } catch (error) {
        toast(error.message);
        if (button) button.disabled = false
    }
});
document.addEventListener('input', e => {
    if (e.target.id === 'query') state.query = e.target.value;
    if (e.target.id === 'lead-search') {
        state.filter = e.target.value;
        $('#lead-grid').innerHTML = leadCards()
    }
    if (['draft-subject', 'draft-body'].includes(e.target.id)) {
        state.dirty = true;
        $('#save-state').textContent = '有未保存的修改'
    }
});
document.addEventListener('change', e => {
    const el = e.target;
    if (el.id === 'confirm-check') $('#send-final').disabled = !el.checked;
    if (el.id === 'quality-filter') {
        state.quality = el.value;
        $('#lead-grid').innerHTML = leadCards()
    }
    if (el.dataset.lead) {
        el.checked ? state.selected.add(el.dataset.lead) : state.selected.delete(el.dataset.lead);
        el.closest('.lead-card').classList.toggle('selected', el.checked)
    }
    if (el.id === 'select-all') {
        filteredLeads().forEach(l => el.checked ? state.selected.add(l.id) : state.selected.delete(l.id));
        $('#lead-grid').innerHTML = leadCards()
    }
    if (el.dataset.lead || el.id === 'select-all') {
        $('#selected-count').textContent = state.selected.size;
        $('#lookup-button').disabled = !state.selected.size || busy() || state.run.drafts.length
    }
});
window.addEventListener('beforeunload', e => {
    if (state.dirty) {
        e.preventDefault();
        e.returnValue = ''
    }
});
document.querySelector('.brand').addEventListener('click', e => {
    e.preventDefault();
    go('home')
});
let bootPromise;
function boot() {
    if (bootPromise) return bootPromise;
    state.stream?.close();
    ++loadSequence;
    Object.assign(state, {session: null, usage: null, run: null, history: [], selected: new Set(),
        draftId: null, dirty: false, query: '', filter: '', quality: 'all', view: 'home', confirmation: null});
    $('#main').replaceChildren();
    $('#history').replaceChildren();
    if ($('#modal').open) $('#modal').close();
    $('#modal-content').replaceChildren();
    bootPromise = (async () => {
        state.session = await authenticate();
        $('#account-name').textContent = state.session.user.username;
        await refreshHistory();
        render();
        $('#auth-root').hidden = true;
        $('#auth-root').replaceChildren();
        document.querySelector('.app-shell').hidden = false;
        void refreshUsage();
    })().catch(error => toast(error.message)).finally(() => { bootPromise = null; });
    return bootPromise;
}

async function refreshUsage() {
    const session = state.session;
    try {
        const usage = await api('/usage');
        if (state.session !== session) return;
        state.usage = usage;
        // 只更新额度区，避免覆盖用户正在输入的研究要求。
        const panel = $('#main .quota-panel');
        if (panel) panel.outerHTML = usagePanel();
    } catch (error) { toast(error.message); }
}

function usagePanel() {
    const u = state.usage;
    const amount = value => value == null ? '未提供' : esc(value);
    const card = (label, data, body) => `<article class="quota-card"><div><span>${label}</span><span class="tag ${data?.status === 'ok' ? '' : 'gray'}">${data?.status === 'ok' ? '已更新' : data ? '暂不可用' : '查询中'}</span></div>${data?.status === 'ok' ? body() : `<p class="quota-unavailable">${esc(data?.message || '正在读取服务商额度…')}</p>`}<small>${data?.checked_at ? '查询时间 ' + esc(new Date(data.checked_at).toLocaleTimeString('zh-CN')) : '请稍候'}</small></article>`;
    return `<section class="quota-panel"><div class="section-top"><div><h3>账户余量</h3><p>当前服务配置的共享额度 · 不等于个人用量</p></div><button class="button small ghost" data-action="refresh-usage">${icon('refresh')}刷新</button></div><div class="quota-grid">${card('DeepSeek · 模型余额', u?.deepseek, () => u.deepseek.balances.map(b => `<p class="quota-value">${amount(b.total)} <span>${esc(b.currency)}</span></p>`).join('') + (u.deepseek.is_available === false ? '<p>服务商提示当前账户不可用</p>' : ''))}${card('Tavily · 搜索额度', u?.tavily, () => `<p class="quota-value">${amount(u.tavily.plan.remaining)} <span>套餐剩余 credits</span></p><dl class="quota-details"><div><dt>当前 Key 剩余</dt><dd>${amount(u.tavily.key.remaining)}</dd></div><div><dt>套餐已用 / 上限</dt><dd>${amount(u.tavily.plan.used)} / ${amount(u.tavily.plan.limit)}</dd></div><div><dt>按量付费已用 / 上限</dt><dd>${amount(u.tavily.paygo.used)} / ${amount(u.tavily.paygo.limit)}</dd></div></dl>`)}</div><p class="quota-footnote">额度约缓存 90 秒；credits 是计费额度，不能直接换算为搜索次数。未提供上限时不推算剩余额度。</p></section>`;
}
void boot();
