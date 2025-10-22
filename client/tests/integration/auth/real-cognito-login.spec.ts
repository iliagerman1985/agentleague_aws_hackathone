import { test, expect } from '@playwright/test';
import { LoginPage } from '../../pages/LoginPage';
import { HomePage } from '../../pages/HomePage';
import { REAL_COGNITO_USER, TEST_URLS } from '../../utils/testData';
import { clearAuth } from '../../utils/auth';

test.describe('Real Cognito Login Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Clear authentication state before each test
    await clearAuth(page);
  });

  test('real cognito login with iliagerman@gmail.com @real-cognito', async ({ page }) => {
    // Test Description: Verifies that real Cognito authentication works with actual AWS Cognito
    // This test uses the real Cognito service instead of the mock service
    // It validates that the actual Cognito integration is working correctly
    
    const loginPage = new LoginPage(page);
    const homePage = new HomePage(page);

    await loginPage.goto();
    await loginPage.expectLoginPage();

    // Fill login form with real Cognito credentials
    await loginPage.login(REAL_COGNITO_USER.email, REAL_COGNITO_USER.password);

    // Verify successful login and navigation to home
    await expect(page).toHaveURL(TEST_URLS.DASHBOARD, { timeout: 15000 });
    await homePage.expectHomePage();
  });
});
