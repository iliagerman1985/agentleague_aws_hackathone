import { Page, expect, Locator } from '@playwright/test';
import { TEST_USERS, TEST_URLS } from './testData';

export type UserType = keyof typeof TEST_USERS;

/**
 * Generate unique test identifiers to avoid conflicts in parallel execution
 */
export function generateTestId(): string {
  return `test_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;
}

/**
 * Generate unique test name with prefix
 */
export function generateTestName(prefix: string): string {
  return `${prefix}_${generateTestId()}`;
}

/**
 * Clear authentication state from the browser
 */
export async function clearAuth(page: Page) {
  // Fast, resilient clear: do not depend on navigation, keep timeouts tiny
  try {
    await page.context().clearCookies();
  } catch (error) {
    console.log('Could not clear cookies (context may be destroyed):', error);
  }

  // Try to clear storage on the current page; ignore errors if not available yet
  try {
    await page.evaluate(() => {
      try { if (typeof localStorage !== 'undefined') localStorage.clear(); } catch {}
      try { if (typeof sessionStorage !== 'undefined') sessionStorage.clear(); } catch {}
    });
  } catch {}

  // Best-effort short navigation to the app origin to ensure a same-origin context,
  // but do not block tests if it fails (no retries, very short timeouts)
  try {
    await page.goto(TEST_URLS.HOME, { timeout: 3000, waitUntil: 'domcontentloaded' });
    await page.evaluate(() => {
      try { if (typeof localStorage !== 'undefined') localStorage.clear(); } catch {}
      try { if (typeof sessionStorage !== 'undefined') sessionStorage.clear(); } catch {}
    });
  } catch {
    // Ignore; login tests will navigate explicitly next
  }
}



/**
 * Login as a specific user type
 */
export async function loginAs(page: Page, userType: UserType) {
  const user = TEST_USERS[userType];

  // This function now performs a clean login without clearing state implicitly.
  // Use clearAuth(page) explicitly in tests that need a fresh session (e.g., login tests).

  // If already authenticated, short-circuit
  try {
    const ok = await isAuthenticated(page);
    if (ok) return;
  } catch {}

  // Navigate to login page
  await page.goto(TEST_URLS.LOGIN);

  // Wait for login form to be visible
  await expect(page.locator('form')).toBeVisible();

  // Wait for input fields to be visible and enabled
  await expect(page.locator('input#email')).toBeVisible();
  await expect(page.locator('input#password')).toBeVisible();

  // Fill credentials
  await page.locator('input#email').fill(user.email);
  await page.locator('input#password').fill(user.password);

  // Submit form and wait for navigation
  await Promise.all([
    page.waitForURL(TEST_URLS.DASHBOARD, { timeout: 15000 }),
    page.locator('button[type="submit"]').click()
  ]);
}

// Fast login that never clears, and only logs in if needed
export async function loginIfNeeded(page: Page, userType: UserType) {
  const user = TEST_USERS[userType];
  try {
    if (await isAuthenticated(page)) return;
  } catch {}
  await page.goto(TEST_URLS.LOGIN);
  await page.locator('input#email').fill(user.email);
  await page.locator('input#password').fill(user.password);
  await Promise.all([
    page.waitForURL(TEST_URLS.DASHBOARD, { timeout: 15000 }),
    page.locator('button[type="submit"]').click()
  ]);
}

/**
 * Check if user is authenticated by checking for dashboard access
 */
export async function isAuthenticated(page: Page): Promise<boolean> {
  try {
    // Navigate to dashboard and allow SPA guards to run
    await page.goto(TEST_URLS.DASHBOARD, { waitUntil: 'domcontentloaded', timeout: 10000 });
    // Give the router a brief moment to redirect if unauthenticated
    await page.waitForTimeout(300);

    // If we were redirected away, not authenticated
    const current = page.url();
    if (!current.includes('/games-management')) return false;

    // Check for UI signals that only exist when logged in
    const signOutVisible = await page.getByRole('button', { name: /sign out/i }).isVisible({ timeout: 500 }).catch(() => false);
    const toolsLinkVisible = await page.getByRole('link', { name: /^tools$/i }).isVisible({ timeout: 500 }).catch(() => false);

    return Boolean(signOutVisible || toolsLinkVisible);
  } catch {
    return false;
  }
}

/**
 * Logout user using the Sign Out button (preserves remembered credentials)
 */
export async function logout(page: Page) {
  try {
    console.log('🔓 Starting logout process...');
    // On mobile, we might need to open the navigation menu first
    const viewport = page.viewportSize();
    const isMobile = viewport && viewport.width < 768;
    console.log(`📱 Mobile detected: ${isMobile}`);

    if (isMobile) {
      // Try multiple selectors for the mobile menu button
      const menuSelectors = [
        page.getByRole('button', { name: 'Toggle navigation menu' }),
        page.locator('button:has(svg)').first(), // Button with Menu icon
        page.locator('.md\\:hidden button'), // Button with md:hidden class
        page.locator('header button').first() // First button in header
      ];

      let menuOpened = false;
      for (let i = 0; i < menuSelectors.length; i++) {
        const menuButton = menuSelectors[i];
        const menuVisible = await menuButton.isVisible({ timeout: 1000 });
        console.log(`🍔 Menu button selector ${i + 1} visible: ${menuVisible}`);
        if (menuVisible) {
          await menuButton.click();
          console.log('✓ Clicked mobile menu button');
          // Wait for menu to open
          await page.waitForTimeout(1000);
          menuOpened = true;
          break;
        }
      }

      if (!menuOpened) {
        console.log('⚠️ Could not find mobile menu button, trying direct Sign Out access');
      }
    }

    // Try multiple selectors for the Sign Out button
    const signOutSelectors = [
      page.getByRole('button', { name: 'Sign Out' }),
      page.getByRole('button', { name: /sign out/i }),
      page.getByText('Sign Out'),
      page.getByText(/sign out/i),
      page.locator('button:has-text("Sign Out")'),
      page.locator('[data-testid="sign-out-button"]'),
      page.locator('button[aria-label="Sign Out"]'),
      page.locator('button[title="Sign Out"]')
    ];

    console.log('🔍 Looking for Sign Out button...');
    let logoutButton: Locator | null = null;
    for (let i = 0; i < signOutSelectors.length; i++) {
      const selector = signOutSelectors[i];
      const isVisible = await selector.isVisible({ timeout: 1000 });
      console.log(`  Selector ${i + 1}: ${isVisible ? '✓ FOUND' : '✗ not found'}`);
      if (isVisible) {
        logoutButton = selector;
        break;
      }
    }

    if (logoutButton) {
      console.log('✓ Found Sign Out button, attempting to click...');
      // Wait for button to be stable and click
      await logoutButton.waitFor({ state: 'visible', timeout: 5000 });
      await logoutButton.click({ timeout: 5000 });
      console.log('✓ Clicked Sign Out button');

      // Wait a moment for the signOut process to complete
      await page.waitForTimeout(1000);

      // Wait for logout to complete and redirect to login page
      // Use a longer timeout and check for URL change or login page elements
      try {
        await expect(page).toHaveURL(TEST_URLS.LOGIN, { timeout: 15000 });
        console.log('✓ Successfully navigated to login page');
      } catch {
        console.log('⚠️ URL did not change to login, checking for login elements...');
        // If URL doesn't change, check if we can see login page elements
        await expect(page.locator('input#email')).toBeVisible({ timeout: 10000 });
        console.log('✓ Login page elements are visible');
      }
    } else {
      console.log('❌ Sign Out button not found with any selector');
      throw new Error('Sign Out button not found');
    }
  } catch (error) {
    console.warn('🔄 Could not use Sign Out button, falling back to manual auth clearing:', error);
    // If logout button not found, clear auth manually
    await clearAuth(page);
  }
}

/**
 * Ensure there's at least one OpenAI integration for tests
 */
export async function ensureOpenAIIntegration(page: Page) {
  try {
    console.log('🔧 Ensuring OpenAI integration exists...');

    // Navigate to settings to check/create LLM integrations
    await page.goto('/settings');
    await page.waitForTimeout(1000);

    // Look for LLM Integrations section and click it
    const llmButton = page.getByRole('button', { name: /llm integrations/i });
    if (await llmButton.isVisible({ timeout: 5000 })) {
      await llmButton.click();
      await page.waitForTimeout(500);
    }

    // Check if there's already an OpenAI integration
    const openaiExists = await page.getByText(/openai/i).isVisible({ timeout: 2000 });

    if (!openaiExists) {
      console.log('📝 Creating OpenAI integration...');

      // Click Add Integration or similar button
      const addButton = page.getByRole('button', { name: /add|create|new/i }).first();
      if (await addButton.isVisible({ timeout: 3000 })) {
        await addButton.click();
        await page.waitForTimeout(500);

        // Select OpenAI tab if needed
        const openaiTab = page.getByRole('tab', { name: /openai/i });
        if (await openaiTab.isVisible({ timeout: 2000 })) {
          await openaiTab.click();
          await page.waitForTimeout(300);
        }

        // Fill in a test API key
        const apiKeyInput = page.locator('input[type="password"], input[placeholder*="api"], input[placeholder*="key"]').first();
        if (await apiKeyInput.isVisible({ timeout: 2000 })) {
          await apiKeyInput.fill('sk-test-key-for-testing-only');
          await page.waitForTimeout(200);
        }

        // Save the integration
        const saveButton = page.getByRole('button', { name: /save|create/i });
        if (await saveButton.isVisible({ timeout: 2000 })) {
          await saveButton.click();
          await page.waitForTimeout(1000);
          console.log('✅ OpenAI integration created');
        }
      }
    } else {
      console.log('✅ OpenAI integration already exists');
    }

  } catch (error) {
    console.log('⚠️ Could not ensure OpenAI integration:', error);
    // Don't throw - tests should continue even if this fails
  }
}

/**
 * Quick setup for tests that need an OpenAI integration
 * Call this in beforeEach or test setup
 */
/**
 * Clean up test data to prevent conflicts between parallel test runs
 */
export async function cleanupTestData(page: Page) {
  try {
    console.log('🧹 Cleaning up test data...');

    // Navigate to tools list and delete any test tools
    await page.goto('/tools');
    await page.waitForTimeout(1000);

    // Look for any test tools and delete them
    const testToolRows = page.getByRole('row').filter({ hasText: /test_\d+_/ });
    const count = await testToolRows.count();

    for (let i = 0; i < count; i++) {
      try {
        const row = testToolRows.nth(i);
        const deleteButton = row.getByRole('button', { name: /delete/i }).first();
        if (await deleteButton.isVisible({ timeout: 1000 })) {
          await deleteButton.click();
          // Handle confirmation if it appears
          try {
            const confirmButton = page.getByRole('button', { name: /confirm|delete|yes/i });
            await confirmButton.click({ timeout: 2000 });
          } catch {
            // No confirmation needed
          }
          await page.waitForTimeout(500);
        }
      } catch (error) {
        console.log(`Could not delete test tool ${i}:`, error);
      }
    }

    console.log(`✅ Cleaned up ${count} test tools`);
  } catch (error) {
    console.log('⚠️ Could not clean up test data:', error);
    // Don't throw - tests should continue even if cleanup fails
  }
}

export async function setupTestWithOpenAI(page: Page, userType: keyof typeof TEST_USERS = "ADMIN") {
  await clearAuth(page);
  await loginAs(page, userType);
  await ensureOpenAIIntegration(page);
}
