import { test, expect } from '@playwright/test';
import { LoginPage } from '../../pages/LoginPage';
import { HomePage } from '../../pages/HomePage';
import { TEST_USERS, TEST_URLS } from '../../utils/testData';
import { clearAuth, logout } from '../../utils/auth';

test.describe('Login Flow - Essential Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Clear authentication state before each test
    await clearAuth(page);
  });

  test('successful login and navigation to home @regression', async ({ page }) => {
    // Test Description: Verifies that a user can successfully log in with valid credentials
    // and is redirected to the home. This is the core login functionality test.
    
    const loginPage = new LoginPage(page);
    const homePage = new HomePage(page);

    await loginPage.goto();
    await loginPage.expectLoginPage();

    // Fill login form with admin credentials
    await loginPage.login(TEST_USERS.ADMIN.email, TEST_USERS.ADMIN.password);

    // Verify successful login and navigation to home
    await expect(page).toHaveURL(TEST_URLS.DASHBOARD, { timeout: 15000 });
    await homePage.expectHomePage();
  });

  test('login with invalid credentials shows error', async ({ page }) => {
    // Test Description: Verifies that login with invalid credentials shows an appropriate
    // error message and does not redirect to the home.

    const loginPage = new LoginPage(page);

    await loginPage.goto();
    await loginPage.expectLoginPage();

    // Try to login with invalid credentials
    await loginPage.login('invalid@test.com', 'wrongpassword');

    // Should stay on login page and show error
    await expect(page).toHaveURL(TEST_URLS.LOGIN);
    await loginPage.expectErrorMessage();
  });

  test('login form has all required fields visible', async ({ page }) => {
    // Test Description: Verifies that all required form fields (email, password, submit button)
    // are visible and accessible on the login page.
    
    const loginPage = new LoginPage(page);
    
    await loginPage.goto();
    await loginPage.expectLoginPage();

    // Check that all required form fields are visible
    await expect(loginPage.emailInput).toBeVisible();
    await expect(loginPage.passwordInput).toBeVisible();
    await expect(loginPage.submitButton).toBeVisible();
  });

  test('login form has link to registration page', async ({ page }) => {
    // Test Description: Verifies that there is a link to the registration page
    // for users who need to create an account.
    
    const loginPage = new LoginPage(page);
    
    await loginPage.goto();
    await loginPage.expectLoginPage();

    // Check for registration link
    const registrationLink = page.locator('a[href*="/register"], a:has-text("Sign up"), a:has-text("Register"), a:has-text("Create account")');
    await expect(registrationLink).toBeVisible();
    
    // Click the link and verify navigation
    await registrationLink.click();
    await expect(page).toHaveURL(TEST_URLS.REGISTER);
  });

  test('redirect to login when accessing protected route @regression', async ({ page }) => {
    // Test Description: Verifies that unauthenticated users are redirected to the login page
    // when trying to access protected routes like the home.

    // Try to access home without being logged in
    await page.goto(TEST_URLS.DASHBOARD);

    // Should be redirected to login page
    await expect(page).toHaveURL(TEST_URLS.LOGIN, { timeout: 15000 });

    const loginPage = new LoginPage(page);
    await loginPage.expectLoginPage();
  });

  test('remember me functionality stores and retrieves credentials', async ({ page }) => {
    // Test Description: Verifies that the "remember me" functionality correctly stores
    // credentials in localStorage and retrieves them when the page is reloaded.

    const loginPage = new LoginPage(page);
    const testEmail = TEST_USERS.ADMIN.email;
    const testPassword = TEST_USERS.ADMIN.password;

    await loginPage.goto();
    await loginPage.expectLoginPage();

    // Fill credentials and check remember me
    await loginPage.fillCredentials(testEmail, testPassword);
    await loginPage.checkRememberMe();

    // Verify remember me checkbox is checked
    await expect(loginPage.rememberMeCheckbox).toBeChecked();

    // Submit the form (this should trigger the remember me storage)
    await loginPage.submit();

    // Wait for successful login and navigation to home
    await expect(page).toHaveURL(TEST_URLS.DASHBOARD, { timeout: 15000 });

    // Verify credentials are stored in localStorage
    const storedEmail = await page.evaluate(() => localStorage.getItem('rememberedEmail'));
    const storedPassword = await page.evaluate(() => localStorage.getItem('rememberedPassword'));

    expect(storedEmail).toBe(testEmail);
    expect(storedPassword).toBeTruthy(); // Password should be stored (base64 encoded)

    // Decode the stored password to verify it matches
    const decodedPassword = await page.evaluate(() => {
      const stored = localStorage.getItem('rememberedPassword');
      return stored ? atob(stored) : null;
    });
    expect(decodedPassword).toBe(testPassword);

    // Use the logout utility function which handles mobile navigation robustly
    // This preserves remembered credentials since we're not clearing localStorage manually
    await logout(page);
    await loginPage.expectLoginPage();

    // Wait for the React component to load remembered credentials from localStorage
    // The useEffect hook needs time to run and populate the form fields
    await expect(loginPage.emailInput).toHaveValue(testEmail, { timeout: 10000 });
    await expect(loginPage.passwordInput).toHaveValue(testPassword, { timeout: 5000 });
    await expect(loginPage.rememberMeCheckbox).toBeChecked();

    // Test that we can login with the pre-filled credentials
    await loginPage.submit();
    await expect(page).toHaveURL(TEST_URLS.DASHBOARD, { timeout: 15000 });
  });

  test('remember me unchecked clears stored credentials', async ({ page }) => {
    // Test Description: Verifies that when "remember me" is unchecked during login,
    // any previously stored credentials are cleared from localStorage.

    const loginPage = new LoginPage(page);
    const testEmail = TEST_USERS.ADMIN.email;
    const testPassword = TEST_USERS.ADMIN.password;

    // First, store some credentials by logging in with remember me checked
    await loginPage.goto();
    await loginPage.login(testEmail, testPassword, true);
    await expect(page).toHaveURL(TEST_URLS.DASHBOARD, { timeout: 15000 });

    // Verify credentials are stored
    const storedEmail = await page.evaluate(() => localStorage.getItem('rememberedEmail'));
    expect(storedEmail).toBe(testEmail);

    // Clear auth and go back to login
    await clearAuth(page);
    await loginPage.goto();
    await loginPage.expectLoginPage();

    // Fill credentials but don't check remember me (it should be unchecked by default after clearing auth)
    await loginPage.fillCredentials(testEmail, testPassword);

    // Ensure remember me is unchecked
    if (await loginPage.rememberMeCheckbox.isChecked()) {
      await loginPage.rememberMeCheckbox.click();
    }
    await expect(loginPage.rememberMeCheckbox).not.toBeChecked();

    // Submit the form
    await loginPage.submit();
    await expect(page).toHaveURL(TEST_URLS.DASHBOARD, { timeout: 15000 });

    // Verify credentials are cleared from localStorage
    const clearedEmail = await page.evaluate(() => localStorage.getItem('rememberedEmail'));
    const clearedPassword = await page.evaluate(() => localStorage.getItem('rememberedPassword'));

    expect(clearedEmail).toBeNull();
    expect(clearedPassword).toBeNull();

    // Clear auth and verify credentials are not pre-filled
    await clearAuth(page);
    await loginPage.goto();
    await loginPage.expectLoginPage();

    // Wait a moment for the component to load and verify no credentials are pre-filled
    await page.waitForTimeout(1000);
    await expect(loginPage.emailInput).toHaveValue('');
    await expect(loginPage.passwordInput).toHaveValue('');
    await expect(loginPage.rememberMeCheckbox).not.toBeChecked();
  });

  test('remember me handles corrupted stored password gracefully', async ({ page }) => {
    // Test Description: Verifies that the application handles corrupted base64 encoded
    // passwords in localStorage gracefully by clearing them and not crashing.

    const loginPage = new LoginPage(page);

    // Navigate to login page first
    await loginPage.goto();
    await loginPage.expectLoginPage();

    // Manually set corrupted data in localStorage after page is loaded
    await page.evaluate(() => {
      // Clear any existing auth tokens to prevent auto-login interference
      localStorage.removeItem('access_token');
      localStorage.removeItem('id_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('token_expires_at');
      localStorage.removeItem('user_info');

      // Set the test data
      localStorage.setItem('rememberedEmail', 'test@example.com');
      localStorage.setItem('rememberedPassword', 'invalid-base64-data!@#');
    });

    // Reload the page to trigger the useEffect that reads from localStorage
    await page.reload();
    await loginPage.expectLoginPage();

    // Wait for the React component to process the localStorage data
    // The email should be loaded, but the corrupted password should be cleared
    await expect(loginPage.emailInput).toHaveValue('test@example.com', { timeout: 8000 });
    await expect(loginPage.passwordInput).toHaveValue(''); // Should be empty due to decode error
    await expect(loginPage.rememberMeCheckbox).toBeChecked(); // Should still be checked since email was loaded

    // Verify that the corrupted password was removed from localStorage
    const clearedPassword = await page.evaluate(() => localStorage.getItem('rememberedPassword'));
    expect(clearedPassword).toBeNull();
  });
});
