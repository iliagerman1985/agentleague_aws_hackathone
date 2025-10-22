import { Page, expect, Locator } from '@playwright/test';
import { TEST_URLS } from '../utils/testData';

export class ConfirmSignUpPage {
  readonly page: Page;
  readonly emailDisplay: Locator;
  readonly confirmationCodeInput: Locator;
  readonly submitButton: Locator;
  readonly errorMessage: Locator;
  readonly successMessage: Locator;
  readonly backToRegisterLink: Locator;

  constructor(page: Page) {
    this.page = page;
    this.emailDisplay = page.locator('[data-testid="email-display"], .email-display, span:has-text("@")');
    this.confirmationCodeInput = page.locator('input[name="confirmationCode"], input#confirmationCode, input[data-testid="confirmation-code"]');
    this.submitButton = page.locator('button[type="submit"], button:has-text("Confirm"), button:has-text("Verify")');
    this.errorMessage = page.locator('.text-destructive, [role="alert"], .error, .text-red-500, div:has-text("error"), div:has-text("Error")');
    this.successMessage = page.locator('.text-green-500, .text-success, .success, div:has-text("success"), div:has-text("Success")');
    this.backToRegisterLink = page.locator('a[href="/register"], a:has-text("Back to"), a:has-text("Register")');
  }

  async goto() {
    await this.page.goto(TEST_URLS.CONFIRM_SIGNUP);
  }

  async fillConfirmationCode(code: string) {
    await this.confirmationCodeInput.fill(code);
  }

  async submit() {
    await this.submitButton.click();
  }

  async confirmSignUp(code: string) {
    await this.fillConfirmationCode(code);
    await this.submit();
  }

  async expectConfirmSignUpPage() {
    await expect(this.page).toHaveURL(TEST_URLS.CONFIRM_SIGNUP);
    await expect(this.confirmationCodeInput).toBeVisible();
    await expect(this.submitButton).toBeVisible();
  }

  async expectValidationError() {
    await expect(this.page).toHaveURL(TEST_URLS.CONFIRM_SIGNUP);
    // Check for HTML5 validation or custom error messages
    const hasValidationError = await this.page.evaluate(() => {
      // Check for HTML5 validation
      const codeInput = document.querySelector('input[name="confirmationCode"], input#confirmationCode') as HTMLInputElement;
      if (codeInput && !codeInput.validity.valid) return true;

      // Check for custom error messages
      const errorElement = document.querySelector('.text-destructive, [role="alert"], .error, .text-red-500');
      return errorElement !== null;
    });

    expect(hasValidationError).toBe(true);
  }

  async expectErrorMessage(message?: string) {
    await expect(this.errorMessage).toBeVisible();
    if (message) {
      await expect(this.errorMessage).toContainText(message);
    }
  }

  async expectSuccessMessage(message?: string) {
    await expect(this.successMessage).toBeVisible();
    if (message) {
      await expect(this.successMessage).toContainText(message);
    }
  }

  async waitForLoadingToFinish() {
    // Wait for any loading states to finish
    await this.page.waitForLoadState('networkidle');
  }

  async clickBackToRegisterLink() {
    await this.backToRegisterLink.click();
  }
}
