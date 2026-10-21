# NOTICE — ru-seo

Навык написан своими словами. Код и скрипты upstream не копировались и не запускались.
Источник проверен 2026-10-04.

## Horosheff/google-yandex-seo-skill — MIT
- URL: https://github.com/Horosheff/google-yandex-seo-skill
- Commit: bdd76f94eeae739ed105114117f350c7f9c41ecb
- Copyright (c) 2026 Ertugrul Akben (так указано в LICENSE репозитория)
- Использовано: перечень технических, on-page, Google-, Яндекс-, performance- и GEO-проверок,
  статусы PASS/WARN/FAIL/N/A, пороги веса HTML (> 2 МБ / > 10 МБ), ориентир длины title,
  порог доли кириллицы — пересказ в `SKILL.md`, `references/checklist.md`, `references/text-side.md`,
  `references/geo-ai.md`.
- Не использовано и не запускалось: `run-audit.js` (Node ESM; зависимости chalk, cheerio, dayjs,
  fast-xml-parser, fs-extra; требует npm install; делает HTTP-запросы к сайту и пишет файлы отчёта).

### Changes made
- Проверки пересказаны по-русски, сокращены, переупорядочены по приоритету «Яндекс → Google → GEO»
  и дополнены собственными правилами по умолчанию (диапазоны title/description, Clean-param, отказ
  от Host, OG 1200×630, политика ИИ-ботов, IndexNow, отказ от Турбо, проверки перед деплоем).

## Собственные материалы
- Правила по умолчанию и чек-лист перед деплоем — из собственной практики SEO-аудита
  русскоязычных сайтов (2026), не сторонний код.

---

## MIT License (текст для Horosheff/google-yandex-seo-skill)

Permission is hereby granted, free of charge, to any person obtaining a copy of this software
and associated documentation files (the "Software"), to deal in the Software without restriction,
including without limitation the rights to use, copy, modify, merge, publish, distribute,
sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or
substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT
NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT
OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
