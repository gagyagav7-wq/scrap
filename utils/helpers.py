“””
utils/helpers.py
Helper functions: stats reporter, export utilities, dll.
“””

import sqlite3
import time

from config.settings import DB_PATH

def print_banner():
“”“Print banner saat startup.”””
print(”””
╔══════════════════════════════════════════╗
║     🕷️  UNIVERSAL SCRAPER v1.0          ║
║     Modular • Fast • Configurable        ║
╚══════════════════════════════════════════╝
“””)

def print_stats(db_path: str = DB_PATH):
“”“Print ringkasan hasil scraping dari database.”””
conn = sqlite3.connect(db_path)
cur = conn.cursor()

```
total_movies = cur.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
with_stream  = cur.execute("SELECT COUNT(*) FROM movies WHERE stream_link IS NOT NULL").fetchone()[0]
total_errors = cur.execute("SELECT COUNT(*) FROM crawl_errors").fetchone()[0]
categories   = cur.execute("SELECT COUNT(DISTINCT category) FROM movie_categories").fetchone()[0]

conn.close()

print(f"""
```

📊 HASIL SCRAPING:
🎬 Total film   : {total_movies}
🎥 Punya stream : {with_stream}
📂 Kategori     : {categories}
❌ Error        : {total_errors}
💾 Database     : {db_path}
“””)

def export_to_csv(db_path: str = DB_PATH, output_path: str = “output/movies.csv”):
“”“Export data movies dari DB ke CSV.”””
import csv
conn = sqlite3.connect(db_path)
cur = conn.cursor()

```
rows = cur.execute("""
    SELECT m.url, m.title, m.synopsis, m.stream_link, 
           GROUP_CONCAT(mc.category, ' | ') as categories
    FROM movies m
    LEFT JOIN movie_categories mc ON m.url = mc.url
    GROUP BY m.url
""").fetchall()
conn.close()

with open(output_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["URL", "Title", "Synopsis", "Stream Link", "Categories"])
    writer.writerows(rows)

print(f"✅ CSV exported: {output_path} ({len(rows)} rows)")
```
