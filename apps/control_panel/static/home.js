// Control Pipeline 3.0 — «Главная»: what needs attention, quick launch, latest results, machines. Plus «Настройки» and topbar chips.
import { runName } from './models-catalog-ui.js?v=c3-20261019p';
import { loadInventory, waiting, topRow } from './inventory.js?v=c3-20261019u';
const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const json = (path) => fetch(path).then((r) => (r.ok ? r.json() : Promise.reject(new Error(r.statusText))));
const ago = (ts) => {
  if (!ts) return '';
  const m = Math.max(0, Math.round((Date.now() / 1000 - ts) / 60));
  return m < 1 ? 'только что' : m < 60 ? `${m} мин назад` : m < 1440 ? `${Math.round(m / 60)} ч назад` : `${Math.round(m / 1440)} дн назад`;
};
const icon = (d) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${d}"/></svg>`;
export const uptime = (h) => (h == null ? '' : h < 48 ? `работает ${Math.round(h)} ч` : `работает ${Math.round(h / 24)} дн`);

// Test and smoke runs stay in Модели; the home page shows real work only.
const NOISE = /smoke|ux.?check|ux-\d+|проверк|проба|тест|test/i;
// A run titled with the raw workflow name (no «·») shows «Модель · режим»; the full title stays in the tooltip.
const resultName = (r) => (!/ · /.test(r.title || '') && runName(r.kind)) || r.title || r.kind;
const IMG = /\.(png|jpe?g|webp|gif)$/i, VID = /\.(mp4|webm|mov)$/i, AUD = /\.(wav|mp3|flac|ogg|m4a)$/i;

const LAUNCH = [
  ['models/video', 'Видео', 'Текст или кадр → ролик', 'M4 6h12v12H4zM16 10l4-2v8l-4-2'],
  ['models/image', 'Картинки', 'Генерация и правка', 'M4 4h16v16H4zM4 16l5-5 4 4 3-3 4 4M15 8h.01'],
  ['models/voice', 'Голос', 'Озвучка и клон голоса', 'M12 3a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3zM5 11a7 7 0 0 0 14 0M12 18v3'],
  ['models/music', 'Музыка', 'Трек по описанию', 'M9 18V5l11-2v13M9 18a3 3 0 1 1-6 0 3 3 0 0 1 6 0zM20 16a3 3 0 1 1-6 0 3 3 0 0 1 6 0z'],
  ['models/3d', '3D', 'Модель из картинки', 'm12 3 8 4.5v9L12 21l-8-4.5v-9zM12 12l8-4.5M12 12v9M12 12 4 7.5'],
  ['models/text', 'Текст', 'Чат с локальной моделью', 'M4 5h16v11H8l-4 4zM8 9h8M8 12h5'],
  ['montage', 'Монтаж', 'Склейка роликов проекта', 'M4 7h16M4 17h16M7 4v6M17 14v6M12 4v16'],
  ['quick', 'Конвертеры', 'PDF, фото, видео, документы', 'M7 4h7l5 5v11H7zM14 4v5h5M10 14h6M13 11l3 3-3 3'],
];

export async function loadHome() {
  const [health, runs, board, inventory] = await Promise.allSettled([json('/api/health'), json('/api/models/runs?limit=40'), json('/api/board'), loadInventory()]);
  return { health: health.value || null, runs: runs.value?.runs || [], queue: runs.value?.queue || [], board: board.value || null, inventory: inventory.value || null };
}

