import asyncio
import os

import nest_asyncio
from playwright.async_api import async_playwright

from core.browser import create_browser_context
from core.discovery import discover_targets
from db.manager import DB_QUEUE, db_writer
from scrapers.category_list import scrape_category
from utils.helpers import export_to_csv, print_banner, print_stats

nest_asyncio.apply()

# Pastikan folder output ada

os.makedirs(“output”, exist_ok=True)

async def main():
print_banner()
print(“🚀 Memulai operasi scraping…\n”)

```
# Start background DB writer
writer_task = asyncio.create_task(db_writer())

async with async_playwright() as p:
    browser, context = await create_browser_context(p)

    try:
        # FASE 1: Discovery - cari semua kategori
        print("=" * 50)
        print("FASE 1: DISCOVERY")
        print("=" * 50)
        targets = await discover_targets(context)

        if not targets:
            print("⚠️  Tidak ada target ditemukan. Cek SEED_PATHS di config/settings.py")
            return

        # FASE 2: Panen - scrape tiap kategori
        print("\n" + "=" * 50)
        print(f"FASE 2: SCRAPING ({len(targets)} kategori)")
        print("=" * 50)

        for target in targets:
            await scrape_category(context, target)

    finally:
        await browser.close()

# SHUTDOWN PROTOCOL: Pastikan semua data tersimpan
print("\n⏳ Menyelesaikan penulisan database...")
await DB_QUEUE.join()
await DB_QUEUE.put(None)  # Sinyal shutdown ke writer
await writer_task

# Laporan akhir
print("\n" + "=" * 50)
print_stats()
export_to_csv()
print("✨ OPERASI SELESAI!")
```

if **name** == “**main**”:
asyncio.run(main())
