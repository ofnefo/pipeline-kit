"""Heuristic preflight for Russian lyrics (stdlib only; never edits the source).

Flags long or dense lines, articulation collisions, section variance, cliches, repeated end words,
filler/abstract words, an optional project jargon list and orthographic rhyme tails. Writes new JSON and
Markdown reports and refuses to overwrite previous ones. Heuristics only: verify by ear and metronome.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

WORD_RE = re.compile(r"[A-Za-zА-Яа-яЁё]+(?:[-'][A-Za-zА-Яа-яЁё]+)*")
RU_VOWELS = set("аеёиоуыэюя")
ALL_VOWELS = RU_VOWELS | set("aeiouy")
RU_CONSONANTS = set("бвгджзйклмнпрстфхцчшщ")

STOPWORDS = {
    "а", "без", "бы", "в", "во", "вот", "все", "всё", "где", "да", "для", "до", "его", "ее", "её",
    "если", "есть", "же", "за", "и", "из", "или", "к", "как", "ко", "когда", "ли", "мне", "мой", "мы",
    "на", "над", "не", "нет", "но", "о", "об", "он", "она", "они", "от", "по", "под", "при", "про",
    "с", "со", "так", "там", "тебе", "тебя", "то", "ты", "у", "что", "это", "я",
}
FILLERS = {"будто", "как-то", "очень", "просто", "словно", "снова", "лишь", "только", "вдруг", "навсегда"}
ABSTRACT = {"бесконечность", "боль", "вечность", "время", "душа", "любовь", "надежда", "память", "пустота", "свобода", "страх", "судьба", "тьма", "чувство"}
STYLE_JARGON: set[str] = set()  # project-specific overused words; fill with --jargon
CLICHES = (
    "боль внутри", "в глубине души", "горит внутри", "демоны внутри", "душа болит", "звезды над нами",
    "крылья за спиной", "навсегда с тобой", "потерянный рай", "разбитое сердце", "свет в конце",
    "тьма внутри", "холод в груди", "эхо прошлого", "мы дышим", "пустая комната",
)
POV = {"first_singular": {"я", "мне", "меня", "мой", "моя", "моё", "мои"}, "first_plural": {"мы", "нам", "нас", "наш", "наша", "наше", "наши"}, "second": {"ты", "тебе", "тебя", "твой", "твоя", "твоё", "твои"}, "third": {"он", "она", "они", "его", "её", "их"}}


def syllables(word: str) -> int:
    return sum(char in ALL_VOWELS for char in word.lower())


def max_run(text: str, alphabet: set[str]) -> int:
    best = current = 0
    for char in text.lower():
        if char in alphabet:
            current += 1
            best = max(best, current)
        elif char.isalpha():
            current = 0
    return best


def clean_line(line: str) -> str:
    return re.sub(r"^[>\-*+]\s*", "", line.strip())


def lyric_lines(text: str) -> list[dict]:
    records: list[dict] = []
    section = "unsectioned"
    in_frontmatter = text.startswith("---")
    in_fence = False
    section_counts = Counter()
    for number, raw in enumerate(text.splitlines(), start=1):
        stripped = raw.strip()
        if number == 1 and in_frontmatter:
            continue
        if in_frontmatter:
            if stripped == "---":
                in_frontmatter = False
            continue
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or not stripped:
            continue
        section_match = re.fullmatch(r"\[([^]]+)]", stripped)
        parenthetical = re.fullmatch(r"\((куплет|припев|бридж|интро|аутро|verse|chorus|bridge|intro|outro)([^)]*)\)", stripped, re.I)
        heading = re.fullmatch(r"#{1,6}\s+(куплет|припев|бридж|интро|аутро|verse|chorus|bridge|intro|outro)(.*)", stripped, re.I)
        label = section_match.group(1) if section_match else (
            parenthetical.group(1) + parenthetical.group(2) if parenthetical else
            heading.group(1) + heading.group(2) if heading else None)
        if label is not None:
            label = label.strip()
            section_counts[label] += 1
            section = label if section_counts[label] == 1 else f"{label} #{section_counts[label]}"
            continue
        if stripped.startswith("#"):
            continue
        line = clean_line(raw)
        if WORD_RE.search(line):
            records.append({"line_no": number, "section": section, "text": line})
    return records


def boundary_collisions(words: list[str]) -> list[str]:
    collisions = []
    for left, right in zip(words, words[1:]):
        tail = re.sub(r"[^а-яё]", "", left.lower())[-2:]
        head = re.sub(r"[^а-яё]", "", right.lower())[:2]
        combined = tail + head
        if sum(char in RU_CONSONANTS for char in combined) >= 3 and all(char in RU_CONSONANTS for char in combined if char):
            collisions.append(f"{left} {right}")
    return collisions


def rhyme_tail(word: str) -> str:
    normalized = re.sub(r"[^а-яё]", "", word.lower()).replace("ё", "е")
    positions = [index for index, char in enumerate(normalized) if char in RU_VOWELS]
    if not positions:
        return normalized[-3:]
    return normalized[positions[-1] :]


def line_analysis(record: dict, bpm: float | None, beats_per_bar: int, line_bars: float) -> dict:
    words = WORD_RE.findall(record["text"])
    lowered = [word.lower() for word in words]
    count = sum(syllables(word) for word in words)
    seconds = (60 / bpm) * beats_per_bar * line_bars if bpm else None
    return {
        **record,
        "words": len(words),
        "syllables": count,
        "characters": sum(char.isalpha() for char in record["text"]),
        "end_word": lowered[-1] if lowered else "",
        "rhyme_tail_orthographic": rhyme_tail(lowered[-1]) if lowered else "",
        "long_words": [word for word in words if syllables(word) >= 5],
        "max_consonant_run": max_run("".join(lowered), RU_CONSONANTS),
        "boundary_collisions": boundary_collisions(words),
        "estimated_seconds": seconds,
        "syllables_per_second": count / seconds if seconds else None,
    }


def section_summary(lines: list[dict]) -> dict:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for line in lines:
        grouped[line["section"]].append(line)
    summary = {}
    for name, items in grouped.items():
        values = [item["syllables"] for item in items]
        summary[name] = {
            "lines": len(items),
            "performance_mode": items[0].get("performance", {}).get("mode", "song"),
            "syllables_mean": statistics.mean(values),
            "syllables_min": min(values),
            "syllables_max": max(values),
            "syllables_stdev": statistics.pstdev(values) if len(values) > 1 else 0.0,
        }
    return summary


def build_report(source: Path, mode: str, bpm: float | None, beats_per_bar: int, line_bars: float, timing: dict | None = None) -> dict:
    text = source.read_text(encoding="utf-8-sig")
    raw_lines = lyric_lines(text)
    if bpm is not None and not 20 <= bpm <= 400:
        raise ValueError("BPM must be between 20 and 400")
    if not 1 <= beats_per_bar <= 16 or not 0 < line_bars <= 32:
        raise ValueError("Invalid beats-per-bar or line-bars")
    timing = timing or {}
    known = {record["section"] for record in raw_lines}
    if set(timing) - known:
        raise ValueError(f"Unknown timing sections: {sorted(set(timing)-known)}")
    lines = []
    for record in raw_lines:
        local = timing.get(record["section"], {})
        if set(local) - {"mode", "bpm", "line_bars", "beats_per_bar"}:
            raise ValueError("Unknown timing field")
        local_mode = local.get("mode", mode)
        local_bpm = local.get("bpm", bpm)
        local_beats = local.get("beats_per_bar", beats_per_bar)
        local_bars = local.get("line_bars", line_bars)
        if local_mode not in ("song", "rap", "spoken"):
            raise ValueError("Unknown mode")
        if local_bpm is not None and not 20 <= local_bpm <= 400:
            raise ValueError("Invalid section BPM")
        if not 1 <= local_beats <= 16 or not 0 < local_bars <= 32:
            raise ValueError("Invalid section bar allocation")
        line = line_analysis(record, local_bpm, local_beats, local_bars)
        line["performance"] = {"mode": local_mode, "bpm": local_bpm, "beats_per_bar": local_beats, "line_bars": local_bars}
        lines.append(line)
    all_words = [word.lower() for line in lines for word in WORD_RE.findall(line["text"])]
    content_counts = Counter(word for word in all_words if word not in STOPWORDS and len(word) > 2)
    lowered_text = " ".join(all_words)
    sections = section_summary(lines) if lines else {}
    issues: list[dict] = []
    line_limit = {"song": 16, "rap": 26, "spoken": 32}[mode]
    for line in lines:
        local_mode = line["performance"]["mode"]
        line_limit = {"song": 16, "rap": 26, "spoken": 32}[local_mode]
        if line["syllables"] > line_limit:
            issues.append({"kind": "long_line", "severity": "review", "line": line["line_no"], "value": line["syllables"]})
        if line["max_consonant_run"] >= 5 or line["boundary_collisions"]:
            issues.append({"kind": "articulation", "severity": "listen", "line": line["line_no"], "collisions": line["boundary_collisions"]})
        if line["syllables_per_second"] and line["syllables_per_second"] > (7.2 if local_mode == "rap" else 5.2):
            issues.append({"kind": "density", "severity": "record", "line": line["line_no"], "syllables_per_second": line["syllables_per_second"]})
    for name, data in sections.items():
        if data["lines"] > 2 and data["syllables_stdev"] > (5 if data["performance_mode"] == "rap" else 3.5):
            issues.append({"kind": "section_variance", "severity": "review", "section": name, "stdev": data["syllables_stdev"]})
    # Match inside each lyric line, never stitch the end of one line to the next.
    cliche_hits = sorted({phrase for phrase in CLICHES for line in lines
                          if phrase in " ".join(w.lower() for w in WORD_RE.findall(line["text"])).replace("ё", "е")})
    if cliche_hits:
        issues.append({"kind": "cliche", "severity": "rewrite_or_earn", "phrases": cliche_hits})
    end_words = Counter(line["end_word"] for line in lines if line["end_word"])
    repeated_ends = {word: count for word, count in end_words.items() if count > 1}
    if repeated_ends:
        issues.append({"kind": "repeated_end_words", "severity": "review", "words": repeated_ends})
    rhyme_groups: dict[str, list[int]] = defaultdict(list)
    for line in lines:
        tail = line["rhyme_tail_orthographic"]
        if tail:
            rhyme_groups[tail].append(line["line_no"])
    rhyme_groups = {tail: numbers for tail, numbers in rhyme_groups.items() if len(numbers) > 1}
    pov_counts = {name: sum(word in lexicon for word in all_words) for name, lexicon in POV.items()}
    return {
        "schema_version": 2,
        "section_timing": timing,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": str(source.resolve()),
        "mode": mode,
        "timing_assumption": {"bpm": bpm, "beats_per_bar": beats_per_bar, "line_bars": line_bars, "warning": "A written line is not automatically one bar."},
        "summary": {"lines": len(lines), "words": len(all_words), "syllables": sum(line["syllables"] for line in lines), "sections": len(sections)},
        "sections": sections,
        "lines": lines,
        "repeated_content_words": dict(content_counts.most_common(30)),
        "filler_words": {word: content_counts[word] for word in FILLERS if content_counts[word]},
        "abstract_words": {word: content_counts[word] for word in ABSTRACT if content_counts[word]},
        "style_jargon": {word: content_counts[word] for word in STYLE_JARGON if content_counts[word]},
        "point_of_view_markers": pov_counts,
        "cliche_hits": cliche_hits,
        "orthographic_rhyme_tail_groups": rhyme_groups,
        "issues": issues,
        "limits": [
            "Syllables are estimated from written vowels.",
            "Rhyme tails use the final written vowel, not a stress dictionary; verify by ear.",
            "The report cannot judge truth, image quality, delivery or whether a deviation is artistically necessary.",
        ],
    }


def markdown(report: dict) -> str:
    result = ["# Lyric preflight", "", f"Source: `{report['source']}`", f"Mode: `{report['mode']}`", ""]
    summary = report["summary"]
    result += [f"Lines: **{summary['lines']}** · Words: **{summary['words']}** · Approx. syllables: **{summary['syllables']}**", "", "## Sections", "", "| Section | Lines | Mean syllables | Range | Std dev |", "|---|---:|---:|---:|---:|"]
    for name, data in report["sections"].items():
        result.append(f"| {name} | {data['lines']} | {data['syllables_mean']:.2f} | {data['syllables_min']}–{data['syllables_max']} | {data['syllables_stdev']:.2f} |")
    result += ["", "## Line map", "", "| # | Section | Syllables | Words | Syll/s | End | Text |", "|---:|---|---:|---:|---:|---|---|"]
    for line in report["lines"]:
        speed = f"{line['syllables_per_second']:.2f}" if line["syllables_per_second"] is not None else "—"
        safe_text = line["text"].replace("|", "\\|")
        result.append(f"| {line['line_no']} | {line['section']} | {line['syllables']} | {line['words']} | {speed} | {line['end_word']} | {safe_text} |")
    result += ["", "## Flags", ""]
    if report["issues"]:
        result.extend(f"- `{item['kind']}` — {json.dumps(item, ensure_ascii=False)}" for item in report["issues"])
    else:
        result.append("- No automatic flags. This is not an artistic approval.")
    result += ["", "## Limits", ""] + [f"- {item}" for item in report["limits"]]
    return "\n".join(result) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Heuristic preflight for Russian lyrics; never edits the source.")
    parser.add_argument("source", type=Path)
    parser.add_argument("--mode", choices=("song", "rap", "spoken"), default="song")
    parser.add_argument("--bpm", type=float)
    parser.add_argument("--beats-per-bar", type=int, default=4)
    parser.add_argument("--line-bars", type=float, default=1.0)
    parser.add_argument("--timing-json", type=Path, help="Per-section mode/BPM/bar allocation; labels must match the line map")
    parser.add_argument("--json", type=Path)
    parser.add_argument("--markdown", type=Path)
    parser.add_argument("--jargon", help="comma-separated project jargon words, or @file with one word per line")
    args = parser.parse_args()
    if args.jargon:
        raw = Path(args.jargon[1:]).read_text(encoding="utf-8-sig") if args.jargon.startswith("@") else args.jargon
        STYLE_JARGON.update(w.strip().lower() for w in re.split(r"[,\n]", raw) if w.strip())
    source = args.source.resolve()
    timing = json.loads(args.timing_json.read_text(encoding="utf-8-sig")) if args.timing_json else None
    report = build_report(source, args.mode, args.bpm, args.beats_per_bar, args.line_bars, timing)
    json_path = (args.json or source.with_suffix(source.suffix + ".preflight.json")).resolve()
    markdown_path = (args.markdown or source.with_suffix(source.suffix + ".preflight.md")).resolve()
    if json_path == source or markdown_path == source or json_path == markdown_path:
        raise ValueError("Reports must have distinct paths and cannot replace the lyric")
    for path in (json_path, markdown_path):
        if path.exists():
            raise FileExistsError(f"Preserve previous reports; choose a new output path: {path}")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    with json_path.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    with markdown_path.open("x", encoding="utf-8") as handle:
        handle.write(markdown(report))
    print(json.dumps({"json": str(json_path), "markdown": str(markdown_path), "issues": len(report["issues"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
