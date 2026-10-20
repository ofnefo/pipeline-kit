// GPU, downloads and agents tabs: the "ops" views with their small forms (add download, retry, cancel).
import { destinationFields, initDownloadPicker, restoreDownloadDrafts, clearDownloadDraft } from './download-picker.js';
import { renderProjectSessions } from './project-sessions.js?v=c3-20261019s';
const esc = (v) => String(v ?? '—').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const dot = (state) => `<i class="dot ${state}"></i>`;
const FIT_LABEL = { ok: ['Памяти хватит', 'ok'], offload: ['Пойдёт с выгрузкой в RAM', 'warn'], no: ['Не хватает памяти', 'bad'], true: ['Памяти хватит', 'ok'], false: ['Не хватает памяти', 'bad'] };
const pill = (text, state = '') => `<span class="pill ${state}">${esc(text)}</span>`;
const bar = (pct) => `<div class="bar"><i class="${pct > 90 ? 'bad' : pct > 80 ? 'warn' : ''}" style="width:${Math.min(100, pct || 0)}%"></i></div>`;
const row = (k, v) => `<div class="row"><span>${esc(k)}</span><span>${v}</span></div>`;
const gb = (b) => ((b || 0) / 1073741824).toFixed(2);
const gbm = (mb) => ((mb || 0) / 1024).toFixed(1);
const mins = (s) => s == null ? '—' : s < 3600 ? `${Math.round(s / 60)} мин` : `${(s / 3600).toFixed(1)} ч`;
const FMT = { hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit' };
const toDate = (t) => { if (!t) return null; const n = Number(t); const d = Number.isFinite(n) ? new Date((n > 1e11 ? n : n * 1000)) : new Date(String(t).replace(' ', 'T')); return Number.isNaN(d.getTime()) ? null : d; };
const date = (t) => { const d = toDate(t); return d ? d.toLocaleString('ru-RU', FMT) : (t ? String(t) : '—'); };
const request = async (url, body) => {
  const r = await fetch(url, body ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {});
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || r.statusText);
  return data;
};
let reload = () => {};
let dlFilter = 'active';
const DL_PAGE = 50;
let dlLimit = DL_PAGE; // rows shown in the current group; «Показать ещё» adds a page, switching groups resets it

