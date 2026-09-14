#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：leadgraph 
@File ：studio_store.py
@Author ：zlh
@Date ：2026-09-14 10:20 
"""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


def now():
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.execute('CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, payload TEXT NOT NULL)')

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=10)
        try:
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def create(self, run):
        with self.connection() as db:
            db.execute('INSERT INTO runs VALUES (?,?)', (run['id'], json.dumps(run, ensure_ascii=False)))
        return run

    def get(self, run_id):
        with self.connection() as db:
            row = db.execute('SELECT payload FROM runs WHERE id=?', (run_id,)).fetchone()
        if row is None:
            raise KeyError(run_id)
        return json.loads(row[0])

    def list(self, limit=100):
        with self.connection() as db:
            sql = 'SELECT payload FROM runs ORDER BY rowid DESC'
            if limit is not None:
                sql += ' LIMIT ' + str(max(0, int(limit)))
            return [json.loads(row[0]) for row in db.execute(sql)]

    def mutate(self, run_id, fn):
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT payload FROM runs WHERE id=?', (run_id,)).fetchone()
            if row is None:
                raise KeyError(run_id)
            run = json.loads(row[0])
            result = fn(run)
            run['updated_at'] = now()
            run['version'] = run.get('version', 0) + 1
            db.execute('UPDATE runs SET payload=? WHERE id=?', (json.dumps(run, ensure_ascii=False), run_id))
            return result

    def recover_interrupted(self):
        with self.connection() as db:
            items = [json.loads(row[0]) for row in db.execute('SELECT payload FROM runs')]
        for item in items:
            if item['status'] not in {'researching', 'contacts_searching', 'drafting'} and not any(
                draft['status'] == 'sending' for draft in item.get('drafts', [])
            ):
                continue
            def recover(run):
                if run['status'] in {'researching', 'contacts_searching', 'drafting'}:
                    run['status'] = 'interrupted'
                    run['notice'] = '服务重启，未完成的操作已停止。已保存的结果仍可查看。'
                for draft in run.get('drafts', []):
                    if draft['status'] == 'sending':
                        draft['status'] = 'unknown'
                        draft['error'] = '服务在发送期间中断。请检查邮箱发件记录，系统不会自动重发。'
            self.mutate(item['id'], recover)
