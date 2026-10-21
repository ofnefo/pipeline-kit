# Document register

Required columns:

| Column | Meaning |
| --- | --- |
| `document_id` | Stable project-local identifier |
| `type` | proposal, contract, appendix, invoice, act, letter, report, tender, other |
| `title` | Human-readable title |
| `counterparty` | Party or recipient; blank until known |
| `estimate_version` | Approved estimate version supporting amounts/scope |
| `owner` | Person responsible for the next action |
| `status` | planned, drafting, review, approved, issued, superseded, archived |
| `native_file` | Relative DOCX/XLSX/PPTX path |
| `pdf_file` | Relative PDF path when required |
| `approval` | missing, internal, client, legal, signed as applicable |
| `delivery_target` | Destination only after it is known and authorized |
| `source_refs` | Brief/source clause/register references |
| `notes` | Gaps, exceptions and next action |

Statuses describe facts, not intent. Creating a PDF does not make a document approved or issued. A changed approved document gets a new version; the prior row/file remains traceable as superseded.
