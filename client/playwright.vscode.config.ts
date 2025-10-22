import { defineConfig, devices } from '@playwright/test';

/**
 * VS Code Playwright Extension Configuration
 * This config automatically manages test servers for the VS Code Test Explorer
 * @see https://playwright.dev/docs/test-configuration
 */

export default defineConfig({
  testDir: './tests/integration',
  outputDir: './test-results/artifacts',
  
  /* Run tests in files in parallel */
  fullyParallel: true,
  
  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,
  
  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,
  
  /* Configure workers based on environment */
  workers: process.env.CI ? 1 : 1, // Use 1 worker for VS Code to avoid conflicts
  
  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: [
    ['html', { outputFolder: './test-results/html-report', open: 'never' }],
    ['json', { outputFile: './test-results/results.json' }],
    ['line']
  ],
  
  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    /* Base URL to use in actions like `await page.goto('/')`. */
    baseURL: 'http://localhost:5889',

    /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
    trace: 'on-first-retry',

    /* Take screenshot on failure */
    screenshot: 'only-on-failure',

    /* Record video only on failure to save space */
    video: 'retain-on-failure',

    /* Global timeout for actions */
    actionTimeout: 15000,

    /* Global timeout for navigation */
    navigationTimeout: 30000,
  },

  /* Configure projects for major browsers */
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        headless: true, // Run in headless mode by default for VS Code
      },
    },
  ],

  /* Global setup to ensure servers are running */
  globalSetup: './playwright-global-setup.ts',

  /* Note: We don't stop servers in globalTeardown to allow debugging */
  /* Use 'just stop-test-servers' manually when done */
});
