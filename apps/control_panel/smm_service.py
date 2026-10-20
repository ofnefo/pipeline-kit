"""Local editorial workspace. No remote sends or background scheduler.

SQLite transactions + revision checks protect edits from concurrent browser tabs.
Provider/account permissions are deliberately separate from an editorial ready state.
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
import kit_config as config
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

router = APIRouter(prefix='/api/smm', tags=['smm'])
DB = config.workspace('state/smm.sqlite3')
CATALOG = Path(__file__).parent.parent / 'catalog' / 'smm.json'
STATES = {'idea': 'Идеи', 'production': 'В работе', 'review': 'На проверке',
          'ready': 'Готово к публикации', 'archived': 'Архив'}
NETWORKS = {'telegram': 'Telegram', 'instagram': 'Instagram', 'tiktok': 'TikTok',
            'vk': 'VK', 'youtube': 'YouTube', 'website': 'Сайт / SEO'}


def catalog():
    return json.loads(CATALOG.read_text(encoding='utf-8'))


def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA journal_mode=WAL')
    db.executescript('''
        CREATE TABLE IF NOT EXISTS posts (
            id TEXT PRIMARY KEY, revision INTEGER NOT NULL, payload TEXT NOT NULL,
            updated TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS accounts (
            brand TEXT NOT NULL, network TEXT NOT NULL, handle TEXT NOT NULL,
            PRIMARY KEY(brand, network));
        CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY, post_id TEXT, action TEXT, revision INTEGER, at TEXT);
    ''')
    with db:
        if db.execute("INSERT OR IGNORE INTO meta VALUES ('seed', '1')").rowcount:
            for post in catalog()['starter_posts']:
                insert_post(db, post)
    return db


def insert_post(db, payload):
    ident = uuid4().hex
    now = datetime.now().astimezone().isoformat()
    db.execute('INSERT INTO posts VALUES (?,1,?,?)', (ident, json.dumps(payload, ensure_ascii=False), now))
    db.execute('INSERT INTO events(post_id,action,revision,at) VALUES (?,?,1,?)', (ident, 'created', now))
    return ident


def unpack(row):
    return {**json.loads(row['payload']), 'id': row['id'], 'revision': row['revision'], 'updated': row['updated']}


class Post(BaseModel):
    brand: str
    title: str = Field(min_length=1, max_length=180)
    network: Literal['telegram', 'instagram', 'tiktok', 'vk', 'youtube', 'website']
    status: Literal['idea', 'production', 'review', 'ready', 'archived'] = 'idea'
    text: str = Field(default='', max_length=16000)
    asset: str = Field(default='', max_length=2000)
    scheduled: str = Field(default='', max_length=40)
    campaign: str = Field(default='', max_length=120)
    cta: str = Field(default='', max_length=500)
    notes: str = Field(default='', max_length=4000)

    @field_validator('brand')
    @classmethod
    def known_brand(cls, value):
        if value not in {b['id'] for b in catalog()['brands']}:
            raise ValueError('Неизвестный бренд')
        return value

    @field_validator('title')
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError('Добавьте название')
        return value.strip()

    @field_validator('scheduled')
    @classmethod
    def date(cls, value):
        if value:
            dt = datetime.fromisoformat(value)
            if dt.tzinfo is None:
                raise ValueError('Укажите дату с часовым поясом')
        return value


class Revision(Post):
    revision: int = Field(ge=1)


class Batch(BaseModel):
    posts: list[Post] = Field(min_length=1, max_length=12)


class Account(BaseModel):
    brand: str
    network: str
    handle: str = Field(max_length=250)


@router.get('')
def state():
    db = connect()
    try:
        data = catalog()
        return {'brands': data['brands'], 'providers': data['providers'], 'states': STATES,
                'networks': NETWORKS, 'posting_enabled': False,
                'posts': [unpack(x) for x in db.execute('SELECT * FROM posts ORDER BY updated DESC')],
                'accounts': [dict(x) for x in db.execute('SELECT * FROM accounts')]}
    finally:
        db.close()


@router.post('/posts')
def create(body: Batch):
    db = connect()
    try:
        with db:
            ids = [insert_post(db, p.model_dump()) for p in body.posts]
        return {'ids': ids, 'published': False}
    finally:
        db.close()


@router.put('/posts/{ident}')
def update(ident: str, body: Revision):
    db = connect()
    try:
        with db:
            now = datetime.now().astimezone().isoformat()
            count = db.execute('UPDATE posts SET revision=revision+1,payload=?,updated=? WHERE id=? AND revision=?',
                               (json.dumps(body.model_dump(exclude={'revision'}), ensure_ascii=False), now, ident, body.revision)).rowcount
            if not count:
                exists = db.execute('SELECT 1 FROM posts WHERE id=?', (ident,)).fetchone()
                raise HTTPException(409 if exists else 404,
                                    'Карточка изменена в другом окне. Сохраните свой текст и откройте актуальную версию.' if exists else 'Карточка не найдена')
            db.execute('INSERT INTO events(post_id,action,revision,at) VALUES (?,?,?,?)',
                       (ident, 'edited', body.revision + 1, now))
        return {'id': ident, 'revision': body.revision + 1, 'published': False}
    finally:
        db.close()


@router.put('/accounts')
def account(body: Account):
    if body.brand not in {b['id'] for b in catalog()['brands']} or body.network not in NETWORKS:
        raise HTTPException(400, 'Неизвестный бренд или площадка')
    db = connect()
    try:
        with db:
            db.execute('INSERT INTO accounts VALUES (?,?,?) ON CONFLICT(brand,network) DO UPDATE SET handle=excluded.handle',
                       (body.brand, body.network, body.handle.strip()))
        return {'saved': True, 'connected': False}
    finally:
        db.close()


@router.get('/export')
def export(brand: str = ''):
    data = state()
    if brand and brand not in {b['id'] for b in data['brands']}:
        raise HTTPException(400, 'Неизвестный бренд')
    return JSONResponse({'schema': 'smm-editorial-package/v1', 'published': False,
                         'timezone': 'Europe/Moscow', 'assets': 'references-only',
                         'posts': [p for p in data['posts'] if p['status'] != 'archived' and (not brand or p['brand'] == brand)]},
                        headers={'Content-Disposition': 'attachment; filename="smm-editorial-package.json"'})


# Publishing accounts and remote delivery are optional external integrations.