// ---------- GPU ----------
export function renderGpu(d) {
  const g = d.gpu || {};
  const lock = d.lock || {};
  const head = d.headroom || {};
  const procs = (d.processes || []).map((p) => row(`${p.what} (${p.name}, PID ${p.pid})`, `${(p.vram_mb / 1024).toFixed(2)} ГБ`)).join('') || row('Ничего не держит VRAM', '');
  const procsNote = d.processes_source === 'counters'
    ? `<p class="note">По счётчикам Windows (GPU Process Memory): выделенная видеопамять каждого процесса. Общие поверхности рабочего стола засчитываются каждому, кто их держит, поэтому сумма ${gbm(d.processes_vram_mb)} ГБ больше занятого по nvidia-smi (${gbm(g.vram_used_mb)} ГБ). Модели здесь — ComfyUI и Assistant worker.</p>`
    : d.processes_vram_mb ? `<p class="note">Всего процессы держат ${gbm(d.processes_vram_mb)} ГБ.</p>` : '';
  const comfyUp = d.comfy?.state === 'running';
  const lockState = lock.state === 'held' ? 'bad' : lock.state === 'stale' ? 'warn' : 'ok';
  const lockText = lock.state === 'held' ? 'занята' : lock.state === 'stale' ? 'просроченная' : lock.unreadable ? 'файл не читается' : 'свободна';
  const lockRows = lock.state === 'free' ? row('Файл', '<code>gpu.lock</code> отсутствует — любой пайплайн может взять GPU') : `${row('Кто', esc(lock.owner))}${lock.agent ? row('Агент', esc(lock.agent)) : ''}${row('Зачем', esc(lock.purpose))}
    ${row('PID', `${esc(lock.pid)} ${lock.pid_alive ? pill('жив', 'ok') : pill('процесса нет', 'warn')}`)}${row('Держит', mins(lock.age_s))}${lock.touched_s != null ? row('Обновлялась', mins(lock.touched_s) + ' назад') : ''}
    ${row('Lock устареет через', mins(Math.max(0, (lock.stale_after_s || 0) - (lock.touched_s ?? lock.age_s ?? 0))))}`;
  const queue = d.queue || [];
  const qRows = queue.map((t) => row(`${t.position}. ${t.title || t.purpose || ''}`, `${esc(t.mine ? 'панель' : t.owner)} · ${t.state === 'started' ? 'запускается' : `ждёт ${mins(t.age_s)}`}`)).join('')
    || row('Очередь пуста', d.queue_error ? pill('не читается', 'warn') : '');
  const qErr = d.dispatch_error ? `<p class="note">Ошибка диспетчера ${mins(d.dispatch_error.age_s)} назад: <code>${esc(d.dispatch_error.text)}</code></p>` : '';
  const fits = Object.entries(head.fits || {}).map(([name, ok]) => `<li><span>${esc(name)}</span>${pill(FIT_LABEL[ok]?.[0] || 'Нет оценки', FIT_LABEL[ok]?.[1] || '')}</li>`).join('');
  const stale = (d.stale_locks || []).map((s) => `<li>${esc(s.name)} <small>${esc(s.owner || '')} · ${date(s.mtime)}</small></li>`).join('');
  return `<div class="grid">
    <div class="card"><h3>${esc(g.name)}<small>${g.power_w ?? '—'} Вт</small></h3>${row('Температура', `${g.temp_c}°C`)}${row('Загрузка', `${g.util_pct}%`)}
      ${row('VRAM', `${Math.round(g.vram_used_mb / 102.4) / 10} / ${Math.round(g.vram_total_mb / 1024)} ГБ`)}${bar(g.vram_used_mb / g.vram_total_mb * 100)}
      ${row('Свободно VRAM', `${Math.round((head.free_mb || 0) / 102.4) / 10} ГБ ${pill(head.state === 'ok' ? 'хватает' : head.state === 'warn' ? 'впритык' : 'мало', head.state === 'ok' ? 'ok' : head.state === 'warn' ? 'warn' : 'bad')}`)}
      <p class="note">Оценка памяти для моделей:</p><ul class="gpu-fit-list">${fits || '<li>Нет данных</li>'}</ul></div>
    <div class="card"><h3><span>${dot(lockState)}Блокировка GPU</span>${pill(lockText, lockState)}</h3>${lockRows}
      ${lock.state === 'stale' ? '<p class="note">Владелец не обновлял блокировку дольше 2 ч — следующий запуск заберёт её автоматически.</p>' : ''}
      ${stale ? `<details class="note"><summary>Старые файлы блокировок: ${(d.stale_locks || []).length}</summary><ul>${stale}</ul><p>Хранятся как квитанции; удалять не обязательно.</p></details>` : ''}</div>
    <div class="card"><h3><span>Общая очередь GPU</span>${pill(queue.length ? `${queue.length} ждёт` : 'пусто', queue.length ? 'warn' : 'ok')}</h3>${qRows}
      <p class="note">Агенты и панель ждут здесь, пока lock занят; задачи панели стартуют сами по очереди. Убрать свою задачу — во вкладке «Модели».</p>${qErr}</div>
    <div class="card"><h3>Кто занимает GPU</h3>${procs}${procsNote}</div>
    <div class="card" data-disclosure-skip><h3><span>${dot(comfyUp ? 'ok' : '')}ComfyUI</span>${pill(comfyUp ? 'работает' : 'остановлен', comfyUp ? 'ok' : '')}</h3>
      ${comfyUp ? row('Очередь', `${d.comfy.queue?.running ?? 0} выполняется · ${d.comfy.queue?.pending ?? 0} ждёт`) : row('Запуск', 'сам гаснет через 30 мин простоя')}
      ${comfyUp ? row('Вкладка «Модели»', 'готова к запускам') : row('Вкладка «Модели»', 'нужен запущенный ComfyUI')}
      <div class="actions" style="margin-top:12px">${comfyUp ? '<button class="ghost" data-gpu="comfy|stop">Остановить</button>' : '<button data-gpu="comfy|start">Запустить</button>'}</div></div>
    <div class="card" data-disclosure-skip><h3><span>${dot(d.mint_worker ? 'ok' : '')}Assistant worker (T-lite 8B)</span>${pill(d.mint_worker ? 'готов' : 'спит', d.mint_worker ? 'ok' : '')}</h3>
      ${row('Роль', 'Локальная LLM для черновиков и mint:helper. Чат панели работает независимо от этого worker.')}
      <p class="note">Порт 8745, через LiteLLM :4000 как <code>mint-worker</code>. Запуск модели занимает GPU; сначала проверь текущие задачи.</p>
      <div class="actions" style="margin-top:12px">${d.mint_worker ? '' : '<button data-gpu="mint|start">Разбудить</button>'}</div></div>
    <div class="card"><h3>Правила</h3><ul class="plain">${(d.rules || []).map((r) => `<li>${esc(r)}</li>`).join('')}</ul></div>
  </div>`;
}

