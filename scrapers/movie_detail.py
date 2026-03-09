import asyncio
from config.settings import GOTO_TIMEOUT, SNIFF_WAIT, STREAM_PATTERNS
from db.manager import DB_QUEUE

def _is_stream_url(url: str) -> bool:
    """Cek apakah URL adalah link video/stream."""
    return any(pattern in url for pattern in STREAM_PATTERNS)

async def scrape_detail(context, url: str, category: str, sem: asyncio.Semaphore):
    """
    Scrape detail film dengan Auto-Heuristic Scanning.
    Tidak perlu selector manual lagi!
    """
    async with sem:
        page = await context.new_page()
        captured_streams: list[str] = []

        # THE SNIFFER: Nyadap network request
        page.on(
            "request",
            lambda req: captured_streams.append(req.url) if _is_stream_url(req.url) else None
        )

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=GOTO_TIMEOUT)
            
            # 🧠 OTAK HEURISTIC: Biarkan JS di browser yang mikir
            auto_data = await page.evaluate('''() => {
                // 1. Cari Judul (Prioritas: OG Tag -> H1 -> Title Tag)
                let title = document.querySelector('meta[property="og:title"]')?.content || 
                            document.querySelector('h1')?.innerText || 
                            document.title || 'Unknown Title';
                
                // Bersihkan judul dari embel-embel "Nonton Film", dll
                title = title.replace(/(Nonton Film|Nonton|Streaming|Subtitle Indonesia)/gi, '').trim();

                // 2. Cari Sinopsis (Prioritas: OG Tag -> Paragraf Terpanjang)
                let synopsis = document.querySelector('meta[property="og:description"]')?.content;
                if (!synopsis || synopsis.length < 50) {
                    let paragraphs = Array.from(document.querySelectorAll('p'));
                    let longest = paragraphs.sort((a, b) => b.innerText.length - a.innerText.length)[0];
                    synopsis = longest ? longest.innerText : 'No Synopsis';
                }

                // 3. Cari Poster (Prioritas: OG Tag -> Gambar pertama dengan ukuran besar)
                let poster = document.querySelector('meta[property="og:image"]')?.content;
                if (!poster) {
                    let images = Array.from(document.querySelectorAll('img'));
                    let bigImage = images.find(img => img.width > 150 && img.height > 200);
                    poster = bigImage ? bigImage.src : null;
                }

                return { title, synopsis, poster };
            }''')

            # Tunggu stream URL muncul
            await asyncio.sleep(SNIFF_WAIT)

            # Fallback cari iframe kalau sniffer gak nangkep
            stream = captured_streams[0] if captured_streams else None
            if not stream:
                iframe = await page.query_selector("iframe")
                if iframe:
                    stream = await iframe.get_attribute("src")

            movie_data = {
                "url": url,
                "title": auto_data["title"],
                "synopsis": auto_data["synopsis"],
                "poster": auto_data["poster"],
                "stream_link": stream,
            }

            await DB_QUEUE.put(("MOVIE", (movie_data, category)))
            print(f"  ✅ [{category}] {auto_data['title'][:40]}...")

        except Exception as e:
            err_msg = f"{type(e).__name__}: {str(e)[:100]}"
            await DB_QUEUE.put(("ERROR", (url, "DETAIL", err_msg)))
            print(f"  ❌ Gagal: {url[:50]}... — {err_msg}")

        finally:
            await page.close()
