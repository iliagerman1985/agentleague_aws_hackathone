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
  // Default workers for e2e runs
  workers: process.env.E2E_WORKERS ? Number(process.env.E2E_WORKERS) : (process.env.CI ? 1 : 1),

  /* Exclude real Cognito tests by default (use mock Cognito for VS Code) */
  grep: /^(?!.*@real-cognito).*$/,
  
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

    /* Take screenshot on all tests (success and failure) */
    screenshot: 'on',

    /* Record video on all tests (success and failure) */
    video: 'on',

    /* Global timeout for actions */
    actionTimeout: 15000,

    /* Global timeout for navigation */
    navigationTimeout: 30000,
  },

  /* Configure projects for major browsers */
  projects: [
    // E2E default: single worker unless overridden with E2E_WORKERS
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        headless: true,
      },
    },
    // Regression suite: runs selected tests with higher parallelism
    {
      name: 'regression',
      testDir: './tests/integration',
      grep: /@regression/,
      retries: process.env.CI ? 1 : 0,
      workers: process.env.REGRESSION_WORKERS ? Number(process.env.REGRESSION_WORKERS) : 10,
      use: {
        ...devices['Desktop Chrome'],
        headless: true,
      },
    },
  ],

  /* VS Code Extension Usage:
   * 1. Run 'just start-test-servers' in terminal first
   * 2. Use Test Explorer to run tests
   * 3. Run 'just stop-test-servers' when done
   *
   * This approach is more reliable and faster for repeated test runs.
   */
});
