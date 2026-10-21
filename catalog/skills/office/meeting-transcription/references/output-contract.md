# Meeting transcript output contract

## Versioned transcript package

Each run creates a new folder `<source>-transcript-vNNN/` (never overwrite an existing one):

| File | Content |
|---|---|
| `source.json` | source name, sha256, duration, runtime and model provenance |
| `meeting-16khz.wav` | duration-preserving working audio (excluded from the zip) |
| `transcript.raw.json` | verbatim recognised text, engine per window, word timestamps, resumable window checkpoints |
| `transcript.json` | speaker-labelled segments with uncertainty metadata |
| `transcript.md`, `transcript.txt` | readable derivatives |
| `transcript.srt` | subtitle cues derived from word timestamps |
| `result.json` | completion status and artifact paths |
| `meeting-transcript.zip` | text artifacts + provenance |

A reviewed, named version is another folder (e.g. `<source>-reviewed-v001/`) produced by applying a speaker map; the
unnamed package stays unchanged.

## Protocol draft package

`<source>-protocol-draft-vNNN/` next to the transcript:

- `protocol-draft.json` - summary, decisions, tasks (`task`, `owner`, `due`, `time`), open questions, per-item
  `flags` (`time-not-in-transcript`, `owner-not-in-transcript`), transcript sha256 and LLM call provenance
  (endpoint, model, chunk count).
- `protocol-draft.md` - readable draft for review.
- `actions.csv` - `;`-separated, UTF-8 with BOM (opens correctly in Excel), every row `status=draft`.

Suggested exit codes for a drafting script: `0` written, `1` LLM failure or unparseable answer (nothing written),
`2` bad input or non-local endpoint.

## Downstream documents

After review create separate artifacts (`protocol-v001.docx`, `decisions-v001.md`, `actions-v001.xlsx`). Every task,
amount, date or commitment points back to a transcript timestamp. External task creation, sending or publication
needs an explicit target and authorisation.
