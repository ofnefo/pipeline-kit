// «Каналы»: network connections, approval queue, per-network preview. Approval is the owner's «да» on one
// exact post revision; nothing leaves the panel until posting is switched on at Local node and «Отправить» is pressed.
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const request = async (url, method, body) => {
  const r = await fetch(url, method ? {method, headers:{'Content-Type':'application/json'}, body: body === undefined ? undefined : JSON.stringify(body)} : {cache:'no-store'});
  const d = await r.json().catch(() => ({}));
  // FastAPI validation errors arrive as a list; show the first reason without the pydantic prefix
  const first = Array.isArray(d.detail) && String(d.detail[0]?.msg || '').replace(/^Value error, /, '');
  if (!r.ok) throw Error(typeof d.detail === 'string' ? d.detail : first || 'Проверьте заполнение полей.');
  return d;
};
if (!document.querySelector('link[data-social-css]')) {
  const link = Object.assign(document.createElement('link'), {rel:'stylesheet', href:'/static/social.css?v=w3s-20261019'});
  link.dataset.socialCss = ''; document.head.append(link);
}
const API = '/api/smm/social';
const QUEUE = {draft:['черновик',''], scheduled:['одобрен, ждёт отправки','ok'], publishing:['отправляется','warn'],
  remote_scheduled:['в отложке сети','ok'], published:['опубликован','ok'], failed:['ошибка','bad'],
  unknown:['неизвестно — проверьте в сети','bad'], manual:['выложить вручную','warn'], cancelled:['отменён','']};
