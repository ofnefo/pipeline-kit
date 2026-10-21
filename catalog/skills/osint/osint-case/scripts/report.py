"""Validate an OSINT case's evidence JSONL and render a Markdown report. Offline: no network, no lookups.

Examples:
  python -X utf8 report.py --case-dir cases/own-domain-001
  python -X utf8 report.py --case-dir cases/own-domain-001 --check-only

Any invalid evidence line -> no report, exit 2. Reports are written as new files and never overwritten.
Sharing a report is a separate, approved action outside this script.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REQUIRED = ("id", "kind", "statement", "source_url_or_file", "retrieved_at", "tool", "tool_version",
            "confidence", "verification_status")
KINDS = {"claim", "hypothesis"}
CONFIDENCE = {"high", "medium", "low", "unknown"}
STATUS = {"verified", "unverified", "contradicted", "error"}
SHA_RE = re.compile(r"[0-9a-f]{64}")


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_url(value):
    return value.lower().startswith(("http://", "https://"))


def parse_utc(value):
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    stamp = datetime.fromisoformat(text)
    if stamp.utcoffset() is None or stamp.utcoffset().total_seconds() != 0:
        raise ValueError("retrieved_at must be ISO 8601 in UTC (Z or +00:00)")
    return stamp


def validate_record(record, case_dir):
    """Return a list of problems for one evidence record (empty = valid)."""
    if not isinstance(record, dict):
        return ["record is not a JSON object"]
    errors = [f"missing/empty {k}" for k in REQUIRED if not str(record.get(k, "")).strip()]
    if errors:
        return errors
    if record["kind"] not in KINDS:
        errors.append(f"kind must be one of {sorted(KINDS)}")
    if record["confidence"] not in CONFIDENCE:
        errors.append(f"confidence must be one of {sorted(CONFIDENCE)}")
    if record["verification_status"] not in STATUS:
        errors.append(f"verification_status must be one of {sorted(STATUS)}")
    if record["kind"] == "hypothesis" and record["verification_status"] == "verified":
        errors.append("a verified item is a claim, not a hypothesis")
    try:
        parse_utc(str(record["retrieved_at"]))
    except ValueError as exc:
        errors.append(str(exc))
    digest = record.get("source_sha256")
    if digest is not None and not SHA_RE.fullmatch(str(digest)):
        errors.append("source_sha256 must be 64 lowercase hex chars")
    source = str(record["source_url_or_file"])
    if not is_url(source):
        if not digest:
            errors.append("file sources require source_sha256")
        local = (case_dir / source).resolve()
        if not local.is_relative_to(case_dir.resolve()):
            errors.append("file source must be a path relative to the case directory")
        elif local.is_file() and digest and SHA_RE.fullmatch(str(digest)) and sha256(local) != digest:
            errors.append("source_sha256 does not match the file in the case directory")
    return errors


def load_evidence(path, case_dir):
    records, errors, seen = [], [], set()
    for number, line in enumerate(Path(path).read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"line {number}: invalid JSON ({exc.msg})")
            continue
        problems = validate_record(record, case_dir)
        if isinstance(record, dict) and record.get("id") in seen:
            problems.append("duplicate id")
        if isinstance(record, dict):
            seen.add(record.get("id"))
        errors += [f"line {number}: {p}" for p in problems]
        records.append(record)
    if not records and not errors:
        errors.append("evidence file has no records")
    return records, errors


def _item(r):
    tail = f"; limitations: {r['limitations']}" if r.get("limitations") else ""
    sha = f"; sha256 `{r['source_sha256']}`" if r.get("source_sha256") else ""
    return (f"- **{r['id']}** - {r['statement']}\n"
            f"  - Source: {r['source_url_or_file']}{sha}\n"
            f"  - Retrieved (UTC): {r['retrieved_at']}; tool: {r['tool']} {r['tool_version']}\n"
            f"  - Confidence: {r['confidence']}; verification: {r['verification_status']}{tail}")


def render(case, records, generated_at):
    open_ = [r for r in records if r["verification_status"] in ("verified", "unverified")]
    claims = [r for r in open_ if r["kind"] == "claim"]
    hypotheses = [r for r in open_ if r["kind"] == "hypothesis"]
    contradicted = [r for r in records if r["verification_status"] == "contradicted"]
    errors = [r for r in records if r["verification_status"] == "error"]
    auth = case.get("authorization") or {}
    lines = [f"# OSINT report: {case['case_id']}", "",
             f"Generated (UTC): {generated_at}. Built offline from the case evidence file; "
             "no network requests were made while building.", "",
             "## Case scope", "", f"- Scope: {case.get('scope', '')}",
             f"- Target class: {case.get('target_class', 'not recorded')}",
             f"- Authorisation: {auth.get('by', 'NOT RECORDED')} - {auth.get('basis', '')}".rstrip(" -"),
             f"- Collection mode: {case.get('collection_mode', 'passive')}", "",
             f"## Facts ({len(claims)})", ""]
    lines += [_item(r) for r in claims] or ["None."]
    lines += ["", f"## Hypotheses - NOT confirmed ({len(hypotheses)})", "",
              "Each item below is an assumption, not an established fact."]
    lines += [_item(r).replace("- **", "- [HYPOTHESIS] **", 1) for r in hypotheses] or ["None."]
    if contradicted:
        lines += ["", f"## Contradicted ({len(contradicted)})", ""] + [_item(r) for r in contradicted]
    if errors:
        lines += ["", f"## Collection errors and gaps ({len(errors)})", ""] + [_item(r) for r in errors]
    lines += ["", "## Limitations", "",
              "- A matching username or photo does not establish identity.",
              "- Wi-Fi or cell-based geolocation does not prove where a person is.",
              "- Confidence is an analyst's judgement, not a probability.", ""]
    return "\n".join(lines)


def build(case_dir, *, evidence=None, out=None, check_only=False):
    case_dir = Path(case_dir).resolve()
    case = json.loads((case_dir / "case.json").read_text(encoding="utf-8-sig"))
    records, errors = load_evidence(Path(evidence) if evidence else case_dir / "evidence.jsonl", case_dir)
    if errors:
        raise ValueError("Evidence validation failed:\n" + "\n".join(errors))
    summary = {"case_id": case["case_id"], "records": len(records),
               "claims": sum(r["kind"] == "claim" for r in records),
               "hypotheses": sum(r["kind"] == "hypothesis" for r in records),
               "authorized": bool((case.get("authorization") or {}).get("by"))}
    if check_only:
        return {**summary, "status": "valid"}
    now = datetime.now(timezone.utc)
    out = Path(out) if out else case_dir / "reports" / f"report-{now:%Y%m%dT%H%M%SZ}.md"
    out = out.resolve()
    if not out.is_relative_to(case_dir) or out.suffix.lower() != ".md":
        raise ValueError("report must be a new .md file inside the case directory")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("x", encoding="utf-8") as handle:  # never overwrite an earlier report
        handle.write(render(case, records, now.isoformat(timespec="seconds")))
    return {**summary, "report": str(out), "report_sha256": sha256(out), "status": "built"}


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--case-dir", required=True, type=Path)
    ap.add_argument("--evidence", type=Path, help="default: <case-dir>/evidence.jsonl")
    ap.add_argument("--out", type=Path, help="default: <case-dir>/reports/report-<UTC>.md (never overwritten)")
    ap.add_argument("--check-only", action="store_true", help="validate evidence, write nothing")
    a = ap.parse_args(argv)
    try:
        result = build(a.case_dir, evidence=a.evidence, out=a.out, check_only=a.check_only)
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
