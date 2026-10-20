// Keep secondary information available without filling every screen by default.
const prefix = 'pipeline.disclosure.v1:';
const saved = key => { try { return localStorage.getItem(prefix + key); } catch { return null; } };
const remember = (key, open) => { try { localStorage.setItem(prefix + key, String(open)); } catch {} };
const titleOf = el => {
  const copy = el.cloneNode(true);
  copy.querySelectorAll('small, .pill, .count, button').forEach(n => n.remove());
  return copy.textContent.trim().replace(/\s+/g, ' ').slice(0, 150);
};

function setCard(card, open) {
  card.classList.toggle('is-collapsed', !open);
  const button = card.querySelector(':scope > h3 > [data-disclosure-toggle]');
  button.setAttribute('aria-expanded', String(open));
  button.textContent = open ? '▾' : '▸';
  card.querySelector(':scope > .disclosure-body').hidden = !open;
}

export function applyDisclosure(view, route) {
  // Existing section headings delimit meaningful groups; keep their contents together.
  [...view.querySelectorAll(':scope > h2')].forEach((heading, i) => {
    if (heading.closest('[data-disclosure-skip]')) return;
    const section = document.createElement('details'); section.className = 'page-section';
    section.open = i === 0 && ['quick', 'domains', 'storage', 'downloads', 'sites'].includes(route);
    const summary = document.createElement('summary');
    heading.before(section); section.append(summary); summary.append(heading);
    while (section.nextSibling && section.nextSibling.nodeName !== 'H2') section.append(section.nextSibling);
  });
  let ordinal = 0;
  view.querySelectorAll('.card').forEach(card => {
    if (card.matches('a') || card.closest('dialog, details, [data-disclosure-skip]') || card.dataset.disclosureKey) return;
    const header = card.querySelector(':scope > h3');
    if (!header || card.children.length < 2) return;
    const key = route + ':card:' + titleOf(header), index = ordinal++;
    const body = document.createElement('div'); body.className = 'disclosure-body';
    body.id = 'disclosure-' + route + '-' + index;
    [...card.childNodes].filter(n => n !== header).forEach(n => body.append(n));
    card.append(body); card.dataset.disclosureKey = key;
    const button = document.createElement('button'); button.type = 'button';
    button.className = 'disclosure-toggle'; button.dataset.disclosureToggle = '';
    button.setAttribute('aria-label', 'Раскрыть или свернуть: ' + titleOf(header));
    button.setAttribute('aria-controls', body.id); header.prepend(button);
    // Primary work form remains reachable; secondary cards start compact.
    // data-disclosure-default lets a view decide (Health: open only when the card shows a problem).
    const preset = card.dataset.disclosureDefault;
    const stored = saved(key), open = stored === null ? preset ? preset === 'open' : index === 0 || card.matches('form') || !!body.querySelector('form, .models-form, #chat-form, .err, [role="alert"]') : stored === 'true';
    setCard(card, open);
  });
  view.querySelectorAll('details').forEach((detail, i) => {
    if (detail.dataset.disclosureKey || detail.closest('[data-disclosure-skip]')) return;
    const summary = detail.querySelector(':scope > summary'); if (!summary) return;
    const key = route + ':details:' + titleOf(summary).replace(/\d+/g, '#') + ':' + i;
    detail.dataset.disclosureKey = key;
    const stored = saved(key); if (stored !== null) detail.open = stored === 'true';
    detail.addEventListener('toggle', () => remember(key, detail.open));
  });
}

export function initDisclosure() {
  document.addEventListener('click', e => {
    const toggle = e.target.closest('[data-disclosure-toggle]');
    if (toggle) {
      const card = toggle.closest('[data-disclosure-key]'), open = toggle.getAttribute('aria-expanded') !== 'true';
      setCard(card, open); remember(card.dataset.disclosureKey, open);
    }
  });
}
