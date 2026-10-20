"""Bounded Windows directory notification journal; no scan, hashing or service."""
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path, PureWindowsPath
import stat
import struct
import threading
import time

MAX_EVENTS = 2000
HISTORY_NOTE = ('Изменения записываются, пока работает панель, без предварительного сканирования. '
                'Переименование связывается только по паре уведомлений Windows в одной корневой папке. '
                'Перенос между папками Windows может сообщить как отдельные удаление и создание; '
                'такие события не склеиваются в подтверждённое перемещение. '
                'Периоды остановки и потеря уведомлений отмечаются как пропуски; их история не восстанавливается. '
                'Журнал хранит последние 2000 событий. Скрытые и служебные папки, ссылки и точки подключения исключены.')
EVENT_LABELS = {'create': 'Создано', 'delete': 'Удалено', 'modify': 'Изменено',
                'rename': 'Переименовано / перемещено', 'rename_from': 'Прежнее имя (пара не получена)',
                'rename_to': 'Новое имя (пара не получена)', 'gap': 'Пропуск истории',
                'watch_start': 'Наблюдение началось', 'watch_stop': 'Наблюдение остановлено'}
REASONS = {'panel_not_running': 'Панель не работала; события неизвестны',
           'history_begins_here': 'Начало истории; прежние события неизвестны',
           'notification_overflow': 'Переполнение буфера Windows; часть событий потеряна',
           'invalid_notification': 'Неполное уведомление Windows', 'watcher_error': 'Ошибка наблюдения',
           'journal_unreadable': 'Предыдущий журнал не удалось прочитать',
           'shutdown': 'Панель остановлена', 'error': 'Ошибка наблюдения'}


class Journal:
    def __init__(self, path):
        self.path = Path(path)
        self.lock = threading.Lock()
        self.events = []
        self.sequence = 0
        self.load_error = None
        try:
            if self.path.stat().st_size > 8 * 1024 * 1024:
                raise ValueError('journal exceeds read limit')
            data = json.loads(self.path.read_text(encoding='utf-8'))
            self.events = data['events'][-MAX_EVENTS:]
            self.sequence = max((int(e['id']) for e in self.events), default=0)
        except FileNotFoundError:
            pass
        except (OSError, ValueError, KeyError, TypeError) as exc:
            self.load_error = type(exc).__name__

    def append(self, events):
        if not events:
            return
        with self.lock:
            for event in events:
                self.sequence += 1
                self.events.append(dict(event, id=self.sequence, at=time.time()))
            self.events = self.events[-MAX_EVENTS:]
            payload = json.dumps({'version': 1, 'events': self.events}, ensure_ascii=False)
            while len(payload.encode('utf-8')) > 4 * 1024 * 1024 and len(self.events) > 1:
                self.events = self.events[len(self.events)//2:]
                payload = json.dumps({'version': 1, 'events': self.events}, ensure_ascii=False)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix('.tmp')
            tmp.write_text(payload, encoding='utf-8')
            os.replace(tmp, self.path)

    def snapshot(self, root=None, relative='', limit=100):
        with self.lock:
            events = list(self.events)
        prefix = PureWindowsPath(relative)
        def visible(e):
            if root is not None and e.get('root') not in (root, None):
                return False
            paths = [e[k] for k in ('path', 'from', 'to') if e.get(k)]
            return not paths or not relative or any(PureWindowsPath(p).is_relative_to(prefix) for p in paths)
        return [e for e in events if visible(e)][-limit:]


def permitted(base, relative, blocked):
    """Reject lexical/blocked components first; lstat never follows a reparse point."""
    rel = PureWindowsPath(relative)
    if not rel.parts or rel.is_absolute() or rel.drive or any(
            p in ('.', '..') or ':' in p or p.startswith('.') or p.casefold() in blocked for p in rel.parts):
        return False
    target = Path(base) / Path(relative)
    for p in [*reversed(target.parents), target]:
        try:
            info = p.lstat()
        except FileNotFoundError:
            # Removed/renamed paths no longer exist. Never probe descendants of a missing parent.
            return True
        except OSError:
            return False
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            return False
    return True


if os.name == 'nt':
    KERNEL = ctypes.WinDLL('kernel32', use_last_error=True)
    class OVERLAPPED(ctypes.Structure):
        _fields_ = [('Internal', ctypes.c_size_t), ('InternalHigh', ctypes.c_size_t),
                    ('Offset', wintypes.DWORD), ('OffsetHigh', wintypes.DWORD), ('hEvent', wintypes.HANDLE)]
    def api(name, restype, *args):
        fn = getattr(KERNEL, name)
        fn.restype, fn.argtypes = restype, list(args)
        return fn
    CreateFile = api('CreateFileW', wintypes.HANDLE, wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                     ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE)
    CreateEvent = api('CreateEventW', wintypes.HANDLE, ctypes.c_void_p, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR)
    ReadChanges = api('ReadDirectoryChangesW', wintypes.BOOL, wintypes.HANDLE, ctypes.c_void_p,
                      wintypes.DWORD, wintypes.BOOL, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD),
                      ctypes.POINTER(OVERLAPPED), ctypes.c_void_p)
    GetResult = api('GetOverlappedResult', wintypes.BOOL, wintypes.HANDLE, ctypes.POINTER(OVERLAPPED),
                    ctypes.POINTER(wintypes.DWORD), wintypes.BOOL)
    CancelIo = api('CancelIoEx', wintypes.BOOL, wintypes.HANDLE, ctypes.POINTER(OVERLAPPED))
    Wait = api('WaitForSingleObject', wintypes.DWORD, wintypes.HANDLE, wintypes.DWORD)
    ResetEvent = api('ResetEvent', wintypes.BOOL, wintypes.HANDLE)
    Close = api('CloseHandle', wintypes.BOOL, wintypes.HANDLE)


