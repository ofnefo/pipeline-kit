# NOTICE - neural-video

Authored skill. No third-party text or code is copied verbatim. The references below were written in our own words;
the following projects were idea sources and are credited here.

| Upstream | URL | Commit consulted | Licence | Used for | Changes made |
|---|---|---|---|---|---|
| DirectorSKILL (wangzhang-wu) | https://github.com/wuwangzhang1216/DirectorSKILL | c65ae0d14457053efb1e354c7e7f7e120d97fad1 | MIT | prompt shapes, motion budget, failure codes, cost ladder, triage | paraphrased, adapted to local open models, cloud syntax removed |
| visual-skills (Serge Shima) | https://github.com/smixs/visual-skills | 92be33a5a73325fb3d8e0c73b22744b114e2a90e | CC BY 4.0 | universal prompt rules, fixes and skeletons | paraphrased, restructured |
| director-skills (0xhughs) | https://github.com/0xhughs/director-skills | 35ca0a2b4cd55b0668aa9ea0f40273324b774bb4 | MIT | prompt components, negative patterns, iteration and diagnostics | paraphrased |
| jacob-ye-seedance-prompt (Jacob Ye) | https://github.com/jacobye2017-afk/jacob-ye-seedance-prompt | 2e6435b4169a06737a2a220bb4e5c31d834fdf57 | CC BY 4.0 | repair and QC notes, prompt order | paraphrased, model-specific syntax removed |
| fal-ai-community/skills | https://github.com/fal-ai-community/skills | 9ca850412943251fc9a466c4c29fdaf7a303a3d8 | MIT | subject-camera-light ordering idea | paraphrased |
| Wan2.2 (Wan-Video) | https://github.com/Wan-Video/Wan2.2 | not pinned | Apache-2.0 | README model facts, prompt-rewriter rules in `wan/utils/system_prompt.py` | paraphrased |

CC BY 4.0 attribution: ideas from smixs/visual-skills and jacob-ye-seedance-prompt are adapted (not copied) in
`references/prompt-structure.md` and `references/failure-diagnosis.md`; licence text:
https://creativecommons.org/licenses/by/4.0/.
