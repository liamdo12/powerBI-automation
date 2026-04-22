import re
from pathlib import Path

from behave import given, then, when
from playwright.sync_api import expect

from pages.report_page import ReportPage
from utils.image_stitch import stitch_to_file


_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "reports" / "output"

_MAX_SCROLL_STEPS = 40


@given('I open the base URL')
def step_open_base_url(context):
    context.page.goto(context.base_url)


@given('I open "{url}"')
def step_open_url(context, url):
    context.page.goto(url)


@when('I click "{selector}"')
def step_click(context, selector):
    context.page.locator(selector).click()


@when('I fill "{selector}" with "{value}"')
def step_fill(context, selector, value):
    context.page.locator(selector).fill(value)


@then('the page title should contain "{text}"')
def step_title_contains(context, text):
    expect(context.page).to_have_title(re.compile(re.escape(text)))


@then('the "{title}" container should be visible')
def step_container_visible(context, title):
    timeout = _visual_timeout(context)
    report = ReportPage(context.page, context.base_url)
    report.wait_for_visuals_ready(timeout=timeout)
    container = report.container_by_title(title, timeout=timeout)
    expect(container).to_be_visible()


@then('the "{title}" of column should be visible')
def step_column_visible(context, title):
    timeout = _visual_timeout(context)
    report = ReportPage(context.page, context.base_url)
    report.wait_for_visuals_ready(timeout=timeout)
    container = report.container_by_column_header(title, timeout=timeout)
    expect(container).to_be_visible()


@then('the element "{selector}" should be visible')
def step_element_visible(context, selector):
    expect(context.page.locator(selector)).to_be_visible()


@then('I scroll the container "{title}" horizontally')
def step_scroll_container_horizontally(context, title):
    timeout = _visual_timeout(context)
    report = ReportPage(context.page, context.base_url)
    report.wait_for_visuals_ready(timeout=timeout)
    container = report.container_by_title(title, timeout=timeout)

    report.scroll_chart_horizontally(container, dx=-10_000)

    frames: list[bytes] = []
    for _ in range(_MAX_SCROLL_STEPS):
        frames.append(context.page.screenshot(clip=report.visual_bbox(container)))
        info = report.get_chart_scrollbar(container)
        if info["remaining_right"] <= 1:
            break
        step = max(int(info["thumb"]["w"]), 1)
        report.scroll_chart_horizontally(container, dx=step)

    out = stitch_to_file(frames, _OUTPUT_DIR / f"{_slug(title)}_horizontal.png",
                         orientation="horizontal")
    print(f"[stitch] {len(frames)} frames -> {out}")


@then('I scroll the table of column "{title}" vertically')
def step_scroll_table_vertically(context, title):
    timeout = _visual_timeout(context)
    report = ReportPage(context.page, context.base_url)
    report.wait_for_visuals_ready(timeout=timeout)
    container = report.container_by_column_header(title, timeout=timeout)

    try:
        report.scroll_table_vertically(container, dy=-10_000_000)
    except RuntimeError:
        pass

    bbox = report.visual_bbox(container)
    page_step = max(int(bbox["height"] * 0.9), 50)

    frames: list[bytes] = [context.page.screenshot(clip=report.visual_bbox(container))]
    for _ in range(_MAX_SCROLL_STEPS):
        result = report.scroll_table_vertically(container, dy=page_step)
        if result["scrolledY"] == 0:
            break
        frames.append(context.page.screenshot(clip=report.visual_bbox(container)))

    out = stitch_to_file(frames, _OUTPUT_DIR / f"{_slug(title)}_vertical.png",
                         orientation="vertical")
    print(f"[stitch] {len(frames)} frames -> {out}")


def _visual_timeout(context) -> int:
    return int(context.config.userdata.get("visual_timeout", "30000") or 30000)


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
