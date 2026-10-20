#!/usr/bin/env python3
"""Initialize, resolve and diagnose Office Pipeline workspaces."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import os
import re
import shutil
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import project_checks as quality

PROJECT_FILE = "OFFICE_PROJECT.json"
PROJECTS_DIR = "ПРОЕКТЫ"
PIPELINE_DIR = "ПАЙПЛАЙН"  # legacy workspace layout
SCHEMA_DIR = Path("docs") / "schema"  # skeleton layout (restructure 2026-10-05): ПАЙПЛАЙН/schemas -> docs/schema
TEMPLATE_NAME = "ШАБЛОН_ПРОЕКТА"
TEMPLATES_DIR = "templates"
PROJECTS_ROOT_ENV = "OFFICE_PROJECTS_ROOT"
ROOT_MARKER = ".pipeline-root.json"
REQUIRED_DIRS = ("00_ВХОДЯЩИЕ", "01_БРИФ", "02_СМЕТА", "03_ДОКУМЕНТЫ", "04_ОПЛАТЫ", "05_ВЫДАЧА", "99_АРХИВ")
GATES = ("intake", "estimate_lock", "document_plan", "review", "delivery")
REGISTER_COLUMNS = {
    "documents_register": (
        "document_id", "type", "title", "counterparty", "estimate_version", "owner",
        "status", "native_file", "pdf_file", "approval", "delivery_target", "source_refs", "notes",
    ),
    "payments_register": (
        "payment_id", "contractor", "purpose", "amount", "source", "status",
        "planned_date", "paid_date", "credit_start_date", "notes",
    ),
}


def configure_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8", errors="replace")


def plugin_root() -> Path:
    return Path(__file__).resolve().parents[3]


def workspace_template() -> Path:
    return Path(__file__).resolve().parents[1] / 'templates'


def find_project(start: Path) -> Path | None:
    current = start.resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if (candidate / PROJECT_FILE).is_file() and candidate.name != TEMPLATE_NAME:
            return candidate
    return None


def configured_projects_root(workspace: Path) -> Path | None:
    """Projects root from env OFFICE_PROJECTS_ROOT or <workspace>/config/paths.json "projects_root"."""
    value = os.environ.get(PROJECTS_ROOT_ENV, "").strip()
    if not value:
        config_path = workspace / "config" / "paths.json"
        if config_path.is_file():
            config = json.loads(config_path.read_text(encoding="utf-8-sig"))
            configured = config.get("projects_root") if isinstance(config, dict) else None
            if isinstance(configured, str):
                value = configured.strip()
    if not value:
        return None
    path = Path(os.path.expandvars(value)).expanduser()
    if not path.is_absolute():
        path = workspace / path
    return path.resolve()


def projects_root(workspace: Path) -> Path:
    """Env OFFICE_PROJECTS_ROOT > config/paths.json projects_root > <workspace>/ПРОЕКТЫ (legacy)."""
    return configured_projects_root(workspace) or workspace / PROJECTS_DIR


def template_dir(workspace: Path) -> Path | None:
    """Workspace project template: <workspace>/templates/ШАБЛОН_ПРОЕКТА, else legacy <projects>/ШАБЛОН_ПРОЕКТА."""
    for candidate in (workspace / TEMPLATES_DIR / TEMPLATE_NAME, projects_root(workspace) / TEMPLATE_NAME):
        if candidate.is_dir():
            return candidate
    return None


def list_projects(workspace: Path) -> list[Path]:
    """Live projects directly under the projects root; the template is never listed."""
    root = projects_root(workspace)
    if not root.is_dir():
        return []
    return sorted(
        item for item in root.iterdir()
        if item.is_dir() and item.name != TEMPLATE_NAME and (item / PROJECT_FILE).is_file()
    )


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _marker_workspace(marker: Path) -> Path | None:
    try:
        value = load_json(marker).get("pipeline_root")
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(value, str) or not value.strip():
        return None
    root = Path(os.path.expandvars(value.strip())).expanduser()
    if not root.is_absolute():
        root = marker.parent / root
    return root.resolve()


def is_workspace_root(path: Path) -> bool:
    """A pipeline workspace has docs/schema (skeleton layout) or ПАЙПЛАЙН/ (legacy layout)."""
    return (path / SCHEMA_DIR).is_dir() or (path / PIPELINE_DIR).is_dir()


def find_workspace(start: Path) -> Path | None:
    current = start.resolve()
    if current.is_file():
        current = current.parent
    markers: list[Path] = []
    for candidate in (current, *current.parents):
        if is_workspace_root(candidate) and projects_root(candidate).is_dir():
            return candidate
        if (candidate / ROOT_MARKER).is_file():
            markers.append(candidate / ROOT_MARKER)
    # The projects root may live outside the workspace (e.g. workspace/projects\office). Accept a workspace
    # named by a .pipeline-root.json marker, or the workspace this plugin ships in, only when the
    # start path is inside that workspace's projects root.
    fallbacks = [found for found in map(_marker_workspace, markers) if found]
    script_parents = Path(__file__).resolve().parents
    if len(script_parents) > 5:
        fallbacks.append(script_parents[5])  # <workspace>/plugins/office-pipeline/skills/office-pipeline/scripts
    for workspace in fallbacks:
        if not is_workspace_root(workspace):
            continue
        root = projects_root(workspace)
        if root.is_dir() and _is_within(current, root):
            return workspace
    return None


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} root must be an object")
    return value


def safe_relative(project: Path, value: Any, *, field: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty relative path")
    relative = Path(value)
    if relative.is_absolute():
        raise ValueError(f"{field} must be relative to the project")
    resolved = (project / relative).resolve()
    try:
        resolved.relative_to(project.resolve())
    except ValueError as exc:
        raise ValueError(f"{field} escapes the project root") from exc
    return resolved


def copy_missing_tree(source: Path, destination: Path) -> None:
    for item in source.rglob("*"):
        relative = item.relative_to(source)
        target = destination / relative
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)


def initialize(workspace: Path, code: str, name: str, mode: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{1,63}", code):
        raise ValueError("code must be 2-64 characters: letters, digits, dot, underscore or hyphen")
    template = workspace_template()
    if not template.is_dir():
        raise FileNotFoundError(f"Bundled workspace template is missing: {template}")
    workspace = workspace.resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    if not (workspace / SCHEMA_DIR).is_dir():
        # Skeleton workspaces already carry these files in docs/schema and docs/process.
        copy_missing_tree(template / PIPELINE_DIR, workspace / PIPELINE_DIR)
    projects = projects_root(workspace)
    projects.mkdir(parents=True, exist_ok=True)
    template_project = template / PROJECTS_DIR / TEMPLATE_NAME
    if template_dir(workspace) is None:
        # Legacy layout keeps the template beside projects; an external projects root keeps it in templates/.
        external = configured_projects_root(workspace) is not None
        retained_template = (workspace / TEMPLATES_DIR if external else projects) / TEMPLATE_NAME
        shutil.copytree(template_project, retained_template)
    destination = projects / code
    if destination.exists():
        raise FileExistsError(f"Project already exists: {destination}")
    shutil.copytree(template_project, destination)
    config_path = destination / PROJECT_FILE
    config = load_json(config_path)
    config.setdefault("project", {})["code"] = code
    config["project"]["name"] = name
    config["project"]["mode"] = mode
    config["project"]["created"] = date.today().isoformat()
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return destination


def load_estimate_engine():
    path = Path(__file__).parent / "estimate_engine.py"
    specification = importlib.util.spec_from_file_location("office_estimate_engine", path)
    if specification is None or specification.loader is None:
        raise RuntimeError(f"Cannot load estimate engine: {path}")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def check_register(path: Path, expected: tuple[str, ...]) -> tuple[list[str], list[str]]:
    blockers: list[str] = []
    warnings: list[str] = []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.reader(stream)
            header = next(reader, [])
        missing = [column for column in expected if column not in header]
        if missing:
            blockers.append(f"{path.name} misses columns: {', '.join(missing)}")
        extra = [column for column in header if column and column not in expected and column != 'estimate_sha256']
        if extra:
            warnings.append(f"{path.name} has additional columns: {', '.join(extra)}")
    except (OSError, UnicodeError, csv.Error) as exc:
        blockers.append(f"Cannot read {path.name}: {exc}")
    return blockers, warnings


def diagnose(project: Path) -> dict[str, Any]:
    project = project.resolve()
    blockers: list[str] = []
    warnings: list[str] = []
    checks: list[dict[str, Any]] = []
    config_path = project / PROJECT_FILE
    if not config_path.is_file():
        return {"project": str(project), "status": "blocked", "blockers": [f"Missing {PROJECT_FILE}"], "warnings": [], "checks": []}
    try:
        config = load_json(config_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return {"project": str(project), "status": "blocked", "blockers": [str(exc)], "warnings": [], "checks": []}

    schema_dir = workspace_template() / PIPELINE_DIR / 'schemas'
    invalid = quality.schema_errors(config, schema_dir / 'office-project.schema.json')
    if invalid:
        return {"project": str(project), "status": "blocked", "blockers": invalid, "warnings": [], "checks": [],
                "delivery_readiness": "blocked", "delivery_blockers": invalid}

    project_data = config.get("project") or {}
    code = project_data.get("code")
    if not code:
        blockers.append("project.code is missing")
    if project.name == TEMPLATE_NAME:
        blockers.append("Template folder cannot be diagnosed as a live project")
    gate = (config.get("pipeline") or {}).get("current_gate")
    if gate not in GATES:
        blockers.append(f"pipeline.current_gate must be one of: {', '.join(GATES)}")
    for directory in REQUIRED_DIRS:
        exists = (project / directory).is_dir()
        checks.append({"check": f"directory:{directory}", "ok": exists})
        if not exists:
            blockers.append(f"Missing required directory: {directory}")

    files = config.get("files") or {}
    resolved_files: dict[str, Path] = {}
    for key in ("estimate_json", "estimate_workbook", "documents_register", "payments_register", "delivery_dir"):
        try:
            path = safe_relative(project, files.get(key), field=f"files.{key}")
            resolved_files[key] = path
            exists = path.exists()
            checks.append({"check": f"file:{key}", "ok": exists, "path": str(path)})
            if not exists and key != "estimate_workbook":
                blockers.append(f"Configured path does not exist: files.{key} -> {path}")
            elif not exists:
                warnings.append(f"Estimate workbook has not been created yet: {path}")
        except ValueError as exc:
            blockers.append(str(exc))

    calculation: dict[str, Any] | None = None
    estimate: dict[str, Any] = {}
    estimate_path = resolved_files.get("estimate_json")
    if estimate_path and estimate_path.is_file():
        try:
            estimate = load_json(estimate_path)
            invalid = quality.schema_errors(estimate, schema_dir / 'estimate.schema.json')
            if invalid:
                raise ValueError('; '.join(invalid))
            engine = load_estimate_engine()
            calculation = engine.json_ready(engine.calculate(estimate))
            checks.append({"check": "estimate_calculation", "ok": True, "warnings": len(calculation["warnings"])})
            warnings.extend(f"Estimate: {item}" for item in calculation["warnings"])
            if not estimate.get("items"):
                warnings.append("Active estimate contains no items")
        except (OSError, json.JSONDecodeError, ValueError, RuntimeError, ArithmeticError, TypeError) as exc:
            blockers.append(f"Estimate calculation failed: {exc}")
            checks.append({"check": "estimate_calculation", "ok": False})
            estimate = {}

    rows_by_kind = {}
    late = gate in ('review', 'delivery')
    for key, expected in REGISTER_COLUMNS.items():
        path = resolved_files.get(key)
        if path and path.is_file():
            found_blockers, found_warnings = check_register(path, expected)
            blockers.extend(found_blockers)
            warnings.extend(found_warnings)
            checks.append({"check": f"register:{key}", "ok": not found_blockers})
            if not found_blockers:
                try:
                    rows, row_errors, row_warnings = quality.register_rows(path, key, project, estimate, late)
                    rows_by_kind[key] = rows
                    blockers.extend(row_errors)
                    warnings.extend(row_warnings)
                except (OSError, ValueError, csv.Error, UnicodeError) as exc:
                    blockers.append(f'{key}: {exc}')

    if calculation is not None and 'payments_register' in rows_by_kind:
        blockers.extend(quality.reconcile_payments(rows_by_kind['payments_register'], estimate.get('payments', [])))

    # Readiness is deliberately separate from a healthy intake structure.
    delivery_blockers = []
    import document_profiles
    profile_check = document_profiles.validate(project, config)
    blockers.extend(profile_check['errors'])
    delivery_blockers.extend(profile_check['errors'] + profile_check['pending'])
    checks.append({'check': 'document_profiles', **profile_check})
    import normcontrol
    norm_check = normcontrol.validate(project, config)
    blockers.extend(norm_check['errors'])
    delivery_blockers.extend(norm_check['errors'] + norm_check['pending'])
    checks.append({'check': 'normcontrol', **norm_check})
    for key in rows_by_kind:
        _, strict_errors, _ = quality.register_rows(resolved_files[key], key, project, estimate, True)
        delivery_blockers.extend(strict_errors)
    approval = config.get('approvals', {})
    accepted = {'approved', 'internal', 'client', 'legal', 'signed'}
    for name in ('estimate', 'documents', 'delivery'):
        if approval.get(name) not in accepted:
            delivery_blockers.append(f'Missing {name} approval')
    if not estimate.get('items'):
        delivery_blockers.append('Active estimate contains no items')
    if estimate.get('version', {}).get('status') != 'approved':
        delivery_blockers.append('Active estimate version is not approved')
    if not config.get('project', {}).get('owner'):
        delivery_blockers.append('Missing project owner')
    if not config.get('tax_basis'):
        delivery_blockers.append('Missing tax_basis: record the project-provided assumptions/source')
    active_documents = [r for r in rows_by_kind.get('documents_register', []) if r.get('status') not in {'superseded', 'archived'}]
    if not active_documents:
        delivery_blockers.append('No active documents registered')
    for row in active_documents:
        if row.get('status') not in {'approved', 'issued'} or row.get('approval') not in accepted:
            delivery_blockers.append(f'Document {row.get("document_id")}: not approved')
        if estimate_path and estimate_path.is_file() and row.get('estimate_sha256') != quality.digest(estimate_path):
            delivery_blockers.append(f'Document {row.get("document_id")}: missing/stale estimate_sha256')

    reconciliation = None
    workbook = resolved_files.get('estimate_workbook')
    if not workbook or not workbook.is_file():
        delivery_blockers.append('Missing estimate workbook')
    elif not files.get('workbook_map'):
        delivery_blockers.append('Missing workbook_map for independent reconciliation')
    elif calculation is not None:
        try:
            mapping = load_json(safe_relative(project, files['workbook_map'], field='files.workbook_map'))
            reconciliation = quality.reconcile_workbook(project, workbook, mapping, calculation)
            delivery_blockers.extend(reconciliation['blockers'])
        except (OSError, ValueError, KeyError, TypeError, quality.zipfile.BadZipFile, quality.ET.ParseError) as exc:
            delivery_blockers.append(f'Workbook reconciliation: {exc}')
    required_qa = {files['estimate_workbook']}
    required_qa.update(r[field] for r in active_documents for field in ('native_file', 'pdf_file') if r.get(field))
    if not files.get('qa_evidence'):
        delivery_blockers.append('Missing qa_evidence for current artifact hashes')
    else:
        try:
            evidence = load_json(safe_relative(project, files['qa_evidence'], field='files.qa_evidence'))
            delivery_blockers.extend(quality.check_evidence(project, evidence, required_qa))
        except (OSError, ValueError, TypeError) as exc:
            delivery_blockers.append(f'QA evidence: {exc}')
    if calculation:
        delivery_blockers.extend(f'Unresolved calculation warning: {w}' for w in calculation['warnings'])
    if late:
        # Review requires reconciliation; final approvals are still allowed to be pending.
        pending_approvals = {'Missing estimate approval', 'Missing documents approval', 'Missing delivery approval', 'Active estimate version is not approved'}
        gate_errors = delivery_blockers if gate == 'delivery' else [x for x in delivery_blockers if x not in pending_approvals and not (x.startswith('Document ') and x.endswith(': not approved'))]
        blockers.extend(gate_errors)
    delivery_blockers = list(dict.fromkeys(blockers + delivery_blockers))

    return {
        "schema_version": 1,
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "project": str(project),
        "project_code": code,
        "current_gate": gate,
        "status": "blocked" if blockers else "pass_with_warnings" if warnings else "pass",
        "blockers": blockers,
        "warnings": warnings,
        "checks": checks,
        "calculation": calculation,
        "reconciliation": reconciliation,
        "delivery_readiness": "blocked" if delivery_blockers else "ready_for_authorized_delivery",
        "delivery_blockers": delivery_blockers,
    }


def render_report(result: dict[str, Any]) -> str:
    lines = [
        "# Office Pipeline diagnostic",
        "",
        f"- Project: `{result.get('project', '')}`",
        f"- Code: `{result.get('project_code') or ''}`",
        f"- Gate: `{result.get('current_gate') or ''}`",
        f"- Status: **{result.get('status', 'blocked')}**",
        "",
        "## Blockers",
        "",
    ]
    lines.extend(f"- {item}" for item in result.get("blockers", []))
    if not result.get("blockers"):
        lines.append("- None")
    lines.extend(["", "## Warnings", ""])
    lines.extend(f"- {item}" for item in result.get("warnings", []))
    if not result.get("warnings"):
        lines.append("- None")
    lines.extend(['', '## Delivery readiness', '', f"- {result.get('delivery_readiness', 'not_checked')}", ''])
    lines.extend(f'- {item}' for item in result.get('delivery_blockers', []))
    calculation = result.get("calculation") or {}
    financial = calculation.get("financial_result") or {}
    if financial:
        lines.extend(["", "## Reconciliation snapshot", ""])
        for key in ("contract_price", "estimate_total", "credit_interest", "gross_profit", "net_profit", "margin"):
            lines.append(f"- `{key}`: {financial.get(key)}")
    lines.extend(["", "## Checks", "", "| Check | Result |", "| --- | --- |"])
    for item in result.get("checks", []):
        lines.append(f"| `{item.get('check')}` | {'PASS' if item.get('ok') else 'FAIL'} |")
    return "\n".join(lines) + "\n"


def resolve_project_argument(value: str | None) -> Path:
    start = Path(value) if value else Path.cwd()
    if (start / PROJECT_FILE).is_file():
        return start.resolve()
    found = find_project(start)
    if found:
        return found
    workspace = find_workspace(start)
    if workspace and value:
        candidate = projects_root(workspace) / value
        if (candidate / PROJECT_FILE).is_file():
            return candidate.resolve()
    raise FileNotFoundError(f"No live {PROJECT_FILE} found from {start}")


def main(argv: list[str] | None = None) -> int:
    configure_console()
    parser = argparse.ArgumentParser(description="Office Pipeline workspace helper.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    resolve_parser = subparsers.add_parser("resolve", help="Resolve active project/workspace from a path.")
    resolve_parser.add_argument("--start", type=Path, default=Path.cwd())
    list_parser = subparsers.add_parser("list", help="List live projects under the resolved projects root (template excluded).")
    list_parser.add_argument("--start", type=Path, default=Path.cwd())
    init_parser = subparsers.add_parser("init", help="Create a project from the bundled template.")
    init_parser.add_argument("--workspace", type=Path, required=True)
    init_parser.add_argument("--code", required=True)
    init_parser.add_argument("--name", required=True)
    init_parser.add_argument("--mode", choices=("commercial", "fz44", "internal"), default="commercial")
    doctor_parser = subparsers.add_parser("doctor", help="Run read-only structural and calculation checks.")
    doctor_parser.add_argument("--project")
    doctor_parser.add_argument("--json", action="store_true", dest="as_json")
    report_parser = subparsers.add_parser("report", help="Write a persistent Markdown diagnostic report.")
    report_parser.add_argument("--project")
    report_parser.add_argument("--output", type=Path, required=True)
    report_parser.add_argument("--overwrite", action="store_true")
    deliver_parser = subparsers.add_parser("deliver", help="Enqueue explicitly selected final PDFs after delivery preflight.")
    deliver_parser.add_argument("--project")
    deliver_parser.add_argument("--document", action="append", required=True, dest="documents", help="Exact document ID; repeat to select more.")
    deliver_mode = deliver_parser.add_mutually_exclusive_group()
    deliver_mode.add_argument("--dry-run", action="store_true", help="Validate and print receipt without writes or enqueue.")
    deliver_mode.add_argument("--local-only", action="store_true", help="Validate selection; explicitly opt out of delivery.")
    args = parser.parse_args(argv)
    try:
        if args.command == "resolve":
            project = find_project(args.start)
            workspace = find_workspace(args.start)
            print(json.dumps({"project": str(project) if project else None, "workspace": str(workspace) if workspace else None,
                              "projects_root": str(projects_root(workspace)) if workspace else None}, ensure_ascii=False, indent=2))
            return 0 if project or workspace else 1
        if args.command == "list":
            workspace = find_workspace(args.start)
            if not workspace:
                raise FileNotFoundError(f"No Office workspace found from {args.start}")
            print(json.dumps({"workspace": str(workspace), "projects_root": str(projects_root(workspace)),
                              "projects": [item.name for item in list_projects(workspace)]}, ensure_ascii=False, indent=2))
            return 0
        if args.command == "init":
            project = initialize(args.workspace, args.code, args.name, args.mode)
            print(project)
            return 0
        project = resolve_project_argument(args.project)
        if args.command == "deliver":
            from office_delivery import deliver
            # Pass this module's API without re-importing it under another name.
            from types import SimpleNamespace
            api = SimpleNamespace(diagnose=diagnose, load_json=load_json, safe_relative=safe_relative,
                                  quality=quality, PROJECT_FILE=PROJECT_FILE)
            result = deliver(api, project, args.documents, dry_run=args.dry_run, local_only=args.local_only)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        result = diagnose(project)
        if args.command == "doctor":
            print(json.dumps(result, ensure_ascii=False, indent=2) if args.as_json else render_report(result))
        else:
            output = args.output.resolve()
            if output.exists() and not args.overwrite:
                raise FileExistsError(f"Report exists; pass --overwrite to replace it: {output}")
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(render_report(result), encoding="utf-8")
            print(output)
        return 1 if result["blockers"] else 0
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
