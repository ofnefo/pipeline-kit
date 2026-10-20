import { loadGallery, renderGallery, mountGallery } from './gallery.js?v=gallery-curated-20261020b';
import { loadMintWorkspace, renderMintWorkspace, mountMintWorkspace } from './assistant-workspace.js?v=c3-20261019';
import { loadInventory, renderInventory, mountInventory, renderInventorySummary } from './inventory.js?v=c3-20261019u';
// Pipeline Control Web: tiny SPA, no build step. Every view = fetch JSON -> render HTML.
import { loadBoard, renderBoard, initBoard, setBoardStatus } from './board.js?v=c3-20261019u';
import { loadSmm, renderSmm, initSmm } from './smm.js?v=w3s-20261019';
import { loadProjects, renderProjects, initProjects } from './projects.js?v=c3-20261019s';
import { renderQuickEdits, renderTools, initQuick } from './quick-tools.js?v=c3-20261019t';
import { renderGpu, renderDownloads, renderAgents, initOps } from './ops.js?v=c3-20261019s';
import { loadModels, renderModels, initModels, setModelsGroup } from './models.js?v=c3-20261019p';
import { loadHome, renderHome, mountHome, renderSettings, mountSettings, loadChips, getTheme, setTheme, uptime } from './home.js?v=c3-20261019u';
import { loadKeys, renderKeys, mountKeys } from './keys.js?v=c3-20261019g';
import { initProjectBrowser } from './project-files.js?v=ux35-20261011';
import { applyDisclosure, initDisclosure } from './disclosure.js?v=ux35-20261011';
const $ = (s) => document.querySelector(s);
const esc = (v) => String(v ?? '—').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const api = async (path, opts) => {
  const r = await fetch(path, opts);
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || r.statusText);
  return data;
};
const post = (path, body) => api(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body || {}) });
const ago = (ts) => { if (!ts) return '—'; const m = Math.round((Date.now() / 1000 - ts) / 60); return m < 60 ? `${m} мин назад` : m < 2880 ? `${Math.round(m / 60)} ч назад` : `${Math.round(m / 1440)} дн назад`; };
const dot = (state) => `<i class="dot ${state}"></i>`;
const pill = (text, state = '') => `<span class="pill ${state}">${esc(text)}</span>`;
const bar = (pct) => `<div class="bar"><i class="${pct > 90 ? 'bad' : pct > 80 ? 'warn' : ''}" style="width:${Math.min(100, pct || 0)}%"></i></div>`;
const row = (k, v) => `<div class="row"><span>${esc(k)}</span><span>${v}</span></div>`;

import { configurePortableViews } from './portable.js';
const views = {
  gallery: { title: 'Результаты', sub: 'Архив генераций, тестов и прогонов · просмотр, сравнение и выбор', load: loadGallery, render: renderGallery, mount: mountGallery },
  home: { title: 'Главная', sub: 'Что требует внимания, быстрый запуск и последние результаты', load: loadHome, render: renderHome, mount: mountHome },
  settings: { title: 'Настройки', sub: 'Оформление и ключи доступа', load: loadKeys, render: (d) => renderSettings(renderKeys(d)),
    mount: (view) => { const a = mountSettings(view), b = mountKeys(view); return () => { a?.(); b?.(); }; } },
  inventory: { title: 'Инвентарь', sub: 'Что сделано, что проверено и что ждёт вашего решения', load: loadInventory, render: renderInventory, mount: mountInventory },
  mint: { title: 'Assistant', sub: 'Поручения помощника', load: loadMintWorkspace, render: renderMintWorkspace, mount: mountMintWorkspace },
  // Studio renders itself with Preact; the module and its vendor file load only when the tab opens.
  studio: { title: 'Студия', sub: 'Проект целиком: чаты с моделями, результаты и файлы; неразобранное — во Входящих', load: async () => null,
    render: () => '<div id="studio-root"></div>', mount: async (view) => { const root = view.querySelector('#studio-root'); const mod = await import('./studio.js?v=c3-20261019o'); return root?.isConnected ? mod.mountStudio(root) : undefined; } },
  montage: { title: 'Монтаж', sub: 'Склейка роликов проекта: дорожки, клипы, субтитры и рендер', load: async () => null,
    render: () => '<div id="studio-root"></div>', mount: async (view) => { const root = view.querySelector('#studio-root'); const mod = await import('./studio.js?v=c3-20261019o'); return root?.isConnected ? mod.mountStudio(root, { mode: 'montage' }) : undefined; } },
  smm: { title: 'SMM и продвижение', sub: 'Бренды, контент-план и подготовка публикаций', load: loadSmm, render: renderSmm },
  quick: { title: 'Конвертеры', sub: 'Перевести файл в другой формат, сжать, обрезать или открыть в онлайн-редакторе', load: async () => ({ convert: await api('/api/convert/catalog'), runs: (await api('/api/convert/runs?limit=12')).runs || [], tools: await api('/api/tools') }), render: renderQuickEdits },
  tools: { title: 'Навыки', sub: 'Навыки агентов по направлениям: с какого начинать и какие вспомогательные', load: () => api('/api/tools'), render: renderTools },
  models: { title: 'Модели', sub: 'Создавайте видео, изображения и звук. Выберите задачу — панель покажет подходящие модели.', load: loadModels, render: renderModels },
  projects: { title: 'Проекты', sub: 'Проекты по пайплайнам, файлы и результаты', load: loadProjects,
    render: (d) => '<div class="view-actions"><button type="button" class="ghost" data-file-browser-open title="Все папки проектов: предпросмотр, отчёты, история">Файлы</button></div>' + renderProjects(d) },
  board: { title: 'Задачи', sub: 'План, исполнители и результаты в одном месте', load: loadBoard, render: renderBoard },
  health: { title: 'Здоровье', sub: 'Ноутбук, локального узла и облако одним экраном', load: async () => { const [h, inventory] = await Promise.all([api('/api/health'), loadInventory().catch(() => null)]); return { ...h, inventory }; }, render: renderHealth },
  server: { title: 'Сервер', sub: 'Сайты, домены, хранилище и бэкапы', load: () => api(serverTabs[serverTab].api), render: (d) => serverBar() + serverTabs[serverTab].render(d) },
  gpu: { title: 'GPU', sub: 'Optional GPU на локальном узле: кто занимает видеокарту', load: () => api('/api/gpu'), render: renderGpu },
  downloads: { title: 'Загрузки', sub: 'Модели и ассеты: докачка, проверка файлов и учёт нагрузки сети', load: () => api('/api/downloads'), render: renderDownloads },
  agents: { title: 'Агенты', sub: 'Сессии Claude, Codex и Happy', load: () => api('/api/agents'), render: renderAgents },
};

