import { test, expect } from '@playwright/test';

test('debug login error', async ({ page }) => {
  // Go to login page
  await page.goto('http://localhost:5174/login');
  
  // Fill invalid credentials
  await page.fill('input[type="email"]', 'invalid@test.com');
  await page.fill('input[type="password"]', 'wrongpassword');
  
  // Submit form
  await page.click('button[type="submit"]');
  
  // Wait a bit for the error to appear
  await page.waitForTimeout(2000);
  
  // Take a screenshot
  await page.screenshot({ path: 'debug-login-error.png' });
  
  // Get all text content on the page
  const pageContent = await page.textContent('body');
  console.log('Page content:', pageContent);
  
  // Check for any elements with error-related classes
  const errorElements = await page.locator('[class*="error"], [class*="destructive"], [class*="red"]').all();
  console.log('Error elements found:', errorElements.length);
  
  for (const element of errorElements) {
    const text = await element.textContent();
    const className = await element.getAttribute('class');
    console.log(`Error element: class="${className}", text="${text}"`);
  }
  
  // Check console logs
  const logs = [];
  page.on('console', msg => logs.push(msg.text()));
  
  console.log('Console logs:', logs);
});
