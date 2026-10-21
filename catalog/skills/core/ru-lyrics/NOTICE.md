# NOTICE — ru-lyrics

The skill text is original work written in Russian: songwriting techniques were retold in our own
words and adapted to the Russian accentual-syllabic verse system. No code, song lines or text
fragments from the repositories below were copied.

| Source | Commit | Licence | How it was used |
|---|---|---|---|
| github.com/regiellis/suno-songwriter-agent-skill | 89c11de860e680ef35db584d3a5667b1438ea600 | MIT, Copyright (c) 2026 Regi Ellis | Ideas: workflow order, quality gates, section roles, "structure before lines", rule of three, anti-patterns. Suno fields and tags were not carried over: the generator here is a local ACE-Step. |
| github.com/jtydhr88/lyric-writing-skills (`lw-song-intent`, `lw-ai-tell-audit`, `lw-rap`) | 61c907495197f8fd041dbfc0849baa67da1368bc | MIT for its own structure, Copyright (c) 2026 Terry Jia; per the repository NOTICE, book quotations are not covered by the licence | Ideas: brief questions, "one thought in one sentence with a picture", artificiality tells and two separate scores, rhyme density vs intelligibility, an unrhymed key line. The source skills are in Chinese; Chinese phonetics and quotations were not used. The rule "always vary the chorus" was relaxed: repetition can be the core of a track. |
| github.com/vkdinnovation-code/VadimaraSonoMusic | ccc2f6b73b9303a42f200d55ada1b5d71579d634 | No separate licence file; the skill header states MIT | Ideas: three text layers, marks only at problem spots, mandatory ё, a risk table, dictionary edits as proposals, self-review roles, section energy. |
| github.com/mrrepac/russian-rhymes | 49d7e37df8414771340ce8f5e127772eac19b360 | Code MIT; dictionary layers: Koziev CC0, OpenRussian CC BY-SA 4.0, Wiktionary CC BY-SA 4.0, KartaSlov CC BY-NC-SA 4.0 (non-commercial), FreeDict CC BY-SA 3.0 | Ideas only, rewritten: a rhyme key built from the stressed tail with reduction and devoicing, and precision levels. No dictionaries or text were carried over; users may install the tool themselves. |

Facts about the ACE-Step 1.5 lyrics format, tags, modes and intelligibility come from the authors'
own local smoke tests with a ComfyUI-based setup. ACE-Step 1.5: code and weights under MIT.

Changes for the public kit: private render commands, scripts, project names, host names and paths
were removed; rendering is described only as parameters handed to whoever runs it.
