from __future__ import annotations

import re
import time
from typing import Callable, List, Optional

from playwright.sync_api import Frame, Locator, TimeoutError as PWTimeout

from pages.base_page import BasePage


VISUAL_CONTAINER_SELECTOR = "visual-container, [class*='visualContainerHost']"

_CONTAINER_ANCESTOR_XPATH = (
    "xpath=ancestor-or-self::visual-container"
    " | ancestor-or-self::*[contains(@class,'visualContainerHost')]"
)

_STRATEGY_PROBE_MS = 2500


class ReportPage(BasePage):

    def _frame(self) -> Frame:
        for frame in self.page.frames:
            if frame is self.page.main_frame:
                continue
            url = (frame.url or "").lower()
            if "powerbi" in url or "fabric" in url:
                return frame
        return self.page.main_frame


    def wait_for_visuals_ready(self, timeout: int = 30000) -> "ReportPage":
        self.page.wait_for_load_state("networkidle")
        self._frame().wait_for_selector(VISUAL_CONTAINER_SELECTOR, timeout=timeout)
        return self


    def scroll_report_by(self, dy: int = 400, dx: int = 0) -> "ReportPage":
        frame = self._frame()
        frame.evaluate(
            r"""([dx, dy]) => {
                const pick = () => {
                    const fixed = document.querySelector('.mid-viewport');
                    if (fixed && fixed.scrollHeight > fixed.clientHeight) return fixed;
                    let best = null, bestArea = 0;
                    for (const n of document.querySelectorAll('*')) {
                        const cs = getComputedStyle(n);
                        const oy = cs.overflowY, ox = cs.overflowX;
                        const scY = (oy === 'auto' || oy === 'scroll') && n.scrollHeight > n.clientHeight + 2;
                        const scX = (ox === 'auto' || ox === 'scroll') && n.scrollWidth > n.clientWidth + 2;
                        if (!scY && !scX) continue;
                        const area = n.clientWidth * n.clientHeight;
                        if (area > bestArea) { best = n; bestArea = area; }
                    }
                    return best;
                };
                const el = pick();
                if (!el) throw new Error('No scrollable report viewport found');
                el.scrollBy({ left: dx, top: dy, behavior: 'instant' });
            }""",
            [dx, dy],
        )
        return self

    def scroll_container_into_view(self, container: Locator) -> "ReportPage":
        container.scroll_into_view_if_needed()
        return self


    def container_by_title(self, title: str, timeout: int = 30000) -> Locator:

        frame = self._frame()
        pattern = re.compile(re.escape(title), re.IGNORECASE)
        css_title = _css_escape(title)

        strategies: List[Callable[[], Locator]] = [
            lambda: frame.get_by_role("heading", name=pattern).first,
            lambda: frame.locator(f"[aria-label*={css_title} i]").first,
            lambda: frame.locator(f"[title*={css_title} i]").first,
            lambda: frame.get_by_text(pattern, exact=False).first,
        ]

        return self._first_visible_container(strategies, timeout=timeout, label=title)

    def container_by_column_header(self, header: str, timeout: int = 30000) -> Locator:
        frame = self._frame()
        pattern = re.compile(re.escape(header), re.IGNORECASE)
        css_header = _css_escape(header)

        strategies: List[Callable[[], Locator]] = [
            lambda: frame.get_by_role("columnheader", name=pattern).first,
            lambda: (
                frame.locator(".pivotTableCellWrap, [class*='pivotTableCell']")
                .filter(has_text=pattern)
                .first
            ),
            lambda: frame.locator(f"[aria-label*={css_header} i]").first,
            lambda: frame.locator(f"[title*={css_header} i]").first,
        ]

        return self._first_visible_container(strategies, timeout=timeout, label=header)

    def list_visible_titles(self) -> List[str]:

        frame = self._frame()
        titles: List[str] = []
        for loc in frame.get_by_role("heading").all():
            try:
                if loc.is_visible():
                    titles.append(loc.inner_text().strip())
            except Exception:
                continue
        for loc in frame.locator("[aria-label]").all()[:200]:
            try:
                if loc.is_visible():
                    label = loc.get_attribute("aria-label") or ""
                    if label.strip():
                        titles.append(label.strip())
            except Exception:
                continue
        seen = set()
        out = []
        for t in titles:
            if t not in seen:
                seen.add(t)
                out.append(t)
        return out

    def _first_visible_container(
        self,
        strategies: List[Callable[[], Locator]],
        timeout: int,
        label: str,
    ) -> Locator:
        deadline = time.monotonic() + max(timeout, _STRATEGY_PROBE_MS) / 1000.0
        last_error: Optional[BaseException] = None

        while time.monotonic() < deadline:
            for build in strategies:
                remaining_ms = int((deadline - time.monotonic()) * 1000)
                if remaining_ms <= 0:
                    break
                slice_ms = min(_STRATEGY_PROBE_MS, remaining_ms)
                try:
                    loc = build()
                    loc.wait_for(state="visible", timeout=slice_ms)
                except PWTimeout as err:
                    last_error = err
                    continue
                except Exception as err:
                    last_error = err
                    continue

                ancestor = loc.locator(_CONTAINER_ANCESTOR_XPATH).first
                if ancestor.count() > 0:
                    return ancestor
                return loc

        raise last_error or PWTimeout(
            f"No locator strategy found a visible match for: {label!r}"
        )


def _css_escape(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'