configurePortableViews(views);
// «Сервер» joins the former Сайты/Домены/Хранилище/Бэкапы tabs; each sub-tab loads only its own data.
const serverTabs = {
  sites: { label: 'Сайты', sub: 'Доступность, SSL и сервисы на облаке Remote', api: '/api/sites', render: renderSites },
  domains: { label: 'Домены', sub: 'Remote: сроки продления и DNS-записи', api: '/api/domains', render: renderDomains },
  storage: { label: 'Хранилище', sub: 'Что где лежит и сколько занимает', api: '/api/storage', render: renderStorage },
  backups: { label: 'Бэкапы', sub: 'HDD локального узла и приватный GitHub', api: '/api/backups', render: renderBackups },
};
let serverTab = 'sites';
const serverBar = () => `<div class="subtabs" role="navigation" aria-label="Разделы сервера">${Object.entries(serverTabs).map(([k, t]) =>
  `<a href="#server/${k}"${k === serverTab ? ' class="active" aria-current="page"' : ''}>${t.label}</a>`).join('')}</div>`;

let current = 'home';
// Old bookmarks keep working: #sites → #server/sites, #files → Проекты with the file browser open.
function route(hash) {
  let [tab, sub] = String(hash || '').split('/');
  if (serverTabs[tab]) [tab, sub] = ['server', tab];
  if (tab === 'server' && serverTabs[sub]) serverTab = sub;
  if (tab === 'board' && sub) setBoardStatus(sub);
  if (tab === 'models' && sub) setModelsGroup(sub, decodeURIComponent(String(hash).split('/')[2] || ''));
  // #files/<path> (UX-41: back from the montage page) opens the file browser in that folder.
  if (tab === 'files') return show('projects', { openFiles: String(hash).split('/').slice(1).map((x) => { try { return decodeURIComponent(x); } catch { return x; } }).join('/') || true });
  return show(tab);
}
let dispose = null;
let renderVersion = 0;
async function show(tab, { openFiles = false, background = false } = {}) {
  const version = ++renderVersion;
  const selected = views[tab] ? tab : 'home';
  const definition = views[selected];
  const selectedServer = serverTab;
  const key = selected === 'server' ? 'server/' + selectedServer : selected;
  const view = $('#view');
  const changed = view.dataset.tab !== key;
  const modelScroll = !changed && selected === 'models' ? {group: view.querySelector('[data-m-group][aria-pressed="true"]')?.dataset.mGroup, top: view.querySelector('.model-list')?.scrollTop || 0} : null;
  if (changed && typeof dispose === 'function') { dispose(); dispose = null; }
  current = selected;
  document.body.dataset.workspace = selected;
  document.querySelectorAll('nav a[data-tab]').forEach(a => {
    const active = a.dataset.tab === selected;
    a.classList.toggle('active', active);
    if (active) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current');
  });
  $('#title').textContent = definition.title;
  document.title = selected === 'home' ? 'Control Pipeline' : definition.title + ' · Control Pipeline';
  $('#subtitle').textContent = selected === 'server' ? serverTabs[selectedServer].sub : definition.sub;
  const head = selected === 'server' ? serverBar() : '';
  if (changed) view.innerHTML = head + '<div class="workspace-loading" role="status">Загружаем раздел…</div>';
  view.dataset.tab = key;
  view.setAttribute('aria-busy', 'true');
  $('#refresh').disabled = true;
  $('#updated').textContent = background ? 'Обновление…' : 'Загрузка…';
  try {
    const data = await definition.load();
    if (version !== renderVersion) return;
    if (typeof dispose === 'function') { dispose(); dispose = null; }
    view.innerHTML = definition.render(data);
    if (modelScroll && modelScroll.group === view.querySelector('[data-m-group][aria-pressed="true"]')?.dataset.mGroup) { const list = view.querySelector('.model-list'); if (list) list.scrollTop = modelScroll.top; }
    applyDisclosure(view, selected === 'server' ? selectedServer : selected);
    const cleanup = await definition.mount?.(view);
    if (version !== renderVersion) { cleanup?.(); return; }
    dispose = cleanup;
    const files = openFiles && view.querySelector('.view-actions [data-file-browser-open]');
    if (files) { if (typeof openFiles === 'string') files.dataset.fileBrowserStart = openFiles; files.click(); delete files.dataset.fileBrowserStart; }
    $('#updated').textContent = 'Обновлено ' + new Date().toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
  } catch (e) {
    if (version !== renderVersion) return;
    const message = '<div class="workspace-error" role="alert"><strong>Не удалось обновить раздел</strong><p>' + esc(e.message) + '</p><button type="button" class="ghost" data-view-retry>Попробовать снова</button></div>';
    view.querySelector('.workspace-error')?.remove();
    if (changed || view.querySelector('.workspace-loading')) view.innerHTML = head + message;
    else view.insertAdjacentHTML('afterbegin', message);
    $('#updated').textContent = 'Нет обновления';
  } finally {
    if (version === renderVersion) { view.setAttribute('aria-busy', 'false'); $('#refresh').disabled = false; }
  }
}
document.addEventListener('click', e => { if (e.target.closest('[data-view-retry]')) show(current); });