class Watcher:
    def __init__(self, root, journal, blocked):
        self.root, self.journal, self.blocked = root, journal, blocked
        self.stop_event, self.ready = threading.Event(), threading.Event()
        self.thread = threading.Thread(target=self.run, name='project-files-' + root['id'], daemon=True)
        self.status = 'starting'
        self.error = None
        self.handle = None
        self.old_name = None
        self.modified = {}

    def emit(self, action, **values):
        self.journal.append([dict(values, action=action, root=self.root['id'])])

    def flush_old(self, rows):
        if self.old_name:
            name, _ = self.old_name
            if permitted(self.root['path'], name, self.blocked):
                rows.append({'action': 'rename_from', 'path': name})
            self.old_name = None

    def decode(self, raw):
        rows, pos = [], 0
        while pos < len(raw):
            if pos + 12 > len(raw):
                raise ValueError('short notification header')
            following, action, length = struct.unpack_from('<III', raw, pos)
            if length % 2 or pos + 12 + length > len(raw):
                raise ValueError('invalid notification name')
            name = raw[pos+12:pos+12+length].decode('utf-16-le')
            allowed = permitted(self.root['path'], name, self.blocked)
            if action == 4:
                self.flush_old(rows)
                self.old_name = (name, time.monotonic())
            elif action == 5:
                old = self.old_name
                self.old_name = None
                old_allowed = old and permitted(self.root['path'], old[0], self.blocked)
                if allowed and old_allowed:
                    rows.append({'action': 'rename', 'from': old[0], 'to': name})
                else:
                    if old_allowed:
                        rows.append({'action': 'rename_from', 'path': old[0]})
                    if allowed:
                        rows.append({'action': 'rename_to', 'path': name})
            else:
                self.flush_old(rows)
                label = {1: 'create', 2: 'delete', 3: 'modify'}.get(action)
                if allowed and label:
                    now = time.monotonic()
                    if action != 3 or now - self.modified.get(name, 0) >= 1:
                        rows.append({'action': label, 'path': name})
                    if action == 3:
                        self.modified[name] = now
            if not following:
                break
            if following < 12 + length or pos + following >= len(raw):
                raise ValueError('invalid notification offset')
            pos += following
        if len(self.modified) > 2000:
            self.modified = {}
        self.journal.append([dict(row, root=self.root['id']) for row in rows])

    def run(self):
        event, handle, pending = None, None, False
        overlapped = None
        try:
            if os.name != 'nt':
                raise OSError('Windows directory notifications unavailable')
            base = Path(os.path.abspath(self.root['path']))
            # Verify the watched root itself before opening a recursive directory handle.
            for part in [*reversed(base.parents), base]:
                info = part.lstat()
                if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                    raise OSError('watch root is a reparse point')
            handle = CreateFile(str(base), 1, 7, None, 3, 0x02000000 | 0x40000000, None)
            if handle == ctypes.c_void_p(-1).value:
                handle = None
                raise ctypes.WinError(ctypes.get_last_error())
            self.handle = handle
            event = CreateEvent(None, True, False, None)
            if not event:
                raise ctypes.WinError(ctypes.get_last_error())
            overlapped = OVERLAPPED(hEvent=event)
            buffer = (wintypes.DWORD * 16384)()  # DWORD-aligned 64 KiB
            count = wintypes.DWORD()
            first = True
            while not self.stop_event.is_set():
                ResetEvent(event)
                accepted = ReadChanges(handle, buffer, ctypes.sizeof(buffer), True, 1 | 2 | 8 | 16,
                                       None, ctypes.byref(overlapped), None)
                if not accepted and ctypes.get_last_error() != 997:
                    raise ctypes.WinError(ctypes.get_last_error())
                pending = True
                if first:
                    self.status = 'watching'
                    self.emit('watch_start', folder=str(base))
                    self.ready.set()
                    first = False
                while not self.stop_event.is_set():
                    waited = Wait(event, 250)
                    if waited == 0:
                        break
                    if waited != 258:
                        raise ctypes.WinError(ctypes.get_last_error())
                    if self.old_name and time.monotonic() - self.old_name[1] > 1:
                        rows = []
                        self.flush_old(rows)
                        self.journal.append([dict(row, root=self.root['id']) for row in rows])
                if self.stop_event.is_set():
                    break
                result = GetResult(handle, ctypes.byref(overlapped), ctypes.byref(count), False)
                pending = False
                if not result:
                    error = ctypes.get_last_error()
                    if error == 1022:
                        self.old_name = None
                        self.emit('gap', reason='notification_overflow')
                        continue
                    raise ctypes.WinError(error)
                if count.value == 0:
                    self.old_name = None
                    self.emit('gap', reason='notification_overflow')
                else:
                    try:
                        self.decode(ctypes.string_at(buffer, count.value))
                    except (ValueError, UnicodeError):
                        self.old_name = None
                        self.emit('gap', reason='invalid_notification')
        except Exception as exc:
            self.status, self.error = 'error', str(exc)
            try:
                self.emit('gap', reason='watcher_error', error=type(exc).__name__)
            except OSError:
                pass
        finally:
            if handle and pending:
                CancelIo(handle, ctypes.byref(overlapped))
                # Cancellation is asynchronous. Keep OVERLAPPED and buffer alive until completion.
                count = wintypes.DWORD()
                GetResult(handle, ctypes.byref(overlapped), ctypes.byref(count), True)
            self.handle = None
            if event:
                Close(event)
            if handle:
                Close(handle)
            try:
                rows = []
                self.flush_old(rows)
                self.journal.append([dict(row, root=self.root['id']) for row in rows])
                self.emit('watch_stop', reason='shutdown' if self.stop_event.is_set() else 'error')
            except OSError:
                pass
            if self.status != 'error':
                self.status = 'stopped'
            self.ready.set()