// ---------- Downloads ----------
export function renderDownloads(d) {
  restoreDownloadDrafts();
  const st = { done: 'ok', running: 'warn', queued: '', error: 'bad', cancelled: '' };
  const stRu = { done: 'скачано', running: 'качается', queued: 'в очереди', error: 'ошибка', cancelled: 'отменено' };
  const folder = (p) => { const parts = String(p || '').split(/[\\/]/).filter(Boolean); return parts.length > 1 ? '…/' + parts[parts.length - 2] : (p || '—'); };
  const groups = d.groups || [];
  const current = groups.find((g) => g.key === dlFilter) || groups[0] || { jobs: [] };
  const tabs = groups.map((g) => `<button class="${g.key === current.key ? '' : 'ghost'}" data-dl-tab="${g.key}">${esc(g.title)} <span class="count">${g.count}</span></button>`).join('');
  const all = current.jobs || [];
  const rows = all.slice(0, dlLimit).map((j) => {
    const pct = j.size ? Math.round(100 * j.have / j.size) : 0;
    const act = j.status === 'error' || j.status === 'cancelled' ? `<button class="ghost" data-dl-retry="${esc(j.id)}">Повторить</button>` :
      j.status === 'queued' ? `<button class="ghost" data-dl-cancel="${esc(j.id)}">Отменить</button>` : j.status === 'running' ? '<small>Идёт передача</small>' : '';
    const where = j.status === 'error' && j.error ? esc(j.error.slice(0, 160)) : `<span title="${esc(j.target)}">${esc(folder(j.target))}</span>`;
    return `<tr><td>${pill(stRu[j.status] || j.status, st[j.status] || '')}</td><td>${esc(j.group)}</td><td title="${esc(`${j.target}
ID ${j.id}`)}">${esc(j.name)}</td>
      <td class="num">${gb(j.have)} / ${gb(j.size)} ГБ</td><td style="width:16%">${bar(pct)}</td>
      <td class="cell-muted" style="max-width:260px">${where}</td><td class="proj-actions">${act}</td></tr>`;
  }).join('') || `<tr><td colspan="7" class="note">В этой группе пусто.</td></tr>`;
  const left = all.length - Math.min(dlLimit, all.length);
  const more = left > 0 ? `<div class="actions" style="margin-top:8px"><button class="ghost" data-dl-more>Показать ещё ${Math.min(DL_PAGE, left)}</button><small class="note">показано ${dlLimit} из ${all.length}</small></div>` : '';
  const bulk = current.key === 'problem' && current.count ? `<button class="ghost" data-dl-retry-all="${esc(current.jobs.map((j) => j.id).join(','))}">Повторить все (${current.count})</button>` : '';
  return `<div class="kpis"><div class="kpi"><span>Загрузчик</span><b>${d.worker_alive ? dot('ok') + ' работает' : dot('') + ' остановлен'}</b>фоновая очередь локального узла</div>
    ${groups.map((g) => `<div class="kpi"><span>${esc(g.title)}</span><b>${g.count}</b>${gb(g.have)} / ${gb(g.bytes)} ГБ</div>`).join('')}
    <div class="kpi"><span>Осталось скачать</span><b>${gb(d.left_bytes)} ГБ</b>с докачкой и проверкой файлов</div></div>
    <details class="page-section"><summary><h2>Добавить загрузку</h2></summary>
    <div class="grid dl-add-grid" style="margin-bottom:18px">
      <form class="card dl-form" id="dl-hf"><h3>Добавить модель с Hugging Face</h3>
        <label>Репозиторий <input name="repo" placeholder="Wan-AI/Wan2.2-I2V-A14B" required></label>
        <label>Файлы или маски (по одному в строке) <textarea name="files" rows="2" required placeholder="split_files/diffusion_models/wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors"></textarea></label>
        ${destinationFields()}
        <label>Группа <input name="group" placeholder="video"></label>
        <div class="two"><label>Ветка <input name="revision" value="main"></label><label class="check"><input type="checkbox" name="flat"> без подпапок</label></div>
        <label>Заметка <input name="note" placeholder="для какого пайплайна"></label>
        <div class="actions"><button type="submit">В очередь</button><span class="form-msg"></span></div></form>
      <form class="card dl-form" id="dl-url"><h3>Добавить по ссылке</h3>
        <label>URL <input name="url" placeholder="https://…/model.safetensors" required></label>
        ${destinationFields(true)}
        <label>Группа <input name="group"></label>
        <details class="note"><summary>Подробности</summary><label>Контрольная сумма sha256, если известна <input name="sha256"></label></details>
        <label>Заметка <input name="note"></label>
        <div class="actions"><button type="submit">В очередь</button><span class="form-msg"></span></div></form>
    </div></details>
    <div class="actions" style="margin-bottom:10px">${tabs}${bulk}</div>
    <div class="table-wrap"><table><thead><tr><th>Статус</th><th>Группа</th><th>Файл</th><th class="num">Скачано</th><th></th><th>Папка / ошибка</th><th></th></tr></thead><tbody>${rows}</tbody></table></div>${more}
    <details class="note"><summary>Подробности: журнал загрузчика</summary>${d.worker_pid ? `<p>Процесс PID ${esc(d.worker_pid)}, локальный загрузчик.</p>` : ''}<pre style="white-space:pre-wrap">${esc((d.log_tail || []).join('\n'))}</pre><p>Очередь: ${esc(d.queue)}. Перед большими закачками проверяется доступная пропускная способность сети.</p></details>`;
}