// UX-35: every Health card starts collapsed when it is fine and open when it shows a problem.
const health = (issue) => ` data-disclosure-default="${issue ? 'open' : 'closed'}"`;
const HOST_NAMES = { laptop: 'Ноутбук', local: 'Локальный узел', vps: 'Облако', azure: 'Облако' };
const hostName = (n) => HOST_NAMES[String(n || '').toLowerCase()] || n || '?';
function hostCard(h, extra = '') {
  if (h?.monitoring === 'paused') return `<div class="card"${health(true)}><h3>${esc(hostName(h.host))} ${pill('мониторинг приостановлен', 'warn')}</h3><p class="note">${esc(h.reason)} Доступность компьютера сейчас не проверяется.</p></div>`;
  if (!h || !h.online) return `<div class="card"${health(true)}><h3><span>${dot('bad')}${esc(hostName(h?.host))}</span>${pill('нет связи', 'bad')}</h3><p class="note">${esc(h?.error)}</p></div>`;
  const disks = Object.entries(h.disks || {}).map(([k, d]) => `${row(`Диск ${k}:`, `${d.free_gb} ГБ свободно`)}${bar(d.used_pct)}`).join('');
  const g = h.gpu;
  const issue = h.pending_reboot || h.reboot_required || h.ram_used_pct >= 90 || h.disk_used_pct >= 90 || Object.values(h.disks || {}).some((d) => d.used_pct >= 90);
  return `<div class="card"${health(issue)}><h3><span>${dot(h.pending_reboot || h.reboot_required ? 'warn' : 'ok')}${esc(hostName(h.host))}</span>
    <small>${uptime(h.uptime_h)}</small></h3>
    ${h.cpu_pct !== undefined ? row('CPU', `${h.cpu_pct}%`) : ''}${h.load ? row('Нагрузка', h.load.map((x) => x.toFixed(2)).join(' / ')) : ''}
    ${row('RAM', `${h.ram_used_pct}% из ${h.ram_total_gb} ГБ`)}
    ${g ? row('GPU', `${esc(g.name)} · ${g.temp_c}°C · ${g.util_pct}% · VRAM ${Math.round(g.vram_used_mb / 1024 * 10) / 10}/${Math.round(g.vram_total_mb / 1024)} ГБ`) : ''}
    ${disks}${h.disk_free_gb !== undefined ? row('Диск /', `${h.disk_free_gb} ГБ свободно`) + bar(h.disk_used_pct) : ''}
    ${h.pending_reboot || h.reboot_required ? row('Windows', pill('ждёт перезагрузки', 'warn')) : ''}
    ${h.heartbeat_age_s !== undefined ? row('Сигнал', `${Math.round(h.heartbeat_age_s / 60)} мин назад`) : ''}${extra}</div>`;
}

