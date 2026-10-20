// Shared tag palette (PLAN.md §2). Colours live only in style.css tokens; JS picks a class.
const STATUS = { verified: 'ok', downloaded: 'warn', unverified: 'warn', broken: 'bad', cloud: 'cloud', paid: 'cloud', archive: 'archive' };
const TYPE = { video: 'video', image: 'image', audio: 'audio', music: 'audio', voice: 'audio', '3d': 'td', text: 'text', llm: 'text' };
const ROLE = { primary: 'role-primary', aux: 'role-aux', reference: 'role-ref' };
const MAPS = { status: STATUS, type: TYPE, role: ROLE };
const esc = (v) => String(v ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

export function tagClass(kind, value) {
  const v = MAPS[kind]?.[String(value || '').toLowerCase()];
  return v ? `tag tag-${v}` : 'tag';
}
export const tag = (kind, value, text = value) => `<span class="${tagClass(kind, value)}">${esc(text)}</span>`;
