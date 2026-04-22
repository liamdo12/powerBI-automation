import os
import sys
from pathlib import Path
from constants.urls import BASE_URL

from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def before_all(context):
    ud = context.config.userdata
    context.browser_name = ud.get("browser", "chromium")
    context.headless = _bool(ud.get("headless"), default=True)
    context.base_url = ud.get("base_url", BASE_URL)
    context.slow_mo = int(ud.get("slow_mo", "0") or 0)
    context.visual_timeout = int(ud.get("visual_timeout", "30000") or 30000)
    context.viewport = {
        "width": int(ud.get("viewport_width", "1280") or 1280),
        "height": int(ud.get("viewport_height", "720") or 720),
    }

    context.playwright = sync_playwright().start()
    browser_type = getattr(context.playwright, context.browser_name)
    context.browser = browser_type.launch(
        headless=context.headless,
        slow_mo=context.slow_mo,
    )


def before_scenario(context, scenario):
    context.playwright_context = context.browser.new_context(viewport=context.viewport)
    context.page = context.playwright_context.new_page()
    context.page.set_default_timeout(context.visual_timeout)
    context.page.set_default_navigation_timeout(context.visual_timeout)


def after_step(context, step):
    status = getattr(step.status, "name", str(step.status))
    if status in ("failed", "error"):
        artifacts = PROJECT_ROOT / "reports" / "screenshots"
        artifacts.mkdir(parents=True, exist_ok=True)
        safe_name = step.name.replace(" ", "_").replace("/", "_")[:80]
        path = artifacts / f"{safe_name}.png"
        try:
            context.page.screenshot(path=str(path), full_page=True)
        except Exception:
            pass


def after_scenario(context, scenario):
    ctx = getattr(context, "playwright_context", None)
    if ctx is not None:
        ctx.close()


def after_all(context):
    browser = getattr(context, "browser", None)
    if browser is not None:
        browser.close()
    pw = getattr(context, "playwright", None)
    if pw is not None:
        pw.stop()
