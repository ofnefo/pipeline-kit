# Cloud video (paid, opt-in per job)

Policy: local-first. Cloud video is never a default, draft or fallback route. Use it only when the operator asked for
cloud for **this job**; quote that request in the receipt. Each job needs a cost estimate first, the operator's OK on
the estimate, and a receipt.

## Rules

- API tokens live only in the operator's environment (e.g. `REPLICATE_API_TOKEN`), never in files, arguments,
  receipts or chat.
- Estimate from the provider's published price for the model, mode, duration and resolution. Refuse to run without an
  explicit confirm or a max-cost guard; refuse if the guard is below the estimate.
- Write a `receipt.json` per job: provider, model, params, reference hashes, task id, estimate, provider-reported usage,
  timings, output path + hash. No automatic retries; a moderation refusal is a failed task.
- Video-reference inputs are usually billed at video-input rates.

## Facts from Replicate's public docs

- Prediction statuses: starting, processing, succeeded, failed, canceled, aborted. Predictions time out after 30 min.
- API prediction inputs, outputs, file URLs and logs are kept about **1 hour** by default: download outputs
  immediately; a resume/poll helper only helps inside that window.
- Aborted predictions are not billed; canceled ones are billed for the run time so far.
- Replicate publishes an MCP server and agent skills (find/compare/run models, prompting guides). Video prompt
  structure there (scene, subject, action, camera, light, audio/dialogue, time-coded shots, style) matches
  [prompt-structure.md](prompt-structure.md).

## Hybrid use

Plan cloud per segment, not per film: a cloud first/last-frame bridge or v2v for one weak transition, then local
continuation and the normal seam checks in [segment-repair.md](segment-repair.md). Compare the actual seams, not the
provider's showcase. A new model needs its own adapter mapping and a pilot before it is called supported.
