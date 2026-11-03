"""Tiny DB layer: Postgres (DATABASE_URL) or SQLite (DB_PATH) fallback for tests/local. Optional DB_SCHEMA puts tables in their own Postgres schema (for sharing a DB)."""
import os, sqlite3
from contextlib import contextmanager
URL=os.environ.get("DATABASE_URL",""); PG=URL.startswith("postgres"); SCH=os.environ.get("DB_SCHEMA","")
if PG:
    import psycopg
    from psycopg.rows import dict_row
class C:
    def __init__(s,raw): s.raw=raw
    def execute(s,sql,p=()):
        if PG:
            cur=s.raw.cursor(); cur.execute(sql.replace("?","%s"),p); return cur
        return s.raw.execute(sql,p)
    def executescript(s,sql):
        for st in [x.strip() for x in sql.split(";") if x.strip()]: s.execute(st)
@contextmanager
def db():
    if PG:
        raw=psycopg.connect(URL,row_factory=dict_row)
        if SCH: raw.execute(f'create schema if not exists "{SCH}"'); raw.execute(f'set search_path to "{SCH}"')
    else:
        raw=sqlite3.connect(os.environ.get("DB_PATH","/tmp/lienwaiver.db")); raw.row_factory=sqlite3.Row
    try: yield C(raw); raw.commit()
    finally: raw.close()
ID="serial primary key" if PG else "integer primary key"
BLOB="bytea" if PG else "blob"
