// Настройки › Ключи (3.0): which access keys are connected and who uses them. Values are never shown or kept by the panel.
const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const pill = (text, state = '') => `<span class="pill ${state}">${esc(text)}</span>`;
const line = (k, v) => (v ? `<p><span>${esc(k)}</span> ${esc(v)}</p>` : '');
const SAVED = 'Ключ сохранён. Программы увидят его после перезапуска; иногда нужно выйти из Windows и войти снова.';

export async function loadKeys() {
  try {
    const r = await fetch('/api/keys', { cache: 'no-store' });
    return r.ok ? await r.json() : { error: true };
  } catch {
    return { error: true };
  }
}

function keyRow(k) {
  const where = k.where?.length ? k.where.join(', ') : 'нигде не задан';
  const users = k.used_by?.length ? k.used_by.join(', ') : '';
  const sub = [k.kind === 'env' ? `<code>${esc(k.name)}</code>` : '', esc(k.detail || (k.kind === 'file' ? k.name : ''))].filter(Boolean).join(' · ');
  const state = k.set ? pill(k.kind === 'file' ? 'есть' : 'подключён', 'ok') : pill(k.kind === 'file' ? 'нет' : 'не задан', 'warn');
  const action = k.kind !== 'env' ? '' : !k.set && k.replaceable
    ? `<button type="button" class="secondary" data-keys-add="${esc(k.name)}">Добавить</button>`
    : k.set && k.replaceable
      ?`<button type="button" class="secondary" data-keys-add="${esc(k.name)}" data-keys-replace>Заменить</button>` : '';
  const more = line('Для чего:', k.purpose) + line('Где лежит:', where) + line('Кто использует:', users);
  return `<div class="inv-row keys-row${k.set ? '' : ' keys-missing'}"><div class="inv-main"><b>${esc(k.title)}</b>${sub ? `<small>${sub}</small>` : ''}</div>
    <div class="keys-act">${state}${action}</div>${more ? `<details class="inv-more"><summary>Подробнее</summary><div>${more}</div></details>` : ''}</div>`;
}

function mcpBlock(list) {
  const byName = new Map();
  for (const s of list || []) {
    const cur = byName.get(s.name) || { where: new Set(), keys: new Set() };
    cur.where.add(s.where); (s.keys || []).forEach((k) => cur.keys.add(k));
    byName.set(s.name, cur);
  }
  if (!byName.size) return '';
  const rows = [...byName].sort(([a], [b]) => a.localeCompare(b)).map(([name, s]) => `<div class="inv-row"><div class="inv-main"><b>${esc(name)}</b><small>${esc([...s.where].join(' · '))}</small></div>${s.keys.size ? `<span class="keys-names">${[...s.keys].map((k) => `<code>${esc(k)}</code>`).join(' ')}</span>` : pill('без ключа')}</div>`).join('');
  const withKeys = [...byName.values()].filter((s) => s.keys.size).length;
  return `<details class="inv-group"><summary><b>MCP-серверы</b><span class="count">${byName.size}</span></summary>
    <p class="keys-note">${withKeys ? `Ключ нужен ${withKeys} из ${byName.size}; эти ключи есть в списке выше.` : 'Ни одному серверу не нужен отдельный ключ.'} Настройки серверов здесь только показываются.</p>
    <div class="inv-rows">${rows}</div></details>`;
}

function form() {
  return `<form class="keys-form" data-keys-form hidden novalidate>
    <label>Имя ключа<input name="name" autocomplete="off" autocapitalize="characters" spellcheck="false" maxlength="64" placeholder="OPENAI_API_KEY" required></label>
    <label>Значение<input name="value" type="password" autocomplete="new-password" spellcheck="false" maxlength="8192" required></label>
    <label>Название <small>необязательно</small><input name="title" autocomplete="off" maxlength="80" placeholder="OpenAI"></label>
    <label>Для чего <small>необязательно</small><input name="purpose" autocomplete="off" maxlength="200" placeholder="Генерация текста в студии"></label>
    <p class="keys-hint">Значение уйдёт в переменные Windows на Пушкиной. Панель его не сохраняет и больше не покажет.</p>
    <p class="keys-error" role="alert" hidden></p>
    <div class="keys-form-act"><button type="submit">Сохранить</button><button type="button" class="secondary" data-keys-cancel>Отмена</button></div>
  </form>`;
}

