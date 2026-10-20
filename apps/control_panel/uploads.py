"""Uploads from the browser (converters and the Models tab). Files land in <hub>/PipelineWeb/uploads/<ts>-<name>;
nothing is executed, the path is handed to a converter or a model runner. Also the shared path guard for
serving result files back to the browser.
"""
from __future__ import annotations

import re
import shutil
import time
import uuid
from pathlib import Path
import kit_config as config

import collectors as c

WEB_ROOT = config.workspace('web')
UPLOADS = WEB_ROOT / 'uploads'
MAX_UPLOAD = 4 * 1024 ** 3
# Where a pasted server path may point (read-only use as a conversion/model source).
SOURCE_ROOTS = [config.workspace('projects'), WEB_ROOT]
_SAFE = re.compile(r'[^\w.\-()\[\] а-яА-ЯёЁ]+')


def safe_name(name, limit=120):
    name = _SAFE.sub('_', Path(str(name or 'file')).name).strip('. ') or 'file'
    return name[-limit:]


def save_upload(upload):
    """Stream a Starlette UploadFile to disk; returns {'path','name','size'}."""
    UPLOADS.mkdir(parents=True, exist_ok=True)
    from project_files_service import native
    native(UPLOADS)
    name = safe_name(upload.filename)
    dest = UPLOADS / f"{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex}-{name}"
    size = 0
    with dest.open('xb') as fh:
        while True:
            chunk = upload.file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_UPLOAD:
                fh.close()
                dest.unlink(missing_ok=True)
                raise ValueError('Файл больше 4 ГБ — положите его в проект и укажите путь')
            fh.write(chunk)
    return {'path': str(dest), 'name': name, 'size': size}


def resolve_source(path_text):
    """A server path typed by the user: must exist and sit under one of SOURCE_ROOTS."""
    raw = str(path_text or '').strip().strip('"')
    if not raw:
        raise ValueError('Нужен файл: загрузите его или укажите путь на локальном узле')
    p = guarded_path(raw, SOURCE_ROOTS)
    if not p.is_file():
        raise KeyError(raw)
    return p


def guarded_path(path_text, roots):
    from project_files_service import native, secret_name, BLOCKED
    p = Path(str(path_text or '').replace('\\', '/')).absolute()
    for root in roots:
        try:
            relative = p.relative_to(Path(root).absolute())
        except ValueError:
            continue
        if any(part.startswith('.') or ':' in part or part.casefold() in BLOCKED or secret_name(part) for part in relative.parts):
            raise ValueError('Hidden, credential and traversal paths are refused')
        return native(p)
    raise ValueError('Файл вне разрешённых папок')


def inside(path_text, roots):
    return guarded_path(path_text, roots)


def cleanup(max_age_days=14):
    """Drop old uploads; results folders are kept (they are receipts)."""
    cutoff = time.time() - max_age_days * 86400
    removed = 0
    if UPLOADS.is_dir():
        for p in UPLOADS.iterdir():
            try:
                if p.is_file() and p.stat().st_mtime < cutoff:
                    p.unlink()
                    removed += 1
                elif p.is_dir() and p.stat().st_mtime < cutoff:
                    shutil.rmtree(p, ignore_errors=True)
                    removed += 1
            except OSError:
                pass
    return removed