function renderHealth(d) {
  const p = d.local, v = d.vps, s = d.sites, b = d.backups;
  const svcDown = (p.services || []).filter((x) => !x.up && x.task).length;
  const svcSleep = (p.services || []).filter((x) => !x.up && !x.task).length;
  const kpis = `<div class="kpis">
    <a class="kpi" href="#server/sites" title="Подробно — Сервер › Сайты"><span>Сайты</span><b>${s.ok}/${s.total}</b>${pill(s.ok === s.total ? 'все работают' : 'есть проблемы', s.ok === s.total ? 'ok' : 'bad')}</a>
    <div class="kpi"><span>Ближайший SSL</span><b>${s.min_ssl_days ?? '—'} дн</b>${pill(v.certbot_timer === 'active' ? 'автопродление включено' : 'автопродление не работает', v.certbot_timer === 'active' ? 'ok' : 'warn')}</div>
    <div class="kpi"><span>Службы локального узла</span><b>${(p.services || []).filter((x) => x.up).length}/${(p.services || []).length - svcSleep}</b>${pill(svcDown ? `${svcDown} не работает` : svcSleep ? `в норме, ${svcSleep} по запросу` : 'в норме', svcDown ? 'warn' : 'ok')}</div>
    <div class="kpi"><span>Бэкап данных на HDD</span><b>${ago(b.restic_last)}</b>${pill(b.restic_ok ? 'без ошибок' : 'требует проверки', b.restic_ok ? 'ok' : 'warn')}</div>
  </div>`;
  const services = `<div class="card"${health(svcDown)}><h3>Службы локального узла</h3>${(p.services || []).map((x) =>
    row(x.name, `${dot(x.up ? 'ok' : x.task ? 'bad' : '')}${x.up ? 'работает' : x.task ? 'остановлена' : 'спит (по запросу)'}`)).join('')}</div>`;
  const vpsAll = [...(v.pm2 || []).map((x) => x.status === 'online'), ...(v.units || []).map((x) => x.active === 'active')];
  const vpsBad = vpsAll.filter((ok) => !ok).length;
  const vpsSvc = v.online ? `<div class="card"${health(vpsBad)}><h3>Облако: сервисы <small>${vpsBad ? `${vpsBad} с ошибкой` : 'без ошибок'}</small></h3>
    ${row('Работают', `${dot(vpsBad ? 'bad' : 'ok')}${vpsAll.length - vpsBad} из ${vpsAll.length}`)}<p class="note"><a href="#server/sites">Список, логи и перезапуск — Сервер › Сайты</a></p></div>` : '';
  return kpis + `<div class="grid">${alertsCard(d.alerts)}${hostCard(d.laptop)}${hostCard(p)}${hostCard(v)}${services}${vpsSvc}</div>` + renderInventorySummary(d.inventory);
}

function alertsCard(a) {
  if (!a) return '';
  const list = a.active || [];
  const worst = list.some((x) => x.level === 'bad') ? 'bad' : list.length ? 'warn' : 'ok';
  const state = !a.enabled ? pill('выключены', 'warn') : list.length ? pill(`${list.length} активно`, worst) : pill('всё спокойно', 'ok');
  const rows = list.map((x) => `<div class="row alert"><span>${dot(x.level)}${esc(x.text)}</span><span>${ago(x.first_seen)}</span></div>`).join('');
  return `<div class="card"${list.length || a.last_error ? ' data-disclosure-skip' : health(!a.enabled)}><h3><span>${dot(a.enabled ? worst : 'warn')}Оповещения</span>${state}</h3>${rows}
    ${row('Проверка', `${ago(a.last_run)} · каждые ${Math.round((a.interval_s || 300) / 60)} мин`)}
    ${a.last_error ? row('Telegram', `<span class="err">${esc(a.last_error)}</span>`) : row('Куда', 'Telegram')}</div>`;
}