class FileEvents:
    def __init__(self, journal_path, blocked=()):
        self.journal = Journal(journal_path)
        self.blocked = frozenset(blocked)
        self.watchers = []
        self.started = False

    def start(self, roots):
        if self.started:
            return
        self.started = True
        self.watchers = []
        previous = self.journal.snapshot(limit=1)
        self.journal.append([{'action': 'gap', 'reason': 'panel_not_running' if previous else 'history_begins_here',
                              'since': previous[-1]['at'] if previous else None}])
        if self.journal.load_error:
            self.journal.append([{'action': 'gap', 'reason': 'journal_unreadable'}])
        seen = []
        for root in roots:
            path = Path(os.path.abspath(root['path']))
            if any(path.is_relative_to(p) for p in seen):
                continue
            seen.append(path)
            watcher = Watcher(root, self.journal, self.blocked)
            self.watchers.append(watcher)
            watcher.thread.start()

    def stop(self):
        for watcher in self.watchers:
            watcher.stop_event.set()
        # Threads wake within 250 ms, cancel their outstanding I/O, wait for cancellation and close handles.
        for watcher in self.watchers:
            watcher.thread.join(timeout=5)
            if watcher.thread.is_alive():
                watcher.status = 'shutdown_pending'
        self.started = False

    def snapshot(self, root=None, relative=''):
        return {'events': self.journal.snapshot(root, relative), 'history_note': HISTORY_NOTE,
                'watchers': [{'root': w.root['id'], 'status': w.status, 'error': w.error}
                             for w in self.watchers if root is None or w.root['id'] == root]}
