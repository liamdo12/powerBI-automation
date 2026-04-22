import re

from behave import given, then, when
from playwright.sync_api import expect

from pages.report_page import ReportPage


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
def step_container_visible(context, title):
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
    report.scroll_container_into_view(container)

    container.screenshot(path=f"{title.lower().replace(" ", "_")}.png")


def _visual_timeout(context) -> int:
    return int(context.config.userdata.get("visual_timeout", "30000") or 30000)
