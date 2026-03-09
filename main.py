"""
main.py
Entry point utama versi CLI.
Jalankan: python3 main.py --help
"""

import asyncio
import os
import argparse
import nest_asyncio

# =====================================================================
# 1. SETUP CLI MENGGUNAKAN ARGPARSE (HARUS DI ATAS!)
# =====================================================================
parser = argparse.ArgumentParser(description="🕷️ UNIVERSAL SCRAPER CLI")
parser.add_argument("-u", "--url", type=str, help="Target Base URL (contoh: http://178.62.86.69)")
parser.add_argument("-c", "--concurrency", type=int, help="Jumlah tab browser paralel (default dari settings)")
parser.add_argument("-l", "--limit", type=int, help="Max movie per kategori (0 = unlimited)")
args = parser.parse_args()

# =====================================================================
# 2. OVERRIDE SETTINGS SECARA DINAMIS DI MEMORI
# =====================================================================
import config.settings as settings

if args.url:
    settings.BASE_URL = args.url
if args.concurrency is not None:
    settings.CONCURRENCY = args.concurrency
if args.limit is not None:
    settings.MAX_MOVIES_PER_CATEGORY = args.limit

# =====================================================================
# 3. IMPORT MODUL LAIN SETELAH SETTINGS DIUPDATE
# =====================================================================
from playwright.async_api import async_playwright
from core.browser import create_browser_context
from core.discovery import discover_targets
from db.manager import DB_QUEUE, db_writer
from scrapers.category_list import scrape_category
from utils.helpers import export_to_csv, print_banner, print_stats

nest_asyncio.apply()

# Pastikan folder output ada
os.makedirs("output", exist_ok=True)

async def main():
    print_banner()
    print(f"🌍 Target URL: {settings.BASE_URL}")
    print(f"🚀 Memulai operasi scraping dengan {settings.CONCURRENCY} tab paralel...\n")

    # Start background DB writer
    writer_task = asyncio.create_task(db_writer())

    async with async_playwright() as p:
        browser, context = await create_browser_context(p)

        try:
            # FASE 1: Discovery
            print("=" * 50)
            print("FASE 1: DISCOVERY")
            print("=" * 50)
            targets = await discover_targets(context)

            if not targets:
                print("⚠️  Tidak ada target ditemukan. Cek SEED_PATHS di config/settings.py")
                return

            # FASE 2: Panen
            print("\n" + "=" * 50)
            print(f"FASE 2: SCRAPING ({len(targets)} kategori)")
            print("=" * 50)

            for target in targets:
                await scrape_category(context, target)

        finally:
            await browser.close()

    # SHUTDOWN PROTOCOL
    print("\n⏳ Menyelesaikan penulisan database...")
    await DB_QUEUE.join()
    await DB_QUEUE.put(None)  # Sinyal shutdown ke writer
    await writer_task

    # Laporan akhir
    print("\n" + "=" * 50)
    print_stats()
    export_to_csv()
    print("✨ OPERASI SELESAI!")

if __name__ == "__main__":
    asyncio.run(main())