// ---------- Agents ----------
export function renderAgents(d) {
  const all = d.sessions || [];
  const table = (rows, empty, withDir) => rows.length ? `<div class="table-wrap"><table><thead><tr><th>Хост</th><th>Что</th>${withDir ? '<th>Папка</th>' : ''}<th class="num">Работает</th></tr></thead><tbody>${
    rows.map((s) => `<tr><td>${esc(s.host)}</td><td>${dot('ok')}${esc(s.kind)}${s.role && s.role !== 'сессия' ? ' ' + pill(s.role) : ''}</td>${withDir ? `<td style="overflow-wrap:anywhere">${esc(s.cwd)}</td>` : ''}<td class="num">${s.started_h_ago} ч</td></tr>`).join('')
  }</tbody></table></div>` : `<p class="note">${empty}</p>`;
  const sessions = all.filter((s) => (s.role || 'сессия') === 'сессия');
  const services = all.filter((s) => s.role && s.role !== 'сессия');
  const claims = d.claims || {};
  const claimRows = (claims.agents || []).map((a) => `<tr><td>${pill(a.kind, a.kind === 'operator' ? 'ok' : a.kind === 'codex' ? 'warn' : '')} ${esc(a.agent)}</td>
    <td>${a.cards.map((c) => `<div class="proj-claim"><b>${esc(c.card)}</b>${c.lock ? ' ' + pill('блокировка', 'ok') : ''}<small>${esc(c.what)} · до ${date(c.until)}</small></div>`).join('')}</td></tr>`).join('');
  const inbox = d.inbox || {};
  const inboxRows = Object.entries(inbox).filter(([k]) => k !== 'error').map(([k, v]) => `<div class="row"><span>${esc(k)}</span><span>${v.count} непрочитанных</span></div>${(v.latest || []).map((m) => `<p class="note" style="margin:4px 0">${esc(m)}</p>`).join('')}`).join('');
  const codex = d.codex || {};
  const codexRows = (codex.threads || []).map((t) => `<tr><td>${esc(t.name || t.id)}</td><td style="overflow-wrap:anywhere">${esc(t.cwd)}</td><td>${esc(t.source)}</td><td class="num">${date(t.updated)}</td></tr>`).join('');
  const mcp = d.mcp || {};
  const mcpRows = (mcp.servers || []).map((s) => `<tr><td>${esc(s.name)}${s.global ? ' ' + pill('общий') : ''}<br>${pill(s.config_state === 'disabled' ? 'Отключён в манифесте' : 'В манифесте', s.config_state === 'disabled' ? 'warn' : '')}</td><td>${s.local ? 'Записан' : 'Не назначен'}</td><td>${s.laptop ? 'Записан' : 'Не назначен'}</td><td>${s.codex ? 'Есть настройки' : 'Нет настроек'}</td><td>${esc(s.execution_host)}</td><td style="color:var(--muted);font-size:12px">${esc(s.status_note)}<details><summary>Назначение</summary>${esc(s.about)}</details></td></tr>`).join('');
  return `${renderProjectSessions(d.projects)}<div class="kpis"><div class="kpi"><span>Сессии сейчас</span><b>${sessions.length}</b>${esc((d.live_kinds || []).join(', ') || 'нет')}</div>
    <div class="kpi"><span>Занятые карточки NameNode</span><b>${claims.total ?? '—'}</b>${(claims.agents || []).length} агент(ов)</div>
    <div class="kpi"><span>Почта агентам</span><b>${(inbox['claude:*']?.count ?? 0) + (inbox['codex:*']?.count ?? 0)}</b>claude:* + codex:*</div>
    <div class="kpi"><span>Потоки Codex</span><b>${codex.ok ? (codex.threads || []).length : '—'}</b>${codex.ok ? 'Codex Hub на связи' : pill('Codex Hub не отвечает', 'warn')}</div></div>
    <h2 style="margin-top:0">Рабочие сессии</h2>${table(sessions, 'Сейчас нет открытых сессий Claude или Codex.', true)}
    <h2>Кто что держит в NameNode</h2>${claimRows ? `<div class="table-wrap"><table><thead><tr><th>Агент</th><th>Карточки</th></tr></thead><tbody>${claimRows}</tbody></table></div>` : `<p class="note">${esc(claims.error || 'Ничего не занято.')}</p>`}
    <div class="grid" style="margin-top:18px"><div class="card"><h3>Почта NameNode</h3>${inboxRows || `<p class="note">${esc(inbox.error || 'Пусто')}</p>`}<p class="note">Своя почта: <code>namenode inbox agent=claude:&lt;сессия&gt;</code>.</p></div>
    <div class="card"><h3>Приложения и службы</h3>${table(services, 'Нет запущенных приложений агентов.', false)}</div></div>
    <h2>Последние потоки Codex</h2>${codexRows ? `<div class="table-wrap"><table><thead><tr><th>Поток</th><th>Папка</th><th>Источник</th><th class="num">Обновлён</th></tr></thead><tbody>${codexRows}</tbody></table></div>` : `<p class="note">${esc(codex.error || 'Потоков нет')}</p>`}
    <h2>Настройки MCP <small class="note">agents/manifest.json v${esc(mcp.version)} · ${mcp.skills ?? 0} общих skills · ${mcp.projects ?? 0} проектов</small></h2>
    <p class="note">Это назначение подключений агентам, а наличие программ на локальном узле показано в «Инструментах». Запись для ноутбука может быть клиентом серверного инструмента. «Не назначен» не означает «программа не установлена». Живые подключения здесь не проверяются; ноутбук не опрашивается.</p>
    <div class="table-wrap"><table><thead><tr><th>Сервер / конфигурация</th><th>Агенты Пушкины</th><th>Агенты ноутбука</th><th>Настройки Codex</th><th>Где исполняется</th><th>Проверка / назначение</th></tr></thead><tbody>${mcpRows || `<tr><td colspan="6" class="note">${esc(mcp.error || 'манифест не прочитан')}</td></tr>`}</tbody></table></div>
    <p class="note">Новая сессия: меню «Пуск» → Studio → «Claude - Music», «Codex - Video - Local node»… или с телефона в Happy: «+» → Local node → папка пайплайна.</p>`;
}

