import { Page, expect, Locator } from '@playwright/test';
import { TEST_URLS, SELECTORS } from '../utils/testData';

export class HomePage {
  readonly page: Page;
  readonly title: Locator;
  readonly userMenu: Locator;

  constructor(page: Page) {
    this.page = page;
    this.title = page.locator(SELECTORS.DASHBOARD.TITLE);
    this.userMenu = page.locator(SELECTORS.DASHBOARD.USER_MENU);
  }

  async goto() {
    await this.page.goto(TEST_URLS.DASHBOARD);
  }

  async expectHomePage() {
    await expect(this.page).toHaveURL(TEST_URLS.DASHBOARD);
    await expect(this.title).toBeVisible();
  }

  async expectTitle(title: string) {
    await expect(this.title).toContainText(title);
  }

  async waitForLoad() {
    await this.page.waitForLoadState('networkidle');
    await expect(this.title).toBeVisible();
  }
}
