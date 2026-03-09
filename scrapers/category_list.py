“””
scrapers/category_list.py
Scraper untuk halaman list/kategori film.
Ambil semua link film dari satu halaman kategori.
“””

import asyncio

from config.settings import (
BASE_URL,
CHUNK_SIZE,
CONCURRENCY,
GOTO_TIMEOUT,
MAX_MOVIES_PER_CATEGORY,
SELECTOR_TIMEOUT,
SELECTORS,
)
from db.manager import DB_QUEUE
from scrapers.movie_detail import scrape_detail

async def scrape_category(context, target: dict):
“””
Scrape semua film dari satu halaman kategori.
Proses link dalam chunk untuk stabilitas memori.

```
Args:
    context: Playwright BrowserContext
    target: dict dengan keys "url" dan "cat"
"""
url = target["url"]
cat = target["cat"]
sem = asyncio.Semaphore(CONCURRENCY)
page = await context.new_page()

try:
    print(f"\n📂 Scraping kategori: {cat}")
    await page.goto(url, wait_until="domcontentloaded", timeout=GOTO_TIMEOUT)
    await page.wait_for_selector(SELECTORS["movie_list"], timeout=SELECTOR_TIMEOUT)

    links = await page.evaluate(
        f"() => [...document.querySelectorAll('{SELECTORS['movie_list']}')].map(a => a.href)"
    )

    # Filter hanya link dari domain yang sama
    unique_links = list(dict.fromkeys([
        l for l in links if BASE_URL in l
    ]))

    # Terapkan limit jika dikonfigurasi
    if MAX_MOVIES_PER_CATEGORY > 0:
        unique_links = unique_links[:MAX_MOVIES_PER_CATEGORY]

    print(f"  📋 Ditemukan {len(unique_links)} film.")

    # Proses per chunk
    for i in range(0, len(unique_links), CHUNK_SIZE):
        chunk = unique_links[i:i + CHUNK_SIZE]
        print(f"  ⚙️  Batch {i // CHUNK_SIZE + 1}: {len(chunk)} film...")
        tasks = [scrape_detail(context, link, cat, sem) for link in chunk]
        await asyncio.gather(*tasks)

except Exception as e:
    err_msg = str(e)[:200]
    await DB_QUEUE.put(("ERROR", (url, "LIST", err_msg)))
    print(f"  ❌ Kategori gagal: {cat} — {err_msg}")

finally:
    await page.close()
```
