"""
main.py
Entry point utama versi Interaktif (Bot Nanya).
Jalankan: python3 main.py
"""

import asyncio
import os
import nest_asyncio

# =====================================================================
# 1. SETUP INTERAKTIF (BOT NANYA KE USER)
# =====================================================================
import config.settings as settings

def interactive_setup():
    print("\n" + "="*50)
    print("🤖 SETUP BOT SCRAPER")
    print("Kosongkan dan langsung tekan ENTER untuk pakai settingan default.")
    print("="*50)

    # 1. Tanya URL Target
    url = input(f"[?] Target URL ({settings.BASE_URL}): ").strip()
    if url:
        settings.BASE_URL = url

    # 2. Tanya Jumlah Tab (Concurrency)
    conc = input(f"[?] Jumlah Tab Paralel ({settings.CONCURRENCY}): ").strip()
    if conc.isdigit():
        settings.CONCURRENCY = int(conc)

    # 3. Tanya Limit Film
    limit = input(f"[?] Limit film per kategori ({settings.MAX_MOVIES_PER_CATEGORY}): ").strip()
    if limit.isdigit():
        settings.MAX_MOVIES_PER_CATEGORY = int(limit)

    print("="*50 + "\n")

# Panggil fungsi tanya jawabnya SEBELUM script lain diload
interactive_setup()

# =====================================================================
# 2. IMPORT MODUL LAIN SETELAH SETTINGS DIUPDATE
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
    print(f"🌍 Target Website: {settings.BASE_URL}")
    print(f"🚀 Memulai scraping dengan {settings.CONCURRENCY} tab paralel...\n")

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