export function renderKeys(d) {
  const head = `<div class="keys-head"><div><h3>Ключи и доступы</h3><p>Здесь видно, какие ключи подключены и кто ими пользуется. Сами значения панель не показывает и не хранит.</p></div>`;
  if (!d || d.error || !Array.isArray(d.keys)) {
    return `<div class="card keys" data-disclosure-skip data-keys>${head}</div><p class="keys-note" role="status">Не удалось проверить ключи. Обновите страницу чуть позже.</p></div>`;
  }
  const env = d.keys.filter((k) => k.kind === 'env').sort((a, b) => (b.set - a.set) || a.title.localeCompare(b.title, 'ru'));
  const files = d.keys.filter((k) => k.kind === 'file');
  const on = d.keys.filter((k) => k.set).length;
  const checked = d.checked_at ? new Date(d.checked_at * 1000).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' }) : '';
  return `<div class="card keys" data-disclosure-skip data-keys>${head}<button type="button" data-keys-add>Добавить ключ</button></div>
    <p class="keys-sum"><span><i class="dot-ok"></i>Подключено ${on}</span><span><i class="dot-warn"></i>Не задано ${d.keys.length - on}</span>${checked ? `<span class="keys-time">проверено в ${esc(checked)}</span>` : ''}</p>
    <p class="keys-flash" role="status" aria-live="polite"></p>
    ${form()}
    <h4 class="keys-h">API-ключи</h4><div class="inv-rows">${env.map(keyRow).join('')}</div>
    <h4 class="keys-h">Входы и файлы доступа</h4><div class="inv-rows">${files.map(keyRow).join('')}</div>
    ${mcpBlock(d.mcp)}</div>`;
}

export function mountKeys(view) {
  let busy = false;
  const card = () => view.querySelector('[data-keys]');
  const parts = () => { const f = card()?.querySelector('[data-keys-form]'); return f && { f, err: f.querySelector('.keys-error'), submit: f.querySelector('[type=submit]') }; };
  const close = () => { const p = parts(); if (!p) return; p.f.reset(); p.f.hidden = true; delete p.f.dataset.replace; p.err.hidden = true; p.f.elements.name.readOnly = false; };
  const open = (name = '', replace = false) => {
    const p = parts(); if (!p) return;
    close(); p.f.hidden = false;
    p.f.elements.name.value = name; p.f.elements.name.readOnly = Boolean(name);
    if (replace) p.f.dataset.replace = '1';
    p.submit.textContent = replace ? 'Заменить' : 'Сохранить';
    card().querySelector('.keys-flash').textContent = '';
    (name ? p.f.elements.value : p.f.elements.name).focus();
  };
  const click = (e) => {
    const add = e.target.closest('[data-keys-add]');
    if (add) {
      const replace = add.hasAttribute('data-keys-replace');
      if (replace && !confirm(`Заменить значение ${add.dataset.keysAdd}? Старое значение будет перезаписано.`)) return;
      open(add.dataset.keysAdd, replace);
    } else if (e.target.closest('[data-keys-cancel]')) close();
  };
  const submit = async (e) => {
    const p = parts();
    if (!p || e.target !== p.f) return;
    e.preventDefault();
    if (busy) return;
    const el = p.f.elements;
    const body = { name: el.name.value.trim().toUpperCase(), value: el.value.value, title: el.title.value.trim(), purpose: el.purpose.value.trim(), replace: p.f.dataset.replace === '1' };
    const fail = (msg) => { p.err.textContent = msg; p.err.hidden = false; };
    if (!/^[A-Z][A-Z0-9_]{2,63}$/.test(body.name)) return fail('Имя: латинские заглавные буквы, цифры и «_», например OPENAI_API_KEY.');
    if (!body.value.trim()) return fail('Вставьте значение ключа.');
    busy = true; p.submit.disabled = true;
    try {
      const r = await fetch('/api/keys', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) {
        fail(typeof data.detail === 'string' ? data.detail : 'Не удалось сохранить ключ. Повторите попытку.');
        if (r.status === 409 && /Заменить/.test(data.detail || '')) { p.f.dataset.replace = '1'; p.submit.textContent = 'Заменить'; }
        return;
      }
      el.value.value = '';
      const fresh = await loadKeys();
      const node = card();
      // The key is already saved; if the re-check fails, keep the old list and still say so.
      if (node && !fresh.error) node.outerHTML = renderKeys(fresh); else close();
      const flash = card()?.querySelector('.keys-flash');
      if (flash) flash.textContent = SAVED;
      card()?.querySelector('[data-keys-add]')?.focus();
    } catch {
      fail('Нет связи с панелью. Повторите попытку.');
    } finally {
      busy = false;
      const q = parts(); if (q) q.submit.disabled = false;
    }
  };
  // A 409 can switch the form to "replace"; typing another name must not carry that consent over.
  const input = (e) => {
    const p = parts();
    if (!p || e.target !== p.f.elements.name || p.f.elements.name.readOnly) return;
    delete p.f.dataset.replace; p.submit.textContent = 'Сохранить';
  };
  view.addEventListener('click', click);
  view.addEventListener('submit', submit);
  view.addEventListener('input', input);
  return () => { view.removeEventListener('click', click); view.removeEventListener('submit', submit); view.removeEventListener('input', input); };
}
