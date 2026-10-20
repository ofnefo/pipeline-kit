const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const labels = {running:'Работает сейчас', idle:'Ожидает следующей задачи', not_loaded:'Не запущена', not_found:'Не запущена', error:'Ошибка сессии', unknown:'Не удалось проверить'};
export function renderProjectSessions(data) {
  if (!data) return '<p class="note" role="status">Список проектных сессий пока недоступен. Обновите страницу после подключения сервиса.</p>';
  if (data.error) return `<p class="err" role="alert">${esc(data.error)}</p>`;
  const rows = data.rows || [];
  const active = rows.filter(r => !stoppedStates.includes(r.state)), stopped = rows.filter(r => stoppedStates.includes(r.state));
  return `<section aria-label="Проектные сессии"><h2>Проектные сессии</h2>
    <p class="note">Проверено ${esc(new Date(data.checked_at * 1000).toLocaleTimeString('ru-RU'))}. Фоновый Claude Code работает отдельно от вкладок Claude Desktop. Новые задачи в Desktop ведёт claude:wave-coordinator.</p>
    ${rows.length ? `${active.length ? active.map(row).join('') : '<p class="note">Сейчас ни одна не запущена.</p>'}${stopped.length ? `<details class="proj-section"><summary>Не запущены · ${stopped.length}</summary>${stopped.map(row).join('')}</details>` : ''}` : '<p class="note">Проектные сессии ещё не зарегистрированы.</p>'}</section>`;
}
const stoppedStates = ['not_loaded', 'not_found'];
const row = r => `<details class="proj-section"><summary style="overflow-wrap:anywhere">${esc(r.title || r.key)} · <span class="pill ${r.state === 'running' ? 'ok' : ''}">${esc(labels[r.state] || labels.unknown)}</span></summary>
    <p class="note" style="overflow-wrap:anywhere">${esc(r.owner)} · ${r.engine === 'claude' ? 'Claude Code · фоновый CLI' : 'Codex · проектная сессия'}</p>
    <p class="note" style="overflow-wrap:anywhere">Карточка: ${esc(r.card || 'не назначена')}<br>Сессия: ${esc(r.thread_id || r.session_id)}</p>
    <p class="note">${r.engine === 'claude' ? 'Статус подтверждает процесс, а не завершение задачи.' : 'Статус получен из текущего состояния сессии Codex.'} ${['unknown','error','not_found'].includes(r.state) ? 'Обновите страницу. Если статус не изменится, передайте владельцу имя сессии для проверки.' : 'Результат и приёмку смотрите в карточке проекта.'}</p></details>`;
