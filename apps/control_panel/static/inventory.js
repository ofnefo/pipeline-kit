// Система › Инвентарь (3.0): what is done and what waits for Operator, from the inventory agent's registry (read-only).
const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const verdictState = (v) => (/^pass/i.test(v || '') ? 'ok' : /fail|провал|не прош/i.test(v || '') ? 'bad' : 'warn');
const docState = (s) => (/review|приёмк|ждёт/i.test(s || '') ? 'warn' : /delivered|accepted|сдан/i.test(s || '') ? 'ok' : '');
const docLabel = { warn: 'ждёт вас', ok: 'сдано' };
const pill = (text, state = '') => (text ? `<span class="pill ${state}">${esc(text)}</span>` : '');
const more = (body) => (body ? `<details class="inv-more"><summary>Подробнее</summary><div>${body}</div></details>` : '');
const line = (k, v) => (v ? `<p><span>${esc(k)}</span> ${esc(v)}</p>` : '');
const when = (iso) => { const d = new Date(iso); return isNaN(d) ? '' : d.toLocaleString('ru-RU', { day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit' }); };

export async function loadInventory() {
  const r = await fetch('/api/inventory', { cache: 'no-store' });
  if (!r.ok) throw new Error('Не удалось открыть инвентарь. Повторите попытку.');
  return r.json();
}

// Rows are shared with Главная (decisions) and Здоровье (tests and documents): вариант A, Инвентарь вне меню.
export const waiting = (d) => (d?.available ? (d.top10 || []).filter((x) => x.waits_operator === true) : []);
export const topRow = (x, badge = true) => `<div class="inv-row${x.waits_operator === true ? ' inv-wait' : ''}"><div class="inv-main"><b>${esc(x.item)}</b>${x.ask ? `<p class="inv-ask">${esc(x.ask)}</p>` : ''}</div>${badge ? (x.waits_operator === true ? pill('ждёт вас', 'warn') : pill('в работе')) : ''}${more(line('Состояние:', x.status) + line('Где:', x.where))}</div>`;
const testRow = (t) => `<div class="inv-row"><div class="inv-main"><b>${esc(t.what)}</b><small>${esc(t.date)}</small></div>${pill(t.verdict, verdictState(t.verdict))}${more(line('Результат:', t.last_result) + line('Как:', t.how) + line('Где:', t.where))}</div>`;
const docRow = (x) => `<div class="inv-row"><div class="inv-main"><b>${esc(x.what)}</b><small>${esc(x.date)}</small></div>${pill(docLabel[docState(x.status)], docState(x.status))}${more(line('Состояние:', x.status) + line('Заметка:', x.note) + line('Папка:', x.path))}</div>`;
const passed = (d) => d.tests.filter((t) => verdictState(t.verdict) === 'ok').length;
const onReview = (d) => d.documents.filter((x) => docState(x.status) === 'warn').length;

function group(title, count, rows, open = false) {
  return `<details class="inv-group"${open ? ' open' : ''}><summary><b>${esc(title)}</b><span class="count">${count}</span></summary><div class="inv-rows">${rows}</div></details>`;
}

export function renderInventory(d) {
  if (!d?.available) {
    return '<div class="mint-offline" role="status"><span class="mint-offline-dot" aria-hidden="true"></span><div><b>Инвентарь ещё не собран</b><p>Сводку «что сделано и что ждёт решения» собирает агент инвентаря. Как только он её сохранит, она появится здесь.</p></div></div>';
  }
  const waits = waiting(d);
  const pass = passed(d), review = onReview(d);
  const kpis = `<div class="kpis">
    <button type="button" class="kpi" data-inv-jump><span>Ждут вашего решения</span><b>${waits.length}</b></button>
    <div class="kpi"><span>Творческая приёмка</span><b>${d.decisions.length}</b></div>
    <div class="kpi"><span>Тесты прошли</span><b>${pass} из ${d.tests.length}</b></div>
    <div class="kpi"><span>Документы на приёмке</span><b>${review}</b></div>
    <a class="kpi" href="#board"><span>Открытые задачи</span><b>${d.board_open.length}${d.board_total ? ` <small>из ${d.board_total}</small>` : ''}</b></a></div>`;
  const top = d.top10.map((x) => topRow(x)).join('');
  const decisions = d.decisions.map((x) => `<div class="inv-row"><div class="inv-main">${esc(x.text)}</div></div>`).join('');
  const tests = d.tests.map(testRow).join('');
  const docs = d.documents.map(docRow).join('');
  const sites = d.sites.map((x) => `<div class="inv-row"><div class="inv-main"><b>${esc(x.site)}</b><small>${esc(x.state)}</small></div>${more(line('Прод:', x.prod) + line('Репозиторий:', x.repo) + line('Коммиты:', x.commits))}</div>`).join('');
  const bots = d.bots.map((x) => `<div class="inv-row"><div class="inv-main"><b>${esc(x.bot)}</b><small>${esc(x.status)}</small></div>${more(line('Где:', x.where) + line('Заметка:', x.note))}</div>`).join('');
  const board = d.board_open.map((x) => `<div class="inv-row"><div class="inv-main"><b>${esc(x.title)}</b><small>${esc(x.id)}${x.updated ? ' · ' + esc(x.updated) : ''}</small></div>${pill(x.status)}</div>`).join('');
  return `<section class="inventory">${kpis}
    <h2 id="inventory-waits" class="inv-h">Главное сейчас</h2><div class="inv-rows inv-top">${top}</div>
    ${group('Творческая приёмка', d.decisions.length, decisions, true)}
    ${group('Тесты', d.tests.length, tests)}
    ${group('Документы и медиа', d.documents.length, docs)}
    ${group('Сайты', d.sites.length, sites)}
    ${group('Боты', d.bots.length, bots)}
    ${group('Открытые задачи', d.board_open.length, board + '<p class="note"><a href="#board">Вся доска — «Задачи»</a></p>')}
    <p class="note inv-foot">Сводку собрал агент инвентаря${d.updated_at ? ', ' + esc(when(d.updated_at)) : ''}. Проектов: ${d.counts.projects}, пайплайнов: ${d.counts.pipelines}.</p></section>`;
}

// Здоровье › «Подробнее»: tests and documents without opening the full inventory (still at #inventory).
export function renderInventorySummary(d) {
  if (!d?.available) return '';
  return `<details class="inv-group inv-health"><summary><b>Подробнее: тесты и документы</b><span class="count">тесты ${passed(d)} из ${d.tests.length} · на приёмке ${onReview(d)}</span></summary>
    ${group('Тесты', d.tests.length, d.tests.map(testRow).join(''))}
    ${group('Документы и медиа', d.documents.length, d.documents.map(docRow).join(''))}
    <p class="note"><a href="#inventory">Весь инвентарь: решения, сайты, боты</a></p></details>`;
}

// The hash is the section router, so the tile scrolls instead of linking to an anchor.
export function mountInventory(view) {
  const jump = (event) => {
    if (!event.target.closest('[data-inv-jump]')) return;
    view.querySelector('#inventory-waits')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };
  view.addEventListener('click', jump);
  return () => view.removeEventListener('click', jump);
}
