// Only connected enhancement forms are offered. Opening a form never runs a job.
const OPTIONS = [
  ['video_rife', 'Плавность', 'RIFE · промежуточные кадры'],
  ['video_esrgan', 'Размер ×2', 'Real-ESRGAN · ширина и высота'],
  ['seedvr2_upscale_video', 'Детализация', 'SeedVR2 · восстановление деталей'],
];
export function videoOutputs(run) {
  return (run.outputs || []).filter(o => o.path && /\.(mp4|webm|mov|mkv)$/i.test(o.path));
}
export function enhancementOptions(cat) {
  const items = (cat?.groups || []).flatMap(g => g.items || []);
  return OPTIONS.flatMap(([id, label, description]) => {
    const model = items.find(it => it.id === id && it.group === 'video');
    const input = model?.fields?.find(f => f.kind === 'upload' && ['source', 'input_video'].includes(f.name) && f.accept === 'video/*');
    return input ? [{ id, label, description, model, input }] : [];
  });
}
export function enhancementBlock(run, cat, esc, selectedPath) {
  const outputs = videoOutputs(run);
  if (run.status === 'running' || !outputs.length) return '';
  const choices = enhancementOptions(cat);
  return `<details class="run-enhance"><summary>Улучшить видео</summary>
    <label class="field">Исходный ролик<select data-enhance-source data-source-run="${esc(run.id)}" aria-label="Исходный ролик">${outputs.map((o, i) => `<option value="${i}"${o.path === selectedPath ? ' selected' : ''}>${esc(o.name || o.path.split(/[\\/]/).pop())}</option>`).join('')}</select></label>
    ${choices.length ? `<div class="run-actions">${choices.map(c => `<button type="button" class="ghost small" data-enhance="${c.id}" data-source-run="${esc(run.id)}" title="${esc(c.description)}">${esc(c.label)} · ${esc(c.description.split(' · ')[0])}</button>`).join('')}</div><small>Выберите улучшение, проверьте настройки и запустите обработку в форме. Исходник сохранится.</small>` : '<p class="note">Обработка видео сейчас не подключена. Обновите каталог и попробуйте ещё раз.</p>'}
  </details>`;
}