function renderSites(d) {
  const localActions = d.local_vps_actions === true;
  const rows = d.sites.slice().sort((a, b) => a.ok - b.ok || a.domain.localeCompare(b.domain)).map((s) => `<tr>
    <td>${dot(s.ok ? 'ok' : 'bad')}<a href="https://${esc(s.domain)}" target="_blank" style="color:inherit">${esc(s.domain)}</a></td>
    <td class="num">${esc(s.http)}</td><td class="num">${s.ms} мс</td>
    <td class="num">${s.ssl_days_left ?? '—'} дн ${s.ssl_days_left !== null && s.ssl_days_left < 21 ? pill('скоро', 'warn') : ''}</td>
    <td>${esc(s.ssl_issuer || s.error || '')}</td></tr>`).join('');
  const v = d.vps || {};
  const svc = [...(v.pm2 || []).map((x) => ({ kind: 'pm2', name: x.name, ok: x.status === 'online', info: `${x.status} · перезапусков ${x.restarts} · ${x.mem_mb} МБ` })),
               ...(v.units || []).map((x) => ({ kind: 'systemd', name: x.unit, ok: x.active === 'active', info: x.sub }))];
  const svcRows = svc.map((x) => `<tr><td>${dot(x.ok ? 'ok' : 'bad')}${esc(x.name)}</td><td>${esc(x.kind)}</td><td>${esc(x.info)}</td>
    <td class="actions"><button class="ghost" data-logs="${x.kind}|${esc(x.name)}">Логи</button>${localActions ? `<button class="ghost danger-text" data-restart="${x.kind}|${esc(x.name)}">Перезапуск…</button>` : ''}</td></tr>`).join('');
  return `<div class="table-wrap"><table><thead><tr><th>Сайт</th><th class="num">HTTP</th><th class="num">Ответ</th><th class="num">SSL</th><th>Сертификат</th></tr></thead><tbody>${rows}</tbody></table></div>
    <h2>Nginx и SSL</h2><div class="card"><div class="actions">
      <button class="ghost" data-nginx="check">Проверить nginx</button>
      <button class="ghost" data-nginx="certificates">Сертификаты</button>
      <button class="ghost" data-nginx="renewal-status">Автопродление</button>
      <button class="ghost" data-site-plan="1">Новый домен: план…</button>
      ${localActions ? '<span class="actions-sep"></span><button class="ghost danger-text" data-nginx="reload" title="nginx -t, затем reload: затрагивает все сайты VPS">Применить nginx…</button>' : ''}
    </div><p class="note">${localActions ? 'Применение: сначала nginx -t, затем reload без остановки nginx. Затрагивает все сайты VPS.' : 'Перезапуск сервисов и применение nginx доступны только в локальной панели.'} Новый домен пока только планируется — установка и выпуск SSL не выполняются.</p></div>
    <h2>Сервисы на облаке</h2><div class="table-wrap"><table><thead><tr><th>Сервис</th><th>Тип</th><th>Состояние</th><th></th></tr></thead><tbody>${svcRows}</tbody></table></div>
    ${localActions ? '<p class="note">Перезапуск рабочего сервиса требует ввести его точное имя.</p>' : ''}`;
}

function renderDomains(d) {
  if (!d.ok) return `<div class="card"><h3>${pill(d.need_setup ? 'нужен пароль API' : 'ошибка', d.need_setup ? 'warn' : 'bad')}</h3>
    <p>${d.need_setup ? 'Запустите на ноутбуке ярлык «Remote API - enter password» и введите логин и альтернативный пароль API.' : esc(d.error)}</p></div>`;
  const byDays = [...d.domains].sort((a, b) => (a.days_left ?? Infinity) - (b.days_left ?? Infinity)); // expiring first
  const rows = byDays.map((x) => {
    const st = x.days_left === null ? '' : x.days_left < 30 ? 'bad' : x.days_left < 60 ? 'warn' : 'ok';
    return `<tr><td>${dot(st)}${esc(x.domain)}</td><td>${esc(x.state)}</td><td class="num">${esc(x.expires)}</td>
      <td class="num">${x.days_left ?? '—'} дн ${st === 'bad' ? pill('продлить', 'bad') : st === 'warn' ? pill('скоро', 'warn') : ''}</td><td>${x.hosted_here ? pill('на нашем сервере', 'ok') : ''}</td>
      <td class="actions"><button class="ghost" data-dns="${esc(x.domain)}">DNS</button></td></tr>`;
  }).join('');
  const due = d.domains.filter((x) => x.days_left !== null && x.days_left < 60).sort((a, b) => a.days_left - b.days_left);
  const soon = due.length;
  return `<div class="kpis"><div class="kpi"><span>Доменов</span><b>${d.domains.length}</b></div>
    <div class="kpi"><span>Продлить в ближайшие 60 дней</span><b>${soon}</b>${pill(soon ? 'проверьте автопродление' : 'всё спокойно', soon ? 'warn' : 'ok')}${due.length ? `<p class="note">${due.map((x) => `${esc(x.domain)} — ${x.days_left} дн`).join('<br>')}</p>` : ''}</div></div>
    <h2>Список доменов</h2><div class="table-wrap"><table><thead><tr><th>Домен</th><th>Статус</th><th class="num">Оплачен до</th><th class="num">Осталось</th><th></th><th></th></tr></thead>
    <tbody>${rows}</tbody></table></div><p class="note">Пока только просмотр. Изменение DNS-записей — следующим шагом, с подтверждением.</p>`;
}

