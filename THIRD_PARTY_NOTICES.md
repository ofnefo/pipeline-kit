# Included third-party components

| Component | Location | Licence / provenance |
| --- | --- | --- |
| htm 3.1.1 | `apps/control_panel/static/vendor/htm-3.1.1` | Apache-2.0, included `LICENSE`; unmodified standalone ESM bundle, upstream URL and hash in `SOURCE.json` |
| Preact and hooks in the htm standalone bundle | same directory | MIT, included `LICENSE-PREACT`; upstream https://github.com/preactjs/preact |
| Three.js r186 subset | `apps/control_panel/static/vendor/three-r186` | MIT, included `LICENSE`; upstream commit, per-file hashes and relative-import modifications recorded in `SOURCE.json` |
| Onest variable font | `apps/control_panel/static/fonts/onest-var.woff2` | SIL OFL 1.1, included `OFL-Onest.txt`; https://github.com/googlefonts/onest |
| JetBrains Mono variable font | `apps/control_panel/static/fonts/jbmono-var.woff2` | SIL OFL 1.1, included `OFL-JetBrainsMono.txt`; https://github.com/JetBrains/JetBrainsMono |

`modules/office/scripts/spreadsheet_findings.py` acknowledges the audit-xls checklist from anthropics/financial-services (Apache-2.0) as a methodological reference. The toolkit retains that attribution; no financial-services plugin tree is bundled. The Apache-2.0 text is included with htm above.

Python packages are installed separately from pinned requirements and retain their upstream licences. Optional external programs, models, SDKs and plugins are referenced, not redistributed. No licence for one component grants rights to another. Owned-source provenance is in `provenance.json`; no explicit licence is granted for the original source. Publication does not grant a licence to reuse that source. The bundled third-party components retain their respective licences above.
