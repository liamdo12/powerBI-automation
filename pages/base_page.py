from playwright.sync_api import Page


class BasePage:
    def __init__(self, page: Page, base_url: str = ""):
        self.page = page
        self.base_url = base_url.rstrip("/")

    def open(self, path: str = "/"):
        target = path if path.startswith("http") else f"{self.base_url}{path}"
        self.page.goto(target)
        return self

    def title(self) -> str:
        return self.page.title()
