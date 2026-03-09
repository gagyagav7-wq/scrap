import asyncio
import os
import nest_asyncio

# =====================================================================
# 1. SETUP INTERAKTIF + PATH INTERNAL STORAGE
# =====================================================================
import config.settings as settings

def interactive_setup():
    print("\n" + "="*50)
    print("🤖 SETUP BOT SCRAPER (INTERNAL STORAGE MODE)")
    print("="*50)

    # 1. Tanya URL Target
    url = input(f"[?] Target URL ({settings.BASE_URL}): ").strip()
    if url:
        settings.BASE_URL = url

    # 2. Tanya Lokasi Simpan
    print("\n[?] Simpan hasil ke mana?")
    print(" 1. Folder Script (Default)")
    print(" 2. Internal HP (Folder Download/Scraper)")
    pilihan = input("Pilih (1/2): ").strip()

    if pilihan == "2":
        # Path umum internal storage di Ubuntu PRoot/Chroot biasanya di /sdcard atau /storage/emulated/0
        internal_path = "/sdcard/Download/Scraper_Results"
        os.makedirs(internal_path, exist_ok=True)
        settings.DB_PATH = f"{internal_path}/scraped_data.db"
        # Kita juga perlu update path CSV di helpers nantinya kalau mau otomatis
        print(f"✅ Lokasi diset ke: {internal_path}")
    else:
        os.makedirs("output", exist_ok=True)
        print("✅ Lokasi diset ke: folder output internal script")

    # 3. Tanya Jumlah Tab
    conc = input(f"\n[?] Jumlah Tab Paralel ({settings.CONCURRENCY}): ").strip()
    if conc.isdigit():
        settings.CONCURRENCY = int(conc)

    print("="*50 + "\n")

interactive_setup()

# =====================================================================
# 2. IMPORT MODUL (Sama seperti sebelumnya)
# =====================================================================
from playwright.async_api import async_playwright
from core.browser import create_browser_context
from core.discovery import discover_targets
from db.manager import DB_QUEUE, db_writer
from scrapers.category_list import scrape_category
from utils.helpers import export_to_csv, print_banner, print_stats

nest_asyncio.apply()

async def main():
    print_banner()
    
    # Pastikan directory DB sudah ada sebelum writer jalan
    db_dir = os.path.dirname(settings.DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    writer_task = asyncio.create_task(db_writer())

    async with async_playwright() as p:
        browser, context = await create_browser_context(p)
        try:
            targets = await discover_targets(context)
            if not targets: return

            for target in targets:
                await scrape_category(context, target)
        finally:
            await browser.close()

    await DB_QUEUE.join()
    await DB_QUEUE.put(None)
    await writer_task

    print_stats()
    # Export CSV ke lokasi yang sama dengan DB
    csv_path = settings.DB_PATH.replace(".db", ".csv")
    export_to_csv(db_path=settings.DB_PATH, output_path=csv_path)
    
    print(f"\n✨ SELESAI! Cek file di: {settings.DB_PATH}")

if __name__ == "__main__":
    asyncio.run(main())
