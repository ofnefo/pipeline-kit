# Production modules

Run commands from the distribution root using the Python environment in README.md. Outputs belong to your workspace. Nothing in these modules is launched by importing Control.

| Module | Retained implementation | Additional requirements |
| --- | --- | --- |
| Office | Project templates and registers, Decimal estimate calculations, intake inventory and extraction, estimate/document consistency checks, proposal draft DOCX, transport-document helpers | `requirements-office.txt`; optional PDF extraction uses `requirements-pdf.txt`; PDF rendering uses LibreOffice |
| Design | Layer compositor, asset inspection, contact sheets, physical print size/PPI preflight | Pillow in base environment |
| Video | CPU editorial revisions, CFR cuts, timeline interchange, montage/captions/mixing/loudness; Control timeline, source review and annotations | FFmpeg + ffprobe on PATH; timeline interchange additionally `requirements-editorial.txt` |
| Music | Two-pass loudness/true-peak mastering, Russian lyric timing and pronunciation preflight | FFmpeg + ffprobe for audio; text tools use stdlib |
| Web | Offline HTML evidence and UTM construction | stdlib; does not crawl or deploy |

## Office

```sh
python -m pip install -r requirements-office.txt
python modules/office/scripts/office_project.py init --workspace workspace/office --code sample --name "Sample project"
python modules/office/scripts/estimate_engine.py calculate examples/estimate.json --as-of 2026-01-01 --output workspace/estimate-result.json
python modules/office/scripts/office_project.py list --start workspace/office
```

The estimate example costs 600.00; after the explicitly supplied tax, payroll and bonus rates, net profit is 198.00. Rates are inputs, not jurisdiction defaults. `office_project.py doctor --project <created-project> --json` validates the project; a newly initialized project deliberately reports missing production/approval data. Its exit status must not be rewritten as PASS. Use `--help` on `document_inventory.py`, `extract_source.py`, `prepare_proposal.py` and `ttn.py` for their exact inputs. Normcontrol and spreadsheet checks are library helpers called by the project doctor. Proposal creation requires explicit commercial context and writes a draft, not an approved deliverable. Spreadsheet inputs still need a separately selected workbook authoring/recalculation tool. Transport-document templates are source snapshots; configure the required form and facts for your project.

Office workspaces retain their own `OFFICE_WORKSPACE.json` / `OFFICE_PROJECT.json` structure. They can live below the Control workspace; Control's generic New project dialog does not initialize an Office project. Delivery is local-only; no messaging outbox ships with the kit.

## Graphics

```sh
python modules/design/scripts/compose_layers.py --spec examples/composition.json --output workspace/composition.png --proof workspace/composition-proof.png
python modules/design/scripts/preflight_print.py --help
python modules/design/scripts/make_contact_sheet.py --help
```

The sample produces 640×360 RGBA pixels and refuses an existing output unless `--overwrite` is explicit. Text layers require a chosen font path in the spec. Record physical dimensions, target PPI, bleed and colour requirements before print preflight; the tool cannot approve appearance or infer a print vendor's requirements.

## Video and audio

Install FFmpeg and ffprobe yourself and put both on PATH. Run `python pipeline_kit.py doctor` to inspect availability. Set `PIPELINE_KIT_WORKSPACE` consistently for standalone production commands and Control. Create a lowercase video project slug in Control, then use Studio → Montage to review local media, save annotations and edit the timeline. Render/export requires FFmpeg. Source media stay in the project; results get new paths.

```sh
python modules/video/scripts/editorial.py --help
python modules/video/scripts/montage.py --help
python modules/music/scripts/master_audio.py --help
python modules/music/scripts/lyric_preflight.py --help
python modules/music/scripts/ru_pronunciation.py --help
```

Each video subcommand has its own `--help` and accepts a named project in `workspace/projects/video`. For two-pass mastering pass an explicit input/output and a profile shown by `--help`; inspect the JSON before/after measurements and listen to the actual output. The bundled text preflight finds timing/phonetic evidence; it does not synthesize speech or judge a performance.

Neural generation, weights, ComfyUI workflows, OpenMontage, FilmCraft, EffectCraft, Adobe bridges and GPU workers are not bundled. Existing UI task handoffs remain ordinary board tasks and do not run external workers. Capability errors are explicit. Install any upstream integration separately, review its licence, resource use and path adapter, then implement and test the adapter before enabling it.

## Offline web evidence

```sh
python modules/web/scripts/seo_growth.py --help
```

Audit saved HTML rather than a live client site. Findings concern the supplied HTML only; they do not establish indexing, rankings, accessibility or live performance.

## Optional dependencies

`requirements-office.txt`, `requirements-pdf.txt` and `requirements-editorial.txt` pin separate Python additions. External executables are operator-installed and versioned in your own environment receipt. No third-party applications, SDK trees, model weights, client sites or private products ship here. See `config/optional-components.json` for upstream links and `THIRD_PARTY_NOTICES.md` for included browser libraries and fonts.