function attention(d) {
  const out = [];
  const h = d.health;
  for (const a of h?.alerts?.active || []) out.push({ level: a.level === 'bad' ? 'bad' : 'warn', text: a.text, href: '#health', note: ago(a.first_seen) });
  const p = h?.local;
  if (p?.pending_reboot) out.push({ level: 'info', text: 'Локальный узел ждёт перезагрузки после обновлений Windows', href: '#health', note: 'когда будет удобно' });
  for (const [k, disk] of Object.entries(p?.disks || {})) if (disk.used_pct >= 90) out.push({ level: disk.used_pct >= 95 ? 'bad' : 'warn', text: `Диск ${k}: на локальном узле почти заполнен — свободно ${disk.free_gb} ГБ`, href: '#server/storage', note: `${disk.used_pct}%` });
  if (h?.vps?.online === false) out.push({ level: 'bad', text: 'Облачный сервер не отвечает', href: '#health', note: '' });
  const down = (p?.services || []).filter((s) => !s.up && s.task && !/mint/i.test(s.name));
  if (down.length) out.push({ level: 'warn', text: `Не работает: ${down.map((s) => s.name).join(', ')}`, href: '#health', note: '' });
  const tasks = d.board?.tasks || [];
  const review = tasks.filter((t) => t.status === 'review').length, blocked = tasks.filter((t) => t.status === 'blocked').length;
  if (review) out.push({ level: 'info', text: `${review} ${plural(review, 'задача ждёт', 'задачи ждут', 'задач ждут')} вашей проверки`, href: '#board', note: 'Задачи' });
  if (blocked) out.push({ level: 'warn', text: `${blocked} ${plural(blocked, 'задача остановлена', 'задачи остановлены', 'задач остановлено')} — нужен ответ`, href: '#board', note: 'Задачи' });
  const failed = d.runs.filter((r) => r.status === 'error' && r.started > Date.now() / 1000 - 86400 && !NOISE.test(r.title || '')).length;
  if (failed) out.push({ level: 'warn', text: `${failed} ${plural(failed, 'генерация', 'генерации', 'генераций')} за сутки ${failed === 1 ? 'завершилась' : 'завершились'} ошибкой`, href: '#models', note: 'Модели' });
  return out;
}
const plural = (n, one, few, many) => (n % 10 === 1 && n % 100 !== 11 ? one : n % 10 >= 2 && n % 10 <= 4 && (n % 100 < 10 || n % 100 >= 20) ? few : many);

function outputsOf(r) {
  let o = r.outputs;
  if (typeof o === 'string') { try { o = JSON.parse(o); } catch { o = []; } }
  return Array.isArray(o) ? o.filter((x) => x && x.path) : [];
}

function thumb(r) {
  const outs = outputsOf(r);
  const media = outs.find((o) => IMG.test(o.path)) || outs.find((o) => VID.test(o.path)) || outs[0];
  if (!media) return { html: icon('M4 4h16v16H4z'), href: '#models' };
  const src = '/api/models/file?path=' + encodeURIComponent(media.path);
  if (IMG.test(media.path)) return { html: `<img src="${esc(src)}" alt="" loading="lazy" decoding="async">`, href: src };
  if (VID.test(media.path)) return { html: `<video src="${esc(src)}#t=0.1" muted playsinline preload="metadata"></video>`, href: src };
  if (AUD.test(media.path)) return { html: icon('M9 18V5l11-2v13M9 18a3 3 0 1 1-6 0 3 3 0 0 1 6 0zM20 16a3 3 0 1 1-6 0 3 3 0 0 1 6 0z'), href: src };
  return { html: icon('M7 4h7l5 5v11H7zM14 4v5h5'), href: src };
}

function meter(label, pct) {
  if (pct == null) return '';
  const cls = pct >= 90 ? 'bad' : pct >= 80 ? 'warn' : '';
  return `<div class="meter"><span>${esc(label)}</span><i><em class="${cls}" style="width:${Math.min(100, pct)}%"></em></i><span>${Math.round(pct)}%</span></div>`;
}