function renderStorage(d) {
  const disks = Object.entries(d.disks || {}).map(([k, x]) => `<div class="kpi"><span>локального узла ${k}:</span><b>${x.free_gb} ГБ</b>свободно из ${x.total_gb}${bar(x.used_pct)}</div>`).join('');
  const lap = d.laptop ? Object.entries(d.laptop).map(([k, x]) => `<div class="kpi"><span>Ноутбук ${k}:</span><b>${x.free_gb} ГБ</b>свободно из ${x.total_gb}${bar(x.used_pct)}</div>`).join('') : '';
  const max = Math.max(...d.folders.map((f) => f.gb || 0), 1);
  const rows = d.folders.slice().sort((a, b) => (b.gb || 0) - (a.gb || 0)).map((f) => `<tr><td>${esc(f.name)}</td><td class="num">${f.gb ?? '—'} ГБ</td>
    <td style="width:35%">${bar((f.gb || 0) / max * 100)}</td><td class="cell-muted">${esc(f.path)}</td></tr>`).join('');
  return `<div class="kpis">${lap}${disks}</div><h2>Папки и размеры</h2><div class="table-wrap"><table><thead><tr><th>Что</th><th class="num">Размер</th><th></th><th>Где (локального узла)</th></tr></thead><tbody>${rows}</tbody></table></div>
    <p class="note">${d.scanning ? 'Размеры ещё подсчитываются. Папки уже можно посмотреть. ' : ''}Размеры пересчитываются раз в час; оценка учитывает hard links. Это не полная проверка дубликатов.</p>`;
}

function renderBackups(d) {
  const rows = (d.hdd || []).map((b) => `<tr><td>${esc(b.name)}</td><td>${ago(b.last)}</td><td class="cell-muted">${esc(b.path)}</td></tr>`).join('');
  const gh = d.github || {};
  const rs = d.restic || {};
  const rsState = rs.ok ? 'без ошибок' : rs.status === 'partial' ? 'частичная копия' : 'требует проверки';
  const rsProblems = rs.partial ? `Часть файлов не попала в снимок. Ошибок чтения: ${esc(rs.read_errors ?? '—')}.` : (rs.problems || []).map(esc).join('<br>');
  const ghBad = Object.entries(gh.reason_counts || {}).reduce((n, [k, v]) => n + (k === 'runner' ? 0 : Number(v) || 0), 0);
  const ghNote = !gh.planned ? '' : gh.ok === false && ghBad ? `проблемы: ${ghBad} из ${gh.planned}` : `${gh.repos ?? 0} из ${gh.planned} репозиториев`;
  const ghProblems = gh.reason_counts?.authentication ? `<p class="note">В последнем прогоне не сработала авторизация GitHub для ${esc(gh.reason_counts.authentication)} репозиториев. Это результат того запуска; текущая настройка доступа проверяется отдельно.</p>` : (gh.problems || []).length ? `<p class="note">${(gh.problems || []).map(esc).join('<br>')}</p>` : '';
  // UX-24: say why a repo was not pushed; the secret scan blocking a push is the guard working, not a broken backup.
  const ghBlocked = gh.reason_counts?.blocked ? `<p class="note">${pill('не отправлено', 'warn')} ${esc(gh.reason_counts.blocked)} репоз. — проверка секретов нашла подозрительные строки, поэтому копия на GitHub не ушла. Список и файлы: <code>${esc(gh.source || '')}</code>.</p>` : '';
  return `<div class="kpis"><div class="kpi"><span>GitHub (код), последняя попытка</span><b>${ago(gh.last)}</b>${pill(gh.ok === false ? 'не в порядке' : gh.last ? 'ок' : 'нет данных', gh.ok === false ? 'bad' : gh.last ? 'ok' : 'warn')} ${esc(ghNote)}</div>
    <div class="kpi"><span>Данные на HDD · restic</span><b>${ago(rs.last)}</b>${pill(rsState, rs.ok ? 'ok' : 'warn')}</div>
    <div class="kpi"><span>Копия данных вне дома</span><b>не настроена</b>${pill('нужно выбрать хранилище', 'warn')}</div></div>${ghProblems}${ghBlocked}
    <p class="note">Настроенный restic сохраняет данные на D: этого же компьютера. GitHub хранит код и не заменяет внешнюю копию проектов и баз. Внешнее хранилище для данных пока не подключено.</p>
    ${rsProblems ? `<p class="note">${rsProblems}</p>` : ''}
    ${rs.snapshot_id ? `<p class="note">Снимок restic: <code>${esc(rs.snapshot_id)}</code>. Проверка репозитория: ${rs.check_exit === 0 ? 'пройдена' : 'требует проверки'}.</p>` : ''}
    <h2>Архивные наборы на HDD локального узла</h2><div class="table-wrap"><table><thead><tr><th>Набор</th><th>Изменён</th><th>Где</th></tr></thead><tbody>${rows}</tbody></table></div>`;
}

