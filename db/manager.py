“””
db/manager.py
Handles all database operations: init, write queue, dan error logging.
“””

import asyncio
import sqlite3
import time

from config.settings import DB_PATH, DB_QUEUE_SIZE

DB_QUEUE: asyncio.Queue = asyncio.Queue(maxsize=DB_QUEUE_SIZE)

def init_db(path: str = DB_PATH) -> sqlite3.Connection:
“”“Inisialisasi database SQLite dengan WAL mode untuk performa tinggi.”””
conn = sqlite3.connect(path)
cur = conn.cursor()
cur.execute(“PRAGMA journal_mode=WAL;”)
cur.execute(“PRAGMA synchronous=NORMAL;”)

```
cur.execute('''
    CREATE TABLE IF NOT EXISTS movies (
        url         TEXT PRIMARY KEY,
        title       TEXT,
        synopsis    TEXT,
        poster      TEXT,
        stream_link TEXT,
        scraped_at  INTEGER
    )
''')
cur.execute('''
    CREATE TABLE IF NOT EXISTS movie_categories (
        url      TEXT,
        category TEXT,
        PRIMARY KEY (url, category)
    )
''')
cur.execute('''
    CREATE TABLE IF NOT EXISTS crawl_errors (
        url       TEXT,
        stage     TEXT,
        error_msg TEXT,
        timestamp INTEGER
    )
''')
conn.commit()
return conn
```

async def db_writer():
“””
Async consumer yang duduk di background, baca dari DB_QUEUE,
dan commit ke SQLite setiap 25 record atau pas shutdown.
“””
conn = init_db()
cur = conn.cursor()
pending = 0
print(“🏠 DB Writer: Standby…”)

```
try:
    while True:
        task = await DB_QUEUE.get()
        try:
            if task is None:  # Sinyal shutdown
                if pending > 0:
                    conn.commit()
                    print(f"💾 DB Writer: Final commit ({pending} records).")
                return

            task_type, data = task

            if task_type == "MOVIE":
                movie, category = data
                cur.execute('''
                    INSERT INTO movies (url, title, synopsis, poster, stream_link, scraped_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(url) DO UPDATE SET
                        title       = excluded.title,
                        synopsis    = excluded.synopsis,
                        stream_link = excluded.stream_link,
                        scraped_at  = excluded.scraped_at
                ''', (
                    movie["url"], movie["title"], movie["synopsis"],
                    movie.get("poster"), movie.get("stream_link"), int(time.time())
                ))
                cur.execute(
                    "INSERT OR IGNORE INTO movie_categories VALUES (?, ?)",
                    (movie["url"], category)
                )

            elif task_type == "ERROR":
                url, stage, msg = data
                cur.execute(
                    "INSERT INTO crawl_errors VALUES (?, ?, ?, ?)",
                    (url, stage, msg, int(time.time()))
                )

            pending += 1
            if pending >= 25:
                conn.commit()
                pending = 0

        finally:
            DB_QUEUE.task_done()

finally:
    conn.close()
    print("🔒 DB Writer: Koneksi ditutup.")
```