function hostCard(name, h, href) {
  if (!h) return '';
  if (h.monitoring === 'paused') return `<a class="host" href="${href}"><header><b><i class="dot-warn"></i>${name}</b><small>не наблюдается</small></header></a>`;
  if (!h.online) return `<a class="host" href="${href}"><header><b><i class="dot-bad"></i>${name}</b><small>нет связи</small></header></a>`;
  const disks = Object.entries(h.disks || {});
  const main = disks.find(([k]) => k === 'E') || disks[0];
  const warn = h.pending_reboot || h.reboot_required;
  return `<a class="host" href="${href}"><header><b><i class="${warn ? 'dot-warn' : 'dot-ok'}"></i>${name}</b><small>${uptime(h.uptime_h)}</small></header>
    ${meter('CPU', h.cpu_pct ?? (h.load ? h.load[0] * 100 / 4 : null))}${meter('RAM', h.ram_used_pct)}${main ? meter(`Диск ${main[0]}`, main[1].used_pct) : meter('Диск', h.disk_used_pct)}
    ${h.gpu ? meter('GPU', h.gpu.util_pct) : ''}</a>`;
}

export function renderHome(d) {
  const att = attention(d);
  const attHtml = att.length
    ? `<div class="home-attn">${att.slice(0, 6).map((a) => `<a class="attn" data-level="${a.level}" href="${a.href}"><span>${esc(a.text)}</span>${a.note ? `<small>${esc(a.note)}</small>` : ''}</a>`).join('')}</div>`
    : '<div class="home-calm">Локальная рабочая область готова. Внешний мониторинг выключен; задач на проверку нет</div>';
  const launch = `<div class="launch">${LAUNCH.map(([href, title, sub, d]) => `<a href="#${href}">${icon(d)}<span><b>${title}</b><small>${sub}</small></span></a>`).join('')}</div>`;
  const runs = d.runs.filter((r) => r.status === 'done' && !NOISE.test(r.title || '') && outputsOf(r).length).slice(0, 8);
  const busy = d.runs.filter((r) => r.status === 'running').length + (d.queue?.length || 0);
  const recent = runs.length
    ? `<div class="recent">${runs.map((r) => { const t = thumb(r); return `<a href="${esc(t.href)}" target="_blank" rel="noopener" title="${esc(r.title)}"><span class="thumb">${t.html}</span><span><b>${esc(resultName(r))}</b><small>${esc(ago(r.started))}</small></span></a>`; }).join('')}</div>`
    : '<p class="note">Пока нет готовых результатов. Запустите генерацию в разделе «Модели».</p>';
  // Вариант A: decisions from the inventory registry live here; the first three are open, the rest behind «Ещё».
  const waits = waiting(d.inventory);
  const decide = waits.length ? `<section class="home-decide"><h2><span>Ждут вашего решения · ${waits.length}</span><a href="#board/mine">Мои решения в Задачах →</a></h2>
    <div class="inv-rows">${waits.slice(0, 3).map((x) => topRow(x, false)).join('')}</div>
    ${waits.length > 3 ? `<details><summary>Ещё ${waits.length - 3}</summary><div class="inv-rows">${waits.slice(3).map((x) => topRow(x, false)).join('')}</div></details>` : ''}</section>` : '';
  const h = d.health;
  const hosts = h ? `<div class="hosts">${hostCard('Локальный узел', h.local, '#health')}${hostCard('Ноутбук', h.laptop, '#health')}${hostCard('Облако', h.vps, '#server')}</div>` : '<p class="note">Состояние машин сейчас недоступно.</p>';
  return `<div class="home">
    <section><h2>Требует внимания</h2>${attHtml}</section>
    ${decide}
    <section><h2>Создать</h2>${launch}</section>
    <section><h2><span>Последние результаты${busy ? ` · в работе ${busy}` : ''}</span><a href="#models">Все генерации →</a></h2>${recent}</section>
    <section><h2><span>Машины</span><a href="#health">Подробно →</a></h2>${hosts}</section>
  </div>`;
}

export function mountHome(view) {
  // Video thumbnails show their first frame only; play on hover, without sound.
  const on = (e) => e.target.closest?.('.recent a')?.querySelector('video')?.play().catch(() => {});
  const off = (e) => { const v = e.target.closest?.('.recent a')?.querySelector('video'); if (v) { v.pause(); v.currentTime = 0.1; } };
  view.addEventListener('mouseover', on); view.addEventListener('mouseout', off);
  return () => { view.removeEventListener('mouseover', on); view.removeEventListener('mouseout', off); };
}