function modal(title, html, okLabel) {
  $('#m-title').textContent = title; $('#m-body').innerHTML = html;
  const ok = $('#m-ok'); ok.hidden = !okLabel; ok.textContent = okLabel || '';
  $('#modal').showModal();
  return new Promise((res) => $('#modal').addEventListener('close', () => res($('#modal').returnValue === 'ok'), { once: true }));
}

document.addEventListener('click', async (e) => {
  const t = e.target.closest('button'); if (!t) return;
  if (t.dataset.nginx) {
    const action = t.dataset.nginx;
    let body;
    if (action === 'reload') {
      const ok = await modal('Применить nginx на VPS?', '<p>Будут перечитаны настройки всех сайтов после успешной проверки. Введите nginx:</p><input id="confirm-name" autocomplete="off">', 'Проверить и применить');
      if (!ok) return;
      body = { confirm: $('#confirm-name').value.trim() };
    }
    t.disabled = true;
    try {
      const r = action === 'reload' ? await post('/api/nginx/reload', body) : await api(`/api/nginx/${action}`);
      modal(r.ok ? 'Nginx / SSL: выполнено' : 'Nginx / SSL: ошибка', `<pre>${esc(r.output)}</pre><p class="note">Квитанция: ${esc(r.receipt)}</p>`);
    } catch (err) { modal('Не выполнено', esc(err.message)); }
    finally { t.disabled = false; }
  }
  if (t.dataset.sitePlan) {
    const ok = await modal('Новый домен — предварительный план', '<p>Ничего не установит и не изменит на VPS.</p><label>Домен <input id="site-domain" placeholder="app.example.com"></label><label>Порт приложения <input id="site-port" type="number" min="1024" max="65535" value="8080"></label>', 'Составить план');
    if (!ok) return;
    try {
      const r = await post('/api/sites/plan', { domain: $('#site-domain').value, port: Number($('#site-port').value) });
      modal(`План: ${r.domain} — НЕ ПРИМЕНЁН`, `<ol>${r.steps.map((s) => `<li>${esc(s)}</li>`).join('')}</ol><pre>${esc(r.nginx_config)}</pre>`);
    } catch (err) { modal('Ошибка плана', esc(err.message)); }
  }
  if (t.dataset.logs) {
    const [kind, name] = t.dataset.logs.split('|');
    t.disabled = true;
    try { const r = await api(`/api/vps/${kind}/${encodeURIComponent(name)}/logs`); modal(`Логи: ${name}`, `<pre>${esc(r.output)}</pre>`); }
    catch (err) { modal('Ошибка', esc(err.message)); } finally { t.disabled = false; }
  }
  if (t.dataset.dns) {
    const dn = t.dataset.dns; t.disabled = true;
    try {
      const r = await api(`/api/domains/${encodeURIComponent(dn)}/dns`);
      const body = r.ok ? `<div class="table-wrap"><table><thead><tr><th>Тип</th><th>Имя</th><th>Значение</th></tr></thead><tbody>${
        r.records.map((x) => `<tr><td>${esc(x.type)}</td><td>${esc(x.name)}</td><td style="word-break:break-all">${esc(x.content)}${x.prio ? ' · prio ' + esc(x.prio) : ''}</td></tr>`).join('')}</tbody></table></div>`
        : `<p class="err">${esc(r.error)}</p>`;
      modal(`DNS: ${dn}`, body);
    } catch (err) { modal('Ошибка', esc(err.message)); } finally { t.disabled = false; }
  }
  if (t.dataset.restart) {
    const [kind, name] = t.dataset.restart.split('|');
    const ok = await modal(`Перезапустить ${name}?`, `<p>Это рабочий сервис на облаке. Сайт может быть недоступен несколько секунд.<br>Введите имя сервиса для подтверждения:</p><input id="confirm-name" autocomplete="off" placeholder="${esc(name)}">`, 'Перезапустить');
    if (!ok) return;
    try { const r = await post(`/api/vps/${kind}/${encodeURIComponent(name)}/restart`, { confirm: $('#confirm-name').value.trim() }); modal(r.ok ? 'Перезапущен' : 'Ошибка', `<pre>${esc(r.output)}</pre>`); show(current); }
    catch (err) { modal('Не выполнено', esc(err.message)); }
  }
  if (t.dataset.gpu) {
    const [target, action] = t.dataset.gpu.split('|');
    t.disabled = true; t.textContent = '…';
    try { await post(`/api/gpu/${target}/${action}`); } catch (err) { modal('Ошибка', esc(err.message)); }
    show(current);
  }
});

