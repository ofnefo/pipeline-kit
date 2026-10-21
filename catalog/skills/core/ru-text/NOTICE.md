# NOTICE — ru-text

`SKILL.md` and `references/*.md` are original work: the ideas, rule structure and pattern lists come from the
sources below, but the wording and all examples were written anew. The vendored code in `scripts/` is unchanged.

Sources were checked at the commits listed below (2026-10-04).

## Vendored code (scripts/)

### milchin.py — typographer
- Source: https://github.com/beaverbeard/milchin, commit 09e3768473936f6057060df74c3db03f7b324ce2
- Licence: MIT, Copyright (c) 2026 Rodion Scryabin (beaverbeard). Full text: `scripts/LICENSE-milchin.txt`.
- Unchanged. Python standard library only, no network access.

### humanizer_ru/ — slop and bureaucratese linter
- Source: https://github.com/comol/Humanizer_RU, commit 19186272a14488843d6d9a02115ced557957ed59
- Licence: MIT, Copyright (c) 2026 comol. Full text: `scripts/LICENSE-humanizer-ru.txt`.
- Third-party notices (smixs, Vladimir-Human, ilyautov — humanizer-ru, MIT; chukovsky):
  `scripts/THIRD_PARTY_NOTICES-humanizer-ru.md`.
- Unchanged. The linter's term profile is upstream's IT/1C profile; outside that domain, ignore its 1C-term findings.
  The upstream network install via `uvx` is not used; optional `pymorphy3` improves morphology.

## Material the references are based on

### redaktura-skills — CC BY 4.0
- Source: https://github.com/N1arko/redaktura-skills, commit d1ebaff4fb8b97f939826a1cac284c10303be6f1
- Authors: © 2026 Людмила Сарычева (Lyudmila Sarycheva), Никита Архипов (Nikita Arkhipov) — https://gladlax.ru
- Licence: Creative Commons Attribution 4.0 International, https://creativecommons.org/licenses/by/4.0/
- **Changes made:** ideas and working order from the redaktura, statya, post, ux-copy and redpolitika skills
  (editing passes, article brief, the "competitor" test, signs of machine text, UX-writing principles) were used;
  the text was rewritten and shortened and the examples replaced. The promo skill served only as a guide for `ru-promo`.
- The original authors did not take part in this adaptation and do not endorse it.

### talkstream/ru-text — MIT
- Source: https://github.com/talkstream/ru-text, commit c5d2ee5e6f64d7f59a6783b32a6afc54201ccc6e
- Copyright (c) 2026 Arseniy Kamyshev. Licence: MIT.
- Used: typography rules, common grammar errors, info-style, business correspondence, UX text.
  Rewritten; the repository's code, hooks and scripts are not used.

### Humanizer_RU — MIT
- See above. Besides the code, ideas used: careful/deep/audit modes, the treatment hierarchy, the false-positive list,
  the pattern catalogue. Examples replaced.

### slopotron — MIT
- Source: https://github.com/beaverbeard/slopotron, commit 122d38545c7e415844e9cf39dc4350455ad8cf18
- Copyright (c) 2026 Rodion Scryabin. Licence: MIT.
- Used: the frequency approach (clusters, not single words), the structural slop layer, the "do not flag" list.

### chukovsky — MIT
- Source: https://github.com/beaverbeard/chukovsky, commit 26d55599a11798d57788d0f15974127d1bc34733
- Licence: MIT. Used: editing order, severity scale for findings.

### yandex-tone-of-voice-skill — MIT
- Source: https://github.com/Dankosik/yandex-tone-of-voice-skill, commit c7bce1a1922f5c7885db02d6917d42a21f6b294e
- Copyright (c) 2026 Dankosik. Licence: MIT.
- **An independent reconstruction from public texts, not an official Yandex guide, and not endorsed by Yandex.**
  "Яндекс"/"Yandex" is a trademark of its owner. Used: the ideas of tone registers and the "responsible topics" layer.

### nora-gal — no licence stated
- Source: https://github.com/Halfofthesky/nora-gal, commit 74a5be1a522b41f11c44108e8ce3de1df4eec411
- The repository has no LICENSE file; it draws on Нора Галь (Nora Gal), «Слово живое и мёртвое», a copyrighted book.
  Ideas only, rewritten (signs of bureaucratese, types of calques); no text or examples from the book or the repository were copied.

## MIT licence text (for the MIT sources above)

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
documentation files (the "Software"), to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of
the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
