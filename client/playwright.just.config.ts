import { defineConfig, devices } from '@playwright/test';

/**
 * End-to-End Test Configuration
 * These tests run against the actual backend and frontend services
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: './tests/integration',
  outputDir: './test-results/artifacts',
  /* Run tests in files in parallel - disabled for stability */
  fullyParallel: false,
  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,
  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,
  /* Configure workers based on environment */
  workers: process.env.PLAYWRIGHT_WORKERS ? parseInt(process.env.PLAYWRIGHT_WORKERS) : (process.env.CI ? 1 : undefined),
  /* Global timeout for each test */
  timeout: 60000,
  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: [
    ['html', { outputFolder: './test-results/html-report', open: 'never' }],
    ['json', { outputFile: './test-results/results.json' }],
    ['line']
  ],
  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    /* Base URL to use in actions like `await page.goto('/')`. */
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5889',

    /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
    trace: 'on-first-retry',

    /* Take screenshot on failure and success */
    screenshot: 'on',

    /* Record video for all tests to enable review */
    video: 'on',

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
        headless: true, // Run in headless mode by default
      },
    },

    /* Test against mobile viewports. */
    {
      name: 'Mobile Chrome',
      use: {
        ...devices['Pixel 5'],
        headless: true, // Run in headless mode by default
      },
    },
  ],

  /* Run your local dev server before starting the tests */
  // webServer: {
  //   command: 'npm run start',
  //   url: 'http://127.0.0.1:3000',
  //   reuseExistingServer: !process.env.CI,
  // },
});
