from __future__ import annotations

import re
import time
from typing import Callable, List, Optional

from playwright.sync_api import Frame, Locator, TimeoutError as PWTimeout

from pages.base_page import BasePage


VISUAL_CONTAINER_SELECTOR = "visual-container, [class*='visualContainerHost']"

_CONTAINER_ANCESTOR_XPATH = (
    "xpath=(ancestor-or-self::visual-container"
    " | ancestor-or-self::*[contains(@class,'visualContainerHost')])[last()]"
)

_STRATEGY_PROBE_MS = 2500

_FIND_CHART_SCROLLBAR_JS = r"""el => {
    let root = el;
    const host = el.querySelector('[aria-label]');
    if (host) {
        const r = host.getBoundingClientRect();
        if (r.width > 0 && r.height > 0) root = host;
    }
    const rootRect = root.getBoundingClientRect();
    const rects = [];
    for (const n of el.querySelectorAll('svg rect')) {
        const r = n.getBoundingClientRect();
        if (r.width < 30 || r.height < 3 || r.height > 15) continue;
        if (r.x < rootRect.x - 1 || r.x + r.width > rootRect.x + rootRect.width + 1) continue;
        if (r.y < rootRect.y + rootRect.height * 0.80) continue;
        if (r.y > rootRect.y + rootRect.height) continue;
        rects.push(r);
    }
    if (rects.length < 2) return null;
    const byY = {};
    for (const r of rects) {
        const k = Math.round(r.y);
        (byY[k] ||= []).push(r);
    }
    for (const k in byY) {
        if (byY[k].length < 2) continue;
        const sorted = byY[k].slice().sort((a, b) => a.width - b.width);
        const thumb = sorted[0];
        const track = sorted[sorted.length - 1];
        return {
            thumb: { x: thumb.x, y: thumb.y, w: thumb.width, h: thumb.height },
            track: { x: track.x, y: track.y, w: track.width, h: track.height },
        };
    }
    return null;
}"""


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

    def _visual_scope(self, anchor: Locator) -> Locator:
        scope = anchor.locator(_CONTAINER_ANCESTOR_XPATH).first
        return scope if scope.count() > 0 else anchor

    def visual_bbox(self, container: Locator) -> dict:
        scope = self._visual_scope(container)
        bbox = scope.evaluate(
            r"""el => {
                const pref = el.querySelector('.visualContainer');
                if (pref) {
                    const r = pref.getBoundingClientRect();
                    if (r.width > 0 && r.height > 0) {
                        return { x: r.x, y: r.y, width: r.width, height: r.height };
                    }
                }
                let best = null;
                for (const n of el.querySelectorAll('[aria-label]')) {
                    const r = n.getBoundingClientRect();
                    if (r.width <= 0 || r.height <= 0) continue;
                    const area = r.width * r.height;
                    if (!best || area > best.area) best = { area, r };
                }
                if (best) {
                    const r = best.r;
                    return { x: r.x, y: r.y, width: r.width, height: r.height };
                }
                const r = el.getBoundingClientRect();
                if (r.width > 0 && r.height > 0) {
                    return { x: r.x, y: r.y, width: r.width, height: r.height };
                }
                return null;
            }"""
        )
        if not bbox:
            raise RuntimeError("Could not resolve a non-zero bbox for container")
        return bbox

    def get_chart_scrollbar(self, container: Locator) -> dict:
        scope = self._visual_scope(container)
        geom = scope.evaluate(_FIND_CHART_SCROLLBAR_JS)
        if not geom:
            raise RuntimeError("No SVG horizontal scrollbar found inside container")

        thumb, track = geom["thumb"], geom["track"]
        remaining_left = thumb["x"] - track["x"]
        remaining_right = (track["x"] + track["w"]) - (thumb["x"] + thumb["w"])
        travel = max(track["w"] - thumb["w"], 1e-9)
        progress = remaining_left / travel
        return {
            "thumb": thumb,
            "track": track,
            "remaining_left": remaining_left,
            "remaining_right": remaining_right,
            "progress": progress,
        }

    def scroll_chart_horizontally(self, container: Locator, dx: int) -> dict:
        scope = self._visual_scope(container)
        geom = scope.evaluate(_FIND_CHART_SCROLLBAR_JS)
        if not geom:
            raise RuntimeError("No SVG horizontal scrollbar found inside container")

        thumb, track = geom["thumb"], geom["track"]
        cx = thumb["x"] + thumb["w"] / 2
        cy = thumb["y"] + thumb["h"] / 2
        min_cx = track["x"] + thumb["w"] / 2
        max_cx = track["x"] + track["w"] - thumb["w"] / 2
        target_cx = max(min_cx, min(max_cx, cx + dx))

        self.page.mouse.move(cx, cy)
        self.page.mouse.down()
        steps = max(5, int(abs(target_cx - cx) / 20))
        for i in range(1, steps + 1):
            self.page.mouse.move(cx + (target_cx - cx) * i / steps, cy, steps=1)
            self.page.wait_for_timeout(20)
        self.page.mouse.up()
        self.page.wait_for_timeout(300)

        return {"thumb": thumb, "track": track, "moved": int(target_cx - cx)}

    def scroll_table_vertically(self, container: Locator, dy: int) -> dict:
        scope = self._visual_scope(container)
        result = scope.evaluate(
            r"""(el, dy) => {
                let scrolledY = 0, candidates = 0;
                for (const n of el.querySelectorAll('*')) {
                    const cs = getComputedStyle(n);
                    const scY = (cs.overflowY === 'auto' || cs.overflowY === 'scroll')
                                && n.scrollHeight > n.clientHeight + 2;
                    if (!scY) continue;
                    candidates++;
                    const before = n.scrollTop;
                    n.scrollBy({ top: dy, behavior: 'instant' });
                    scrolledY += n.scrollTop - before;
                }
                return { scrolledY, candidates };
            }""",
            dy,
        )
        if result["candidates"] == 0:
            raise RuntimeError("No vertical scroll viewport found inside container")
        return result

    def container_by_title(self, title: str, timeout: int = 30000) -> Locator:
        frame = self._frame()
        pattern = _exact_pattern(title)

        strategies: List[Callable[[], Locator]] = [
            lambda: frame.get_by_role("heading", name=pattern).first,
            lambda: frame.get_by_label(pattern).first,
            lambda: frame.get_by_title(pattern).first,
            lambda: frame.get_by_text(pattern).first,
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

                return loc

        raise last_error or PWTimeout(
            f"No locator strategy found a visible match for: {label!r}"
        )


def _css_escape(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _exact_pattern(text: str) -> "re.Pattern[str]":
    return re.compile(rf"^\s*{re.escape(text)}\s*$", re.IGNORECASE)
