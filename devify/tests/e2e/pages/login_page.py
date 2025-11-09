"""
Login Page Object
"""
from playwright.sync_api import Page, expect


class LoginPage:
    """
    Page Object for login page
    """

    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url
        self.url = f"{base_url}/login"

    def goto(self):
        """
        Navigate to login page
        """
        self.page.goto(self.url)
        self.page.wait_for_load_state("networkidle")

    def login(self, username: str, password: str):
        """
        Perform login with username and password
        """
        self.page.fill('input[name="username"]', username)
        self.page.fill('input[name="password"]', password)
        self.page.click('button[type="submit"]')

        # Wait for navigation after login
        self.page.wait_for_url("**/conversations**", timeout=10000)

    def is_logged_in(self) -> bool:
        """
        Check if user is logged in by checking for user menu
        """
        try:
            self.page.wait_for_selector(
                '[data-testid="user-menu"]',
                timeout=5000
            )
            return True
        except Exception:
            return False
