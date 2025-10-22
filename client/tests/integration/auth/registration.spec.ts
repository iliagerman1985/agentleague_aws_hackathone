import { test, expect } from '@playwright/test';
import { RegisterPage } from '../../pages/RegisterPage';
import { TEST_REGISTRATION_DATA, TEST_URLS } from '../../utils/testData';
import { clearAuth } from '../../utils/auth';

test.describe('Registration Flow - Essential Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Clear authentication state before each test
    await clearAuth(page);
  });

  test('successful user registration with valid data @regression', async ({ page }) => {
    // Test Description: Verifies that a user can successfully register with valid data
    // and is redirected to the login page. This is the core registration functionality test.

    const registerPage = new RegisterPage(page);

    await registerPage.goto();
    await registerPage.expectRegisterPage();

    // Fill registration form with valid data
    const userData = TEST_REGISTRATION_DATA.VALID_USER;
    await registerPage.register(
      userData.firstName,
      userData.lastName,
      userData.email,
      userData.password,
      userData.confirmPassword
    );

    // Wait for redirect to login or home (both are valid outcomes)
    console.log('⏳ Waiting for redirect after registration...');

    try {
      // Wait for URL to change away from register page
      await page.waitForFunction(
        () => !window.location.href.includes('/register'),
        { timeout: 15000 }
      );

      const currentUrl = page.url();
      console.log(`✅ Successfully redirected to: ${currentUrl}`);

      // Verify we're on a valid page (login or games-management)
      const isOnLoginOrDashboard = currentUrl.includes('/login') || currentUrl.includes('/games-management');
      if (!isOnLoginOrDashboard) {
        throw new Error(`Redirected to unexpected page: ${currentUrl}`);
      }

    } catch (timeoutError) {
      // If redirect didn't happen, check for errors
      const currentUrl = page.url();
      console.log(`⚠️ No redirect after 15 seconds, still on: ${currentUrl}`);

      if (currentUrl.includes('/register')) {
        // Check for error messages
        const hasError = await registerPage.errorMessage.isVisible();
        if (hasError) {
          const errorText = await registerPage.errorMessage.textContent();
          throw new Error(`Registration failed with error: ${errorText}`);
        }

        // Check if there are any other error indicators
        const hasFormErrors = await page.locator('.text-destructive, .error, [role="alert"]').isVisible();
        if (hasFormErrors) {
          const errorText = await page.locator('.text-destructive, .error, [role="alert"]').textContent();
          throw new Error(`Registration failed with form error: ${errorText}`);
        }

        throw new Error(`Registration completed but no redirect occurred. Still on: ${currentUrl}`);
      }

      throw timeoutError;
    }
  });

  test('registration with mismatched passwords shows error', async ({ page }) => {
    // Test Description: Verifies that registration with mismatched passwords shows
    // a validation error and prevents form submission.

    const registerPage = new RegisterPage(page);

    await registerPage.goto();
    await registerPage.expectRegisterPage();

    // Fill form with mismatched passwords
    await registerPage.register(
      'John',
      'Doe',
      'john.doe@test.com',
      'TestPassword123!',
      'DifferentPassword123!'
    );

    // Should show error and stay on registration page
    await expect(page).toHaveURL(TEST_URLS.REGISTER);
    await registerPage.expectErrorMessage('Passwords do not match');
  });

  test('registration form has all required fields visible', async ({ page }) => {
    // Test Description: Verifies that all required form fields are visible
    // and accessible on the registration page.

    const registerPage = new RegisterPage(page);

    await registerPage.goto();
    await registerPage.expectRegisterPage();

    // Check that all required form fields are visible
    await expect(registerPage.firstNameInput).toBeVisible();
    await expect(registerPage.lastNameInput).toBeVisible();
    await expect(registerPage.emailInput).toBeVisible();
    await expect(registerPage.passwordInput).toBeVisible();
    await expect(registerPage.confirmPasswordInput).toBeVisible();
    await expect(registerPage.submitButton).toBeVisible();
  });

  test('registration form has link to login page', async ({ page }) => {
    // Test Description: Verifies that there is a link to the login page
    // for users who already have an account.

    const registerPage = new RegisterPage(page);

    await registerPage.goto();
    await registerPage.expectRegisterPage();

    // Check for login link
    const loginLink = page.locator('a[href*="/login"], a:has-text("Sign in"), a:has-text("Login"), a:has-text("Already have an account")');
    await expect(loginLink).toBeVisible();

    // Click the link and verify navigation
    await loginLink.click();
    await expect(page).toHaveURL(TEST_URLS.LOGIN);
  });
});
