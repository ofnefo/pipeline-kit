"""CPU helper subset extracted from the owned video worker."""
import hashlib, json, os, re, shutil, subprocess
from datetime import datetime, timezone
from pathlib import Path
PROJECTS=Path(os.environ.get('PIPELINE_KIT_WORKSPACE','workspace')).absolute()/'projects/video'

def find_binary(name):
    found=shutil.which(name)
    return Path(found) if found else None

def utc_now() -> str:

    return datetime.now(timezone.utc).isoformat()

def sha256(path: Path, chunk_size: int = 8 * 1024 * 1024) -> str:

    digest = hashlib.sha256()

    with path.open("rb") as stream:

        while chunk := stream.read(chunk_size):

            digest.update(chunk)

    return digest.hexdigest()

def run(command: list[str | Path], *, capture: bool = False) -> subprocess.CompletedProcess[str]:

    completed = subprocess.run(

        [str(item) for item in command],

        check=False,

        capture_output=capture,

        text=True,

        encoding="utf-8",

        errors="replace",

        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),

    )

    if completed.returncode:

        detail = (completed.stderr or completed.stdout or "").strip()

        raise RuntimeError(detail[-3000:] or f"Command failed with code {completed.returncode}")

    return completed

def checked_project(slug: str) -> Path:

    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,62}", slug):

        raise ValueError("Project id must be lower-case hyphen-case")

    path = (PROJECTS / slug).resolve()

    if path.parent != PROJECTS.resolve() or not path.is_dir():

        raise FileNotFoundError(f"Unknown project: {slug}")

    return path

def append_render(project: Path, payload: dict) -> None:

    record = {"created_at": utc_now(), **payload}

    with (project / "renders.jsonl").open("a", encoding="utf-8") as stream:

        stream.write(json.dumps(record, ensure_ascii=False) + "\n")

def probe(path: Path) -> dict:

    ffprobe = find_binary("ffprobe")

    if not ffprobe:

        raise FileNotFoundError("ffprobe is not available")

    result = run([

        ffprobe, "-v", "error", "-show_format", "-show_streams", "-show_chapters", "-of", "json", path

    ], capture=True)

    payload = json.loads(result.stdout)

    payload["source"] = str(path.resolve())

    return payload
