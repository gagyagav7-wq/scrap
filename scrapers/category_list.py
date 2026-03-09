import asyncio
from config.settings import (
    BASE_URL, CHUNK_SIZE, CONCURRENCY, GOTO_TIMEOUT, MAX_MOVIES_PER_CATEGORY
)
from db.manager import DB_QUEUE
from scrapers.movie_detail import scrape_detail

async def scrape_category(context, target: dict):
    """
    Mencari link film menggunakan logika Auto-Detect.
    """
    url = target["url"]
    cat = target["cat"]
    sem = asyncio.Semaphore(CONCURRENCY)
    page = await context.new_page()

    try:
        print(f"\n📂 Scraping kategori: {cat}")
        await page.goto(url, wait_until="domcontentloaded", timeout=GOTO_TIMEOUT)

        # 🧠 OTAK HEURISTIC LIST: Cari link yang bungkus gambar (biasanya itu link film)
        links = await page.evaluate(f'''(baseUrl) => {{
            let allLinks = Array.from(document.querySelectorAll('a'));
            
            // Filter: Link harus ke domain yang sama & membungkus sebuah <img>
            let movieLinks = allLinks
                .filter(a => a.href.includes(baseUrl) && a.querySelector('img'))
                .map(a => a.href);
            
            return [...new Set(movieLinks)]; // Hapus duplikat
        }}''', BASE_URL)

        if MAX_MOVIES_PER_CATEGORY > 0:
            links = links[:MAX_MOVIES_PER_CATEGORY]

        print(f"  📋 Ditemukan {len(links)} potensi link film.")

        for i in range(0, len(links), CHUNK_SIZE):
            chunk = links[i:i + CHUNK_SIZE]
            print(f"  ⚙️  Batch {i // CHUNK_SIZE + 1}: {len(chunk)} film...")
            tasks = [scrape_detail(context, link, cat, sem) for link in chunk]
            await asyncio.gather(*tasks)

    except Exception as e:
        err_msg = str(e)[:200]
        await DB_QUEUE.put(("ERROR", (url, "LIST", err_msg)))
        print(f"  ❌ Kategori gagal: {cat} — {err_msg}")

    finally:
        await page.close()
