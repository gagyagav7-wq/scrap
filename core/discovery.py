“””
core/discovery.py
Engine untuk discovery kategori/halaman dari seed pages.
Bisa dikustomisasi lewat config/settings.py.
“””

import re
from urllib.parse import urljoin

from config.settings import BASE_URL, CATEGORY_PATTERNS, SEED_PATHS

async def discover_targets(context) -> list[dict]:
“””
Crawl seed pages dan ekstrak semua URL kategori berdasarkan
pattern yang didefinisikan di settings.py.

```
Returns:
    List of dict: [{"url": str, "cat": str}, ...]
"""
seed_urls = [BASE_URL + path for path in SEED_PATHS]
targets = []
page = await context.new_page()

for seed in seed_urls:
    try:
        print(f"  🔍 Scanning seed: {seed}")
        await page.goto(seed, wait_until="domcontentloaded", timeout=30000)
        hrefs = await page.evaluate(
            "() => [...document.querySelectorAll('a[href]')].map(a => a.href)"
        )
        for href in hrefs:
            for pattern, type_group, name_group in CATEGORY_PATTERNS:
                m = re.search(pattern, href)
                if m:
                    targets.append({
                        "url": urljoin(BASE_URL, href),
                        "cat": f"{m.group(type_group).title()}-{m.group(name_group).title()}"
                    })
                    break  # Satu href, satu kategori
    except Exception as e:
        print(f"  ⚠️  Seed gagal ({seed}): {e}")

await page.close()

# Deduplicate by URL
unique = list({t["url"]: t for t in targets}.values())
print(f"✅ Discovery selesai: {len(unique)} kategori ditemukan.")
return unique
```
