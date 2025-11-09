"""
Billing Page Object
"""
from playwright.sync_api import Page, expect


class BillingPage:
    """
    Page Object for /billing page
    """

    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url
        self.url = f"{base_url}/billing"

    def goto(self):
        """
        Navigate to billing page
        """
        self.page.goto(self.url)
        self.page.wait_for_load_state("networkidle")

    def get_current_plan_name(self) -> str:
        """
        Get current plan name from Current Subscription section
        """
        try:
            # Try multiple selectors
            selectors = [
                'text=Free Plan',
                'text=Starter Plan',
                'text=Standard Plan',
                'text=Pro Plan',
                '.plan-name',
                '[data-testid="current-plan-name"]'
            ]

            for selector in selectors:
                if self.page.locator(selector).count() > 0:
                    return self.page.locator(selector).first.text_content()

            return "Unknown"
        except Exception as e:
            print(f"Error getting plan name: {e}")
            return "Error"

    def get_credits_display(self) -> str:
        """
        Get credits display text (e.g., "10/10")
        """
        try:
            # Look for credits display pattern
            locator = self.page.locator('text=/\\d+\\s*\\/\\s*\\d+/')
            if locator.count() > 0:
                return locator.first.text_content().strip()
            return "0/0"
        except Exception:
            return "0/0"

    def get_available_credits(self) -> int:
        """
        Parse available credits from display
        """
        credits_text = self.get_credits_display()
        try:
            available = credits_text.split('/')[0].strip()
            return int(available)
        except Exception:
            return 0

    def get_total_credits(self) -> int:
        """
        Parse total credits from display
        """
        credits_text = self.get_credits_display()
        try:
            total = credits_text.split('/')[1].strip()
            return int(total)
        except Exception:
            return 0

    def click_upgrade_to_standard(self):
        """
        Click 'Upgrade to Standard Plan' button
        """
        button = self.page.locator('button:has-text("升级到 Standard Plan")')
        expect(button).to_be_visible(timeout=5000)
        button.click()

    def click_upgrade_to_pro(self):
        """
        Click 'Upgrade to Pro Plan' button
        """
        button = self.page.locator('button:has-text("升级到 Pro Plan")')
        expect(button).to_be_visible(timeout=5000)
        button.click()

    def click_cancel_subscription(self):
        """
        Click 'Cancel Subscription' button
        """
        button = self.page.locator('button:has-text("取消订阅")')
        expect(button).to_be_visible(timeout=5000)
        button.click()

    def click_resume_subscription(self):
        """
        Click 'Resume Subscription' button
        """
        button = self.page.locator('button:has-text("恢复订阅")')
        expect(button).to_be_visible(timeout=5000)
        button.click()

    def click_downgrade_to_standard(self):
        """
        Click 'Downgrade to Standard Plan' button
        """
        button = self.page.locator('button:has-text("降级到 Standard Plan")')
        expect(button).to_be_visible(timeout=5000)
        button.click()

    def confirm_dialog(self):
        """
        Click confirm button in dialog
        """
        # Look for various confirm button texts
        confirm_buttons = [
            'button:has-text("确认取消")',
            'button:has-text("确认降级")',
            'button:has-text("确认恢复")',
        ]

        for selector in confirm_buttons:
            button = self.page.locator(selector)
            if button.count() > 0:
                button.click()
                return

        raise Exception("No confirm button found in dialog")

    def cancel_dialog(self):
        """
        Click cancel button in dialog
        """
        button = self.page.locator('button:has-text("取消")')
        button.first.click()

    def wait_for_success_message(self, timeout=10000):
        """
        Wait for success message to appear
        """
        self.page.wait_for_selector(
            '.success-message, [role="alert"]',
            timeout=timeout
        )

    def get_auto_renew_status(self) -> bool:
        """
        Get auto-renew status (True if enabled, False if disabled)
        """
        try:
            text = self.page.locator('text=/自动续费.*[是否]/')
            if text.count() > 0:
                content = text.first.text_content()
                return '是' in content
            return False
        except Exception:
            return False

    def is_plan_current(self, plan_name: str) -> bool:
        """
        Check if given plan is the current active plan
        """
        current = self.get_current_plan_name()
        return plan_name.lower() in current.lower()

    def has_success_url_param(self) -> bool:
        """
        Check if URL contains success=true parameter
        """
        return 'success=true' in self.page.url
