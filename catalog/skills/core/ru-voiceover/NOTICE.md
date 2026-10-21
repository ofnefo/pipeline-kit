# NOTICE — ru-voiceover

The skill text is original work written in Russian. No code, scripts or text fragments from the
repositories below were copied; only ideas and observations were taken and retold in our own words.

| Source | Commit | Licence | How it was used |
|---|---|---|---|
| github.com/howdeploy/kisa-stack, skill `elevenlabs-living-voice` | 25744fa0afe9a0028e45123451b15fac36c04596 | MIT, Copyright (c) 2026 howdeploy (KISA) | Ideas: one phrase per breath, key word at the end, punctuation as breathing, "text first, settings second", freezing a successful configuration. ElevenLabs cloud tags were not carried over. |
| github.com/anatolix/narrator, skills `russian-stress-corrections`, `stress-audit`, `ruaccent-stress-resolve` | 73e964ea12ee2773ff5ea308fe6df3ba0f315b6c | No licence file (all rights reserved by default) | Ideas only and general facts about Russian: search all word forms, fix by meaning, decision log with revocations, years and fractions as words, comparing takes by md5. No text or scripts used. |
| github.com/drakulavich/kesha-voice-kit, `docs/tts.md` | ceeabdd92db0ab40e88465173c5dbff392446092 | MIT | Observations on Russian TTS: digits may silently disappear; an abbreviation is read as a word if it can be pronounced by syllables. The kit itself was not installed. |
| github.com/Den4ikAI/ruaccent | 3ac0ad5f6508f6c1a4a604220042232c70a7baf9 | LICENSE: MIT (Copyright 2026 Denis Petrov); `setup.py` states Apache-2.0 — mismatch | Compatibility of the `+` stress notation with `custom_dict`. The tool was not installed or run (it downloads models; model licences not checked). |

Engine facts (segment formats, QA approach, tokenizer behaviour of Qwen3-TTS and XTTS-v2 for ё, `+`
and U+0301) come from the authors' own local tests. XTTS-v2 is distributed under the non-commercial
CPML licence, so the skill restricts it to drafts.

Changes for the public kit: private tooling, host names, paths and delivery steps were replaced by
generic descriptions (a local TTS engine, a local STT model, the project's delivery channel).