export function initOps(refresh) {
  initDownloadPicker();
  reload = refresh;
  document.addEventListener('submit', async (e) => {
    const f = e.target;
    if (f.id !== 'dl-hf' && f.id !== 'dl-url') return;
    e.preventDefault();
    const btn = f.querySelector('[type=submit]'); const msg = f.querySelector('.form-msg');
    btn.disabled = true; msg.classList.remove('err'); msg.textContent = '…';
    try {
      const data = Object.fromEntries(new FormData(f));
      let r;
      if (f.id === 'dl-hf') {
        const files = String(data.files || '').split('\n').map((s) => s.trim()).filter(Boolean);
        r = await request('/api/downloads/add-hf', { repo: data.repo, revision: data.revision || 'main', files: files.length ? files : null, dest: data.dest || '', group: data.group || '', flat: !!data.flat, note: data.note || '' });
      } else {
        r = await request('/api/downloads/add-url', { url: data.url, target: data.target, group: data.group || '', sha256: data.sha256 || '', note: data.note || '' });
      }
      msg.textContent = `Добавлено: ${r.added ?? (r.ids || []).length}`; clearDownloadDraft(f); f.reset();
      setTimeout(reload, 800);
    } catch (err) { msg.textContent = err.message; msg.classList.add('err'); }
    finally { btn.disabled = false; }
  });
  document.addEventListener('click', async (e) => {
    const b = e.target.closest('button'); if (!b) return;
    if (b.dataset.dlTab) { dlFilter = b.dataset.dlTab; dlLimit = DL_PAGE; reload(); return; }
    if (b.hasAttribute('data-dl-more')) { dlLimit += DL_PAGE; reload(); return; }
    const ids = b.dataset.dlRetry ? [b.dataset.dlRetry] : b.dataset.dlRetryAll ? b.dataset.dlRetryAll.split(',') : b.dataset.dlCancel ? [b.dataset.dlCancel] : null;
    if (!ids) return;
    b.disabled = true;
    try { await request(b.dataset.dlCancel ? '/api/downloads/cancel' : '/api/downloads/retry', { ids }); reload(); }
    catch (err) { b.textContent = err.message.slice(0, 60); }
  });
}