const CONN = {connected:['подключено','ok'], needs_relogin:['нужен повторный вход','warn'], disconnected:['не подключено',''], mint:['через Assistant','warn']};
const when = v => v ? new Date(v).toLocaleString('ru-RU',{timeZone:'Europe/Moscow',day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'}) : 'без времени';
// Past plan dates are not offered as defaults: approving one would make the post due at once
const toLocal = v => v && Date.parse(v) > Date.now() ? new Date(Date.parse(v)+3*3600000).toISOString().slice(0,16) : '';
const pill = ([t, c]) => `<span class="pill ${c}">${esc(t)}</span>`;
let st = null, smm = null, brand = '', msg = '', host = null, wired = false;

export async function mountChannels(el, smmData, brandFilter) {
  el.innerHTML = '<div class="card"><h3>External publishing is not configured</h3><p>Prepare and export your content plan here. Connect publishing separately after reviewing the destination and permissions.</p></div>';
}

function paint() {
  if (!host?.isConnected) return;
  const brands = smm.brands.filter(b => !brand || b.id === brand);
  const name = id => smm.brands.find(b => b.id === id)?.name || id;
  const flag = st.posting_enabled
    ? `<span class="pill ok">Публикация включена</span>` : `<span class="pill warn">Публикация выключена</span>`;
  const toggle = st.local_panel
    ? `<button class="ghost small" data-social-posting="${st.posting_enabled ? '0' : '1'}">${st.posting_enabled ? 'Выключить' : 'Включить'}</button>`
    : `<span class="note">Включается только на локальном узле</span>`;
  const providers = Object.entries(st.providers).map(([id, p]) => {
    const app = st.apps[id];
    const rows = st.connections.filter(c => c.provider === id && brands.some(b => b.id === c.brand)).map(c => {
      const action = !p.oauth ? '' : c.status === 'connected'
        ? `<button class="ghost small" data-social-disconnect="${esc(c.brand)}/${id}">Отключить</button>`
        : `<button class="small" data-social-login="${esc(c.brand)}/${id}" ${app?.configured ? '' : 'disabled title="Сначала ключи приложения"'}>${c.status === 'needs_relogin' ? 'Войти снова' : 'Войти'}</button>`;
      return `<li><span class="social-brand">${esc(name(c.brand))}${c.account ? ` <small>${esc(c.account)}</small>` : ''}</span>${pill(CONN[c.status] || [c.status,''])}${action}${c.last_error ? `<small class="err social-wide">${esc(c.last_error)}</small>` : ''}</li>`;
    }).join('');
    const keys = !p.oauth ? `<p class="note">${esc(p.detail)}</p>` : `<details${app.configured ? '' : ' open'}><summary>Ключи приложения ${app.configured ? '· введены' : '· нужны'}</summary>
      <form class="social-keys" data-social-keys="${id}" autocomplete="off">
        <label>ID приложения<input name="client_id" required maxlength="300" spellcheck="false"></label>
        ${app.needs_secret ? '<label>Секрет приложения<input name="client_secret" type="password" required maxlength="500"></label>' : ''}
        ${app.needs_group ? '<label>Номер сообщества VK<input name="group_id" inputmode="numeric" required maxlength="40"></label>' : ''}
        <label>Прокси (необязательно)<input name="proxy" maxlength="300" placeholder="http://адрес:порт" spellcheck="false"></label>
        <p class="note">Адрес возврата для настроек приложения:<code class="social-uri">${esc(app.redirect_uri)}</code><a href="${esc(app.console)}" target="_blank" rel="noopener noreferrer">Открыть консоль сети</a></p>
        <div class="social-row"><button>${app.configured ? 'Заменить ключи' : 'Сохранить ключи'}</button>${app.configured ? `<button type="button" class="ghost small" data-social-forget="${id}">Удалить ключи</button>` : ''}</div>
        <p class="note">Ключи шифруются на локальном узле и обратно не показываются.</p>
      </form></details>`;
    return `<article class="card social-net"><h3>${esc(p.title)}${p.oauth && app.proxy ? '<small>через прокси</small>' : ''}</h3><ul class="social-list">${rows}</ul>${keys}</article>`;
  }).join('');
  const manual = Object.values(st.manual).join(', ');
  const queued = new Set(st.queue.filter(q => !['published','remote_scheduled','failed','cancelled'].includes(q.status)).map(q => q.post_id));
  const ready = smm.posts.filter(p => p.status === 'ready' && (!brand || p.brand === brand) && !queued.has(p.id));
  const queue = st.queue.filter(q => !brand || q.brand === brand).map(row).join('') || '<p class="note">Очередь пуста. Добавьте готовый материал.</p>';
  host.innerHTML = `<div class="social-head">${flag}${toggle}<span class="social-sep"></span>
      <button class="ghost" data-social-dispatch="dry">Тестовый прогон</button>
      <button data-social-dispatch="real" ${st.posting_enabled ? '' : 'disabled title="Публикация выключена"'}>Отправить одобренные</button></div>
    <p id="social-msg" class="social-msg" role="status">${esc(msg)}</p>
    <h2 class="social-h">Подключения</h2>
    <div class="grid social-grid">${providers}</div>
    <p class="note">${esc(manual)} — без API: материал выкладывается вручную, в очереди отмечается ссылкой.</p>
    <h2 class="social-h">Очередь</h2>
    <form class="social-add" data-social-add><label class="smm-grow">Готовый материал<select name="post_id" required>${ready.map(p => `<option value="${esc(p.id)}">${esc(name(p.brand))} · ${esc(smm.networks[p.network])} · ${esc(p.title)}</option>`).join('') || '<option value="">Нет материалов в статусе «Готово»</option>'}</select></label><button ${ready.length ? '' : 'disabled'}>В очередь</button></form>
    <div class="social-queue">${queue}</div>`;
}

function row(q) {
  const s = QUEUE[q.status] || [q.status, ''];
  const pv = q.preview;
  const actions = {
    draft: `<button class="small" data-social-approve="${q.id}">Проверить и одобрить</button><button class="ghost small" data-social-cancel="${q.id}">Убрать</button>`,
    scheduled: `<button class="ghost small" data-social-cancel="${q.id}">Отменить</button>`,
    failed: `<button class="ghost small" data-social-requeue="${esc(q.post_id)}">В черновик заново</button>`,
    unknown: `<button class="small" data-social-resolve="${q.id}">Сверить</button>`,
    manual: `<button class="small" data-social-resolve="${q.id}">Выложено вручную</button><button class="ghost small" data-social-cancel="${q.id}">Отменить</button>`,
  }[q.status] || '';
  const network = q.provider === 'manual' ? (smm.networks[q.network] || 'вручную') : (st.providers[q.provider]?.title || q.provider);
  return `<article class="social-item"><div class="social-main"><strong>${esc(q.title)}</strong>
      <span class="smm-meta"><span>${esc(network)} · ${esc(when(q.publish_at))} · ревизия ${q.approved_revision || q.revision}</span>${pill(s)}</span></div>
    <div class="social-row">${q.link ? `<a href="${esc(q.link)}" target="_blank" rel="noopener noreferrer">Открыть пост</a>` : ''}${actions}</div>
    ${q.error || pv?.warnings?.length ? `<details><summary>${q.error ? 'Что пошло не так' : 'Замечания к посту'}</summary>${q.error ? `<p class="err">${esc(q.error)}</p>` : ''}${(pv?.warnings || []).map(w => `<p class="note">${esc(w)}</p>`).join('')}</details>` : ''}</article>`;
}

function approveDialog(q) {
  const post = smm.posts.find(p => p.id === q.post_id);
  const pv = q.preview || {};
  const dlg = document.querySelector('#social-approve') || Object.assign(document.createElement('dialog'), {id:'social-approve'});
  if (!dlg.isConnected) { dlg.setAttribute('aria-label','Одобрение публикации'); document.body.append(dlg); }
  const network = st.providers[q.provider]?.title || smm.networks[q.network] || 'вручную';
  const over = pv.limit && pv.chars > pv.limit;
  dlg.innerHTML = `<form method="dialog" class="social-approve" data-social-confirm="${q.id}" data-revision="${q.revision}">
    <header><h2>Одобрить публикацию</h2><button type="button" class="ghost small" data-social-close>Закрыть</button></header>
    <p><b>${esc(q.title)}</b><br><span class="note">${esc(network)} · ревизия ${q.revision}</span></p>
    ${pv.title ? `<p class="note">Заголовок: ${esc(pv.title)}</p>` : ''}
    <div class="smm-preview">${esc(pv.text || '(без текста)')}</div>
    <p class="note ${over ? 'err' : ''}">${pv.chars || 0}${pv.limit ? ` из ${pv.limit}` : ''} символов${pv.asset ? ` · материал: ${esc(pv.asset)}` : ''}</p>
    ${(pv.warnings || []).map(w => `<p class="err">${esc(w)}</p>`).join('')}
    <label>Когда (Москва)<input name="publish_at" type="datetime-local" required value="${toLocal(q.publish_at)}"></label>
    <p class="note">Одобрение — ваше «да» именно на эту версию. Любая правка поста снимет его. В сеть пост уйдёт только по кнопке «Отправить одобренные» при включённой публикации; VK и YouTube при времени позже чем через 5 минут получат его заранее, в свою отложку; Instagram — когда время подойдёт.</p>
    <p class="err" role="alert"></p>
    <footer><button type="button" class="ghost" data-social-close>Отмена</button><button value="ok">Да, одобряю ревизию ${q.revision}</button></footer></form>`;
  dlg.showModal();
}

function resolveDialog(q) {
  const dlg = document.querySelector('#social-approve') || Object.assign(document.createElement('dialog'), {id:'social-approve'});
  if (!dlg.isConnected) document.body.append(dlg);
  const unknown = q.status === 'unknown';
  dlg.innerHTML = `<form method="dialog" class="social-approve" data-social-resolved="${q.id}">
    <header><h2>${unknown ? 'Сверка с сетью' : 'Выложено вручную'}</h2><button type="button" class="ghost small" data-social-close>Закрыть</button></header>
    <p><b>${esc(q.title)}</b></p>
    ${unknown ? '<p class="note">Сеть не ответила на отправку. Откройте страницу в самой сети: если пост там есть — вставьте ссылку и нажмите «Вышел». Если нет — «Не вышел», затем поставьте материал в очередь заново.</p>' : ''}
    <label>Ссылка на пост<input name="link" type="url" placeholder="https://"></label>
    <p class="err" role="alert"></p>
    <footer>${unknown ? '<button type="button" class="ghost" data-social-outcome="failed">Не вышел</button>' : '<button type="button" class="ghost" data-social-close>Отмена</button>'}<button type="button" data-social-outcome="published">Вышел</button></footer></form>`;
  dlg.showModal();
}

// fn may return the status line itself (dispatch summaries); otherwise the fixed note is shown
async function act(fn, note) {
  try { const r = fn ? await fn() : ''; msg = typeof r === 'string' && r ? r : note || ''; } catch (e) { msg = e.message; }
  try { st = await request(API); } catch {}
  paint();
}

function wire() {
  document.addEventListener('click', async e => {
    const t = e.target.closest('button'); if (!t) return;
    const d = t.dataset;
    if ('socialClose' in d) return t.closest('dialog').close();
    if (d.socialLogin) {
      const [b, p] = d.socialLogin.split('/'); t.disabled = true;
      try { location.href = (await request(`${API}/oauth/${p}/start`, 'POST', {brand: b})).url; }
      catch (err) { msg = err.message; paint(); }
      return;
    }
    if (d.socialDisconnect) {
      const [b, p] = d.socialDisconnect.split('/');
      if (confirm('Отключить аккаунт? Токен будет удалён с Пушкины.')) act(() => request(`${API}/connections/${b}/${p}`, 'DELETE'), 'Отключено.');
      return;
    }
    if (d.socialForget) { if (confirm('Удалить ключи приложения?')) act(() => request(`${API}/apps/${d.socialForget}`, 'DELETE'), 'Ключи удалены.'); return; }
    if (d.socialPosting) {
      const on = d.socialPosting === '1';
      if (!on || confirm('Включить публикацию? Отправляться будут только одобренные вами ревизии и только по кнопке «Отправить одобренные».'))
        act(() => request(`${API}/posting`, 'POST', {enabled: on}), on ? 'Публикация включена.' : 'Публикация выключена.');
      return;
    }
    if (d.socialDispatch === 'dry') {
      return act(async () => {
        const r = await request(`${API}/dispatch`, 'POST', {dry_run: true});
        return r.plans.length ? `Тестовый прогон: ушло бы ${r.plans.length} — ${r.plans.map(p => `${st.providers[p.provider]?.title} (${p.action === 'schedule' ? 'в отложку' : 'сейчас'})`).join(', ')}.` : 'Тестовый прогон: сейчас отправлять нечего.';
      });
    }
    if (d.socialDispatch === 'real') {
      if (!confirm('Отправить все одобренные посты, время которых подошло (и в отложку сетей — более поздние)?')) return;
      return act(async () => {
        const r = await request(`${API}/dispatch`, 'POST', {dry_run: false});
        const count = s => r.results.filter(x => x.status === s).length;
        return (r.results.length ? `Отправлено: ${count('published') + count('remote_scheduled')}, ошибок: ${count('failed')}, неизвестно: ${count('unknown')}.` : 'Отправлять нечего.');
      });
    }
    if (d.socialCancel) return act(() => request(`${API}/queue/${d.socialCancel}/cancel`, 'POST'), 'Убрано из очереди.');
    if (d.socialRequeue) return act(() => request(`${API}/queue`, 'POST', {post_id: d.socialRequeue}), 'Снова в черновиках очереди.');
    const q = id => st.queue.find(x => x.id === id);
    if (d.socialApprove) return approveDialog(q(d.socialApprove));
    if (d.socialResolve) return resolveDialog(q(d.socialResolve));
    if (d.socialOutcome) {
      const form = t.closest('form'), link = form.link.value.trim();
      try { await request(`${API}/queue/${form.dataset.socialResolved}/resolve`, 'POST', {status: d.socialOutcome, link}); form.closest('dialog').close(); act(null, d.socialOutcome === 'published' ? 'Отмечено как вышедшее.' : 'Отмечено: не вышел.'); }
      catch (err) { form.querySelector('[role=alert]').textContent = err.message; }
    }
  });
  document.addEventListener('submit', async e => {
    const f = e.target;
    if (f.dataset.socialKeys) {
      e.preventDefault();
      const body = Object.fromEntries(new FormData(f));
      return act(() => request(`${API}/apps/${f.dataset.socialKeys}`, 'PUT', body), 'Ключи сохранены. Теперь нажмите «Войти» у нужного бренда.');
    }
    if ('socialAdd' in f.dataset) { e.preventDefault(); return act(() => request(`${API}/queue`, 'POST', {post_id: f.post_id.value}), 'Добавлено в очередь черновиком.'); }
    if (f.dataset.socialConfirm) {
      e.preventDefault();
      const at = f.publish_at.value;
      try {
        await request(`${API}/queue/${f.dataset.socialConfirm}/approve`, 'POST', {revision: Number(f.dataset.revision), publish_at: `${at}:00+03:00`});
        f.closest('dialog').close(); act(null, 'Одобрено.');
      } catch (err) { f.querySelector('[role=alert]').textContent = err.message; }
    }
  });
}
