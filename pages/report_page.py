from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Callable, List, Optional

from playwright.sync_api import Frame, Locator, TimeoutError as PWTimeout

from constants.power_bi import (
    CONTAINER_ANCESTOR_XPATH,
    DEFAULT_OUTPUT_DIR,
    FIND_CHART_SCROLLBAR_JS,
    FIND_TABLE_SCROLL_JS,
    FIND_VISUAL_BBOX_JS,
    MAX_SCROLL_STEPS,
    STRATEGY_PROBE_MS,
    VISUAL_CONTAINER_SELECTOR,
)
from pages.base_page import BasePage
from utils.image_stitch import stitch_to_file


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
        scope = anchor.locator(CONTAINER_ANCESTOR_XPATH).first
        return scope if scope.count() > 0 else anchor

    def visual_bbox(self, container: Locator) -> dict:
        scope = self._visual_scope(container)
        bbox = scope.evaluate(FIND_VISUAL_BBOX_JS)
        if not bbox:
            raise RuntimeError("Could not resolve a non-zero bbox for container")
        return bbox

    def get_chart_scrollbar(self, container: Locator) -> dict:
        scope = self._visual_scope(container)
        geom = scope.evaluate(FIND_CHART_SCROLLBAR_JS)
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

    def get_table_scroll(self, container: Locator) -> dict:
        scope = self._visual_scope(container)
        result = scope.evaluate(FIND_TABLE_SCROLL_JS)
        if not result:
            raise RuntimeError("No vertical scroll viewport found inside container")
        result["remaining_bottom"] = max(
            result["scrollHeight"] - result["clientHeight"] - result["scrollTop"], 0
        )
        return result

    def scroll_chart_horizontally(self, container: Locator, dx: int) -> None:
        self._wheel_over(container, dx=dx, dy=0)

    def scroll_table_vertically(self, container: Locator, dy: int) -> None:
        self._wheel_over(container, dx=0, dy=dy)

    def _wheel_over(self, container: Locator, dx: int, dy: int) -> None:
        box = self.visual_bbox(container)
        cx = box["x"] + box["width"] / 2
        cy = box["y"] + box["height"] / 2
        self.page.mouse.move(cx, cy)
        self.page.mouse.wheel(dx, dy)
        self.page.wait_for_timeout(200)

    def scroll_chart_horizontally_and_capture(
        self,
        title: str,
        timeout: int = 30000,
        output_dir: Optional[Path] = None,
    ) -> Path:
        self.wait_for_visuals_ready(timeout=timeout)
        container = self.container_by_title(title, timeout=timeout)
        self.scroll_chart_horizontally(container, dx=-10_000)

        frames: List[bytes] = []
        for _ in range(MAX_SCROLL_STEPS):
            frames.append(self.page.screenshot(clip=self.visual_bbox(container)))
            if self.get_chart_scrollbar(container)["remaining_right"] <= 1:
                break
            for _ in range(3):
                self.scroll_chart_horizontally(container, dx=1200)

        out = (output_dir or DEFAULT_OUTPUT_DIR) / f"{_slug(title)}_horizontal.png"
        stitch_to_file(frames, out, orientation="horizontal")
        return out

    def scroll_table_vertically_and_capture(
        self,
        column_header: str,
        timeout: int = 30000,
        output_dir: Optional[Path] = None,
    ) -> Path:
        self.wait_for_visuals_ready(timeout=timeout)
        container = self.container_by_column_header(column_header, timeout=timeout)

        self.scroll_table_vertically(container, dy=-10_000_000)

        bbox = self.visual_bbox(container)
        page_step = max(int(bbox["height"] * 0.9), 50)

        frames: List[bytes] = [self.page.screenshot(clip=self.visual_bbox(container))]
        for _ in range(MAX_SCROLL_STEPS):
            before = self.get_table_scroll(container)["scrollTop"]
            self.scroll_table_vertically(container, dy=page_step)
            after = self.get_table_scroll(container)
            if after["scrollTop"] == before:
                break  # hit bottom
            frames.append(self.page.screenshot(clip=self.visual_bbox(container)))
            if after["remaining_bottom"] == 0:
                break

        out = (output_dir or DEFAULT_OUTPUT_DIR) / f"{_slug(column_header)}_vertical.png"
        stitch_to_file(frames, out, orientation="vertical")
        return out

    @staticmethod
    def visual_timeout_from(context) -> int:
        return int(context.config.userdata.get("visual_timeout", "30000") or 30000)

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
        deadline = time.monotonic() + max(timeout, STRATEGY_PROBE_MS) / 1000.0
        last_error: Optional[BaseException] = None

        while time.monotonic() < deadline:
            for build in strategies:
                remaining_ms = int((deadline - time.monotonic()) * 1000)
                if remaining_ms <= 0:
                    break
                slice_ms = min(STRATEGY_PROBE_MS, remaining_ms)
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


def _slug(text: str) -> str:
    """Kebab-ish file-name slug: lowercase alphanumerics, underscores as separators."""
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _exact_pattern(text: str) -> "re.Pattern[str]":
    return re.compile(rf"^\s*{re.escape(text)}\s*$", re.IGNORECASE)
