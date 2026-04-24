from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "reports" / "output"

MAX_SCROLL_STEPS = 40

STRATEGY_PROBE_MS = 2500

VISUAL_CONTAINER_SELECTOR = "visual-container, [class*='visualContainerHost']"


CONTAINER_ANCESTOR_XPATH = (
    "xpath=(ancestor-or-self::visual-container"
    " | ancestor-or-self::*[contains(@class,'visualContainerHost')])[last()]"
)



FIND_VISUAL_BBOX_JS = r"""el => {
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


FIND_TABLE_SCROLL_JS = r"""el => {
    for (const n of el.querySelectorAll('*')) {
        const cs = getComputedStyle(n);
        const scY = (cs.overflowY === 'auto' || cs.overflowY === 'scroll')
                    && n.scrollHeight > n.clientHeight + 2;
        if (!scY) continue;
        return {
            scrollTop: n.scrollTop,
            scrollHeight: n.scrollHeight,
            clientHeight: n.clientHeight,
        };
    }
    return null;
}"""


FIND_CHART_SCROLLBAR_JS = r"""el => {
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