// Theme: dark (default), light or follow the system. Stored per browser.
const THEMES = [['dark', 'Тёмная'], ['light', 'Светлая'], ['system', 'Как в системе']];
export const getTheme = () => { try { return localStorage.getItem('pc-theme') || 'dark'; } catch { return 'dark'; } };
export function setTheme(t) {
  document.documentElement.dataset.theme = t;
  try { localStorage.setItem('pc-theme', t); } catch {}
  document.querySelectorAll('[data-theme-set]').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.themeSet === t)));
}

export function renderSettings(extra = '') {
  const cur = getTheme();
  return `<div class="settings">
    <div class="card" data-disclosure-skip><h3>Оформление</h3><p>Тема хранится в этом браузере. «Как в системе» переключается вместе с Windows или телефоном.</p>
      <div class="seg" role="group" aria-label="Тема">${THEMES.map(([k, l]) => `<button type="button" data-theme-set="${k}" aria-pressed="${k === cur}">${l}</button>`).join('')}</div></div>
    <div class="card" data-disclosure-skip><h3>Меню</h3><p>На компьютере меню можно свернуть до иконок кнопкой справа вверху. На телефоне основные разделы внизу экрана, остальные — в «Ещё».</p></div>
    ${extra}
  </div>`;
}
export function mountSettings(view) {
  const click = (e) => { const b = e.target.closest('[data-theme-set]'); if (b) setTheme(b.dataset.themeSet); };
  view.addEventListener('click', click);
  return () => view.removeEventListener('click', click);
}

// Topbar chips, bell and the sidebar disk meter: one /api/health read every 30 s, whatever section is open.
export function updateChips(h) {
  const p = h?.local || {};
  const set = (id, text, state) => { const el = document.getElementById(id); if (!el) return; el.querySelector('b').textContent = text; el.dataset.state = state; };
  const g = p.gpu;
  if (g) set('chip-gpu', `${g.util_pct}% · ${(g.vram_used_mb / 1024).toFixed(1)}/${Math.round(g.vram_total_mb / 1024)} ГБ`, g.util_pct >= 90 ? 'warn' : g.util_pct > 5 ? 'busy' : 'ok');
  else set('chip-gpu', p.online === false ? 'нет связи' : '—', p.online === false ? 'bad' : '');
  if (p.ram_used_pct != null) set('chip-ram', `${Math.round(p.ram_used_pct)}%`, p.ram_used_pct >= 90 ? 'bad' : p.ram_used_pct >= 80 ? 'warn' : 'ok');
  const comfy = (p.services || []).find((s) => /comfy/i.test(s.name));
  if (comfy) set('chip-comfy', comfy.up ? 'работает' : 'спит', comfy.up ? 'ok' : 'idle');
  const n = (h?.alerts?.active || []).length + (p.pending_reboot ? 1 : 0);
  const count = document.querySelector('#bell .count');
  if (count) { count.hidden = !n; count.textContent = String(n); count.dataset.level = (h?.alerts?.active || []).some((a) => a.level === 'bad') ? 'bad' : 'warn'; }
  const bell = document.getElementById('bell');
  if (bell) bell.title = n ? `Требует внимания: ${n}` : 'Внешние оповещения выключены';
  const e = p.disks?.E;
  if (e) {
    const val = document.getElementById('foot-store-val'); if (val) val.textContent = `${e.free_gb} ГБ свободно`;
    const em = document.querySelector('#foot-store em'); if (em) { em.style.width = `${e.used_pct}%`; em.className = e.used_pct >= 90 ? 'bad' : e.used_pct >= 80 ? 'warn' : ''; }
  }
}
export const loadChips = () => json('/api/health').then(updateChips).catch(() => {});