// Desktop: the menu collapses to an icon rail (remembered). Phone: bottom bar with the main tabs + «Ещё».
const navToggle = $('#nav-toggle'), navMore = $('#nav-more');
function setRail(rail) {
  document.body.classList.toggle('nav-rail', rail);
  navToggle.setAttribute('aria-expanded', String(!rail));
  const label = rail ? 'Развернуть меню' : 'Свернуть меню';
  navToggle.setAttribute('aria-label', label); navToggle.title = label;
  try { localStorage.setItem('pipeline.nav.rail', String(rail)); } catch {}
}
let savedRail = null;
try { savedRail = localStorage.getItem('pipeline.nav.rail') ?? (localStorage.getItem('pipeline.nav.hidden') === 'true' ? 'true' : null); } catch {}
setRail(savedRail === null ? window.innerWidth < 1200 : savedRail === 'true');
navToggle.addEventListener('click', () => setRail(!document.body.classList.contains('nav-rail')));
const setMore = (open) => { document.body.classList.toggle('nav-more-open', open); navMore.setAttribute('aria-expanded', String(open)); };
navMore.addEventListener('click', () => setMore(!document.body.classList.contains('nav-more-open')));
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') setMore(false); });
document.querySelectorAll('nav a[data-tab]').forEach((a) => {
  a.title = a.lastChild.textContent.trim();
  a.addEventListener('click', (e) => { e.preventDefault(); setMore(false); const h = a.dataset.tab === 'server' ? 'server/' + serverTab : a.dataset.tab; if (location.hash.slice(1) === h) show(current); else location.hash = h; });
});
// Owner sessions page (/auth/security) exists only behind the public gateway, not on the local 127.0.0.1 panel.
if (!['127.0.0.1', 'localhost', '[::1]'].includes(location.hostname)) $('#security-link').hidden = false;
window.addEventListener('hashchange', () => route(location.hash.slice(1)));
$('#refresh').addEventListener('click', () => current === 'studio' || current === 'montage' ? document.dispatchEvent(new Event('studio:refresh')) : show(current));
api('/api/version').then((v) => { $('#ver').textContent = String(v.version || '').replace(/\.0$/, ''); }).catch(() => {});
route(location.hash.slice(1) || 'home');
initBoard(() => show(current));
initSmm(() => show(current));
initProjects(() => show(current));
initOps(() => show(current));
initModels(() => show(current));
initQuick(() => show(current));
initProjectBrowser();
initDisclosure();
// Refresh monitoring only. Workspaces keep drafts, selection and scroll until an explicit refresh.
setInterval(() => { if (!document.hidden && $('#view').getAttribute('aria-busy') !== 'true' && ['home', 'health', 'server', 'gpu', 'downloads', 'agents'].includes(current) && !document.querySelector('dialog[open]') && !document.activeElement?.closest('#view input, #view textarea, #view select, #view form')) show(current, { background: true }); }, 30000);

// Local section search, no server requests or global keyboard interception while editing.
const sectionDialog = $('#section-dialog'), sectionQuery = $('#section-query');
const searchHints = {home:'главная обзор внимание', settings:'тема светлая тёмная оформление ключи токены api доступы секреты', studio:'чаты результаты проект файлы', montage:'монтаж видео склейка таймлайн субтитры', quick:'конвертация конвертер формат редакторы pdf фото сжать', models:'видео картинки голос музыка', tools:'навыки skills инструменты', board:'канбан задачи', projects:'файлы отчёты', health:'состояние сеть', server:'сайты домены бэкапы хранилище'};
function searchSections() {
  const term = sectionQuery.value.trim().toLocaleLowerCase('ru');
  const results = Object.entries(views).filter(([id, v]) => (v.title + ' ' + (searchHints[id] || '')).toLocaleLowerCase('ru').includes(term));
  $('#section-results').innerHTML = results.length ? results.map(([id,v]) => '<a href="#' + id + '"><strong>' + esc(v.title) + '</strong><span>' + esc(v.sub) + '</span></a>').join('') : '<p class="note">Раздел не найден. Попробуйте другое название.</p>';
}
$('#section-search').addEventListener('click', () => { sectionQuery.value = ''; searchSections(); sectionDialog.showModal(); sectionQuery.focus(); });
$('#section-close').addEventListener('click', () => sectionDialog.close());
sectionQuery.addEventListener('input', searchSections);
sectionQuery.addEventListener('keydown', e => { if (e.key === 'ArrowDown') { e.preventDefault(); $('#section-results a')?.focus(); } });
$('#section-results').addEventListener('click', e => { if (e.target.closest('a')) sectionDialog.close(); });
document.addEventListener('keydown', e => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k' && !e.target.closest('input,textarea,select,[contenteditable="true"]') && !document.querySelector('dialog[open]')) { e.preventDefault(); $('#section-search').click(); } });

// Theme button cycles dark ↔ light; «Как в системе» lives in Настройки.
$('#theme-toggle').addEventListener('click', () => { const cur = document.documentElement.dataset.theme === 'system' ? (matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark') : getTheme(); setTheme(cur === 'light' ? 'dark' : 'light'); });
loadChips();
setInterval(() => { if (!document.hidden) loadChips(); }, 30000);

$('.skip-link').addEventListener('click', e => { e.preventDefault(); $('#view').focus(); });
