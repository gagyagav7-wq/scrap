“””
scrapers/movie_detail.py
Scraper untuk halaman detail film.

- Network sniffing untuk stream URL
- Ekstrak title, synopsis, poster
- Configurable via settings.py
  “””

import asyncio

from config.settings import (
GOTO_TIMEOUT,
SELECTOR_TIMEOUT,
SELECTORS,
SNIFF_WAIT,
STREAM_PATTERNS,
)
from db.manager import DB_QUEUE

def _is_stream_url(url: str) -> bool:
“”“Cek apakah URL adalah link video/stream.”””
return any(pattern in url for pattern in STREAM_PATTERNS)

async def scrape_detail(context, url: str, category: str, sem: asyncio.Semaphore):
“””
Scrape satu halaman detail film.
Menggunakan network sniffing untuk nangkap stream URL secara real-time.

```
Args:
    context: Playwright BrowserContext
    url: URL halaman detail film
    category: Nama kategori film (untuk DB)
    sem: Semaphore untuk batasi konkurensi
"""
async with sem:
    page = await context.new_page()
    captured_streams: list[str] = []

    # THE SNIFFER: Nyadap semua network request yang lewat
    page.on(
        "request",
        lambda req: captured_streams.append(req.url) if _is_stream_url(req.url) else None
    )

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=GOTO_TIMEOUT)
        await page.wait_for_selector(SELECTORS["title"], timeout=SELECTOR_TIMEOUT)

        # Ekstrak title
        title_el = await page.query_selector(SELECTORS["title"])
        title = (await title_el.inner_text()).strip() if title_el else "Unknown"

        # Ekstrak synopsis
        syn_el = await page.query_selector(SELECTORS["synopsis"])
        synopsis = (await syn_el.inner_text()).strip() if syn_el else "No Synopsis"

        # Ekstrak poster
        poster = None
        poster_el = await page.query_selector(SELECTORS["poster"])
        if poster_el:
            poster = await poster_el.get_attribute("src")

        # Tunggu stream URL muncul dari network activity
        await asyncio.sleep(SNIFF_WAIT)

        # Prioritas: Sniffer result > iframe src
        stream = captured_streams[0] if captured_streams else None
        if not stream:
            iframe = await page.query_selector("iframe")
            if iframe:
                stream = await iframe.get_attribute("src")

        movie_data = {
            "url": url,
            "title": title,
            "synopsis": synopsis,
            "poster": poster,
            "stream_link": stream,
        }

        await DB_QUEUE.put(("MOVIE", (movie_data, category)))
        print(f"  ✅ [{category}] {title[:50]}")

    except Exception as e:
        err_msg = f"{type(e).__name__}: {str(e)[:100]}"
        await DB_QUEUE.put(("ERROR", (url, "DETAIL", err_msg)))
        print(f"  ❌ Gagal: {url[:60]} — {err_msg}")

    finally:
        await page.close()
```
