“””
core/browser.py
Setup dan konfigurasi Playwright browser context.
“””

from playwright.async_api import Browser, BrowserContext, async_playwright

from config.settings import BLOCKED_RESOURCE_TYPES, USER_AGENT

async def block_assets(route):
“””
Intercept semua request dan blokir resource yang nggak perlu.
Script & CSS tetap jalan biar player bisa render.
“””
if route.request.resource_type in BLOCKED_RESOURCE_TYPES:
await route.abort()
else:
await route.continue_()

async def create_browser_context(playwright) -> tuple[Browser, BrowserContext]:
“”“Launch browser dan buat context dengan konfigurasi optimal.”””
browser = await playwright.chromium.launch(headless=True)
context = await browser.new_context(user_agent=USER_AGENT)
await context.route(”**/*”, block_assets)
return browser, context
