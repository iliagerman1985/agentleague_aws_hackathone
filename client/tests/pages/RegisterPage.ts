import { Page, expect, Locator } from '@playwright/test';
import { TEST_URLS } from '../utils/testData';

export class RegisterPage {
  readonly page: Page;
  readonly firstNameInput: Locator;
  readonly lastNameInput: Locator;
  readonly emailInput: Locator;
  readonly passwordInput: Locator;
  readonly confirmPasswordInput: Locator;
  readonly submitButton: Locator;
  readonly errorMessage: Locator;
  readonly successMessage: Locator;
  readonly loginLink: Locator;

  constructor(page: Page) {
    this.page = page;
    this.firstNameInput = page.locator('input#firstName');
    this.lastNameInput = page.locator('input#lastName');
    this.emailInput = page.locator('input#email');
    this.passwordInput = page.locator('input#password');
    this.confirmPasswordInput = page.locator('input#confirmPassword');
    this.submitButton = page.locator('button[type="submit"]');
    this.errorMessage = page.locator('.text-destructive');
    this.successMessage = page.locator('.text-green-600');
    this.loginLink = page.locator('a[href="/login"]');
  }

  async goto() {
    await this.page.goto(TEST_URLS.REGISTER);
  }

  async fillRegistrationForm(
    firstName: string,
    lastName: string,
    email: string,
    password: string,
    confirmPassword: string
  ) {
    await this.firstNameInput.fill(firstName);
    await this.lastNameInput.fill(lastName);
    await this.emailInput.fill(email);
    await this.passwordInput.fill(password);
    await this.confirmPasswordInput.fill(confirmPassword);
  }

  async submit() {
    await this.submitButton.click();
  }

  async register(
    firstName: string,
    lastName: string,
    email: string,
    password: string,
    confirmPassword: string
  ) {
    await this.fillRegistrationForm(firstName, lastName, email, password, confirmPassword);
    await this.submit();
  }

  async expectRegisterPage() {
    await expect(this.page).toHaveURL(TEST_URLS.REGISTER);
    await expect(this.firstNameInput).toBeVisible();
    await expect(this.lastNameInput).toBeVisible();
    await expect(this.emailInput).toBeVisible();
    await expect(this.passwordInput).toBeVisible();
    await expect(this.confirmPasswordInput).toBeVisible();
    await expect(this.submitButton).toBeVisible();
  }

  async expectValidationError() {
    await expect(this.page).toHaveURL(TEST_URLS.REGISTER);
    // Check for HTML5 validation or custom error messages
    const hasValidationError = await this.page.evaluate(() => {
      // Check for HTML5 validation
      const inputs = document.querySelectorAll('input[required]') as NodeListOf<HTMLInputElement>;
      for (const input of inputs) {
        if (!input.validity.valid) return true;
      }

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

  async clickLoginLink() {
    await this.loginLink.click();
  }
}
